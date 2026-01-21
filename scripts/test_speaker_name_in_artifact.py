#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 artifact 中是否使用了真实姓名

检查生成的会议纪要中，说话人是否显示为真实姓名（林煜东、蓝为一）
而不是声纹 ID（speaker_linyudong）或标签（Speaker 1）
"""

import sys
import requests
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from auth_helper import get_jwt_token

task_id = "task_ab07a64f9e8d4f69"

print("=" * 60)
print("测试 Artifact 中的说话人姓名")
print("=" * 60)

# 1. 登录
print("\n1. 登录...")
token = get_jwt_token("test_user")
headers = {"Authorization": f"Bearer {token}"}

# 2. 获取 artifacts 列表
print(f"\n2. 获取 artifacts 列表...")
url = f"http://localhost:8000/api/v1/tasks/{task_id}/artifacts"
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print(f"   ❌ 错误: {response.status_code} - {response.text}")
    sys.exit(1)

data = response.json()
artifacts_by_type = data.get("artifacts_by_type", {})
meeting_minutes = artifacts_by_type.get("meeting_minutes", [])

if not meeting_minutes:
    print("   ❌ 没有找到 meeting_minutes artifact")
    sys.exit(1)

artifact_id = meeting_minutes[0]["artifact_id"]
print(f"   ✓ 找到 artifact: {artifact_id}")

# 3. 获取 artifact 详情
print(f"\n3. 获取 artifact 详情...")
url = f"http://localhost:8000/api/v1/artifacts/{artifact_id}"
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print(f"   ❌ 错误: {response.status_code} - {response.text}")
    sys.exit(1)

data = response.json()
content = data["artifact"]["content"]

print(f"   ✓ Content 类型: {type(content)}")

# 4. 检查内容中的说话人姓名
print(f"\n4. 检查说话人姓名...")

# 将 content 转换为字符串进行搜索
import json
content_str = json.dumps(content, ensure_ascii=False)

# 检查是否包含真实姓名
has_real_names = "林煜东" in content_str or "蓝为一" in content_str
has_speaker_ids = "speaker_linyudong" in content_str or "speaker_lanweiyi" in content_str
has_speaker_labels = "Speaker 1" in content_str or "Speaker 2" in content_str

print(f"\n   检查结果：")
print(f"   - 包含真实姓名（林煜东/蓝为一）: {'✅ 是' if has_real_names else '❌ 否'}")
print(f"   - 包含声纹 ID（speaker_xxx）: {'⚠️ 是' if has_speaker_ids else '✅ 否'}")
print(f"   - 包含标签（Speaker 1/2）: {'⚠️ 是' if has_speaker_labels else '✅ 否'}")

# 5. 显示部分内容
print(f"\n5. 内容预览：")
if isinstance(content, dict):
    for key, value in list(content.items())[:2]:  # 只显示前两个字段
        value_str = str(value)[:200] if value else ""
        print(f"\n   {key}:")
        print(f"   {value_str}...")

# 6. 结论
print(f"\n" + "=" * 60)
print("结论")
print("=" * 60)

if has_real_names and not has_speaker_ids and not has_speaker_labels:
    print("✅ 完美！Artifact 中使用了真实姓名")
elif has_real_names:
    print("⚠️ 部分正确：包含真实姓名，但也包含其他标识")
else:
    print("❌ 问题：Artifact 中没有使用真实姓名")
    print("\n可能的原因：")
    print("1. 这是旧任务，生成时还没有实现真实姓名替换")
    print("2. Worker 没有重启，还在使用旧代码")
    print("3. speakers 表中没有对应的真实姓名数据")
    print("\n解决方案：")
    print("1. 重启 Worker: python worker.py")
    print("2. 创建新任务测试")
