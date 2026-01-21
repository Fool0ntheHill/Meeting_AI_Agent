#!/usr/bin/env python3
"""查看指定任务的 artifact 内容"""

import sqlite3
import json
import sys

task_id = sys.argv[1] if len(sys.argv) > 1 else "task_6b3e4935fcba4507"

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

# 查询任务信息
cursor.execute("""
    SELECT task_id, state, created_at, updated_at
    FROM tasks 
    WHERE task_id = ?
""", (task_id,))

task = cursor.fetchone()
if not task:
    print(f"❌ 任务不存在: {task_id}")
    sys.exit(1)

print(f"任务 ID: {task[0]}")
print(f"状态: {task[1]}")
print(f"创建时间: {task[2]}")
print(f"更新时间: {task[3]}")
print()

# 查询 artifacts
cursor.execute("""
    SELECT artifact_id, artifact_type, version, content, created_at, prompt_instance
    FROM generated_artifacts 
    WHERE task_id = ?
    ORDER BY version DESC
""", (task_id,))

artifacts = cursor.fetchall()
if not artifacts:
    print("❌ 没有找到 artifacts")
    sys.exit(0)

print(f"找到 {len(artifacts)} 个 artifact(s):\n")

for artifact in artifacts:
    artifact_id, artifact_type, version, content, created_at, prompt_instance = artifact
    
    print("=" * 80)
    print(f"Artifact ID: {artifact_id}")
    print(f"类型: {artifact_type}")
    print(f"版本: {version}")
    print(f"创建时间: {created_at}")
    print(f"提示词实例: {prompt_instance[:100] if prompt_instance else 'None'}...")
    print("-" * 80)
    
    # 解析 content
    try:
        # 尝试第一次解析
        parsed = json.loads(content)
        
        # 如果结果还是字符串，再解析一次（处理双重编码）
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        
        # 美化输出
        print("内容:")
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"原始内容（前500字符）: {content[:500]}")
    
    print("=" * 80)
    print()

conn.close()
