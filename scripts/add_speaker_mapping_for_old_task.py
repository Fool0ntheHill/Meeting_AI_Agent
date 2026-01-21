#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为旧任务手动添加 speaker mapping 数据"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.repositories import SpeakerMappingRepository
from src.database.models import Task

task_id = "task_ab07a64f9e8d4f69"

print(f"为任务 {task_id} 添加 speaker mapping...")

with session_scope() as session:
    # 检查任务是否存在
    task = session.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        print("❌ 任务不存在")
        sys.exit(1)
    
    print(f"✓ 找到任务: {task.task_id}")
    
    # 创建 speaker mapping repository
    mapping_repo = SpeakerMappingRepository(session)
    
    # 添加映射（根据实际情况调整）
    # 这里假设有两个说话人
    mappings = [
        ("Speaker 1", "speaker_linyudong"),
        ("Speaker 2", "speaker_lanweiyi"),
    ]
    
    for speaker_label, speaker_id in mappings:
        mapping_repo.create_or_update(
            task_id=task_id,
            speaker_label=speaker_label,
            speaker_name=speaker_id,
            speaker_id=speaker_id,
            confidence=None,
        )
        print(f"  ✓ 添加映射: {speaker_label} -> {speaker_id}")
    
    session.commit()
    print("\n✓ Speaker mapping 添加完成")
    print("\n现在可以测试 API 了：")
    print(f"  python scripts/check_specific_task.py")
