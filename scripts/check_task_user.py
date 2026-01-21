#!/usr/bin/env python3
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.models import Task

with session_scope() as session:
    task = session.query(Task).filter(Task.task_id == 'task_07cb88970c3848c4').first()
    if task:
        print(f"Task ID: {task.task_id}")
        print(f"User ID: {task.user_id}")
        print(f"Tenant ID: {task.tenant_id}")
    else:
        print("Task not found")
