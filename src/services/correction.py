"""Correction service for fixing speaker labels in transcripts."""

import logging
from collections import Counter
from typing import Dict, List

from src.core.models import Segment, TranscriptionResult

logger = logging.getLogger(__name__)


class CorrectionService:
    """
    ASR 修正服务

    负责基于声纹聚类修正 ASR 的说话人标签
    """

    def __init__(self, outlier_threshold: float = 0.3):
        """
        初始化修正服务

        Args:
            outlier_threshold: 异常点阈值(0-1),低于此比例的标签被视为异常
        """
        self.outlier_threshold = outlier_threshold

    async def correct_speakers(
        self, transcript: TranscriptionResult, speaker_mapping: Dict[str, str]
    ) -> TranscriptionResult:
        """
        修正说话人标签

        流程:
        1. 应用声纹识别的映射
        2. 全局身份投票(可选)
        3. 检测异常点
        4. 清洗异常标签
        5. 计算修正前后的 DER(可选)
        6. 返回修正后的转写结果

        Args:
            transcript: 原始转写结果
            speaker_mapping: 说话人标签映射 {"Speaker 0": "张三", "Speaker 1": "李四"}

        Returns:
            TranscriptionResult: 修正后的转写结果
        """
        # 1. 应用说话人映射
        corrected_segments = []
        for segment in transcript.segments:
            new_speaker = speaker_mapping.get(segment.speaker, segment.speaker)
            corrected_segment = Segment(
                text=segment.text,
                start_time=segment.start_time,
                end_time=segment.end_time,
                speaker=new_speaker,
                confidence=segment.confidence,
            )
            corrected_segments.append(corrected_segment)

        # 2. 全局身份投票(检测并修正可能的错误映射)
        corrected_segments = self._apply_global_voting(corrected_segments)

        # 3. 检测并清洗异常点
        corrected_segments = self._clean_outliers(corrected_segments)

        # 4. 创建修正后的转写结果
        corrected_transcript = TranscriptionResult(
            segments=corrected_segments,
            full_text=" ".join(seg.text for seg in corrected_segments),
            duration=transcript.duration,
            language=transcript.language,
            provider=transcript.provider,
        )

        logger.info(
            f"Correction completed: {len(transcript.segments)} segments, "
            f"{len(set(seg.speaker for seg in corrected_segments))} unique speakers"
        )

        return corrected_transcript

    def _apply_global_voting(self, segments: List[Segment]) -> List[Segment]:
        """
        应用全局身份投票

        对于每个说话人,统计其最常见的标签,并将所有片段统一为该标签

        Args:
            segments: 片段列表

        Returns:
            List[Segment]: 投票后的片段列表
        """
        if not segments:
            return segments

        # 统计每个说话人的标签分布
        # 这里假设说话人标签已经通过声纹识别修正,不需要额外投票
        # 如果需要更复杂的投票逻辑,可以在这里实现

        return segments

    def _clean_outliers(self, segments: List[Segment]) -> List[Segment]:
        """
        清洗异常点

        检测出现频率过低的说话人标签,将其视为异常并修正

        Args:
            segments: 片段列表

        Returns:
            List[Segment]: 清洗后的片段列表
        """
        if not segments:
            return segments

        # 统计每个说话人的出现次数
        speaker_counts = Counter(seg.speaker for seg in segments if seg.speaker)

        if not speaker_counts:
            return segments

        total_segments = len(segments)
        outlier_speakers = set()

        # 识别异常说话人(出现频率低于阈值)
        for speaker, count in speaker_counts.items():
            frequency = count / total_segments
            if frequency < self.outlier_threshold:
                outlier_speakers.add(speaker)
                logger.debug(
                    f"Detected outlier speaker: {speaker} "
                    f"(frequency={frequency:.2%}, threshold={self.outlier_threshold:.2%})"
                )

        # 如果没有异常,直接返回
        if not outlier_speakers:
            return segments

        # 找到最常见的说话人作为默认替换
        most_common_speaker = speaker_counts.most_common(1)[0][0]

        # 替换异常说话人
        cleaned_segments = []
        for segment in segments:
            if segment.speaker in outlier_speakers:
                # 将异常说话人替换为最常见的说话人
                # 注意: 这是一个简化的策略,实际应用中可能需要更复杂的逻辑
                cleaned_segment = Segment(
                    text=segment.text,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    speaker=most_common_speaker,
                    confidence=segment.confidence,
                )
                cleaned_segments.append(cleaned_segment)
            else:
                cleaned_segments.append(segment)

        logger.info(
            f"Cleaned {len(outlier_speakers)} outlier speakers, "
            f"replaced with {most_common_speaker}"
        )

        return cleaned_segments

    def calculate_der(
        self, reference: TranscriptionResult, hypothesis: TranscriptionResult
    ) -> float:
        """
        计算 DER (Diarization Error Rate)

        DER = (False Alarm + Missed Detection + Speaker Error) / Total Reference Time

        注: 这是一个简化的实现,实际 DER 计算需要更复杂的对齐算法

        Args:
            reference: 参考转写(真实标签)
            hypothesis: 假设转写(预测标签)

        Returns:
            float: DER 值(0-1)
        """
        if not reference.segments or not hypothesis.segments:
            return 1.0

        # 简化实现: 比较相同时间段内的说话人标签
        total_time = reference.duration
        error_time = 0.0

        # 为每个参考片段找到对应的假设片段
        for ref_seg in reference.segments:
            # 找到时间重叠的假设片段
            overlapping_hyp = [
                hyp_seg
                for hyp_seg in hypothesis.segments
                if self._segments_overlap(ref_seg, hyp_seg)
            ]

            if not overlapping_hyp:
                # Missed Detection
                error_time += ref_seg.end_time - ref_seg.start_time
            else:
                # 检查说话人是否匹配
                for hyp_seg in overlapping_hyp:
                    if ref_seg.speaker != hyp_seg.speaker:
                        # Speaker Error
                        overlap_duration = self._calculate_overlap(ref_seg, hyp_seg)
                        error_time += overlap_duration

        der = error_time / total_time if total_time > 0 else 1.0
        return min(der, 1.0)  # DER 不应超过 1.0

    def _segments_overlap(self, seg1: Segment, seg2: Segment) -> bool:
        """
        检查两个片段是否有时间重叠

        Args:
            seg1: 片段 1
            seg2: 片段 2

        Returns:
            bool: 是否重叠
        """
        return not (seg1.end_time <= seg2.start_time or seg2.end_time <= seg1.start_time)

    def _calculate_overlap(self, seg1: Segment, seg2: Segment) -> float:
        """
        计算两个片段的重叠时长

        Args:
            seg1: 片段 1
            seg2: 片段 2

        Returns:
            float: 重叠时长(秒)
        """
        overlap_start = max(seg1.start_time, seg2.start_time)
        overlap_end = min(seg1.end_time, seg2.end_time)
        return max(0.0, overlap_end - overlap_start)
