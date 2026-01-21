#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 artifact 中的说话人名称"""

import sqlite3
import json

# 查询最新的任务
conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT task_id, state, created_at
    FROM tasks
    WHERE state = 'success'
    ORDER BY created_at DESC
    LIMIT 5
""")

tasks = cursor.fetchall()

print("=" * 60)
print("最近成功的任务:")
print("=" * 60)

for i, task in enumerate(tasks, 1):
    print(f"\n{i}. Task ID: {task[0]}")
    print(f"   状态: {task[1]}")
    print(f"   创建时间: {task[2]}")
    
    # 查询这个任务的 artifact
    cursor.execute("""
        SELECT artifact_id, artifact_type, version, content, created_at
        FROM generated_artifacts
        WHERE task_id = ? AND artifact_type = 'meeting_minutes'
        ORDER BY version DESC
        LIMIT 1
    """, (task[0],))
    
    artifact = cursor.fetchone()
    
    if artifact:
        print(f"   Artifact ID: {artifact[0]}")
        print(f"   版本: {artifact[2]}")
        print(f"   创建时间: {artifact[4]}")
        
        # 解析 content
        try:
            content = json.loads(artifact[3])
            # 如果是双重编码，再解析一次
            if isinstance(content, str):
                content = json.loads(content)
            
            # 检查内容中的说话人名称
            content_str = json.dumps(content, ensure_ascii=False)
            
            if "林煜东" in content_str:
                print(f"   ✓ 包含真实姓名: 林煜东")
            elif "speaker_linyudong" in content_str:
                print(f"   ✗ 包含声纹 ID: speaker_linyudong")
            elif "林雨东" in content_str:
                print(f"   ⚠️  包含错误姓名: 林雨东")
            
            if "蓝为一" in content_str:
                print(f"   ✓ 包含真实姓名: 蓝为一")
            elif "speaker_lanweiyi" in content_str:
                print(f"   ✗ 包含声纹 ID: speaker_lanweiyi")
            
            # 显示会议概要的前 200 个字符
            summary = content.get("会议概要", "")
            if summary:
                print(f"\n   会议概要（前 200 字）:")
                print(f"   {summary[:200]}...")
        except Exception as e:
            print(f"   ❌ 解析 content 失败: {e}")
    else:
        print(f"   ❌ 没有找到 artifact")

conn.close()
