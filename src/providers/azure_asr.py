"""Azure Speech Service ASR Provider Implementation."""

import asyncio
from typing import List, Optional

import httpx

from src.config.models import AzureConfig
from src.core.exceptions import ASRError, AudioFormatError, AuthenticationError, RateLimitError
from src.core.models import ASRLanguage, HotwordSet, Segment, TranscriptionResult
from src.core.providers import ASRProvider
from src.utils.audio import AudioProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AzureASR(ASRProvider):
    """Azure Speech Service ASR 提供商实现"""

    def __init__(self, config: AzureConfig):
        """
        初始化 Azure ASR 提供商

        Args:
            config: Azure 配置
        """
        self.config = config
        self.current_key_index = 0
        self.audio_processor = AudioProcessor()

    async def transcribe(
        self,
        audio_url: str,
        asr_language: ASRLanguage = ASRLanguage.ZH_EN,
        hotword_set: Optional[HotwordSet] = None,
        **kwargs,
    ) -> TranscriptionResult:
        """
        转写音频

        Args:
            audio_url: 音频文件 URL
            asr_language: ASR 识别语言
            hotword_set: 热词集
            **kwargs: 其他提供商特定参数

        Returns:
            TranscriptionResult: 转写结果

        Raises:
            ASRError: ASR 相关错误
            AudioFormatError: 音频格式错误
        """
        try:
            # 下载音频文件
            audio_data = await self._download_audio(audio_url)

            # 保存到临时文件
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                temp_input_path = temp_file.name
                temp_file.write(audio_data)
            
            try:
                # 转换为 WAV 格式（Azure ASR 需要 WAV）
                logger.info(f"Converting audio to WAV format for Azure ASR")
                temp_wav_path = await self.audio_processor.convert_format(temp_input_path)
                
                # 读取转换后的 WAV 数据
                with open(temp_wav_path, 'rb') as f:
                    audio_data = f.read()
                
                # 获取音频时长
                duration = self.audio_processor.get_duration(temp_wav_path)
                logger.info(f"Azure ASR audio duration: {duration}s")
                
                # 清理 WAV 临时文件
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
            finally:
                # 清理输入临时文件
                try:
                    os.unlink(temp_input_path)
                except:
                    pass

            if duration > 7200:  # 2 小时
                # 切分音频并分别转写
                segments = await self._transcribe_long_audio(
                    audio_data, asr_language, hotword_set, **kwargs
                )
            else:
                # 直接转写
                segments = await self._transcribe_audio(
                    audio_data, asr_language, hotword_set, **kwargs
                )

            # 构建完整文本
            full_text = " ".join(seg.text for seg in segments)

            return TranscriptionResult(
                segments=segments,
                full_text=full_text,
                duration=duration,
                language=self._map_language(asr_language),
                provider="azure",
            )

        except (ASRError, AudioFormatError):
            raise
        except Exception as e:
            logger.error(f"Azure ASR transcription failed: {e}")
            raise ASRError(f"Azure ASR transcription failed: {e}")

    async def _transcribe_long_audio(
        self,
        audio_data: bytes,
        asr_language: ASRLanguage,
        hotword_set: Optional[HotwordSet],
        **kwargs,
    ) -> List[Segment]:
        """
        转写超过 2 小时的音频(自动切分)

        Args:
            audio_data: 音频数据
            asr_language: ASR 识别语言
            hotword_set: 热词集
            **kwargs: 其他参数

        Returns:
            List[Segment]: 转写片段列表
        """
        # 切分音频为 2 小时的片段
        chunk_duration = 7200  # 2 小时
        total_duration = self.audio_processor.get_duration(audio_data)
        chunks = []

        current_time = 0.0
        while current_time < total_duration:
            end_time = min(current_time + chunk_duration, total_duration)
            chunk = self.audio_processor.extract_segment(audio_data, current_time, end_time)
            chunks.append((chunk, current_time))
            current_time = end_time

        logger.info(f"Azure ASR split audio into {len(chunks)} chunks")

        # 并发转写所有片段
        tasks = [
            self._transcribe_audio(chunk, asr_language, hotword_set, offset=offset, **kwargs)
            for chunk, offset in chunks
        ]
        results = await asyncio.gather(*tasks)

        # 合并结果
        all_segments = []
        for segments in results:
            all_segments.extend(segments)

        return all_segments

    async def _transcribe_audio(
        self,
        audio_data: bytes,
        asr_language: ASRLanguage,
        hotword_set: Optional[HotwordSet],
        offset: float = 0.0,
        **kwargs,
    ) -> List[Segment]:
        """
        转写单个音频片段

        Args:
            audio_data: 音频数据
            asr_language: ASR 识别语言
            hotword_set: 热词集
            offset: 时间偏移(秒)
            **kwargs: 其他参数

        Returns:
            List[Segment]: 转写片段列表

        Raises:
            ASRError: 转写失败
        """
        # 构建 API 端点
        endpoint = self._get_endpoint()
        url = f"{endpoint}/speechtotext/transcriptions:transcribe?api-version=2025-10-15"

        # 构建请求
        locales = self._map_language_to_locales(asr_language)
        definition = {"locales": locales}

        # 启用说话人分离
        if kwargs.get("enable_diarization", True):
            definition["diarization"] = {"enabled": True, "maxSpeakers": kwargs.get("max_speakers", 10)}

        # 添加短语列表(热词)
        if hotword_set and hotword_set.provider == "azure":
            # Azure 使用短语列表而不是热词库 ID
            # 这里假设 provider_resource_id 包含短语列表(逗号分隔)
            phrases = hotword_set.provider_resource_id.split(",")
            definition["phraseList"] = {"phrases": phrases}

        # 准备 multipart/form-data
        import json
        files = {
            "audio": ("audio.wav", audio_data, "audio/wav"),
            "definition": (None, json.dumps(definition), "application/json"),
        }

        # 发送请求(带重试和密钥轮换)
        for attempt in range(self.config.max_retries):
            try:
                subscription_key = self._get_current_key()
                headers = {"Ocp-Apim-Subscription-Key": subscription_key}

                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    response = await client.post(url, files=files, headers=headers)

                    if response.status_code == 200:
                        result = response.json()
                        return self._parse_result(result, offset)
                    elif response.status_code == 401:
                        # 认证失败,尝试下一个密钥
                        logger.warning(f"Azure ASR authentication failed, rotating key")
                        self._rotate_key()
                        if attempt == self.config.max_retries - 1:
                            raise AuthenticationError("Azure ASR authentication failed with all keys")
                    elif response.status_code == 429:
                        # 速率限制,指数退避
                        wait_time = 2 ** attempt
                        logger.warning(f"Azure ASR rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        if attempt == self.config.max_retries - 1:
                            raise RateLimitError("Azure ASR rate limit exceeded")
                    else:
                        # 记录详细的错误信息
                        logger.error(f"Azure ASR error: {response.status_code}")
                        logger.error(f"Response body: {response.text}")
                        response.raise_for_status()

            except httpx.HTTPError as e:
                logger.error(f"Azure ASR HTTP error: {e}")
                if attempt == self.config.max_retries - 1:
                    raise ASRError(f"Azure ASR HTTP error: {e}")
                await asyncio.sleep(2 ** attempt)

        raise ASRError("Azure ASR transcription failed after all retries")

    def _parse_result(self, result: dict, offset: float = 0.0) -> List[Segment]:
        """
        解析 Azure API 响应为 Segment 列表

        Args:
            result: API 响应
            offset: 时间偏移(秒)

        Returns:
            List[Segment]: 转写片段列表
        """
        phrases = result.get("phrases", [])
        segments = []

        for phrase in phrases:
            # 调整时间戳(加上偏移)
            start_time = phrase.get("offsetMilliseconds", 0) / 1000.0 + offset
            end_time = start_time + phrase.get("durationMilliseconds", 0) / 1000.0

            # 获取说话人信息
            speaker = phrase.get("speaker", "unknown")
            if isinstance(speaker, int):
                speaker = f"Speaker {speaker}"

            segment = Segment(
                text=phrase.get("text", ""),
                start_time=start_time,
                end_time=end_time,
                speaker=speaker,
                confidence=phrase.get("confidence"),
            )
            segments.append(segment)

        return segments

    async def _download_audio(self, audio_url: str) -> bytes:
        """
        下载音频文件

        Args:
            audio_url: 音频文件 URL

        Returns:
            bytes: 音频数据

        Raises:
            ASRError: 下载失败
        """
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.get(audio_url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as e:
            logger.error(f"Azure ASR audio download failed: {e}")
            raise ASRError(f"Azure ASR audio download failed: {e}")

    def _get_endpoint(self) -> str:
        """
        获取 API 端点

        Returns:
            str: API 端点 URL
        """
        if self.config.endpoint:
            return self.config.endpoint
        return f"https://{self.config.region}.api.cognitive.microsoft.com"

    def _get_current_key(self) -> str:
        """
        获取当前订阅密钥

        Returns:
            str: 订阅密钥
        """
        return self.config.subscription_keys[self.current_key_index]

    def _rotate_key(self) -> None:
        """轮换到下一个订阅密钥"""
        self.current_key_index = (self.current_key_index + 1) % len(
            self.config.subscription_keys
        )
        logger.info(f"Azure ASR rotated to key index {self.current_key_index}")

    def _map_language(self, asr_language: ASRLanguage) -> str:
        """
        映射 ASRLanguage 到 Azure 语言代码

        Args:
            asr_language: ASR 语言枚举

        Returns:
            str: Azure 语言代码
        """
        mapping = {
            ASRLanguage.ZH_CN: "zh-CN",
            ASRLanguage.EN_US: "en-US",
            ASRLanguage.ZH_EN: "zh-CN",  # 中英混合使用 locales 数组
            ASRLanguage.JA_JP: "ja-JP",
            ASRLanguage.KO_KR: "ko-KR",
        }
        return mapping.get(asr_language, "zh-CN")

    def _map_language_to_locales(self, asr_language: ASRLanguage) -> List[str]:
        """
        映射 ASRLanguage 到 Azure locales 数组

        中英混合使用 locales 数组 ["zh-CN", "en-US"]

        Args:
            asr_language: ASR 语言枚举

        Returns:
            List[str]: Azure locales 数组
        """
        if asr_language == ASRLanguage.ZH_EN:
            return ["zh-CN", "en-US"]
        else:
            return [self._map_language(asr_language)]

    async def get_task_status(self, task_id: str) -> dict:
        """
        查询转写任务状态

        注: Azure 快速转写 API 是同步的,不支持异步查询

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务状态信息
        """
        raise NotImplementedError("Azure Fast Transcription API does not support async status query")

    def get_provider_name(self) -> str:
        """
        获取提供商名称

        Returns:
            str: 提供商名称 (azure)
        """
        return "azure"
