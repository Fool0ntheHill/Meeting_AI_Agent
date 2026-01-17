"""Transcription service for audio processing."""

import logging
from typing import Dict, List, Optional

from src.core.exceptions import ASRError, AudioFormatError, StorageError
from src.core.models import ASRLanguage, HotwordSet, TranscriptionResult
from src.core.providers import ASRProvider
from src.utils.audio import AudioProcessor
from src.utils.storage import StorageClient

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    转写服务

    负责音频转写,实现双轨 ASR 策略和自动降级
    """

    def __init__(
        self,
        primary_asr: ASRProvider,
        fallback_asr: ASRProvider,
        storage_client: StorageClient,
        audio_processor: AudioProcessor,
    ):
        """
        初始化转写服务

        Args:
            primary_asr: 主 ASR 提供商(火山引擎)
            fallback_asr: 备用 ASR 提供商(Azure)
            storage_client: 存储客户端
            audio_processor: 音频处理器
        """
        self.primary_asr = primary_asr
        self.fallback_asr = fallback_asr
        self.storage = storage_client
        self.audio_processor = audio_processor

    async def transcribe(
        self,
        audio_files: List[str],
        file_order: Optional[List[int]] = None,
        asr_language: ASRLanguage = ASRLanguage.ZH_EN,
        hotword_set: Optional[HotwordSet] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **kwargs,
    ) -> tuple[TranscriptionResult, str, str]:
        """
        转写音频文件

        流程:
        1. 如果多个文件,按 file_order 拼接
        2. 上传到 TOS
        3. 获取适用的热词 (user > tenant > global)
        4. 尝试主 ASR (火山引擎)
        5. 如果失败,降级到备用 ASR (Azure)
        6. 返回标准化结果、音频 URL 和本地音频路径

        Args:
            audio_files: 音频文件路径列表
            file_order: 文件顺序(索引列表),如果为 None 则按原顺序
            asr_language: ASR 识别语言
            hotword_set: 热词集
            user_id: 用户 ID
            tenant_id: 租户 ID
            **kwargs: 其他参数

        Returns:
            tuple[TranscriptionResult, str, str]: (转写结果, 音频 URL, 本地音频路径)

        Raises:
            ASRError: ASR 转写失败
            AudioFormatError: 音频格式错误
            StorageError: 存储操作失败
        """
        try:
            # 1. 处理音频文件 (拼接或使用单个文件)
            local_audio_path, audio_url = await self._prepare_audio(audio_files, file_order)

            # 2. 尝试主 ASR (火山引擎)
            try:
                logger.info(
                    f"Attempting primary ASR ({self.primary_asr.get_provider_name()}) "
                    f"for audio: {audio_url}"
                )
                result = await self.primary_asr.transcribe(
                    audio_url=audio_url,
                    asr_language=asr_language,
                    hotword_set=hotword_set,
                    **kwargs,
                )
                logger.info(
                    f"Primary ASR succeeded: {len(result.segments)} segments, "
                    f"duration={result.duration:.2f}s"
                )
                return result, audio_url, local_audio_path

            except ASRError as e:
                # 主 ASR 失败,降级到备用 ASR
                logger.warning(
                    f"Primary ASR failed: {e}, falling back to "
                    f"{self.fallback_asr.get_provider_name()}"
                )

                # 3. 降级到备用 ASR (Azure)
                result = await self.fallback_asr.transcribe(
                    audio_url=audio_url,
                    asr_language=asr_language,
                    hotword_set=hotword_set,
                    **kwargs,
                )
                logger.info(
                    f"Fallback ASR succeeded: {len(result.segments)} segments, "
                    f"duration={result.duration:.2f}s"
                )
                return result, audio_url, local_audio_path

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise ASRError(f"Transcription failed: {e}", provider="transcription_service")

    async def _prepare_audio(
        self, audio_files: List[str], file_order: Optional[List[int]] = None
    ) -> tuple[str, str]:
        """
        准备音频文件(拼接并上传)

        Args:
            audio_files: 音频文件路径列表
            file_order: 文件顺序

        Returns:
            tuple[str, str]: (本地音频路径, TOS 预签名 URL)

        Raises:
            AudioFormatError: 音频处理失败
            StorageError: 上传失败
        """
        # 如果只有一个文件,直接上传
        if len(audio_files) == 1:
            audio_url = await self._upload_audio(audio_files[0])
            return audio_files[0], audio_url

        # 多个文件,需要拼接
        # 1. 按 file_order 排序
        if file_order is None:
            file_order = list(range(len(audio_files)))

        if len(file_order) != len(audio_files):
            raise AudioFormatError(
                f"file_order length ({len(file_order)}) does not match "
                f"audio_files length ({len(audio_files)})"
            )

        # 按顺序排列文件
        ordered_files = [audio_files[i] for i in file_order]

        # 2. 拼接音频
        logger.info(f"Concatenating {len(ordered_files)} audio files")
        concatenated_path, offsets = await self.audio_processor.concatenate_audio(
            ordered_files
        )

        # 3. 上传拼接后的音频
        # 注意: 不要在这里删除 concatenated_path,因为说话人识别需要使用它
        audio_url = await self._upload_audio(concatenated_path)
        return concatenated_path, audio_url

    async def _upload_audio(self, local_path: str) -> str:
        """
        上传音频到 TOS 并生成预签名 URL

        Args:
            local_path: 本地文件路径

        Returns:
            str: TOS 预签名 URL (24小时有效期)

        Raises:
            StorageError: 上传失败
        """
        import os
        from datetime import datetime

        # 生成对象键
        filename = os.path.basename(local_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_key = f"audio/{timestamp}_{filename}"

        # 上传
        logger.info(f"Uploading audio to TOS: {object_key}")
        audio_url = await self.storage.upload_file(
            local_path=local_path, object_key=object_key, content_type="audio/wav"
        )

        # 生成预签名 URL (24小时有效期)
        # 私有桶需要预签名 URL 才能被外部服务(ASR)访问
        presigned_url = await self.storage.generate_presigned_url(
            object_key=object_key,
            expires_in=86400,  # 24 hours
        )

        logger.info(f"Audio uploaded successfully, presigned URL generated: {presigned_url[:100]}...")
        return presigned_url

    async def get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频时长

        Args:
            audio_path: 音频文件路径

        Returns:
            float: 时长(秒)

        Raises:
            AudioFormatError: 获取失败
        """
        return self.audio_processor.get_duration(audio_path)
