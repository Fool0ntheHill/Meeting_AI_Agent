"""Unit tests for speaker recognition service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import Segment, SpeakerIdentity, TranscriptionResult
from src.services.speaker_recognition import SpeakerRecognitionService


@pytest.fixture
def mock_voiceprint():
    """Mock voiceprint provider"""
    provider = MagicMock()
    provider.identify_speakers = AsyncMock(
        return_value={"Speaker 0": "张三", "Speaker 1": "李四"}
    )
    return provider


@pytest.fixture
def mock_audio_processor():
    """Mock audio processor"""
    processor = MagicMock()
    processor.extract_segment = AsyncMock(return_value=b"audio_sample_data")
    return processor


@pytest.fixture
def mock_storage():
    """Mock storage client"""
    storage = MagicMock()
    storage.download_file = AsyncMock(return_value="/tmp/audio.wav")
    storage.cleanup_temp_files = AsyncMock()
    return storage


@pytest.fixture
def speaker_recognition_service(mock_voiceprint, mock_audio_processor, mock_storage):
    """Speaker recognition service fixture"""
    return SpeakerRecognitionService(
        voiceprint_provider=mock_voiceprint,
        audio_processor=mock_audio_processor,
        storage_client=mock_storage,
        sample_duration_min=3.0,
        sample_duration_max=6.0,
    )


@pytest.fixture
def sample_transcript():
    """Sample transcription result with multiple speakers"""
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
                text="你好,我是李四",
                start_time=2.0,
                end_time=5.5,
                speaker="Speaker 1",
                confidence=0.92,
            ),
            Segment(
                text="今天我们讨论产品规划",
                start_time=5.5,
                end_time=9.0,
                speaker="Speaker 0",
                confidence=0.93,
            ),
            Segment(
                text="我认为应该优先考虑用户反馈",
                start_time=9.0,
                end_time=13.0,
                speaker="Speaker 1",
                confidence=0.94,
            ),
        ],
        full_text="大家好 你好,我是李四 今天我们讨论产品规划 我认为应该优先考虑用户反馈",
        duration=13.0,
        language="zh-CN",
        provider="volcano",
    )


class TestSpeakerRecognitionService:
    """SpeakerRecognitionService 测试类"""

    @pytest.mark.asyncio
    async def test_recognize_speakers_success(
        self, speaker_recognition_service, sample_transcript, mock_voiceprint, mock_audio_processor
    ):
        """测试成功识别说话人"""
        # Mock convert_format to return the same path
        mock_audio_processor.convert_format = AsyncMock(return_value="/tmp/audio.wav")
        
        result = await speaker_recognition_service.recognize_speakers(
            transcript=sample_transcript,
            audio_path="/tmp/audio.wav",
        )

        assert result == {"Speaker 0": "张三", "Speaker 1": "李四"}
        mock_voiceprint.identify_speakers.assert_called_once()

    @pytest.mark.asyncio
    async def test_recognize_speakers_with_known_speakers(
        self, speaker_recognition_service, sample_transcript, mock_voiceprint, mock_audio_processor
    ):
        """测试使用已知说话人列表识别"""
        # Mock convert_format to return the same path
        mock_audio_processor.convert_format = AsyncMock(return_value="/tmp/audio.wav")
        
        known_speakers = [
            SpeakerIdentity(
                speaker_id="spk_001", name="张三", confidence=0.95, metadata={"voiceprint_id": "vp_001"}
            ),
            SpeakerIdentity(
                speaker_id="spk_002", name="李四", confidence=0.92, metadata={"voiceprint_id": "vp_002"}
            ),
        ]

        result = await speaker_recognition_service.recognize_speakers(
            transcript=sample_transcript,
            audio_path="/tmp/audio.wav",
            known_speakers=known_speakers,
        )

        assert result == {"Speaker 0": "张三", "Speaker 1": "李四"}
        call_kwargs = mock_voiceprint.identify_speakers.call_args[1]
        assert call_kwargs["known_speakers"] == known_speakers

    @pytest.mark.asyncio
    async def test_recognize_speakers_cleanup_temp_files(
        self, speaker_recognition_service, sample_transcript, mock_audio_processor
    ):
        """测试临时文件清理 - 转换后的文件会被清理"""
        # Mock convert_format to return a different path (simulating conversion)
        mock_audio_processor.convert_format = AsyncMock(return_value="/tmp/converted_audio.wav")
        
        with patch("os.path.exists", return_value=True), \
             patch("os.remove") as mock_remove:
            await speaker_recognition_service.recognize_speakers(
                transcript=sample_transcript,
                audio_path="/tmp/audio.wav",
            )

            # 验证转换后的临时文件被清理
            mock_remove.assert_called_once_with("/tmp/converted_audio.wav")

    @pytest.mark.asyncio
    async def test_recognize_speakers_empty_transcript(
        self, speaker_recognition_service, mock_voiceprint, mock_audio_processor
    ):
        """测试空转写结果"""
        # Mock convert_format to return the same path
        mock_audio_processor.convert_format = AsyncMock(return_value="/tmp/audio.wav")
        
        empty_transcript = TranscriptionResult(
            segments=[],
            full_text="",
            duration=0.0,
            language="zh-CN",
            provider="volcano",
        )

        result = await speaker_recognition_service.recognize_speakers(
            transcript=empty_transcript,
            audio_path="/tmp/audio.wav",
        )

        # 应该返回空映射
        assert result == {}

    @pytest.mark.asyncio
    async def test_extract_speaker_samples(
        self, speaker_recognition_service, sample_transcript, mock_audio_processor
    ):
        """测试提取说话人样本"""
        samples = await speaker_recognition_service._extract_speaker_samples(
            transcript=sample_transcript,
            audio_path="/tmp/audio.wav",
        )

        # 应该为两个说话人提取样本
        assert len(samples) == 2
        assert "Speaker 0" in samples
        assert "Speaker 1" in samples
        assert samples["Speaker 0"] == b"audio_sample_data"
        assert samples["Speaker 1"] == b"audio_sample_data"

        # 验证提取了正确的片段
        assert mock_audio_processor.extract_segment.call_count == 2

    def test_select_best_segment_ideal_duration(self, speaker_recognition_service):
        """测试选择理想时长的片段"""
        segments = [
            Segment(
                text="短片段",
                start_time=0.0,
                end_time=1.0,
                speaker="Speaker 0",
                confidence=0.95,
            ),
            Segment(
                text="理想时长片段",
                start_time=1.0,
                end_time=5.0,  # 4秒,在 3-6 秒之间
                speaker="Speaker 0",
                confidence=0.90,
            ),
            Segment(
                text="另一个理想片段",
                start_time=5.0,
                end_time=10.5,  # 5.5秒,在 3-6 秒之间
                speaker="Speaker 0",
                confidence=0.92,
            ),
        ]

        best = speaker_recognition_service._select_best_segment(segments)

        # 应该选择置信度最高的理想时长片段
        assert best.start_time == 5.0
        assert best.end_time == 10.5
        assert best.confidence == 0.92

    def test_select_best_segment_no_ideal_duration(self, speaker_recognition_service):
        """测试没有理想时长的片段时选择最接近的"""
        segments = [
            Segment(
                text="短片段",
                start_time=0.0,
                end_time=1.0,
                speaker="Speaker 0",
                confidence=0.95,
            ),
            Segment(
                text="长片段",
                start_time=1.0,
                end_time=10.0,  # 9秒,超过最大时长
                speaker="Speaker 0",
                confidence=0.90,
            ),
        ]

        best = speaker_recognition_service._select_best_segment(segments)

        # 应该选择时长最接近 4.5 秒的片段
        # 1秒距离 4.5 秒差 3.5,9秒距离 4.5 秒差 4.5
        # 所以应该选择 1 秒的片段
        assert best.start_time == 0.0
        assert best.end_time == 1.0

    def test_select_best_segment_empty_list(self, speaker_recognition_service):
        """测试空片段列表"""
        best = speaker_recognition_service._select_best_segment([])
        assert best is None

    @pytest.mark.asyncio
    async def test_get_speaker_statistics(self, speaker_recognition_service, sample_transcript):
        """测试获取说话人统计信息"""
        stats = await speaker_recognition_service.get_speaker_statistics(sample_transcript)

        assert len(stats) == 2

        # Speaker 0: 2 个片段,总时长 5.5 秒
        assert stats["Speaker 0"]["segment_count"] == 2
        assert stats["Speaker 0"]["total_duration"] == pytest.approx(5.5, rel=0.01)
        assert stats["Speaker 0"]["avg_confidence"] == pytest.approx(0.94, rel=0.01)

        # Speaker 1: 2 个片段,总时长 7.5 秒
        assert stats["Speaker 1"]["segment_count"] == 2
        assert stats["Speaker 1"]["total_duration"] == pytest.approx(7.5, rel=0.01)
        assert stats["Speaker 1"]["avg_confidence"] == pytest.approx(0.93, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_speaker_statistics_no_confidence(self, speaker_recognition_service):
        """测试没有置信度的片段"""
        transcript = TranscriptionResult(
            segments=[
                Segment(
                    text="测试",
                    start_time=0.0,
                    end_time=2.0,
                    speaker="Speaker 0",
                    confidence=None,  # 没有置信度
                )
            ],
            full_text="测试",
            duration=2.0,
            language="zh-CN",
            provider="volcano",
        )

        stats = await speaker_recognition_service.get_speaker_statistics(transcript)

        assert stats["Speaker 0"]["avg_confidence"] == 0.0
