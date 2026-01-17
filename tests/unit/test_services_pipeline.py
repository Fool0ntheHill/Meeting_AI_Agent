"""Unit tests for pipeline service."""

import pytest
from unittest.mock import AsyncMock

from src.core.exceptions import LLMError
from src.core.models import (
    ASRLanguage,
    GeneratedArtifact,
    OutputLanguage,
    PromptInstance,
    Segment,
    TranscriptionResult,
)
from src.services.pipeline import PipelineService


@pytest.fixture
def mock_transcription_service():
    """Mock transcription service"""
    return AsyncMock()


@pytest.fixture
def mock_speaker_recognition_service():
    """Mock speaker recognition service"""
    return AsyncMock()


@pytest.fixture
def mock_correction_service():
    """Mock correction service"""
    return AsyncMock()


@pytest.fixture
def mock_artifact_generation_service():
    """Mock artifact generation service"""
    return AsyncMock()


@pytest.fixture
def mock_task_repo():
    """Mock task repository"""
    return AsyncMock()


@pytest.fixture
def sample_transcript():
    """Sample transcription result"""
    return TranscriptionResult(
        segments=[
            Segment(
                text="大家好,今天讨论产品规划。",
                start_time=0.0,
                end_time=5.0,
                speaker="Speaker 0",
                confidence=0.95,
            ),
            Segment(
                text="我们需要确定下一季度的目标。",
                start_time=5.0,
                end_time=10.0,
                speaker="Speaker 1",
                confidence=0.92,
            ),
        ],
        full_text="大家好,今天讨论产品规划。我们需要确定下一季度的目标。",
        duration=10.0,
        language="zh-CN",
        provider="volcano",
    )


@pytest.fixture
def sample_transcript_with_speakers():
    """Sample transcription result with identified speakers"""
    return TranscriptionResult(
        segments=[
            Segment(
                text="大家好,今天讨论产品规划。",
                start_time=0.0,
                end_time=5.0,
                speaker="张三",
                confidence=0.95,
            ),
            Segment(
                text="我们需要确定下一季度的目标。",
                start_time=5.0,
                end_time=10.0,
                speaker="李四",
                confidence=0.92,
            ),
        ],
        full_text="大家好,今天讨论产品规划。我们需要确定下一季度的目标。",
        duration=10.0,
        language="zh-CN",
        provider="volcano",
    )


@pytest.fixture
def sample_artifact(sample_prompt_instance):
    """Sample generated artifact"""
    return GeneratedArtifact(
        artifact_id="art_task_123_meeting_minutes_v1",
        task_id="task_123",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=sample_prompt_instance,
        content='{"title": "产品规划会议", "participants": ["张三", "李四"], "summary": "讨论了产品规划", "key_points": [], "action_items": []}',
        metadata=None,
        created_by="user_456",
    )


@pytest.fixture
def sample_prompt_instance():
    """Sample prompt instance"""
    return PromptInstance(
        template_id="tpl_001",
        language="zh-CN",
        parameters={"meeting_description": "产品规划会议"},
    )


class TestPipelineService:
    """PipelineService 测试类"""

    @pytest.mark.asyncio
    async def test_process_meeting_success(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
        sample_transcript,
        sample_transcript_with_speakers,
        sample_artifact,
        sample_prompt_instance,
    ):
        """Test successful meeting processing through full pipeline"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
        )

        mock_transcription_service.transcribe.return_value = (
            sample_transcript,
            "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx",
            "/tmp/test.wav"
        )
        mock_speaker_recognition_service.recognize_speakers.return_value = {
            "Speaker 0": "张三",
            "Speaker 1": "李四",
        }
        mock_correction_service.correct_speakers.return_value = (
            sample_transcript_with_speakers
        )
        mock_artifact_generation_service.generate_artifact.return_value = sample_artifact

        # Execute
        result = await pipeline.process_meeting(
            task_id="task_123",
            audio_files=["meeting.wav"],
            file_order=[0],
            prompt_instance=sample_prompt_instance,
            user_id="user_456",
        )

        # Verify
        assert result.artifact_id == "art_task_123_meeting_minutes_v1"
        assert result.task_id == "task_123"
        assert result.artifact_type == "meeting_minutes"

        # Verify all services were called
        mock_transcription_service.transcribe.assert_called_once()
        mock_speaker_recognition_service.recognize_speakers.assert_called_once()
        mock_correction_service.correct_speakers.assert_called_once()
        mock_artifact_generation_service.generate_artifact.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_meeting_skip_speaker_recognition(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
        sample_transcript,
        sample_artifact,
        sample_prompt_instance,
    ):
        """Test pipeline with speaker recognition skipped"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
        )

        mock_transcription_service.transcribe.return_value = (
            sample_transcript,
            "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx",
            "/tmp/test.wav"
        )
        mock_artifact_generation_service.generate_artifact.return_value = sample_artifact

        # Execute
        result = await pipeline.process_meeting(
            task_id="task_123",
            audio_files=["meeting.wav"],
            file_order=[0],
            prompt_instance=sample_prompt_instance,
            user_id="user_456",
            skip_speaker_recognition=True,
        )

        # Verify
        assert result.artifact_id == "art_task_123_meeting_minutes_v1"

        # Verify speaker recognition was NOT called
        mock_speaker_recognition_service.recognize_speakers.assert_not_called()
        mock_correction_service.correct_speakers.assert_not_called()

        # Verify other services were called
        mock_transcription_service.transcribe.assert_called_once()
        mock_artifact_generation_service.generate_artifact.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_meeting_transcription_failure(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
        sample_prompt_instance,
    ):
        """Test pipeline failure during transcription phase"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
        )

        mock_transcription_service.transcribe.side_effect = Exception("Transcription failed")

        # Execute & Verify
        with pytest.raises(Exception):
            await pipeline.process_meeting(
                task_id="task_123",
                audio_files=["meeting.wav"],
                file_order=[0],
                prompt_instance=sample_prompt_instance,
                user_id="user_456",
            )

        # Verify subsequent services were NOT called
        mock_speaker_recognition_service.recognize_speakers.assert_not_called()
        mock_correction_service.correct_speakers.assert_not_called()
        mock_artifact_generation_service.generate_artifact.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_meeting_speaker_recognition_failure(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
        sample_transcript,
        sample_prompt_instance,
    ):
        """Test pipeline failure during speaker recognition phase"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
        )

        mock_transcription_service.transcribe.return_value = (
            sample_transcript,
            "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx",
            "/tmp/test.wav"
        )
        mock_speaker_recognition_service.recognize_speakers.side_effect = Exception(
            "Speaker recognition failed"
        )

        # Execute & Verify
        with pytest.raises(Exception):
            await pipeline.process_meeting(
                task_id="task_123",
                audio_files=["meeting.wav"],
                file_order=[0],
                prompt_instance=sample_prompt_instance,
                user_id="user_456",
            )

        # Verify transcription was called
        mock_transcription_service.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_meeting_artifact_generation_failure(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
        sample_transcript,
        sample_transcript_with_speakers,
        sample_prompt_instance,
    ):
        """Test pipeline failure during artifact generation phase"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
        )

        mock_transcription_service.transcribe.return_value = (
            sample_transcript,
            "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx",
            "/tmp/test.wav"
        )
        mock_speaker_recognition_service.recognize_speakers.return_value = {
            "Speaker 0": "张三",
            "Speaker 1": "李四",
        }
        mock_correction_service.correct_speakers.return_value = (
            sample_transcript_with_speakers
        )
        mock_artifact_generation_service.generate_artifact.side_effect = LLMError(
            "LLM rate limit exceeded", provider="gemini"
        )

        # Execute & Verify
        with pytest.raises(LLMError):
            await pipeline.process_meeting(
                task_id="task_123",
                audio_files=["meeting.wav"],
                file_order=[0],
                prompt_instance=sample_prompt_instance,
                user_id="user_456",
            )

        # Verify all previous services were called
        mock_transcription_service.transcribe.assert_called_once()
        mock_speaker_recognition_service.recognize_speakers.assert_called_once()
        mock_correction_service.correct_speakers.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_meeting_with_task_repo(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
        mock_task_repo,
        sample_transcript,
        sample_transcript_with_speakers,
        sample_artifact,
        sample_prompt_instance,
    ):
        """Test pipeline with task repository for status updates"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
            task_repo=mock_task_repo,
        )

        mock_transcription_service.transcribe.return_value = (
            sample_transcript,
            "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx",
            "/tmp/test.wav"
        )
        mock_speaker_recognition_service.recognize_speakers.return_value = {
            "Speaker 0": "张三",
            "Speaker 1": "李四",
        }
        mock_correction_service.correct_speakers.return_value = (
            sample_transcript_with_speakers
        )
        mock_artifact_generation_service.generate_artifact.return_value = sample_artifact

        # Execute
        result = await pipeline.process_meeting(
            task_id="task_123",
            audio_files=["meeting.wav"],
            file_order=[0],
            prompt_instance=sample_prompt_instance,
            user_id="user_456",
        )

        # Verify
        assert result.artifact_id == "art_task_123_meeting_minutes_v1"

        # Verify task status was updated
        assert mock_task_repo.update_status.call_count >= 3  # At least 3 status updates

    @pytest.mark.asyncio
    async def test_process_meeting_multiple_files(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
        sample_transcript,
        sample_transcript_with_speakers,
        sample_artifact,
        sample_prompt_instance,
    ):
        """Test processing meeting with multiple audio files"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
        )

        mock_transcription_service.transcribe.return_value = (
            sample_transcript,
            "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx",
            "/tmp/concatenated.wav"
        )
        mock_speaker_recognition_service.recognize_speakers.return_value = {
            "Speaker 0": "张三",
            "Speaker 1": "李四",
        }
        mock_correction_service.correct_speakers.return_value = (
            sample_transcript_with_speakers
        )
        mock_artifact_generation_service.generate_artifact.return_value = sample_artifact

        # Execute
        result = await pipeline.process_meeting(
            task_id="task_123",
            audio_files=["meeting_part1.wav", "meeting_part2.wav", "meeting_part3.wav"],
            file_order=[0, 1, 2],
            prompt_instance=sample_prompt_instance,
            user_id="user_456",
        )

        # Verify
        assert result.artifact_id == "art_task_123_meeting_minutes_v1"

        # Verify transcription was called with correct parameters
        call_kwargs = mock_transcription_service.transcribe.call_args[1]
        assert call_kwargs["audio_files"] == [
            "meeting_part1.wav",
            "meeting_part2.wav",
            "meeting_part3.wav",
        ]
        assert call_kwargs["file_order"] == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_get_status_without_repo(
        self,
        mock_transcription_service,
        mock_speaker_recognition_service,
        mock_correction_service,
        mock_artifact_generation_service,
    ):
        """Test getting status when task repository is not configured"""
        # Setup
        pipeline = PipelineService(
            transcription_service=mock_transcription_service,
            speaker_recognition_service=mock_speaker_recognition_service,
            correction_service=mock_correction_service,
            artifact_generation_service=mock_artifact_generation_service,
            task_repo=None,
        )

        # Execute
        status = await pipeline.get_status("task_123")

        # Verify
        assert status["task_id"] == "task_123"
        assert status["state"] == "unknown"
        assert "not configured" in status["message"]
