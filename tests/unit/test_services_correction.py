"""Unit tests for correction service."""

import pytest

from src.core.models import Segment, TranscriptionResult
from src.services.correction import CorrectionService


@pytest.fixture
def correction_service():
    """Correction service fixture"""
    return CorrectionService(outlier_threshold=0.3)


@pytest.fixture
def sample_transcript():
    """Sample transcription result"""
    return TranscriptionResult(
        segments=[
            Segment(
                text="大家好",
                start_time=0.0,
                end_time=2.0,
                speaker="Speaker 0",
                confidence=0.95,
            ),
            Segment(
                text="你好",
                start_time=2.0,
                end_time=4.0,
                speaker="Speaker 1",
                confidence=0.92,
            ),
            Segment(
                text="今天讨论产品",
                start_time=4.0,
                end_time=7.0,
                speaker="Speaker 0",
                confidence=0.93,
            ),
            Segment(
                text="我同意",
                start_time=7.0,
                end_time=9.0,
                speaker="Speaker 1",
                confidence=0.94,
            ),
        ],
        full_text="大家好 你好 今天讨论产品 我同意",
        duration=9.0,
        language="zh-CN",
        provider="volcano",
    )


class TestCorrectionService:
    """CorrectionService 测试类"""

    @pytest.mark.asyncio
    async def test_correct_speakers_basic(self, correction_service, sample_transcript):
        """测试基本的说话人修正"""
        speaker_mapping = {"Speaker 0": "张三", "Speaker 1": "李四"}

        result = await correction_service.correct_speakers(sample_transcript, speaker_mapping)

        # 验证说话人已被修正
        assert result.segments[0].speaker == "张三"
        assert result.segments[1].speaker == "李四"
        assert result.segments[2].speaker == "张三"
        assert result.segments[3].speaker == "李四"

        # 验证其他属性保持不变
        assert result.segments[0].text == "大家好"
        assert result.duration == 9.0
        assert result.language == "zh-CN"

    @pytest.mark.asyncio
    async def test_correct_speakers_partial_mapping(self, correction_service, sample_transcript):
        """测试部分映射(某些说话人没有映射)"""
        speaker_mapping = {"Speaker 0": "张三"}  # 只映射 Speaker 0

        result = await correction_service.correct_speakers(sample_transcript, speaker_mapping)

        # Speaker 0 应该被映射
        assert result.segments[0].speaker == "张三"
        assert result.segments[2].speaker == "张三"

        # Speaker 1 保持原标签
        assert result.segments[1].speaker == "Speaker 1"
        assert result.segments[3].speaker == "Speaker 1"

    @pytest.mark.asyncio
    async def test_correct_speakers_empty_mapping(self, correction_service, sample_transcript):
        """测试空映射"""
        speaker_mapping = {}

        result = await correction_service.correct_speakers(sample_transcript, speaker_mapping)

        # 所有说话人应该保持原标签
        assert result.segments[0].speaker == "Speaker 0"
        assert result.segments[1].speaker == "Speaker 1"
        assert result.segments[2].speaker == "Speaker 0"
        assert result.segments[3].speaker == "Speaker 1"

    @pytest.mark.asyncio
    async def test_clean_outliers(self, correction_service):
        """测试清洗异常点"""
        # 创建包含异常说话人的转写
        transcript = TranscriptionResult(
            segments=[
                Segment(text="A", start_time=0.0, end_time=1.0, speaker="张三", confidence=0.95),
                Segment(text="B", start_time=1.0, end_time=2.0, speaker="张三", confidence=0.95),
                Segment(text="C", start_time=2.0, end_time=3.0, speaker="张三", confidence=0.95),
                Segment(text="D", start_time=3.0, end_time=4.0, speaker="张三", confidence=0.95),
                Segment(text="E", start_time=4.0, end_time=5.0, speaker="张三", confidence=0.95),
                Segment(text="F", start_time=5.0, end_time=6.0, speaker="李四", confidence=0.95),
                Segment(text="G", start_time=6.0, end_time=7.0, speaker="李四", confidence=0.95),
                Segment(
                    text="H", start_time=7.0, end_time=8.0, speaker="异常人", confidence=0.95
                ),  # 异常: 只出现 1 次,频率 12.5% < 30%
            ],
            full_text="A B C D E F G H",
            duration=8.0,
            language="zh-CN",
            provider="volcano",
        )

        speaker_mapping = {"张三": "张三", "李四": "李四", "异常人": "异常人"}
        result = await correction_service.correct_speakers(transcript, speaker_mapping)

        # 异常说话人应该被替换为最常见的说话人(张三)
        assert result.segments[7].speaker == "张三"

    @pytest.mark.asyncio
    async def test_clean_outliers_no_outliers(self, correction_service, sample_transcript):
        """测试没有异常点的情况"""
        speaker_mapping = {"Speaker 0": "张三", "Speaker 1": "李四"}

        result = await correction_service.correct_speakers(sample_transcript, speaker_mapping)

        # 所有说话人都应该保持映射后的标签
        speakers = [seg.speaker for seg in result.segments]
        assert speakers == ["张三", "李四", "张三", "李四"]

    def test_calculate_der_perfect_match(self, correction_service):
        """测试完全匹配的 DER"""
        transcript = TranscriptionResult(
            segments=[
                Segment(text="A", start_time=0.0, end_time=2.0, speaker="张三", confidence=0.95),
                Segment(text="B", start_time=2.0, end_time=4.0, speaker="李四", confidence=0.95),
            ],
            full_text="A B",
            duration=4.0,
            language="zh-CN",
            provider="volcano",
        )

        # 参考和假设完全相同
        der = correction_service.calculate_der(transcript, transcript)

        # DER 应该为 0(完全匹配)
        assert der == 0.0

    def test_calculate_der_complete_mismatch(self, correction_service):
        """测试完全不匹配的 DER"""
        reference = TranscriptionResult(
            segments=[
                Segment(text="A", start_time=0.0, end_time=2.0, speaker="张三", confidence=0.95),
                Segment(text="B", start_time=2.0, end_time=4.0, speaker="李四", confidence=0.95),
            ],
            full_text="A B",
            duration=4.0,
            language="zh-CN",
            provider="volcano",
        )

        hypothesis = TranscriptionResult(
            segments=[
                Segment(text="A", start_time=0.0, end_time=2.0, speaker="李四", confidence=0.95),
                Segment(text="B", start_time=2.0, end_time=4.0, speaker="张三", confidence=0.95),
            ],
            full_text="A B",
            duration=4.0,
            language="zh-CN",
            provider="volcano",
        )

        der = correction_service.calculate_der(reference, hypothesis)

        # DER 应该为 1.0(完全不匹配)
        assert der == 1.0

    def test_segments_overlap(self, correction_service):
        """测试片段重叠检测"""
        seg1 = Segment(text="A", start_time=0.0, end_time=2.0, speaker="张三", confidence=0.95)
        seg2 = Segment(text="B", start_time=1.0, end_time=3.0, speaker="李四", confidence=0.95)
        seg3 = Segment(text="C", start_time=3.0, end_time=5.0, speaker="张三", confidence=0.95)

        # seg1 和 seg2 重叠
        assert correction_service._segments_overlap(seg1, seg2) is True

        # seg1 和 seg3 不重叠
        assert correction_service._segments_overlap(seg1, seg3) is False

        # seg2 和 seg3 边界接触(不算重叠)
        assert correction_service._segments_overlap(seg2, seg3) is False

    def test_calculate_overlap(self, correction_service):
        """测试重叠时长计算"""
        seg1 = Segment(text="A", start_time=0.0, end_time=3.0, speaker="张三", confidence=0.95)
        seg2 = Segment(text="B", start_time=1.0, end_time=4.0, speaker="李四", confidence=0.95)
        seg3 = Segment(text="C", start_time=5.0, end_time=7.0, speaker="张三", confidence=0.95)

        # seg1 和 seg2 重叠 2 秒(1.0 到 3.0)
        overlap = correction_service._calculate_overlap(seg1, seg2)
        assert overlap == pytest.approx(2.0, rel=0.01)

        # seg1 和 seg3 不重叠
        overlap = correction_service._calculate_overlap(seg1, seg3)
        assert overlap == 0.0

    @pytest.mark.asyncio
    async def test_correct_speakers_empty_transcript(self, correction_service):
        """测试空转写"""
        empty_transcript = TranscriptionResult(
            segments=[],
            full_text="",
            duration=0.0,
            language="zh-CN",
            provider="volcano",
        )

        speaker_mapping = {"Speaker 0": "张三"}
        result = await correction_service.correct_speakers(empty_transcript, speaker_mapping)

        assert len(result.segments) == 0
        assert result.full_text == ""
