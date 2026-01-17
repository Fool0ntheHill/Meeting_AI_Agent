#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成回收站 API 的实际 JSON 响应示例"""

import json
import sqlite3
from datetime import datetime

def generate_trash_json():
    """从数据库生成实际的回收站 JSON 响应"""
    conn = sqlite3.connect('meeting_agent.db')
    conn.row_factory = sqlite3.Row  # 使用字典形式返回
    cursor = conn.cursor()
    
    # 查询回收站中的任务（模拟 API 的查询逻辑）
    cursor.execute('''
        SELECT 
            t.task_id,
            t.user_id,
            t.tenant_id,
            t.meeting_type,
            t.folder_id,
            t.deleted_at,
            t.created_at,
            t.last_content_modified_at,
            tr.duration
        FROM tasks t
        LEFT JOIN transcripts tr ON t.task_id = tr.task_id
        WHERE t.is_deleted = 1
        ORDER BY t.deleted_at DESC
        LIMIT 10
    ''')
    
    rows = cursor.fetchall()
    
    # 构建响应（模拟 API 返回格式）
    items = []
    for row in rows:
        item = {
            "task_id": row['task_id'],
            "user_id": row['user_id'],
            "tenant_id": row['tenant_id'],
            "meeting_type": row['meeting_type'],
            "folder_id": row['folder_id'],  # 可能为 None
            "duration": row['duration'],  # 可能为 None
            "last_content_modified_at": row['last_content_modified_at'],  # 可能为 None
            "deleted_at": row['deleted_at'],
            "created_at": row['created_at']
        }
        items.append(item)
    
    response = {
        "items": items,
        "total": len(items)
    }
    
    conn.close()
    
    # 打印格式化的 JSON
    print("=" * 80)
    print("GET /api/v1/trash/sessions 实际返回示例")
    print("=" * 80)
    print()
    print(json.dumps(response, indent=2, ensure_ascii=False))
    print()
    print("=" * 80)
    print(f"说明：")
    print(f"- total: {response['total']} 个已删除任务")
    print(f"- folder_id: 可能为 null（表示在根目录）")
    print(f"- duration: 可能为 null（如果没有转写记录）")
    print(f"- last_content_modified_at: 可能为 null（如果没有修改过内容）")
    print("=" * 80)
    
    return response

if __name__ == "__main__":
    generate_trash_json()
