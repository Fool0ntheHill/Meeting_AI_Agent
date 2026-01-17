#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试任务

用于测试 API 的临时任务数据
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.dependencies import get_db
from src.database.repositories import TaskRepository, TranscriptRepository, ArtifactRepository
from src.core.models import TaskState, Segment, TranscriptionResult
import uuid

def create_test_task():
    """创建一个测试任务"""
    print("=" * 80)
    print("  创建测试任务")
    print("=" * 80)
    print()
    
    db = next(get_db())
    
    try:
        # 1. 创建任务
        print("1. 创建任务...")
        task_repo = TaskRepository(db)
        
        task_id = "task_example_001"
        user_id = "user_test_user_001"
        
        # 检查任务是否已存在
        existing_task = task_repo.get_by_id(task_id)
        if existing_task:
            print(f"   ⚠️  任务已存在: {task_id}")
            print(f"   状态: {existing_task.state}")
            print(f"   用户: {existing_task.user_id}")
            
            # 询问是否删除重建
            response = input("\n   是否删除并重新创建? (y/n): ")
            if response.lower() == 'y':
                # 删除旧任务
                db.delete(existing_task)
                db.commit()
                print("   ✅ 旧任务已删除")
            else:
                print("   保留现有任务")
                return task_id
        
        # 创建新任务
        task = task_repo.create(
            task_id=task_id,
            user_id=user_id,
            tenant_id="tenant_test_user_001",
            audio_files=["https://example.com/test_meeting.wav"],
            file_order=[0],
            meeting_type="weekly_sync",
            asr_language="zh-CN+en-US",
            output_language="zh-CN",
            skip_speaker_recognition=False,
        )
        
        print(f"   ✅ 任务已创建: {task_id}")
        print(f"   用户: {user_id}")
        print(f"   状态: {task.state}")
        print()
        
        # 2. 更新任务状态为 SUCCESS
        print("2. 更新任务状态...")
        task_repo.update_state(task_id, TaskState.SUCCESS)
        print(f"   ✅ 任务状态已更新为: SUCCESS")
        print()
        
        # 3. 创建转写记录
        print("3. 创建转写记录...")
        transcript_repo = TranscriptRepository(db)
        
        # 创建一些示例转写片段
        segments = [
            Segment(
                start_time=0.0,
                end_time=5.0,
                text="大家好，欢迎参加本周的技术评审会议。",
                speaker="张三",
                confidence=0.95,
            ),
            Segment(
                start_time=5.5,
                end_time=10.0,
                text="今天我们主要讨论新功能的技术方案。",
                speaker="张三",
                confidence=0.93,
            ),
            Segment(
                start_time=10.5,
                end_time=15.0,
                text="我认为我们应该采用微服务架构。",
                speaker="李四",
                confidence=0.91,
            ),
            Segment(
                start_time=15.5,
                end_time=20.0,
                text="这个方案的优点是可扩展性强。",
                speaker="李四",
                confidence=0.94,
            ),
            Segment(
                start_time=20.5,
                end_time=25.0,
                text="我同意，但是我们需要考虑运维成本。",
                speaker="王五",
                confidence=0.92,
            ),
        ]
        
        # 创建 TranscriptionResult 对象
        full_text = " ".join([seg.text for seg in segments])
        transcription_result = TranscriptionResult(
            segments=segments,
            full_text=full_text,
            duration=25.0,
            language="zh-CN",
            provider="test",
        )
        
        transcript = transcript_repo.create(
            transcript_id=f"transcript_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            transcript_result=transcription_result,
        )
        
        print(f"   ✅ 转写记录已创建")
        print(f"   片段数: {len(segments)}")
        print(f"   总时长: 25.0 秒")
        print(f"   说话人: 张三, 李四, 王五")
        print()
        
        # 4. 提交事务
        db.commit()
        
        print("=" * 80)
        print("  ✅ 测试任务创建成功!")
        print("=" * 80)
        print()
        print(f"任务 ID: {task_id}")
        print(f"用户 ID: {user_id}")
        print(f"状态: SUCCESS")
        print(f"转写片段: {len(segments)} 个")
        print()
        print("现在可以运行测试脚本:")
        print(f"  python scripts/test_artifacts_api.py")
        print()
        
        return task_id
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    create_test_task()
