#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建一个已完成状态的任务

快速创建一个包含完整数据的已完成任务用于测试
"""

import sys
from pathlib import Path
from datetime import datetime
import uuid

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.dependencies import get_db
from src.database.repositories import TaskRepository, TranscriptRepository, ArtifactRepository
from src.core.models import TaskState, Segment, TranscriptionResult
import json


def create_completed_task():
    """创建一个已完成状态的任务"""
    print("=" * 80)
    print("  创建已完成任务")
    print("=" * 80)
    print()
    
    db = next(get_db())
    
    try:
        # 生成唯一的任务 ID
        task_id = f"task_completed_{uuid.uuid4().hex[:8]}"
        user_id = "user_test_user"  # 匹配 JWT token 中的 user_id
        tenant_id = "tenant_test_user"  # 匹配 JWT token 中的 tenant_id
        
        print(f"任务 ID: {task_id}")
        print(f"用户 ID: {user_id}")
        print()
        
        # 1. 创建任务
        print("1. 创建任务...")
        task_repo = TaskRepository(db)
        
        task = task_repo.create(
            task_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            audio_files=["https://example.com/completed_meeting.wav"],
            file_order=[0],
            meeting_type="project_review",
            asr_language="zh-CN+en-US",
            output_language="zh-CN",
            skip_speaker_recognition=False,
        )
        print(f"   ✅ 任务已创建")
        
        # 2. 创建转写记录
        print("2. 创建转写记录...")
        transcript_repo = TranscriptRepository(db)
        
        segments = [
            Segment(
                start_time=0.0,
                end_time=5.0,
                text="大家好，欢迎参加本次项目评审会议。",
                speaker="张三",
                confidence=0.96,
            ),
            Segment(
                start_time=5.5,
                end_time=12.0,
                text="今天我们主要评审上周完成的功能模块，包括用户认证和权限管理。",
                speaker="张三",
                confidence=0.94,
            ),
            Segment(
                start_time=12.5,
                end_time=18.0,
                text="我已经完成了用户认证模块的开发和测试，所有单元测试都通过了。",
                speaker="李四",
                confidence=0.95,
            ),
            Segment(
                start_time=18.5,
                end_time=25.0,
                text="权限管理这块我遇到了一些问题，需要和后端团队协调接口设计。",
                speaker="王五",
                confidence=0.93,
            ),
            Segment(
                start_time=25.5,
                end_time=32.0,
                text="没问题，我们可以在会后单独讨论接口细节。整体来看进度符合预期。",
                speaker="张三",
                confidence=0.95,
            ),
            Segment(
                start_time=32.5,
                end_time=38.0,
                text="下周我们需要完成集成测试，请大家提前准备好测试环境。",
                speaker="张三",
                confidence=0.94,
            ),
        ]
        
        full_text = " ".join([seg.text for seg in segments])
        transcription_result = TranscriptionResult(
            segments=segments,
            full_text=full_text,
            duration=38.0,
            language="zh-CN",
            provider="volcano",
        )
        
        transcript = transcript_repo.create(
            transcript_id=f"transcript_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            transcript_result=transcription_result,
        )
        print(f"   ✅ 转写记录已创建 ({len(segments)} 个片段)")
        
        # 3. 创建会议纪要
        print("3. 创建会议纪要...")
        artifact_repo = ArtifactRepository(db)
        
        meeting_minutes_content = {
            "title": "项目评审会议",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "participants": ["张三", "李四", "王五"],
            "summary": "本次会议对上周完成的用户认证和权限管理功能模块进行了评审。用户认证模块已完成开发和测试，权限管理模块需要进一步协调接口设计。",
            "key_points": [
                "用户认证模块开发完成，所有单元测试通过",
                "权限管理模块需要协调后端接口设计",
                "整体进度符合预期",
                "下周需要完成集成测试"
            ],
            "action_items": [
                {
                    "description": "协调权限管理接口设计",
                    "assignee": "王五",
                    "deadline": "本周五"
                },
                {
                    "description": "准备集成测试环境",
                    "assignee": "全体成员",
                    "deadline": "下周一"
                }
            ]
        }
        
        prompt_instance = {
            "template_id": "tpl_default_meeting_minutes",
            "language": "zh-CN",
            "parameters": {}
        }
        
        artifact = artifact_repo.create(
            artifact_id=f"artifact_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            artifact_type="meeting_minutes",
            version=1,
            prompt_instance=prompt_instance,
            content=json.dumps(meeting_minutes_content, ensure_ascii=False),
            created_by=user_id,
        )
        print(f"   ✅ 会议纪要已创建")
        
        # 4. 更新任务状态为 SUCCESS
        print("4. 更新任务状态...")
        task_repo.update_state(task_id, TaskState.SUCCESS)
        print(f"   ✅ 任务状态已更新为 SUCCESS")
        
        # 5. 提交事务
        db.commit()
        
        print()
        print("=" * 80)
        print("  ✅ 已完成任务创建成功!")
        print("=" * 80)
        print()
        print(f"任务 ID: {task_id}")
        print(f"用户 ID: {user_id}")
        print(f"租户 ID: {tenant_id}")
        print(f"状态: SUCCESS")
        print(f"转写片段: {len(segments)} 个")
        print(f"说话人: 张三, 李四, 王五")
        print(f"会议纪要: 已生成")
        print()
        print("可以使用以下命令查看任务:")
        print(f"  curl http://localhost:8000/api/v1/tasks/{task_id}")
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
    create_completed_task()
