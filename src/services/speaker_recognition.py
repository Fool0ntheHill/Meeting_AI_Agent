"""Speaker recognition service for identifying speakers in audio."""

import logging
from collections import defaultdict
from typing import Dict, List, Optional

from src.core.exceptions import VoiceprintError
from src.core.models import SpeakerIdentity, TranscriptionResult
from src.core.providers import VoiceprintProvider
from src.utils.audio import AudioProcessor
from src.utils.storage import StorageClient

logger = logging.getLogger(__name__)


class SpeakerRecognitionService:
    """
    说话人识别服务

    负责说话人识别,提取音频样本并调用声纹识别
    """

    def __init__(
        self,
        voiceprint_provider: VoiceprintProvider,
        audio_processor: AudioProcessor,
        storage_client: StorageClient,
        sample_duration_min: float = 3.0,
        sample_duration_max: float = 6.0,
    ):
        """
        初始化说话人识别服务

        Args:
            voiceprint_provider: 声纹识别提供商
            audio_processor: 音频处理器
            storage_client: 存储客户端
            sample_duration_min: 最小样本时长(秒)
            sample_duration_max: 最大样本时长(秒)
        """
        self.voiceprint = voiceprint_provider
        self.audio_processor = audio_processor
        self.storage = storage_client
        self.sample_duration_min = sample_duration_min
        self.sample_duration_max = sample_duration_max

    async def recognize_speakers(
        self,
        transcript: TranscriptionResult,
        audio_path: str,
        known_speakers: Optional[List[SpeakerIdentity]] = None,
    ) -> Dict[str, str]:
        """
        识别说话人

        流程:
        1. 使用本地音频文件路径
        2. 为每个唯一 speaker 标签提取样本 (3-6秒)
        3. 调用声纹识别 API
        4. 应用分差挽救机制(由提供商处理)
        5. 返回 speaker 标签到真实姓名的映射

        Args:
            transcript: 转写结果
            audio_path: 本地音频文件路径
            known_speakers: 已知说话人列表(用于 1:N 搜索)

        Returns:
            Dict[str, str]: speaker 标签到真实姓名的映射
                例如: {"Speaker 0": "张三", "Speaker 1": "李四"}

        Raises:
            VoiceprintError: 声纹识别失败
        """
        try:
            # 1. 转换音频格式为 WAV (确保 pydub 可以处理)
            logger.info(f"Converting audio format to WAV: {audio_path}")
            try:
                converted_audio_path = await self.audio_processor.convert_format(audio_path)
                logger.info(f"Audio converted successfully: {converted_audio_path}")
            except Exception as e:
                logger.warning(f"Audio format conversion failed: {e}, using original file")
                converted_audio_path = audio_path
            
            try:
                # 2. 提取每个说话人的音频样本
                speaker_samples = await self._extract_speaker_samples(
                    transcript, converted_audio_path
                )

                if not speaker_samples:
                    logger.warning("No speaker samples extracted, returning empty mapping")
                    return {}

                # 3. 调用声纹识别
                logger.info(f"Recognizing {len(speaker_samples)} speakers")
                speaker_mapping = await self.voiceprint.identify_speakers(
                    transcript=transcript,
                    audio_url=converted_audio_path,  # 使用转换后的路径
                    known_speakers=known_speakers,
                )

                logger.info(f"Speaker recognition completed: {speaker_mapping}")
                return speaker_mapping

            finally:
                # 清理转换后的临时文件 (如果与原文件不同)
                if converted_audio_path != audio_path:
                    import os
                    try:
                        if os.path.exists(converted_audio_path):
                            os.remove(converted_audio_path)
                            logger.debug(f"Cleaned up converted audio file: {converted_audio_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup converted file {converted_audio_path}: {e}")

        except Exception as e:
            logger.error(f"Speaker recognition failed: {e}")
            raise VoiceprintError(
                f"Speaker recognition failed: {e}",
                provider="speaker_recognition_service",
            )

    async def _extract_speaker_samples(
        self, transcript: TranscriptionResult, audio_path: str
    ) -> Dict[str, bytes]:
        """
        为每个唯一说话人提取音频样本

        Args:
            transcript: 转写结果
            audio_path: 音频文件路径

        Returns:
            Dict[str, bytes]: speaker 标签到音频样本的映射
        """
        # 1. 收集每个说话人的所有片段
        speaker_segments = defaultdict(list)
        for segment in transcript.segments:
            if segment.speaker:
                speaker_segments[segment.speaker].append(segment)

        # 2. 为每个说话人选择最佳样本
        speaker_samples = {}
        for speaker, segments in speaker_segments.items():
            # 选择最佳片段(优先选择时长在 3-6 秒之间的片段)
            best_segment = self._select_best_segment(segments)

            if best_segment:
                # 提取音频样本
                try:
                    sample = await self.audio_processor.extract_segment(
                        audio_path=audio_path,
                        start_time=best_segment.start_time,
                        end_time=best_segment.end_time,
                    )
                    speaker_samples[speaker] = sample
                    logger.debug(
                        f"Extracted sample for {speaker}: "
                        f"{best_segment.start_time:.2f}s - {best_segment.end_time:.2f}s"
                    )
                except Exception as e:
                    logger.warning(f"Failed to extract sample for {speaker}: {e}")

        return speaker_samples

    def _select_best_segment(self, segments: List) -> Optional[object]:
        """
        选择最佳音频片段

        优先级:
        1. 时长在 3-6 秒之间的片段
        2. 置信度最高的片段
        3. 时长最长的片段

        Args:
            segments: 片段列表

        Returns:
            最佳片段,如果没有合适的片段则返回 None
        """
        if not segments:
            return None

        # 筛选时长在 3-6 秒之间的片段
        ideal_segments = [
            seg
            for seg in segments
            if self.sample_duration_min
            <= (seg.end_time - seg.start_time)
            <= self.sample_duration_max
        ]

        if ideal_segments:
            # 选择置信度最高的
            return max(ideal_segments, key=lambda seg: seg.confidence or 0.0)

        # 如果没有理想时长的片段,选择时长最接近 4.5 秒的片段
        target_duration = (self.sample_duration_min + self.sample_duration_max) / 2
        return min(
            segments,
            key=lambda seg: abs((seg.end_time - seg.start_time) - target_duration),
        )

    async def get_speaker_statistics(
        self, transcript: TranscriptionResult
    ) -> Dict[str, Dict[str, float]]:
        """
        获取说话人统计信息

        Args:
            transcript: 转写结果

        Returns:
            Dict[str, Dict[str, float]]: 说话人统计信息
                例如: {
                    "Speaker 0": {
                        "total_duration": 120.5,
                        "segment_count": 15,
                        "avg_confidence": 0.95
                    }
                }
        """
        stats = defaultdict(lambda: {"total_duration": 0.0, "segment_count": 0, "confidences": []})

        for segment in transcript.segments:
            if segment.speaker:
                speaker = segment.speaker
                duration = segment.end_time - segment.start_time
                stats[speaker]["total_duration"] += duration
                stats[speaker]["segment_count"] += 1
                if segment.confidence is not None:
                    stats[speaker]["confidences"].append(segment.confidence)

        # 计算平均置信度
        result = {}
        for speaker, data in stats.items():
            confidences = data["confidences"]
            result[speaker] = {
                "total_duration": data["total_duration"],
                "segment_count": data["segment_count"],
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            }

        return result
