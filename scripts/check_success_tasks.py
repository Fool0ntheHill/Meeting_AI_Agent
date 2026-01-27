#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查成功的任务"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import TaskRepository

with session_scope() as db:
    tasks = TaskRepository(db).get_by_user('test_user', limit=50)
    success_tasks = [t for t in tasks if t.state == 'success']
    
    print(f"找到 {len(success_tasks)} 个成功的任务：\n")
    for t in success_tasks:
        print(f"{t.task_id}: {t.state} - {t.created_at}")
