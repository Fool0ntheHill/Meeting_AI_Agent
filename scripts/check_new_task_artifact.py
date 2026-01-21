#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查新任务的 artifact"""

import sqlite3
import json

task_id = "task_6b3e4935fcba4507"

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

print("=" * 60)
print(f"检查任务: {task_id}")
print("=" * 60)

# 1. 检查任务状态
cursor.execute("""
    SELECT task_id, state, created_at, completed_at
    FROM tasks
    WHERE task_id = ?
""", (task_id,))

task = cursor.fetchone()

if task:
    print(f"\n1. 任务信息:")
    print(f"   状态: {task[1]}")
    print(f"   创建时间: {task[2]}")
    print(f"   完成时间: {task[3]}")
else:
    print(f"\n❌ 任务不存在")
    exit(1)

# 2. 检查 artifact
cursor.execute("""
    SELECT artifact_id, artifact_type, version, content, created_at
    FROM generated_artifacts
    WHERE task_id = ?
    ORDER BY version DESC
""", (task_id,))

artifacts = cursor.fetchall()

if artifacts:
    print(f"\n2. Artifacts ({len(artifacts)} 个):")
    for artifact in artifacts:
        print(f"\n   Artifact ID: {artifact[0]}")
        print(f"   类型: {artifact[1]}")
        print(f"   版本: {artifact[2]}")
        print(f"   创建时间: {artifact[4]}")
        
        # 解析 content
        try:
            content = json.loads(artifact[3])
            # 如果是双重编码，再解析一次
            if isinstance(content, str):
                content = json.loads(content)
            
            # 检查说话人名称
            content_str = json.dumps(content, ensure_ascii=False)
            
            if "林煜东" in content_str:
                print(f"   ✓ 包含真实姓名: 林煜东")
            elif "speaker_linyudong" in content_str:
                print(f"   ✗ 包含声纹 ID: speaker_linyudong")
            
            if "蓝为一" in content_str:
                print(f"   ✓ 包含真实姓名: 蓝为一")
            elif "speaker_lanweiyi" in content_str:
                print(f"   ✗ 包含声纹 ID: speaker_lanweiyi")
            
            # 显示会议概要
            if isinstance(content, dict):
                summary = content.get("overall_summary", content.get("会议概要", ""))
                if summary:
                    print(f"\n   会议概要（前 200 字）:")
                    print(f"   {summary[:200]}...")
        except Exception as e:
            print(f"   ❌ 解析 content 失败: {e}")
else:
    print(f"\n❌ 没有找到 artifact")

# 3. 检查 transcript
cursor.execute("""
    SELECT transcript_id, full_text
    FROM transcripts
    WHERE task_id = ?
""", (task_id,))

transcript = cursor.fetchone()

if transcript:
    print(f"\n3. Transcript:")
    print(f"   Transcript ID: {transcript[0]}")
    
    full_text = transcript[1]
    
    # 检查说话人名称
    if "林煜东" in full_text:
        print(f"   ✓ 包含真实姓名: 林煜东")
    elif "speaker_linyudong" in full_text:
        print(f"   ✗ 包含声纹 ID: speaker_linyudong")
    
    if "蓝为一" in full_text:
        print(f"   ✓ 包含真实姓名: 蓝为一")
    elif "speaker_lanweiyi" in full_text:
        print(f"   ✗ 包含声纹 ID: speaker_lanweiyi")
else:
    print(f"\n❌ 没有找到 transcript")

conn.close()

print("\n" + "=" * 60)
