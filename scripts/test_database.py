#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试数据库层功能"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import init_db, session_scope
from src.database.repositories import (
    TaskRepository,
    TranscriptRepository,
    SpeakerMappingRepository,
    ArtifactRepository,
    PromptTemplateRepository,
)
from src.core.models import (
    TranscriptionResult,
    Segment,
    PromptInstance,
    MeetingMinutes,
)
from datetime import datetime


def test_database():
    """测试数据库基本功能"""
    print("=" * 80)
    print("数据库层测试")
    print("=" * 80)
    print()

    # 1. 初始化数据库
    print("[1/7] 初始化数据库...")
    db_path = "test_meeting_agent.db"
    init_db(f"sqlite:///./{db_path}", echo=False)
    print(f"✓ 数据库已创建: {db_path}")
    print()

    # 2. 创建任务
    print("[2/7] 创建任务...")
    with session_scope() as session:
        task_repo = TaskRepository(session)
        task = task_repo.create(
            task_id="task_test_001",
            user_id="user_123",
            tenant_id="tenant_456",
            meeting_type="common",
            audio_files=["meeting1.ogg", "meeting2.ogg"],
            file_order=[0, 1],
            asr_language="zh-CN+en-US",
            output_language="zh-CN",
        )
        print(f"✓ 任务已创建: {task.task_id}")
        print(f"  - 用户: {task.user_id}")
        print(f"  - 音频文件: {task.get_audio_files_list()}")
        print(f"  - 状态: {task.state}")
    print()

    # 3. 保存转写结果
    print("[3/7] 保存转写结果...")
    with session_scope() as session:
        transcript_repo = TranscriptRepository(session)
        
        # 创建转写结果
        transcript_result = TranscriptionResult(
            segments=[
                Segment(
                    text="大家好，今天我们讨论产品规划。",
                    start_time=0.0,
                    end_time=3.5,
                    speaker="Speaker 0",
                    confidence=0.95,
                ),
                Segment(
                    text="好的，我先介绍一下背景。",
                    start_time=3.5,
                    end_time=6.0,
                    speaker="Speaker 1",
                    confidence=0.92,
                ),
            ],
            full_text="大家好，今天我们讨论产品规划。好的，我先介绍一下背景。",
            duration=6.0,
            language="zh-CN",
            provider="volcano",
        )
        
        record = transcript_repo.create(
            transcript_id="transcript_001",
            task_id="task_test_001",
            transcript_result=transcript_result,
        )
        print(f"✓ 转写记录已保存: {record.transcript_id}")
        print(f"  - 片段数: {len(record.get_segments_list())}")
        print(f"  - 时长: {record.duration}秒")
    print()

    # 4. 保存说话人映射
    print("[4/7] 保存说话人映射...")
    with session_scope() as session:
        speaker_repo = SpeakerMappingRepository(session)
        
        speaker_repo.create_or_update(
            task_id="task_test_001",
            speaker_label="Speaker 0",
            speaker_name="张三",
            speaker_id="speaker_linyudong",
            confidence=0.65,
        )
        
        speaker_repo.create_or_update(
            task_id="task_test_001",
            speaker_label="Speaker 1",
            speaker_name="李四",
            speaker_id="speaker_lanweiyi",
            confidence=0.62,
        )
        
        mapping_dict = speaker_repo.get_mapping_dict("task_test_001")
        print(f"✓ 说话人映射已保存:")
        for label, name in mapping_dict.items():
            print(f"  - {label} -> {name}")
    print()

    # 5. 创建提示词模板
    print("[5/7] 创建提示词模板...")
    with session_scope() as session:
        template_repo = PromptTemplateRepository(session)
        
        template = template_repo.create(
            template_id="tpl_test_001",
            title="测试会议纪要模板",
            prompt_body="你是一个专业的会议纪要助手。\n\n请根据以下会议转写生成纪要:\n{transcript}",
            artifact_type="meeting_minutes",
            supported_languages=["zh-CN", "en-US"],
            parameter_schema={
                "meeting_description": {
                    "type": "string",
                    "required": False,
                    "default": "",
                }
            },
            description="用于测试的会议纪要模板",
            is_system=True,
        )
        print(f"✓ 提示词模板已创建: {template.template_id}")
        print(f"  - 标题: {template.title}")
        print(f"  - 类型: {template.artifact_type}")
    print()

    # 6. 保存生成内容
    print("[6/7] 保存生成内容...")
    with session_scope() as session:
        artifact_repo = ArtifactRepository(session)
        
        # 创建会议纪要
        meeting_minutes = MeetingMinutes(
            title="产品规划会议",
            participants=["张三", "李四"],
            summary="讨论了 Q2 产品路线图和用户反馈。",
            key_points=[
                "确定了 Q2 的三个核心功能",
                "分析了用户反馈中的主要问题",
                "制定了下一步的行动计划",
            ],
            action_items=[
                "张三负责整理用户反馈报告",
                "李四负责制定详细的开发计划",
            ],
        )
        
        prompt_instance = PromptInstance(
            template_id="tpl_test_001",
            language="zh-CN",
            parameters={},
        )
        
        record = artifact_repo.create(
            artifact_id="artifact_001",
            task_id="task_test_001",
            artifact_type="meeting_minutes",
            version=1,
            prompt_instance=prompt_instance,
            content=meeting_minutes.model_dump_json(),
            created_by="user_123",
        )
        print(f"✓ 生成内容已保存: {record.artifact_id}")
        print(f"  - 类型: {record.artifact_type}")
        print(f"  - 版本: {record.version}")
    print()

    # 7. 查询数据
    print("[7/7] 查询数据...")
    with session_scope() as session:
        task_repo = TaskRepository(session)
        transcript_repo = TranscriptRepository(session)
        artifact_repo = ArtifactRepository(session)
        
        # 查询任务
        task = task_repo.get_by_id("task_test_001")
        print(f"✓ 任务查询成功:")
        print(f"  - ID: {task.task_id}")
        print(f"  - 状态: {task.state}")
        print(f"  - 创建时间: {task.created_at}")
        print()
        
        # 查询转写记录
        transcript_record = transcript_repo.get_by_task_id("task_test_001")
        if transcript_record:
            transcript_result = transcript_repo.to_transcription_result(transcript_record)
            print(f"✓ 转写记录查询成功:")
            print(f"  - 片段数: {len(transcript_result.segments)}")
            print(f"  - 说话人: {transcript_result.speakers}")
            print()
        
        # 查询生成内容
        artifact_record = artifact_repo.get_latest_by_task("task_test_001", "meeting_minutes")
        if artifact_record:
            artifact = artifact_repo.to_generated_artifact(artifact_record)
            minutes = artifact.get_meeting_minutes()
            print(f"✓ 生成内容查询成功:")
            print(f"  - 标题: {minutes.title}")
            print(f"  - 参与者: {', '.join(minutes.participants)}")
            print(f"  - 关键要点数: {len(minutes.key_points)}")
            print(f"  - 行动项数: {len(minutes.action_items)}")
    print()

    print("=" * 80)
    print("✓ 所有测试通过!")
    print("=" * 80)
    print()
    print(f"数据库文件: {db_path}")
    print("你可以使用 SQLite 客户端查看数据库内容")


if __name__ == "__main__":
    test_database()
