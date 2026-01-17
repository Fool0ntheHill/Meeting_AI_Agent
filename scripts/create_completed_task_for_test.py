"""
创建一个已完成的任务用于集成测试
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from src.database.session import session_scope
from src.database.models import Task, GeneratedArtifactRecord, TranscriptRecord, SpeakerMapping
from src.core.models import TaskState
import json
import uuid

def create_completed_task():
    """创建一个已完成的任务"""
    
    task_id = "task_integration_test_completed"
    
    with session_scope() as session:
        # 检查任务是否已存在
        existing_task = session.query(Task).filter(Task.task_id == task_id).first()
        if existing_task:
            print(f"✓ 任务已存在: {task_id}")
            print(f"  状态: {existing_task.state}")
            return task_id
        
        # 创建任务
        task = Task(
            task_id=task_id,
            user_id="user_test_user",  # 匹配 JWT token 中的 user_id
            tenant_id="tenant_test_user",  # 匹配 JWT token 中的 tenant_id
            state=TaskState.SUCCESS.value,
            audio_files=json.dumps(["test_audio.wav"]),
            file_order=json.dumps([0]),
            meeting_type="common",
            skip_speaker_recognition=False,
            asr_language="zh-CN",
            output_language="zh-CN",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            completed_at=datetime.now(),
        )
        session.add(task)
        
        # 创建转写记录
        transcript_segments = [
            {
                "start_time": 0.0,
                "end_time": 5.0,
                "text": "大家好，欢迎参加今天的会议。",
                "speaker": "speaker_0",
                "confidence": 0.95
            },
            {
                "start_time": 5.5,
                "end_time": 10.0,
                "text": "今天我们主要讨论项目进展。",
                "speaker": "speaker_1",
                "confidence": 0.92
            }
        ]
        
        transcript = TranscriptRecord(
            transcript_id=f"transcript_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            segments=json.dumps(transcript_segments, ensure_ascii=False),
            full_text="大家好，欢迎参加今天的会议。今天我们主要讨论项目进展。",
            duration=10.0,
            language="zh-CN",
            provider="volcano",
            created_at=datetime.now(),
        )
        session.add(transcript)
        
        # 创建说话人映射
        speaker_mappings = [
            SpeakerMapping(
                task_id=task_id,
                speaker_label="speaker_0",
                speaker_name="张三",
                confidence=0.95,
            ),
            SpeakerMapping(
                task_id=task_id,
                speaker_label="speaker_1",
                speaker_name="李四",
                confidence=0.92,
            )
        ]
        for mapping in speaker_mappings:
            session.add(mapping)
        
        # 创建会议纪要衍生内容
        artifact = GeneratedArtifactRecord(
            artifact_id=f"artifact_{uuid.uuid4().hex[:16]}",
            task_id=task_id,
            artifact_type="meeting_minutes",
            version=1,
            prompt_instance=json.dumps({
                "template_id": "tpl_default_meeting_minutes",
                "language": "zh-CN",
                "parameters": {}
            }, ensure_ascii=False),
            content=json.dumps({
                "title": "项目进展讨论会议",
                "date": "2026-01-16",
                "participants": ["张三", "李四"],
                "summary": "本次会议主要讨论了项目的当前进展情况。",
                "key_points": [
                    "项目按计划推进",
                    "需要关注技术风险"
                ],
                "action_items": [
                    {
                        "description": "完成技术方案评审",
                        "assignee": "张三",
                        "deadline": "2026-01-20"
                    }
                ]
            }, ensure_ascii=False),
            created_by="user_test_user",  # 匹配 JWT token 中的 user_id
            created_at=datetime.now(),
        )
        
        session.add(artifact)
        session.commit()
        
        print(f"✓ 成功创建已完成的任务: {task_id}")
        print(f"  状态: {task.state}")
        print(f"  转写片段: {len(transcript_segments)} 个")
        print(f"  说话人: {len(speaker_mappings)} 个")
        print(f"  衍生内容: 1 个 (会议纪要)")
        
        return task_id

if __name__ == "__main__":
    task_id = create_completed_task()
    print(f"\n可以在集成测试中使用此任务 ID: {task_id}")
