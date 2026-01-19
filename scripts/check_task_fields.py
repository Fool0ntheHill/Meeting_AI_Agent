#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查任务的所有字段
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.models import Task


def check_task_fields(task_id: str):
    """检查任务的所有字段"""
    print("=" * 80)
    print(f"  检查任务字段: {task_id}")
    print("=" * 80)
    print()
    
    with session_scope() as session:
        task = session.query(Task).filter(Task.task_id == task_id).first()
        
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print("✅ 任务存在，所有字段值：")
        print()
        
        # 获取所有列
        for column in Task.__table__.columns:
            value = getattr(task, column.name)
            print(f"  {column.name:30s} = {value}")
        
        print()
        print("=" * 80)
        print("关键字段检查：")
        print("=" * 80)
        print(f"  is_deleted: {task.is_deleted} (应该是 False 才能在列表中显示)")
        print(f"  folder_id: {task.folder_id} (None 表示在根目录)")
        print(f"  user_id: {task.user_id}")
        print(f"  state: {task.state}")
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = "task_completed_a8232248"
    
    check_task_fields(task_id)
