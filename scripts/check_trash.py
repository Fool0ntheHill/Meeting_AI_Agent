#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看回收站中的任务"""

import sqlite3
from datetime import datetime

def check_trash():
    conn = sqlite3.connect('meeting_agent.db')
    cursor = conn.cursor()
    
    # 统计回收站任务数
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE is_deleted = 1')
    count = cursor.fetchone()[0]
    print(f"回收站中的任务数: {count}")
    
    if count > 0:
        # 列出最近删除的任务
        cursor.execute('''
            SELECT task_id, name, user_id, deleted_at, created_at 
            FROM tasks 
            WHERE is_deleted = 1 
            ORDER BY deleted_at DESC 
            LIMIT 10
        ''')
        
        print("\n最近删除的任务:")
        print("-" * 80)
        for row in cursor.fetchall():
            task_id, name, user_id, deleted_at, created_at = row
            name_display = name if name else "(未命名)"
            print(f"  任务ID: {task_id}")
            print(f"  名称: {name_display}")
            print(f"  用户: {user_id}")
            print(f"  创建时间: {created_at}")
            print(f"  删除时间: {deleted_at}")
            print("-" * 80)
    
    # 统计未删除的任务数
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE is_deleted = 0 OR is_deleted IS NULL')
    active_count = cursor.fetchone()[0]
    print(f"\n活跃任务数: {active_count}")
    
    conn.close()

if __name__ == "__main__":
    check_trash()
