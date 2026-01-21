#!/usr/bin/env python3
"""测试 artifact 内容标准化功能"""

import sqlite3
import json
from src.utils.artifact_normalizer import ArtifactNormalizer

# 测试的任务 ID
test_tasks = [
    "task_6b3e4935fcba4507",  # v1 格式
    "task_1531b33b1df94a9f",  # v2 格式
    "task_3517a6cc44dc40b9",  # v3 格式
]

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

for task_id in test_tasks:
    print(f"\n{'='*80}")
    print(f"测试任务: {task_id}")
    print(f"{'='*80}\n")
    
    # 获取 artifact
    cursor.execute("""
        SELECT artifact_id, artifact_type, content
        FROM generated_artifacts
        WHERE task_id = ?
        ORDER BY version DESC
        LIMIT 1
    """, (task_id,))
    
    result = cursor.fetchone()
    if not result:
        print(f"❌ 未找到 artifact")
        continue
    
    artifact_id, artifact_type, content = result
    
    # 解析原始内容
    try:
        parsed = json.loads(content)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        continue
    
    print(f"Artifact ID: {artifact_id}")
    print(f"类型: {artifact_type}")
    print(f"\n原始内容类型: {type(parsed)}")
    if isinstance(parsed, dict):
        print(f"原始内容字段: {list(parsed.keys())}")
    elif isinstance(parsed, list):
        print(f"原始内容长度: {len(parsed)}")
        if len(parsed) > 0:
            print(f"第一个元素字段: {list(parsed[0].keys()) if isinstance(parsed[0], dict) else 'N/A'}")
    
    # 标准化
    print(f"\n{'─'*80}")
    print("标准化处理...")
    print(f"{'─'*80}\n")
    
    try:
        normalized_result = ArtifactNormalizer.normalize(parsed, artifact_type)
        
        print(f"✅ 标准化成功!")
        print(f"格式版本: {normalized_result['format_version']}")
        print(f"原始格式: {normalized_result['original_format']}")
        print(f"\n标准化后的内容:")
        print(json.dumps(normalized_result['normalized'], ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ 标准化失败: {e}")
        import traceback
        traceback.print_exc()

conn.close()

print(f"\n{'='*80}")
print("测试完成")
print(f"{'='*80}")
