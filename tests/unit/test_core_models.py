"""Unit tests for core data models."""

from datetime import datetime

import pytest

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


def test_segment_creation():
    """Test Segment model creation"""
    segment = Segment(
        text="Hello world",
        start_time=0.0,
        end_time=1.5,
        speaker="Speaker 1",
        confidence=0.95,
    )
    assert segment.text == "Hello world"
    assert segment.start_time == 0.0
    assert segment.end_time == 1.5
    assert segment.speaker == "Speaker 1"
    assert segment.confidence == 0.95


def test_transcription_result_speakers():
    """Test TranscriptionResult speakers property"""
    segments = [
        Segment(text="Hello", start_time=0.0, end_time=1.0, speaker="Alice"),
        Segment(text="Hi", start_time=1.0, end_time=2.0, speaker="Bob"),
        Segment(text="How are you", start_time=2.0, end_time=3.0, speaker="Alice"),
    ]
    result = TranscriptionResult(
        segments=segments,
        full_text="Hello Hi How are you",
        duration=3.0,
        language="zh-CN",
        provider="volcano",
    )
    assert set(result.speakers) == {"Alice", "Bob"}


def test_meeting_minutes_creation():
    """Test MeetingMinutes model creation"""
    minutes = MeetingMinutes(
        title="Product Planning Meeting",
        participants=["Alice", "Bob"],
        summary="Discussed Q2 roadmap",
        key_points=["Feature A", "Feature B"],
        action_items=["Alice: Implement Feature A"],
    )
    assert minutes.title == "Product Planning Meeting"
    assert len(minutes.participants) == 2
    assert len(minutes.key_points) == 2


def test_prompt_template_creation():
    """Test PromptTemplate model creation"""
    template = PromptTemplate(
        template_id="tpl_001",
        title="Standard Meeting Minutes",
        description="Generate standard meeting minutes",
        prompt_body="Generate minutes for: {meeting_description}",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN", "en-US"],
        parameter_schema={
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
            }
        },
    )
    assert template.template_id == "tpl_001"
    assert template.artifact_type == "meeting_minutes"
    assert "zh-CN" in template.supported_languages


def test_prompt_instance_creation():
    """Test PromptInstance model creation"""
    instance = PromptInstance(
        template_id="tpl_001",
        language="zh-CN",
        parameters={"meeting_description": "Product planning meeting"},
    )
    assert instance.template_id == "tpl_001"
    assert instance.language == "zh-CN"
    assert "meeting_description" in instance.parameters


def test_generated_artifact_get_meeting_minutes():
    """Test GeneratedArtifact.get_meeting_minutes() method"""
    minutes = MeetingMinutes(
        title="Test Meeting",
        participants=["Alice"],
        summary="Test summary",
        key_points=["Point 1"],
        action_items=["Action 1"],
    )
    artifact = GeneratedArtifact(
        artifact_id="art_001",
        task_id="task_001",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=PromptInstance(template_id="tpl_001"),
        content=minutes.model_dump_json(),
        created_by="user_001",
    )
    
    parsed_minutes = artifact.get_meeting_minutes()
    assert parsed_minutes is not None
    assert parsed_minutes.title == "Test Meeting"
    assert len(parsed_minutes.participants) == 1


def test_generated_artifact_get_content_dict():
    """Test GeneratedArtifact.get_content_dict() method"""
    artifact = GeneratedArtifact(
        artifact_id="art_001",
        task_id="task_001",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=PromptInstance(template_id="tpl_001"),
        content='{"title": "Test", "summary": "Summary"}',
        created_by="user_001",
    )
    
    content_dict = artifact.get_content_dict()
    assert isinstance(content_dict, dict)
    assert content_dict["title"] == "Test"
    assert content_dict["summary"] == "Summary"


def test_hotword_set_validation():
    """Test HotwordSet provider validation"""
    # Valid provider
    hotword_set = HotwordSet(
        hotword_set_id="hs_001",
        name="Medical Terms",
        provider="volcano",
        provider_resource_id="lib_001",
        scope="global",
        asr_language=ASRLanguage.ZH_CN,
    )
    assert hotword_set.provider == "volcano"
    
    # Invalid provider should raise ValueError
    with pytest.raises(ValueError, match="provider 必须是"):
        HotwordSet(
            hotword_set_id="hs_002",
            name="Invalid",
            provider="invalid_provider",
            provider_resource_id="lib_002",
            scope="global",
            asr_language=ASRLanguage.ZH_CN,
        )


def test_task_metadata_creation():
    """Test TaskMetadata model creation"""
    metadata = TaskMetadata(
        task_id="task_001",
        audio_files=["file1.wav", "file2.wav"],
        file_order=[0, 1],
        meeting_type="weekly_sync",
        asr_language=ASRLanguage.ZH_EN,
        output_language=OutputLanguage.ZH_CN,
        user_id="user_001",
        tenant_id="tenant_001",
    )
    assert metadata.task_id == "task_001"
    assert len(metadata.audio_files) == 2
    assert metadata.asr_language == ASRLanguage.ZH_EN
    assert metadata.output_language == OutputLanguage.ZH_CN


def test_task_status_creation():
    """Test TaskStatus model creation"""
    status = TaskStatus(
        task_id="task_001",
        state=TaskState.TRANSCRIBING,
        progress=50.0,
        estimated_time=120,
    )
    assert status.task_id == "task_001"
    assert status.state == TaskState.TRANSCRIBING
    assert status.progress == 50.0


def test_create_task_request_validation():
    """Test CreateTaskRequest validation"""
    # Valid request
    request = CreateTaskRequest(
        audio_files=["file1.wav", "file2.wav"],
        file_order=[0, 1],
        meeting_type="weekly_sync",
    )
    assert len(request.audio_files) == 2
    
    # Invalid file_order length
    with pytest.raises(ValueError, match="file_order 长度必须与 audio_files 相同"):
        CreateTaskRequest(
            audio_files=["file1.wav", "file2.wav"],
            file_order=[0],
            meeting_type="weekly_sync",
        )
    
    # Invalid file_order values
    with pytest.raises(ValueError, match="file_order 必须是 0 到 n-1 的排列"):
        CreateTaskRequest(
            audio_files=["file1.wav", "file2.wav"],
            file_order=[0, 2],
            meeting_type="weekly_sync",
        )


def test_enums():
    """Test enum values"""
    assert ASRLanguage.ZH_CN == "zh-CN"
    assert ASRLanguage.ZH_EN == "zh-CN+en-US"
    assert OutputLanguage.ZH_CN == "zh-CN"
    assert TaskState.TRANSCRIBING == "transcribing"
    assert TaskState.SUCCESS == "success"
