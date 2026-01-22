# -*- coding: utf-8 -*-
"""
测试 Pipeline 错误处理集成

模拟各种错误场景，验证错误码是否正确设置
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.pipeline import PipelineService
from src.core.models import PromptInstance, ASRLanguage, OutputLanguage
from src.database.session import session_scope
from src.database.repositories import TaskRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_asr_error():
    """测试 ASR 阶段错误处理"""
    print("\n" + "=" * 80)
    print("测试 1: ASR 阶段 SSL 错误")
    print("=" * 80)
    
    # 创建 mock services
    transcription_service = AsyncMock()
    transcription_service.transcribe.side_effect = Exception("SSL: UNEXPECTED_EOF_WHILE_READING")
    
    speaker_recognition_service = AsyncMock()
    correction_service = AsyncMock()
    artifact_generation_service = AsyncMock()
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        
        # 创建测试任务
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        task_repo.create(
            task_id=task_id,
            user_id="test_user",
            tenant_id="test_tenant",
            meeting_type="test",
            audio_files=["test.ogg"],
            file_order=[0],
            audio_duration=100.0,
        )
        
        # 创建 Pipeline
        pipeline = PipelineService(
            transcription_service=transcription_service,
            speaker_recognition_service=speaker_recognition_service,
            correction_service=correction_service,
            artifact_generation_service=artifact_generation_service,
            task_repo=task_repo,
        )
        
        # 执行 Pipeline（应该失败）
        try:
            await pipeline.process_meeting(
                task_id=task_id,
                audio_files=["test.ogg"],
                file_order=[0],
                prompt_instance=PromptInstance(
                    template_id="test",
                    parameters={},
                    output_language=OutputLanguage.ZH_CN,
                ),
                user_id="test_user",
                tenant_id="test_tenant",
                asr_language=ASRLanguage.ZH_EN,
            )
        except Exception as e:
            print(f"✓ Pipeline 正确抛出异常: {type(e).__name__}")
        
        # 检查任务状态
        task = task_repo.get_by_id(task_id)
        print(f"\n任务状态:")
        print(f"  State: {task.state}")
        print(f"  Error Code: {task.error_code}")
        print(f"  Error Message: {task.error_message}")
        print(f"  Retryable: {task.retryable}")
        
        # 验证
        assert task.state == "failed", f"Expected state=failed, got {task.state}"
        assert task.error_code == "NETWORK_TIMEOUT", f"Expected NETWORK_TIMEOUT, got {task.error_code}"
        assert task.retryable == True, f"Expected retryable=True, got {task.retryable}"
        
        print(f"\n✓ ASR 错误处理测试通过")


async def test_llm_error():
    """测试 LLM 阶段错误处理"""
    print("\n" + "=" * 80)
    print("测试 2: LLM 阶段内容过滤错误")
    print("=" * 80)
    
    # 创建 mock services
    from src.core.models import TranscriptionResult, Segment
    
    transcription_service = AsyncMock()
    transcription_service.transcribe.return_value = (
        TranscriptionResult(
            segments=[Segment(start_time=0, end_time=10, text="测试", speaker="Speaker 1")],
            full_text="测试",
            duration=10.0,
            language="zh-CN",
            provider="volcano",
        ),
        "http://test.com/audio.ogg",
        "/tmp/audio.ogg",
    )
    
    speaker_recognition_service = AsyncMock()
    speaker_recognition_service.recognize_speakers.return_value = {}
    
    correction_service = AsyncMock()
    correction_service.correct_speakers.return_value = TranscriptionResult(
        segments=[Segment(start_time=0, end_time=10, text="测试", speaker="Speaker 1")],
        full_text="测试",
        duration=10.0,
        language="zh-CN",
        provider="volcano",
    )
    
    artifact_generation_service = AsyncMock()
    artifact_generation_service.generate_artifact.side_effect = Exception(
        "Content blocked by safety filters"
    )
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        
        # 创建测试任务
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        task_repo.create(
            task_id=task_id,
            user_id="test_user",
            tenant_id="test_tenant",
            meeting_type="test",
            audio_files=["test.ogg"],
            file_order=[0],
            audio_duration=100.0,
        )
        
        # 创建 Pipeline
        pipeline = PipelineService(
            transcription_service=transcription_service,
            speaker_recognition_service=speaker_recognition_service,
            correction_service=correction_service,
            artifact_generation_service=artifact_generation_service,
            task_repo=task_repo,
        )
        
        # 执行 Pipeline（应该失败）
        try:
            await pipeline.process_meeting(
                task_id=task_id,
                audio_files=["test.ogg"],
                file_order=[0],
                prompt_instance=PromptInstance(
                    template_id="test",
                    parameters={},
                    output_language=OutputLanguage.ZH_CN,
                ),
                user_id="test_user",
                tenant_id="test_tenant",
                asr_language=ASRLanguage.ZH_EN,
            )
        except Exception as e:
            print(f"✓ Pipeline 正确抛出异常: {type(e).__name__}")
        
        # 检查任务状态
        task = task_repo.get_by_id(task_id)
        print(f"\n任务状态:")
        print(f"  State: {task.state}")
        print(f"  Error Code: {task.error_code}")
        print(f"  Error Message: {task.error_message}")
        print(f"  Retryable: {task.retryable}")
        print(f"  Progress: {task.progress}%")
        
        # 验证
        assert task.state == "failed", f"Expected state=failed, got {task.state}"
        assert task.error_code == "LLM_CONTENT_BLOCKED", f"Expected LLM_CONTENT_BLOCKED, got {task.error_code}"
        assert task.retryable == False, f"Expected retryable=False, got {task.retryable}"
        assert task.progress == 70.0, f"Expected progress=70.0, got {task.progress}"
        
        print(f"\n✓ LLM 错误处理测试通过")


async def test_voiceprint_error():
    """测试声纹识别阶段错误处理"""
    print("\n" + "=" * 80)
    print("测试 3: 声纹识别阶段鉴权错误")
    print("=" * 80)
    
    # 创建 mock services
    from src.core.models import TranscriptionResult, Segment
    
    transcription_service = AsyncMock()
    transcription_service.transcribe.return_value = (
        TranscriptionResult(
            segments=[Segment(start_time=0, end_time=10, text="测试", speaker="Speaker 1")],
            full_text="测试",
            duration=10.0,
            language="zh-CN",
            provider="volcano",
        ),
        "http://test.com/audio.ogg",
        "/tmp/audio.ogg",
    )
    
    speaker_recognition_service = AsyncMock()
    speaker_recognition_service.recognize_speakers.side_effect = Exception(
        "Authentication failed: Invalid API key"
    )
    
    correction_service = AsyncMock()
    artifact_generation_service = AsyncMock()
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        
        # 创建测试任务
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        task_repo.create(
            task_id=task_id,
            user_id="test_user",
            tenant_id="test_tenant",
            meeting_type="test",
            audio_files=["test.ogg"],
            file_order=[0],
            audio_duration=100.0,
        )
        
        # 创建 Pipeline
        pipeline = PipelineService(
            transcription_service=transcription_service,
            speaker_recognition_service=speaker_recognition_service,
            correction_service=correction_service,
            artifact_generation_service=artifact_generation_service,
            task_repo=task_repo,
        )
        
        # 执行 Pipeline（应该失败）
        try:
            await pipeline.process_meeting(
                task_id=task_id,
                audio_files=["test.ogg"],
                file_order=[0],
                prompt_instance=PromptInstance(
                    template_id="test",
                    parameters={},
                    output_language=OutputLanguage.ZH_CN,
                ),
                user_id="test_user",
                tenant_id="test_tenant",
                asr_language=ASRLanguage.ZH_EN,
                skip_speaker_recognition=False,  # 不跳过声纹识别
            )
        except Exception as e:
            print(f"✓ Pipeline 正确抛出异常: {type(e).__name__}")
        
        # 检查任务状态
        task = task_repo.get_by_id(task_id)
        print(f"\n任务状态:")
        print(f"  State: {task.state}")
        print(f"  Error Code: {task.error_code}")
        print(f"  Error Message: {task.error_message}")
        print(f"  Retryable: {task.retryable}")
        
        # 验证
        assert task.state == "failed", f"Expected state=failed, got {task.state}"
        assert task.error_code == "VOICEPRINT_AUTH_ERROR", f"Expected VOICEPRINT_AUTH_ERROR, got {task.error_code}"
        assert task.retryable == False, f"Expected retryable=False, got {task.retryable}"
        
        print(f"\n✓ 声纹识别错误处理测试通过")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("Pipeline 错误处理集成测试")
    print("=" * 80)
    
    try:
        await test_asr_error()
        await test_llm_error()
        await test_voiceprint_error()
        
        print("\n" + "=" * 80)
        print("✓ 所有测试通过！")
        print("=" * 80)
        print("\n错误处理已成功集成到 Pipeline 中：")
        print("  1. ASR 阶段错误 → 自动分类并设置错误码")
        print("  2. 声纹识别阶段错误 → 自动分类并设置错误码")
        print("  3. LLM 生成阶段错误 → 自动分类并设置错误码")
        print("  4. 错误信息包含：error_code, error_message, error_details, retryable")
        print("  5. 前端可以基于 error_code 显示友好的错误提示")
        print("\n")
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
