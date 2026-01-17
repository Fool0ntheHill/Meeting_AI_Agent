#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修正与重新生成 API"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.session import init_db, get_session
from src.database.repositories import (
    TaskRepository,
    TranscriptRepository,
    SpeakerMappingRepository,
    ArtifactRepository,
)
from src.core.models import TaskState, TranscriptionResult, Segment
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_transcript_correction():
    """测试转写修正"""
    print("\n" + "=" * 60)
    print("测试转写修正")
    print("=" * 60)
    
    # 初始化数据库
    init_db()
    
    with get_session() as session:
        task_repo = TaskRepository(session)
        transcript_repo = TranscriptRepository(session)
        
        # 1. 创建测试任务
        task = task_repo.create(
            task_id="test_task_correct_001",
            user_id="test_user",
            tenant_id="test_tenant",
            meeting_type="common",
            audio_files=["test.wav"],
            file_order=[0],
            asr_language="zh-CN",
            output_language="zh-CN",
            skip_speaker_recognition=False,
            hotword_set_id=None,
            preferred_asr_provider="volcano",
        )
        
        # 更新任务状态为成功
        task_repo.update_state(
            task_id="test_task_correct_001",
            state=TaskState.SUCCESS,
        )
        
        print(f"✅ 任务创建成功: {task.task_id}")
        
        # 2. 创建转写记录
        transcript_result = TranscriptionResult(
            segments=[
                Segment(
                    text="这是原始转写文本",
                    start_time=0.0,
                    end_time=2.0,
                    speaker="Speaker 0",
                    confidence=0.95,
                )
            ],
            full_text="这是原始转写文本",
            duration=2.0,
            language="zh-CN",
            provider="volcano",
        )
        
        transcript = transcript_repo.create(
            transcript_id="transcript_001",
            task_id="test_task_correct_001",
            transcript_result=transcript_result,
        )
        
        print(f"✅ 转写记录创建成功")
        print(f"   原始文本: {transcript.full_text}")
        
        # 3. 修正转写文本
        corrected_text = "这是修正后的转写文本"
        transcript_repo.update_full_text(
            task_id="test_task_correct_001",
            full_text=corrected_text,
            is_corrected=True,
        )
        
        # 验证修正
        updated_transcript = transcript_repo.get_by_task_id("test_task_correct_001")
        print(f"✅ 转写文本已修正")
        print(f"   修正后文本: {updated_transcript.full_text}")
        print(f"   是否修正: {updated_transcript.is_corrected}")
        
        # 清理
        task_repo.delete("test_task_correct_001")
        print("✅ 测试数据已清理")


def test_speaker_correction():
    """测试说话人修正"""
    print("\n" + "=" * 60)
    print("测试说话人修正")
    print("=" * 60)
    
    with get_session() as session:
        task_repo = TaskRepository(session)
        transcript_repo = TranscriptRepository(session)
        speaker_repo = SpeakerMappingRepository(session)
        
        # 1. 创建测试任务
        task = task_repo.create(
            task_id="test_task_speaker_001",
            user_id="test_user",
            tenant_id="test_tenant",
            meeting_type="common",
            audio_files=["test.wav"],
            file_order=[0],
            asr_language="zh-CN",
            output_language="zh-CN",
            skip_speaker_recognition=False,
            hotword_set_id=None,
            preferred_asr_provider="volcano",
        )
        
        task_repo.update_state(
            task_id="test_task_speaker_001",
            state=TaskState.SUCCESS,
        )
        
        print(f"✅ 任务创建成功: {task.task_id}")
        
        # 2. 创建说话人映射
        speaker_repo.create_or_update(
            task_id="test_task_speaker_001",
            speaker_label="Speaker 0",
            speaker_name="未知说话人 0",
            confidence=0.8,
        )
        
        speaker_repo.create_or_update(
            task_id="test_task_speaker_001",
            speaker_label="Speaker 1",
            speaker_name="未知说话人 1",
            confidence=0.75,
        )
        
        print("✅ 说话人映射创建成功")
        
        # 3. 创建转写记录
        transcript_result = TranscriptionResult(
            segments=[
                Segment(
                    text="大家好",
                    start_time=0.0,
                    end_time=1.0,
                    speaker="Speaker 0",
                    confidence=0.95,
                ),
                Segment(
                    text="你好",
                    start_time=1.0,
                    end_time=2.0,
                    speaker="Speaker 1",
                    confidence=0.90,
                ),
            ],
            full_text="大家好 你好",
            duration=2.0,
            language="zh-CN",
            provider="volcano",
        )
        
        transcript_repo.create(
            transcript_id="transcript_002",
            task_id="test_task_speaker_001",
            transcript_result=transcript_result,
        )
        
        # 4. 修正说话人映射
        speaker_mapping = {
            "Speaker 0": "张三",
            "Speaker 1": "李四",
        }
        
        for label, name in speaker_mapping.items():
            speaker_repo.update_speaker_name(
                task_id="test_task_speaker_001",
                speaker_label=label,
                speaker_name=name,
            )
        
        print("✅ 说话人映射已修正")
        
        # 验证修正
        mappings = speaker_repo.get_by_task_id("test_task_speaker_001")
        for mapping in mappings:
            print(f"   {mapping.speaker_label} -> {mapping.speaker_name} (修正: {mapping.is_corrected})")
        
        # 5. 更新转写片段中的说话人
        transcript = transcript_repo.get_by_task_id("test_task_speaker_001")
        segments = transcript.get_segments_list()
        
        for segment in segments:
            if segment.get("speaker") in speaker_mapping:
                segment["speaker"] = speaker_mapping[segment["speaker"]]
        
        transcript_repo.update_segments("test_task_speaker_001", segments)
        
        # 验证更新
        updated_transcript = transcript_repo.get_by_task_id("test_task_speaker_001")
        updated_segments = updated_transcript.get_segments_list()
        
        print("✅ 转写片段已更新")
        for seg in updated_segments:
            print(f"   [{seg['speaker']}]: {seg['text']}")
        
        # 清理
        task_repo.delete("test_task_speaker_001")
        print("✅ 测试数据已清理")


def test_artifact_regeneration():
    """测试衍生内容重新生成"""
    print("\n" + "=" * 60)
    print("测试衍生内容重新生成")
    print("=" * 60)
    
    with get_session() as session:
        task_repo = TaskRepository(session)
        artifact_repo = ArtifactRepository(session)
        
        # 1. 创建测试任务
        task = task_repo.create(
            task_id="test_task_artifact_001",
            user_id="test_user",
            tenant_id="test_tenant",
            meeting_type="common",
            audio_files=["test.wav"],
            file_order=[0],
            asr_language="zh-CN",
            output_language="zh-CN",
            skip_speaker_recognition=False,
            hotword_set_id=None,
            preferred_asr_provider="volcano",
        )
        
        task_repo.update_state(
            task_id="test_task_artifact_001",
            state=TaskState.SUCCESS,
        )
        
        print(f"✅ 任务创建成功: {task.task_id}")
        
        # 2. 创建第一个版本
        artifact1 = artifact_repo.create(
            artifact_id="artifact_001",
            task_id="test_task_artifact_001",
            artifact_type="meeting_minutes",
            version=1,
            prompt_instance={"template_id": "default", "language": "zh-CN"},
            content={"title": "会议纪要 v1", "content": "这是第一版"},
            created_by="test_user",
        )
        
        print(f"✅ 衍生内容 v1 创建成功: {artifact1.artifact_id}")
        
        # 3. 创建第二个版本
        artifact2 = artifact_repo.create(
            artifact_id="artifact_002",
            task_id="test_task_artifact_001",
            artifact_type="meeting_minutes",
            version=2,
            prompt_instance={"template_id": "detailed", "language": "zh-CN"},
            content={"title": "会议纪要 v2", "content": "这是第二版(更详细)"},
            created_by="test_user",
            metadata={"regenerated": True},
        )
        
        print(f"✅ 衍生内容 v2 创建成功: {artifact2.artifact_id}")
        
        # 4. 查询所有版本
        artifacts = artifact_repo.get_by_task_and_type(
            task_id="test_task_artifact_001",
            artifact_type="meeting_minutes",
        )
        
        print(f"✅ 查询到 {len(artifacts)} 个版本:")
        for artifact in artifacts:
            content = artifact.get_content_dict()
            print(f"   v{artifact.version}: {content.get('title')}")
        
        # 5. 获取最新版本
        latest = artifact_repo.get_latest_by_task(
            task_id="test_task_artifact_001",
            artifact_type="meeting_minutes",
        )
        
        print(f"✅ 最新版本: v{latest.version}")
        
        # 清理
        task_repo.delete("test_task_artifact_001")
        print("✅ 测试数据已清理")


def main():
    """主函数"""
    print("=" * 60)
    print("修正与重新生成 API 测试")
    print("=" * 60)
    
    try:
        test_transcript_correction()
        test_speaker_correction()
        test_artifact_regeneration()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
