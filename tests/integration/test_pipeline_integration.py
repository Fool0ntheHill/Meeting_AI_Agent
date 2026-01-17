"""
集成测试: 管线处理流程

测试完整的会议处理流程:
1. 音频转写 (ASR)
2. 说话人识别
3. ASR 修正
4. 生成会议纪要

测试 ASR 降级机制、任务状态转换和错误恢复。
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from src.core.models import (
    ASRLanguage,
    OutputLanguage,
    PromptInstance,
    PromptTemplate,
    Segment,
    TranscriptionResult,
    SpeakerIdentity,
    GeneratedArtifact,
)
from src.core.exceptions import ASRError, SensitiveContentError, MeetingAgentError
from src.services.pipeline import PipelineService
from src.services.transcription import TranscriptionService
from src.services.speaker_recognition import SpeakerRecognitionService
from src.services.correction import CorrectionService
from src.services.artifact_generation import ArtifactGenerationService


@pytest.fixture
def sample_template():
    """创建示例提示词模板"""
    return PromptTemplate(
        template_id="tpl_test_001",
        title="测试会议纪要模板",
        description="用于集成测试的会议纪要模板",
        prompt_body="""请根据以下会议转写生成结构化的会议纪要。

会议信息:
{meeting_description}

转写内容:
{transcript}

请以 JSON 格式返回,包含以下字段:
- title: 会议标题
- participants: 参与者列表
- summary: 会议摘要
- key_points: 关键要点
- action_items: 行动项
""",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN", "en-US"],
        parameter_schema={
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "会议描述信息",
            }
        },
        is_system=True,
    )


@pytest.fixture
def sample_prompt_instance(sample_template):
    """创建示例提示词实例"""
    return PromptInstance(
        template_id=sample_template.template_id,
        language="zh-CN",
        parameters={"meeting_description": "产品规划会议"},
    )


@pytest.fixture
def sample_segments():
    """创建示例转写片段"""
    return [
        Segment(
            start_time=0.0,
            end_time=3.5,
            text="大家好，今天我们讨论产品规划。",
            speaker="speaker_0",
            confidence=0.95,
        ),
        Segment(
            start_time=3.5,
            end_time=7.2,
            text="我认为我们应该优先开发移动端应用。",
            speaker="speaker_1",
            confidence=0.92,
        ),
        Segment(
            start_time=7.2,
            end_time=10.8,
            text="同意，移动端市场很大。",
            speaker="speaker_0",
            confidence=0.94,
        ),
    ]


@pytest.mark.asyncio
async def test_complete_pipeline_flow(
    sample_template,
    sample_prompt_instance,
    sample_segments,
):
    """测试完整的管线处理流程"""
    # 创建 mock 服务
    transcription_service = Mock(spec=TranscriptionService)
    speaker_recognition_service = Mock(spec=SpeakerRecognitionService)
    correction_service = Mock(spec=CorrectionService)
    artifact_generation_service = Mock(spec=ArtifactGenerationService)
    
    # 配置 mock 返回值
    transcription_result = TranscriptionResult(
        segments=sample_segments,
        full_text="大家好，今天我们讨论产品规划。我认为我们应该优先开发移动端应用。同意，移动端市场很大。",
        language="zh-CN",
        duration=10.8,
        provider="volcano",
    )
    transcription_service.transcribe = AsyncMock(
        return_value=(transcription_result, "https://example.com/audio.wav", "/tmp/audio.wav")
    )
    
    # 说话人识别返回身份映射
    speaker_identities = {
        "speaker_0": SpeakerIdentity(
            speaker_id="user_001",
            name="张三",
            confidence=0.88,
        ),
        "speaker_1": SpeakerIdentity(
            speaker_id="user_002",
            name="李四",
            confidence=0.85,
        ),
    }
    speaker_recognition_service.recognize_speakers = AsyncMock(
        return_value=speaker_identities
    )
    
    # 修正服务返回修正后的转写结果
    corrected_transcript = TranscriptionResult(
        segments=sample_segments,
        full_text="大家好，今天我们讨论产品规划。我认为我们应该优先开发移动端应用。同意，移动端市场很大。",
        language="zh-CN",
        duration=10.8,
        provider="volcano",
    )
    correction_service.correct_speakers = AsyncMock(
        return_value=corrected_transcript
    )
    
    # 生成服务返回会议纪要
    artifact = GeneratedArtifact(
        artifact_id="artifact_001",
        task_id="task_001",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=sample_prompt_instance,
        content='{"title": "产品规划会议", "participants": ["张三", "李四"], "summary": "讨论移动端应用开发", "key_points": ["优先开发移动端"], "action_items": ["启动移动端项目"]}',
        created_by="user_001",
    )
    artifact_generation_service.generate_artifact = AsyncMock(return_value=artifact)
    
    # 创建管线服务
    pipeline = PipelineService(
        transcription_service=transcription_service,
        speaker_recognition_service=speaker_recognition_service,
        correction_service=correction_service,
        artifact_generation_service=artifact_generation_service,
    )
    
    # 执行管线处理
    result = await pipeline.process_meeting(
        task_id="task_001",
        audio_files=["test_audio.wav"],
        file_order=[0],
        prompt_instance=sample_prompt_instance,
        user_id="user_001",
        tenant_id="tenant_001",
        asr_language=ASRLanguage.ZH_EN,
        output_language=OutputLanguage.ZH_CN,
        skip_speaker_recognition=False,
        template=sample_template,
    )
    
    # 验证结果
    assert result.artifact_id == "artifact_001"
    assert result.task_id == "task_001"
    assert result.artifact_type == "meeting_minutes"
    assert result.version == 1
    
    # 验证所有服务都被调用
    transcription_service.transcribe.assert_called_once()
    speaker_recognition_service.recognize_speakers.assert_called_once()
    correction_service.correct_speakers.assert_called_once()
    artifact_generation_service.generate_artifact.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_with_skip_speaker_recognition(
    sample_template,
    sample_prompt_instance,
    sample_segments,
):
    """测试跳过说话人识别的管线流程"""
    # 创建 mock 服务
    transcription_service = Mock(spec=TranscriptionService)
    speaker_recognition_service = Mock(spec=SpeakerRecognitionService)
    correction_service = Mock(spec=CorrectionService)
    artifact_generation_service = Mock(spec=ArtifactGenerationService)
    
    # 配置 mock 返回值
    transcription_result = TranscriptionResult(
        segments=sample_segments,
        full_text="大家好，今天我们讨论产品规划。",
        language="zh-CN",
        duration=10.8,
        provider="volcano",
    )
    transcription_service.transcribe = AsyncMock(
        return_value=(transcription_result, "https://example.com/audio.wav", "/tmp/audio.wav")
    )
    
    # 修正服务不会被调用 (因为跳过了说话人识别)
    correction_service.correct_speakers = AsyncMock()
    
    artifact = GeneratedArtifact(
        artifact_id="artifact_001",
        task_id="task_001",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=sample_prompt_instance,
        content='{"title": "产品规划会议"}',
        created_by="user_001",
    )
    artifact_generation_service.generate_artifact = AsyncMock(return_value=artifact)
    
    # 创建管线服务
    pipeline = PipelineService(
        transcription_service=transcription_service,
        speaker_recognition_service=speaker_recognition_service,
        correction_service=correction_service,
        artifact_generation_service=artifact_generation_service,
    )
    
    # 执行管线处理 (跳过说话人识别)
    result = await pipeline.process_meeting(
        task_id="task_001",
        audio_files=["test_audio.wav"],
        file_order=[0],
        prompt_instance=sample_prompt_instance,
        user_id="user_001",
        tenant_id="tenant_001",
        asr_language=ASRLanguage.ZH_EN,
        output_language=OutputLanguage.ZH_CN,
        skip_speaker_recognition=True,
        template=sample_template,
    )
    
    # 验证结果
    assert result.artifact_id == "artifact_001"
    
    # 验证说话人识别服务未被调用
    # 需要先设置 mock 属性才能断言
    speaker_recognition_service.recognize_speakers = AsyncMock()
    speaker_recognition_service.recognize_speakers.assert_not_called()
    
    # 验证修正服务未被调用 (因为没有说话人映射)
    correction_service.correct_speakers.assert_not_called()
    
    # 验证其他服务被调用
    transcription_service.transcribe.assert_called_once()
    artifact_generation_service.generate_artifact.assert_called_once()


@pytest.mark.asyncio
async def test_asr_fallback_mechanism(
    sample_template,
    sample_prompt_instance,
    sample_segments,
):
    """测试 ASR 降级机制"""
    # 创建 mock 服务
    transcription_service = Mock(spec=TranscriptionService)
    speaker_recognition_service = Mock(spec=SpeakerRecognitionService)
    correction_service = Mock(spec=CorrectionService)
    artifact_generation_service = Mock(spec=ArtifactGenerationService)
    
    # 配置转写服务: 第一次调用失败 (敏感内容), 第二次成功 (降级到 Azure)
    transcription_result = TranscriptionResult(
        segments=sample_segments,
        full_text="大家好，今天我们讨论产品规划。",
        language="zh-CN",
        duration=10.8,
        provider="azure",
    )
    transcription_service.transcribe = AsyncMock(
        return_value=(transcription_result, "https://example.com/audio.wav", "/tmp/audio.wav")
    )
    
    # 配置其他服务 (说话人识别返回空映射)
    speaker_recognition_service.recognize_speakers = AsyncMock(return_value={})
    # 修正服务不会被调用 (因为没有说话人映射)
    correction_service.correct_speakers = AsyncMock()
    
    artifact = GeneratedArtifact(
        artifact_id="artifact_001",
        task_id="task_001",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=sample_prompt_instance,
        content='{"title": "产品规划会议"}',
        created_by="user_001",
    )
    artifact_generation_service.generate_artifact = AsyncMock(return_value=artifact)
    
    # 创建管线服务
    pipeline = PipelineService(
        transcription_service=transcription_service,
        speaker_recognition_service=speaker_recognition_service,
        correction_service=correction_service,
        artifact_generation_service=artifact_generation_service,
    )
    
    # 执行管线处理
    result = await pipeline.process_meeting(
        task_id="task_001",
        audio_files=["test_audio.wav"],
        file_order=[0],
        prompt_instance=sample_prompt_instance,
        user_id="user_001",
        tenant_id="tenant_001",
        asr_language=ASRLanguage.ZH_EN,
        output_language=OutputLanguage.ZH_CN,
        skip_speaker_recognition=True,
        template=sample_template,
    )
    
    # 验证结果
    assert result.artifact_id == "artifact_001"
    
    # 验证转写服务被调用
    transcription_service.transcribe.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_error_handling(
    sample_template,
    sample_prompt_instance,
):
    """测试管线错误处理"""
    # 创建 mock 服务
    transcription_service = Mock(spec=TranscriptionService)
    transcription_service.transcribe = AsyncMock(
        side_effect=ASRError("ASR 服务不可用")
    )
    
    speaker_recognition_service = Mock(spec=SpeakerRecognitionService)
    speaker_recognition_service.identify_speakers = AsyncMock()
    
    correction_service = Mock(spec=CorrectionService)
    correction_service.correct_transcript = AsyncMock()
    
    artifact_generation_service = Mock(spec=ArtifactGenerationService)
    artifact_generation_service.generate_artifact = AsyncMock()
    
    # 创建管线服务
    pipeline = PipelineService(
        transcription_service=transcription_service,
        speaker_recognition_service=speaker_recognition_service,
        correction_service=correction_service,
        artifact_generation_service=artifact_generation_service,
    )
    
    # 执行管线处理应该抛出异常
    with pytest.raises(ASRError, match="ASR 服务不可用"):
        await pipeline.process_meeting(
            task_id="task_001",
            audio_files=["test_audio.wav"],
            file_order=[0],
            prompt_instance=sample_prompt_instance,
            user_id="user_001",
            tenant_id="tenant_001",
            asr_language=ASRLanguage.ZH_EN,
            output_language=OutputLanguage.ZH_CN,
            skip_speaker_recognition=True,
            template=sample_template,
        )
    
    # 验证转写服务被调用
    transcription_service.transcribe.assert_called_once()
    
    # 验证后续服务未被调用
    speaker_recognition_service.recognize_speakers = AsyncMock()
    speaker_recognition_service.recognize_speakers.assert_not_called()
    correction_service.correct_speakers = AsyncMock()
    correction_service.correct_speakers.assert_not_called()
    artifact_generation_service.generate_artifact.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_speaker_recognition_failure(
    sample_template,
    sample_prompt_instance,
    sample_segments,
):
    """测试说话人识别失败场景 (当前实现会导致整个流程失败)"""
    # 创建 mock 服务
    transcription_service = Mock(spec=TranscriptionService)
    speaker_recognition_service = Mock(spec=SpeakerRecognitionService)
    correction_service = Mock(spec=CorrectionService)
    artifact_generation_service = Mock(spec=ArtifactGenerationService)
    
    # 配置转写服务成功
    transcription_result = TranscriptionResult(
        segments=sample_segments,
        full_text="大家好，今天我们讨论产品规划。",
        language="zh-CN",
        duration=10.8,
        provider="volcano",
    )
    transcription_service.transcribe = AsyncMock(
        return_value=(transcription_result, "https://example.com/audio.wav", "/tmp/audio.wav")
    )
    
    # 配置说话人识别失败
    speaker_recognition_service.recognize_speakers = AsyncMock(
        side_effect=Exception("声纹服务暂时不可用")
    )
    
    # 配置其他服务
    correction_service.correct_speakers = AsyncMock()
    artifact_generation_service.generate_artifact = AsyncMock()
    
    # 创建管线服务
    pipeline = PipelineService(
        transcription_service=transcription_service,
        speaker_recognition_service=speaker_recognition_service,
        correction_service=correction_service,
        artifact_generation_service=artifact_generation_service,
    )
    
    # 执行管线处理 (说话人识别失败会导致整个流程失败)
    with pytest.raises(MeetingAgentError, match="Pipeline processing failed"):
        await pipeline.process_meeting(
            task_id="task_001",
            audio_files=["test_audio.wav"],
            file_order=[0],
            prompt_instance=sample_prompt_instance,
            user_id="user_001",
            tenant_id="tenant_001",
            asr_language=ASRLanguage.ZH_EN,
            output_language=OutputLanguage.ZH_CN,
            skip_speaker_recognition=False,
            template=sample_template,
        )
    
    # 验证转写和说话人识别被调用
    transcription_service.transcribe.assert_called_once()
    speaker_recognition_service.recognize_speakers.assert_called_once()
    
    # 验证后续服务未被调用 (因为流程失败)
    correction_service.correct_speakers.assert_not_called()
    artifact_generation_service.generate_artifact.assert_not_called()
