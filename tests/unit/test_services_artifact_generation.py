"""Tests for artifact generation service."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.core.exceptions import LLMError, ValidationError
from src.core.models import (
    GeneratedArtifact,
    OutputLanguage,
    PromptInstance,
    PromptTemplate,
    Segment,
    TranscriptionResult,
)
from src.services.artifact_generation import ArtifactGenerationService


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = AsyncMock()
    return provider


@pytest.fixture
def mock_template_repo():
    """Mock template repository"""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_artifact_repo():
    """Mock artifact repository"""
    repo = AsyncMock()
    return repo


@pytest.fixture
def sample_template():
    """Sample prompt template"""
    return PromptTemplate(
        template_id="tpl_001",
        title="标准会议纪要",
        description="生成标准会议纪要",
        prompt_body="你是会议纪要助手。\n\n会议信息:\n{meeting_description}\n\n请生成纪要...",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN", "en-US"],
        parameter_schema={
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
            }
        },
        is_system=True,
    )


@pytest.fixture
def sample_prompt_instance():
    """Sample prompt instance"""
    return PromptInstance(
        template_id="tpl_001",
        language="zh-CN",
        parameters={"meeting_description": "产品规划会议"},
    )


@pytest.fixture
def sample_transcript():
    """Sample transcription result"""
    return TranscriptionResult(
        task_id="task_123",
        segments=[
            Segment(
                start_time=0.0,
                end_time=5.0,
                text="大家好,今天讨论产品规划。",
                speaker="张三",
            ),
            Segment(
                start_time=5.0,
                end_time=10.0,
                text="我们需要关注用户反馈。",
                speaker="李四",
            ),
        ],
        full_text="大家好,今天讨论产品规划。我们需要关注用户反馈。",
        provider="volcano",
        language="zh-CN",
        duration=10.0,
    )


@pytest.fixture
def sample_artifact():
    """Sample generated artifact"""
    content = {
        "title": "产品规划会议",
        "participants": ["张三", "李四"],
        "summary": "讨论了产品规划和用户反馈",
        "key_points": ["关注用户反馈"],
        "action_items": [],
    }
    return GeneratedArtifact(
        artifact_id="art_task_123_meeting_minutes_v1",
        task_id="task_123",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=PromptInstance(
            template_id="tpl_001",
            language="zh-CN",
            parameters={"meeting_description": "产品规划会议"},
        ),
        content=json.dumps(content, ensure_ascii=False),
        created_by="user_456",
    )


# ============================================================================
# Basic Functionality Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_artifact_success(
    mock_llm_provider,
    sample_template,
    sample_prompt_instance,
    sample_transcript,
    sample_artifact,
):
    """Test successful artifact generation"""
    # Setup
    service = ArtifactGenerationService(llm_provider=mock_llm_provider)
    mock_llm_provider.generate_artifact.return_value = sample_artifact

    # Execute
    result = await service.generate_artifact(
        task_id="task_123",
        transcript=sample_transcript,
        artifact_type="meeting_minutes",
        prompt_instance=sample_prompt_instance,
        output_language=OutputLanguage.ZH_CN,
        user_id="user_456",
        template=sample_template,
    )

    # Verify
    assert result.artifact_id == "art_task_123_meeting_minutes_v1"
    assert result.task_id == "task_123"
    assert result.artifact_type == "meeting_minutes"
    assert result.version == 1
    assert result.created_by == "user_456"

    # Verify LLM was called correctly
    mock_llm_provider.generate_artifact.assert_called_once()
    call_kwargs = mock_llm_provider.generate_artifact.call_args.kwargs
    assert call_kwargs["task_id"] == "task_123"
    assert call_kwargs["template"] == sample_template
    assert call_kwargs["prompt_instance"] == sample_prompt_instance


@pytest.mark.asyncio
async def test_generate_artifact_with_repos(
    mock_llm_provider,
    mock_template_repo,
    mock_artifact_repo,
    sample_template,
    sample_prompt_instance,
    sample_transcript,
    sample_artifact,
):
    """Test artifact generation with template and artifact repositories"""
    # Setup
    service = ArtifactGenerationService(
        llm_provider=mock_llm_provider,
        template_repo=mock_template_repo,
        artifact_repo=mock_artifact_repo,
    )
    mock_template_repo.get.return_value = sample_template
    mock_artifact_repo.get_latest_version.return_value = None
    mock_llm_provider.generate_artifact.return_value = sample_artifact

    # Execute
    result = await service.generate_artifact(
        task_id="task_123",
        transcript=sample_transcript,
        artifact_type="meeting_minutes",
        prompt_instance=sample_prompt_instance,
        user_id="user_456",
    )

    # Verify
    assert result.version == 1
    mock_template_repo.get.assert_called_once_with("tpl_001")
    mock_artifact_repo.create.assert_called_once_with(sample_artifact)


# ============================================================================
# Different Artifact Types Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_action_items(
    mock_llm_provider, sample_transcript
):
    """Test generating action items artifact"""
    # Setup
    template = PromptTemplate(
        template_id="tpl_action",
        title="行动项提取",
        description="提取会议行动项",
        prompt_body="请提取行动项...",
        artifact_type="action_items",
        supported_languages=["zh-CN"],
        parameter_schema={},
        is_system=True,
    )
    prompt_instance = PromptInstance(
        template_id="tpl_action", language="zh-CN", parameters={}
    )

    artifact = GeneratedArtifact(
        artifact_id="art_action_v1",
        task_id="task_123",
        artifact_type="action_items",
        version=1,
        prompt_instance=prompt_instance,
        content=json.dumps({"action_items": ["完成需求文档", "安排评审会议"]}),
        created_by="user_456",
    )

    service = ArtifactGenerationService(llm_provider=mock_llm_provider)
    mock_llm_provider.generate_artifact.return_value = artifact

    # Execute
    result = await service.generate_artifact(
        task_id="task_123",
        transcript=sample_transcript,
        artifact_type="action_items",
        prompt_instance=prompt_instance,
        template=template,
    )

    # Verify
    assert result.artifact_type == "action_items"
    content = result.get_content_dict()
    assert "action_items" in content


@pytest.mark.asyncio
async def test_generate_summary_notes(
    mock_llm_provider, sample_transcript
):
    """Test generating summary notes artifact"""
    # Setup
    template = PromptTemplate(
        template_id="tpl_summary",
        title="摘要笔记",
        description="生成简短摘要",
        prompt_body="请生成摘要...",
        artifact_type="summary_notes",
        supported_languages=["zh-CN", "en-US"],
        parameter_schema={},
        is_system=True,
    )
    prompt_instance = PromptInstance(
        template_id="tpl_summary", language="en-US", parameters={}
    )

    artifact = GeneratedArtifact(
        artifact_id="art_summary_v1",
        task_id="task_123",
        artifact_type="summary_notes",
        version=1,
        prompt_instance=prompt_instance,
        content=json.dumps({"summary": "Product planning discussion"}),
        created_by="user_456",
    )

    service = ArtifactGenerationService(llm_provider=mock_llm_provider)
    mock_llm_provider.generate_artifact.return_value = artifact

    # Execute
    result = await service.generate_artifact(
        task_id="task_123",
        transcript=sample_transcript,
        artifact_type="summary_notes",
        prompt_instance=prompt_instance,
        output_language=OutputLanguage.EN_US,
        template=template,
    )

    # Verify
    assert result.artifact_type == "summary_notes"
    assert result.prompt_instance.language == "en-US"


# ============================================================================
# Prompt Parameter Injection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parameter_injection(
    mock_llm_provider, sample_transcript
):
    """Test prompt parameter injection"""
    # Setup
    template = PromptTemplate(
        template_id="tpl_custom",
        title="自定义模板",
        description="支持多参数",
        prompt_body="会议: {meeting_title}\n主题: {topic}\n重点: {focus_area}",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN"],
        parameter_schema={
            "meeting_title": {"type": "string", "required": True},
            "topic": {"type": "string", "required": True},
            "focus_area": {"type": "string", "required": False, "default": ""},
        },
        is_system=False,
    )

    prompt_instance = PromptInstance(
        template_id="tpl_custom",
        language="zh-CN",
        parameters={
            "meeting_title": "Q2 产品规划",
            "topic": "用户增长策略",
            "focus_area": "新用户留存",
        },
    )

    artifact = GeneratedArtifact(
        artifact_id="art_custom_v1",
        task_id="task_123",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=prompt_instance,
        content=json.dumps({"title": "Q2 产品规划"}),
        created_by="user_456",
    )

    service = ArtifactGenerationService(llm_provider=mock_llm_provider)
    mock_llm_provider.generate_artifact.return_value = artifact

    # Execute
    result = await service.generate_artifact(
        task_id="task_123",
        transcript=sample_transcript,
        artifact_type="meeting_minutes",
        prompt_instance=prompt_instance,
        template=template,
    )

    # Verify
    assert result.prompt_instance.parameters["meeting_title"] == "Q2 产品规划"
    assert result.prompt_instance.parameters["topic"] == "用户增长策略"
    assert result.prompt_instance.parameters["focus_area"] == "新用户留存"


# ============================================================================
# Version Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_version_increment(
    mock_llm_provider, mock_artifact_repo, sample_template, sample_transcript
):
    """Test version number increments correctly"""
    # Setup
    service = ArtifactGenerationService(
        llm_provider=mock_llm_provider, artifact_repo=mock_artifact_repo
    )

    # Mock existing version
    existing_artifact = GeneratedArtifact(
        artifact_id="art_v2",
        task_id="task_123",
        artifact_type="meeting_minutes",
        version=2,
        prompt_instance=PromptInstance(
            template_id="tpl_001", language="zh-CN", parameters={}
        ),
        content="{}",
        created_by="user_456",
    )
    mock_artifact_repo.get_latest_version.return_value = existing_artifact

    new_artifact = GeneratedArtifact(
        artifact_id="art_v3",
        task_id="task_123",
        artifact_type="meeting_minutes",
        version=3,
        prompt_instance=PromptInstance(
            template_id="tpl_001", language="zh-CN", parameters={}
        ),
        content="{}",
        created_by="user_456",
    )
    mock_llm_provider.generate_artifact.return_value = new_artifact

    # Execute
    result = await service.generate_artifact(
        task_id="task_123",
        transcript=sample_transcript,
        artifact_type="meeting_minutes",
        prompt_instance=PromptInstance(
            template_id="tpl_001", language="zh-CN", parameters={}
        ),
        template=sample_template,
    )

    # Verify
    assert result.version == 3
    call_kwargs = mock_llm_provider.generate_artifact.call_args.kwargs
    assert call_kwargs["version"] == 3


@pytest.mark.asyncio
async def test_first_version_without_repo(
    mock_llm_provider, sample_template, sample_transcript, sample_artifact
):
    """Test first version defaults to 1 without repository"""
    # Setup
    service = ArtifactGenerationService(llm_provider=mock_llm_provider)
    mock_llm_provider.generate_artifact.return_value = sample_artifact

    # Execute
    result = await service.generate_artifact(
        task_id="task_123",
        transcript=sample_transcript,
        artifact_type="meeting_minutes",
        prompt_instance=PromptInstance(
            template_id="tpl_001", language="zh-CN", parameters={}
        ),
        template=sample_template,
    )

    # Verify
    assert result.version == 1


# ============================================================================
# Participant Extraction Tests
# ============================================================================


@pytest.mark.asyncio
async def test_extract_participants():
    """Test participant extraction from transcript"""
    # Setup
    service = ArtifactGenerationService(llm_provider=AsyncMock())
    transcript = TranscriptionResult(
        task_id="task_123",
        segments=[
            Segment(start_time=0.0, end_time=5.0, text="Hello", speaker="Alice"),
            Segment(start_time=5.0, end_time=10.0, text="Hi", speaker="Bob"),
            Segment(start_time=10.0, end_time=15.0, text="Hey", speaker="Alice"),
            Segment(start_time=15.0, end_time=20.0, text="Hello", speaker="Charlie"),
        ],
        full_text="Hello Hi Hey Hello",
        provider="volcano",
        language="en-US",
        duration=20.0,
    )

    # Execute
    participants = service._extract_participants(transcript)

    # Verify
    assert len(participants) == 3
    assert "Alice" in participants
    assert "Bob" in participants
    assert "Charlie" in participants
    assert participants == sorted(participants)  # Should be sorted


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_template_not_found(
    mock_llm_provider, mock_template_repo, sample_transcript
):
    """Test error when template not found"""
    # Setup
    service = ArtifactGenerationService(
        llm_provider=mock_llm_provider, template_repo=mock_template_repo
    )
    mock_template_repo.get.return_value = None

    # Execute & Verify
    with pytest.raises(ValidationError, match="模板不存在"):
        await service.generate_artifact(
            task_id="task_123",
            transcript=sample_transcript,
            artifact_type="meeting_minutes",
            prompt_instance=PromptInstance(
                template_id="nonexistent", language="zh-CN", parameters={}
            ),
        )


@pytest.mark.asyncio
async def test_unsupported_language(
    mock_llm_provider, sample_template, sample_transcript
):
    """Test error when language not supported"""
    # Setup
    service = ArtifactGenerationService(llm_provider=mock_llm_provider)

    # Execute & Verify
    with pytest.raises(ValidationError, match="模板不支持语言"):
        await service.generate_artifact(
            task_id="task_123",
            transcript=sample_transcript,
            artifact_type="meeting_minutes",
            prompt_instance=PromptInstance(
                template_id="tpl_001", language="fr-FR", parameters={}
            ),
            template=sample_template,
        )


@pytest.mark.asyncio
async def test_llm_generation_failure(
    mock_llm_provider, sample_template, sample_transcript
):
    """Test error handling when LLM generation fails"""
    # Setup
    service = ArtifactGenerationService(llm_provider=mock_llm_provider)
    mock_llm_provider.generate_artifact.side_effect = LLMError(
        "API rate limit exceeded", provider="gemini"
    )

    # Execute & Verify
    with pytest.raises(LLMError):
        await service.generate_artifact(
            task_id="task_123",
            transcript=sample_transcript,
            artifact_type="meeting_minutes",
            prompt_instance=PromptInstance(
                template_id="tpl_001", language="zh-CN", parameters={}
            ),
            template=sample_template,
        )


@pytest.mark.asyncio
async def test_template_repo_not_configured(
    mock_llm_provider, sample_transcript
):
    """Test error when template repo not configured but needed"""
    # Setup
    service = ArtifactGenerationService(llm_provider=mock_llm_provider)

    # Execute & Verify
    with pytest.raises(ValidationError, match="Template repository not configured"):
        await service.generate_artifact(
            task_id="task_123",
            transcript=sample_transcript,
            artifact_type="meeting_minutes",
            prompt_instance=PromptInstance(
                template_id="tpl_001", language="zh-CN", parameters={}
            ),
        )


# ============================================================================
# List and Version Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_artifacts(mock_llm_provider, mock_artifact_repo):
    """Test listing artifacts grouped by type"""
    # Setup
    service = ArtifactGenerationService(
        llm_provider=mock_llm_provider, artifact_repo=mock_artifact_repo
    )

    artifacts = [
        GeneratedArtifact(
            artifact_id="art_1",
            task_id="task_123",
            artifact_type="meeting_minutes",
            version=1,
            prompt_instance=PromptInstance(
                template_id="tpl_001", language="zh-CN", parameters={}
            ),
            content="{}",
            created_by="user_456",
        ),
        GeneratedArtifact(
            artifact_id="art_2",
            task_id="task_123",
            artifact_type="meeting_minutes",
            version=2,
            prompt_instance=PromptInstance(
                template_id="tpl_001", language="zh-CN", parameters={}
            ),
            content="{}",
            created_by="user_456",
        ),
        GeneratedArtifact(
            artifact_id="art_3",
            task_id="task_123",
            artifact_type="action_items",
            version=1,
            prompt_instance=PromptInstance(
                template_id="tpl_002", language="zh-CN", parameters={}
            ),
            content="{}",
            created_by="user_456",
        ),
    ]
    mock_artifact_repo.list_by_task.return_value = artifacts

    # Execute
    result = await service.list_artifacts("task_123")

    # Verify
    assert len(result) == 2
    assert "meeting_minutes" in result
    assert "action_items" in result
    assert len(result["meeting_minutes"]) == 2
    assert len(result["action_items"]) == 1
    # Should be sorted by version descending
    assert result["meeting_minutes"][0].version == 2
    assert result["meeting_minutes"][1].version == 1


@pytest.mark.asyncio
async def test_get_versions(mock_llm_provider, mock_artifact_repo):
    """Test getting all versions of specific artifact type"""
    # Setup
    service = ArtifactGenerationService(
        llm_provider=mock_llm_provider, artifact_repo=mock_artifact_repo
    )

    versions = [
        GeneratedArtifact(
            artifact_id=f"art_v{i}",
            task_id="task_123",
            artifact_type="meeting_minutes",
            version=i,
            prompt_instance=PromptInstance(
                template_id="tpl_001", language="zh-CN", parameters={}
            ),
            content="{}",
            created_by="user_456",
        )
        for i in [1, 2, 3]
    ]
    mock_artifact_repo.list_by_type.return_value = versions

    # Execute
    result = await service.get_versions("task_123", "meeting_minutes")

    # Verify
    assert len(result) == 3
    # Should be sorted by version descending
    assert result[0].version == 3
    assert result[1].version == 2
    assert result[2].version == 1


@pytest.mark.asyncio
async def test_list_artifacts_without_repo(mock_llm_provider):
    """Test error when listing artifacts without repository"""
    # Setup
    service = ArtifactGenerationService(llm_provider=mock_llm_provider)

    # Execute & Verify
    with pytest.raises(ValidationError, match="Artifact repository not configured"):
        await service.list_artifacts("task_123")


@pytest.mark.asyncio
async def test_get_versions_without_repo(mock_llm_provider):
    """Test error when getting versions without repository"""
    # Setup
    service = ArtifactGenerationService(llm_provider=mock_llm_provider)

    # Execute & Verify
    with pytest.raises(ValidationError, match="Artifact repository not configured"):
        await service.get_versions("task_123", "meeting_minutes")
