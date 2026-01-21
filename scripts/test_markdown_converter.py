#!/usr/bin/env python3
"""测试 Markdown 转换器 - 验证所有历史格式都能正确转换"""

import sqlite3
import json
from src.utils.markdown_converter import MarkdownConverter

# 测试的任务 ID
test_tasks = [
    "task_6b3e4935fcba4507",  # v1 格式（数组）
    "task_1531b33b1df94a9f",  # v2 格式（Markdown 字符串）
    "task_3517a6cc44dc40b9",  # v3 格式（结构化 JSON）
]

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

print("=" * 80)
print("测试 Markdown 转换器 - 万能转接头")
print("=" * 80)

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
    
    print(f"Artifact ID: {artifact_id}")
    print(f"类型: {artifact_type}")
    
    # 解析原始内容
    try:
        parsed = json.loads(content)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        continue
    
    print(f"原始格式: {type(parsed)}")
    if isinstance(parsed, dict):
        print(f"原始字段: {list(parsed.keys())[:5]}...")
    
    # 转换为 Markdown
    print(f"\n{'─'*80}")
    print("转换为 Markdown...")
    print(f"{'─'*80}\n")
    
    try:
        result = MarkdownConverter.convert(parsed, artifact_type)
        
        print(f"✅ 转换成功!")
        print(f"\n标题: {result['title']}")
        print(f"\n内容预览（前500字符）:")
        print("─" * 80)
        print(result['content'][:500])
        if len(result['content']) > 500:
            print(f"\n... (还有 {len(result['content']) - 500} 字符)")
        print("─" * 80)
        
        # 验证格式
        print(f"\n✅ 格式验证:")
        print(f"  - title 类型: {type(result['title'])}")
        print(f"  - content 类型: {type(result['content'])}")
        print(f"  - content 长度: {len(result['content'])} 字符")
        print(f"  - 包含 Markdown 标记: {'##' in result['content']}")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()

conn.close()

print(f"\n{'='*80}")
print("测试完成 - 所有格式都应该成功转换为统一的 Markdown")
print(f"{'='*80}")
