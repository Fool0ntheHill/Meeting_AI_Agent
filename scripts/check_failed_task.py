#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查失败的任务"""

import sqlite3

task_id = "task_5944b2546e524cef"

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

# 查询任务信息
cursor.execute("""
    SELECT task_id, state, audio_files, error_details, created_at
    FROM tasks
    WHERE task_id = ?
""", (task_id,))

row = cursor.fetchone()

if row:
    print(f"任务 ID: {row[0]}")
    print(f"状态: {row[1]}")
    print(f"音频文件: {row[2]}")
    print(f"错误信息: {row[3]}")
    print(f"创建时间: {row[4]}")
else:
    print(f"任务 {task_id} 不存在")

conn.close()
