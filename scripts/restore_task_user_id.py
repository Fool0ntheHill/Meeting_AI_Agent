#!/usr/bin/env python3
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.models import Task

# 恢复两个任务的 user_id
tasks = [
    "task_ab07a64f9e8d4f69",
    "task_07cb88970c3848c4"
]

with session_scope() as session:
    for task_id in tasks:
        task = session.query(Task).filter(Task.task_id == task_id).first()
        if task:
            print(f"\n{task_id}:")
            print(f"  Before: user_id={task.user_id}, tenant_id={task.tenant_id}")
            task.user_id = "user_test_user"
            task.tenant_id = "tenant_test_user"
            print(f"  After: user_id={task.user_id}, tenant_id={task.tenant_id}")
        else:
            print(f"\n{task_id}: Not found")
    
    session.commit()
    print("\n✓ All tasks updated")
