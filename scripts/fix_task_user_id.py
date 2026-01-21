#!/usr/bin/env python3
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.models import Task

task_id = "task_07cb88970c3848c4"

with session_scope() as session:
    task = session.query(Task).filter(Task.task_id == task_id).first()
    if task:
        print(f"Before: user_id={task.user_id}, tenant_id={task.tenant_id}")
        task.user_id = "user_user_test_user"
        task.tenant_id = "tenant_user_test_user"
        session.commit()
        print(f"After: user_id={task.user_id}, tenant_id={task.tenant_id}")
        print("✓ Task updated")
    else:
        print("Task not found")
