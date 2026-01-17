"""Property-based tests for core data models.

Feature: meeting-minutes-agent, Property 7: 数据模型验证
验证: 需求 9.5, 22.5, 27.7

属性 7: 对于任何 Pydantic 数据模型类,如果输入数据缺少必需字段或类型不匹配,
则创建实例时应当抛出 ValidationError。
"""

from datetime import datetime
from typing import Any, Dict

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from src.core.models import (
    ASRLanguage,
    CreateTaskRequest,
    GeneratedArtifact,
    HotwordSet,
    MeetingMinutes,
    OutputLanguage,
    PromptInstance,
    PromptTemplate,
    Segment,
    TaskMetadata,
    TaskState,
    TaskStatus,
    TranscriptionResult,
)


# ============================================================================
# Hypothesis Strategies for generating test data
# ============================================================================


@st.composite
def valid_segment_data(draw):
    """Generate valid Segment data"""
    start = draw(st.floats(min_value=0, max_value=1000))
    end = draw(st.floats(min_value=start, max_value=start + 100))
    return {
        "text": draw(st.text(min_size=1)),
        "start_time": start,
        "end_time": end,
        "speaker": draw(st.text(min_size=1)),
        "confidence": draw(st.floats(min_value=0, max_value=1)),
    }


@st.composite
def invalid_segment_data(draw):
    """Generate invalid Segment data (missing required fields or wrong types)"""
    choice = draw(st.integers(min_value=0, max_value=4))
    
    if choice == 0:
        # Missing 'text' field
        return {
            "start_time": 0.0,
            "end_time": 1.0,
            "speaker": "Speaker 1",
        }
    elif choice == 1:
        # Missing 'start_time' field
        return {
            "text": "Hello",
            "end_time": 1.0,
            "speaker": "Speaker 1",
        }
    elif choice == 2:
        # Wrong type for 'start_time' (string instead of float)
        return {
            "text": "Hello",
            "start_time": "invalid",
            "end_time": 1.0,
            "speaker": "Speaker 1",
        }
    elif choice == 3:
        # Negative start_time (violates ge=0 constraint)
        return {
            "text": "Hello",
            "start_time": -1.0,
            "end_time": 1.0,
            "speaker": "Speaker 1",
        }
    else:
        # confidence out of range (violates 0 <= confidence <= 1)
        return {
            "text": "Hello",
            "start_time": 0.0,
            "end_time": 1.0,
            "speaker": "Speaker 1",
            "confidence": 1.5,
        }


# ============================================================================
# Property 7: 数据模型验证
# ============================================================================


class TestSegmentValidation:
    """Test Segment model validation"""
    
    @given(valid_segment_data())
    def test_valid_segment_creation(self, data: Dict[str, Any]):
        """Property: Valid Segment data should create instance successfully"""
        segment = Segment(**data)
        assert segment.text == data["text"]
        assert segment.start_time == data["start_time"]
        assert segment.end_time == data["end_time"]
        assert segment.speaker == data["speaker"]
    
    @given(invalid_segment_data())
    def test_invalid_segment_raises_validation_error(self, data: Dict[str, Any]):
        """Property: Invalid Segment data should raise ValidationError"""
        with pytest.raises(ValidationError):
            Segment(**data)


class TestTranscriptionResultValidation:
    """Test TranscriptionResult model validation"""
    
    def test_missing_required_field_raises_error(self):
        """Property: Missing required fields should raise ValidationError"""
        # Missing 'segments' field
        with pytest.raises(ValidationError):
            TranscriptionResult(
                full_text="Hello world",
                duration=10.0,
                provider="volcano",
            )
        
        # Missing 'full_text' field
        with pytest.raises(ValidationError):
            TranscriptionResult(
                segments=[],
                duration=10.0,
                provider="volcano",
            )
        
        # Missing 'duration' field
        with pytest.raises(ValidationError):
            TranscriptionResult(
                segments=[],
                full_text="Hello",
                provider="volcano",
            )
        
        # Missing 'provider' field
        with pytest.raises(ValidationError):
            TranscriptionResult(
                segments=[],
                full_text="Hello",
                duration=10.0,
            )
    
    @given(st.floats(max_value=-0.1))
    def test_negative_duration_raises_error(self, duration: float):
        """Property: Negative duration should raise ValidationError"""
        with pytest.raises(ValidationError):
            TranscriptionResult(
                segments=[],
                full_text="Hello",
                duration=duration,
                provider="volcano",
            )


class TestMeetingMinutesValidation:
    """Test MeetingMinutes model validation"""
    
    def test_missing_required_fields_raises_error(self):
        """Property: Missing required fields should raise ValidationError"""
        # Missing 'title'
        with pytest.raises(ValidationError):
            MeetingMinutes(
                participants=["Alice"],
                summary="Summary",
                key_points=[],
                action_items=[],
            )
        
        # Missing 'participants'
        with pytest.raises(ValidationError):
            MeetingMinutes(
                title="Meeting",
                summary="Summary",
                key_points=[],
                action_items=[],
            )
        
        # Missing 'summary'
        with pytest.raises(ValidationError):
            MeetingMinutes(
                title="Meeting",
                participants=["Alice"],
                key_points=[],
                action_items=[],
            )
    
    @given(
        st.text(min_size=1),
        st.lists(st.text(min_size=1), min_size=1),
        st.text(min_size=1),
    )
    def test_valid_meeting_minutes_creation(
        self, title: str, participants: list, summary: str
    ):
        """Property: Valid MeetingMinutes data should create instance successfully"""
        minutes = MeetingMinutes(
            title=title,
            participants=participants,
            summary=summary,
            key_points=[],
            action_items=[],
        )
        assert minutes.title == title
        assert minutes.participants == participants
        assert minutes.summary == summary


class TestPromptTemplateValidation:
    """Test PromptTemplate model validation"""
    
    def test_missing_required_fields_raises_error(self):
        """Property: Missing required fields should raise ValidationError"""
        # Missing 'template_id'
        with pytest.raises(ValidationError):
            PromptTemplate(
                title="Template",
                description="Description",
                prompt_body="Body",
                artifact_type="meeting_minutes",
                parameter_schema={},
            )
        
        # Missing 'prompt_body'
        with pytest.raises(ValidationError):
            PromptTemplate(
                template_id="tpl_001",
                title="Template",
                description="Description",
                artifact_type="meeting_minutes",
                parameter_schema={},
            )
        
        # Missing 'artifact_type'
        with pytest.raises(ValidationError):
            PromptTemplate(
                template_id="tpl_001",
                title="Template",
                description="Description",
                prompt_body="Body",
                parameter_schema={},
            )


class TestPromptInstanceValidation:
    """Test PromptInstance model validation"""
    
    def test_missing_template_id_raises_error(self):
        """Property: Missing template_id should raise ValidationError"""
        with pytest.raises(ValidationError):
            PromptInstance(
                language="zh-CN",
                parameters={},
            )
    
    @given(st.text(min_size=1))
    def test_valid_prompt_instance_creation(self, template_id: str):
        """Property: Valid PromptInstance data should create instance successfully"""
        instance = PromptInstance(template_id=template_id)
        assert instance.template_id == template_id
        assert instance.language == "zh-CN"  # default value
        assert instance.parameters == {}  # default value


class TestGeneratedArtifactValidation:
    """Test GeneratedArtifact model validation"""
    
    def test_missing_required_fields_raises_error(self):
        """Property: Missing required fields should raise ValidationError"""
        prompt_instance = PromptInstance(template_id="tpl_001")
        
        # Missing 'artifact_id'
        with pytest.raises(ValidationError):
            GeneratedArtifact(
                task_id="task_001",
                artifact_type="meeting_minutes",
                version=1,
                prompt_instance=prompt_instance,
                content="{}",
                created_by="user_001",
            )
        
        # Missing 'task_id'
        with pytest.raises(ValidationError):
            GeneratedArtifact(
                artifact_id="art_001",
                artifact_type="meeting_minutes",
                version=1,
                prompt_instance=prompt_instance,
                content="{}",
                created_by="user_001",
            )
        
        # Missing 'created_by'
        with pytest.raises(ValidationError):
            GeneratedArtifact(
                artifact_id="art_001",
                task_id="task_001",
                artifact_type="meeting_minutes",
                version=1,
                prompt_instance=prompt_instance,
                content="{}",
            )


class TestHotwordSetValidation:
    """Test HotwordSet model validation"""
    
    def test_invalid_provider_raises_error(self):
        """Property: Invalid provider should raise ValidationError"""
        with pytest.raises(ValueError, match="provider 必须是"):
            HotwordSet(
                hotword_set_id="hs_001",
                name="Test",
                provider="invalid_provider",
                provider_resource_id="res_001",
                scope="global",
                asr_language=ASRLanguage.ZH_CN,
            )
    
    @given(st.sampled_from(["volcano", "azure"]))
    def test_valid_provider_accepted(self, provider: str):
        """Property: Valid provider should be accepted"""
        hotword_set = HotwordSet(
            hotword_set_id="hs_001",
            name="Test",
            provider=provider,
            provider_resource_id="res_001",
            scope="global",
            asr_language=ASRLanguage.ZH_CN,
        )
        assert hotword_set.provider == provider


class TestTaskMetadataValidation:
    """Test TaskMetadata model validation"""
    
    def test_missing_required_fields_raises_error(self):
        """Property: Missing required fields should raise ValidationError"""
        # Missing 'task_id'
        with pytest.raises(ValidationError):
            TaskMetadata(
                audio_files=["file1.wav"],
                file_order=[0],
                meeting_type="weekly",
                user_id="user_001",
                tenant_id="tenant_001",
            )
        
        # Missing 'audio_files'
        with pytest.raises(ValidationError):
            TaskMetadata(
                task_id="task_001",
                file_order=[0],
                meeting_type="weekly",
                user_id="user_001",
                tenant_id="tenant_001",
            )
        
        # Missing 'user_id'
        with pytest.raises(ValidationError):
            TaskMetadata(
                task_id="task_001",
                audio_files=["file1.wav"],
                file_order=[0],
                meeting_type="weekly",
                tenant_id="tenant_001",
            )


class TestTaskStatusValidation:
    """Test TaskStatus model validation"""
    
    @given(st.floats(min_value=-100, max_value=-0.1))
    def test_negative_progress_raises_error(self, progress: float):
        """Property: Negative progress should raise ValidationError"""
        with pytest.raises(ValidationError):
            TaskStatus(
                task_id="task_001",
                state=TaskState.RUNNING,
                progress=progress,
            )
    
    @given(st.floats(min_value=100.1, max_value=200))
    def test_progress_over_100_raises_error(self, progress: float):
        """Property: Progress > 100 should raise ValidationError"""
        with pytest.raises(ValidationError):
            TaskStatus(
                task_id="task_001",
                state=TaskState.RUNNING,
                progress=progress,
            )
    
    @given(st.floats(min_value=0, max_value=100))
    def test_valid_progress_accepted(self, progress: float):
        """Property: Valid progress (0-100) should be accepted"""
        status = TaskStatus(
            task_id="task_001",
            state=TaskState.RUNNING,
            progress=progress,
        )
        assert status.progress == progress


class TestCreateTaskRequestValidation:
    """Test CreateTaskRequest model validation"""
    
    def test_empty_audio_files_raises_error(self):
        """Property: Empty audio_files list should raise ValidationError"""
        with pytest.raises(ValidationError):
            CreateTaskRequest(
                audio_files=[],
                meeting_type="weekly",
            )
    
    def test_file_order_length_mismatch_raises_error(self):
        """Property: file_order length != audio_files length should raise ValidationError"""
        with pytest.raises(ValueError, match="file_order 长度必须与 audio_files 相同"):
            CreateTaskRequest(
                audio_files=["file1.wav", "file2.wav"],
                file_order=[0],
                meeting_type="weekly",
            )
    
    def test_invalid_file_order_values_raises_error(self):
        """Property: file_order with invalid values should raise ValidationError"""
        # Not a permutation of 0 to n-1
        with pytest.raises(ValueError, match="file_order 必须是 0 到 n-1 的排列"):
            CreateTaskRequest(
                audio_files=["file1.wav", "file2.wav"],
                file_order=[0, 2],
                meeting_type="weekly",
            )
        
        # Duplicate values
        with pytest.raises(ValueError, match="file_order 必须是 0 到 n-1 的排列"):
            CreateTaskRequest(
                audio_files=["file1.wav", "file2.wav"],
                file_order=[0, 0],
                meeting_type="weekly",
            )
    
    @given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
    def test_valid_audio_files_accepted(self, audio_files: list):
        """Property: Valid audio_files list should be accepted"""
        request = CreateTaskRequest(
            audio_files=audio_files,
            meeting_type="weekly",
        )
        assert request.audio_files == audio_files
        assert request.file_order is None  # default value


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
