#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试前端获取 artifact 的 API"""

import requests
from auth_helper import get_jwt_token

task_id = "task_6b3e4935fcba4507"

print("=" * 60)
print("测试前端 Artifact API")
print("=" * 60)

# 1. 登录
print("\n1. 登录...")
token = get_jwt_token("test_user")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. 获取任务详情
print(f"\n2. 获取任务详情: GET /api/v1/tasks/{task_id}")
response = requests.get(
    f"http://localhost:8000/api/v1/tasks/{task_id}",
    headers=headers
)

print(f"   Status: {response.status_code}")

if response.status_code == 200:
    task = response.json()
    print(f"   ✓ 任务状态: {task.get('state')}")
    print(f"   ✓ 任务名称: {task.get('name', 'N/A')}")
else:
    print(f"   ❌ 错误: {response.text}")

# 3. 获取 artifacts 列表
print(f"\n3. 获取 artifacts 列表: GET /api/v1/tasks/{task_id}/artifacts")
response = requests.get(
    f"http://localhost:8000/api/v1/tasks/{task_id}/artifacts",
    headers=headers
)

print(f"   Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"   ✓ 总数: {data.get('total_count')}")
    
    artifacts_by_type = data.get('artifacts_by_type', {})
    for artifact_type, artifacts in artifacts_by_type.items():
        print(f"\n   类型: {artifact_type}")
        for artifact in artifacts:
            print(f"     - Artifact ID: {artifact.get('artifact_id')}")
            print(f"       版本: {artifact.get('version')}")
            print(f"       创建时间: {artifact.get('created_at')}")
else:
    print(f"   ❌ 错误: {response.text}")

# 4. 获取 artifact 详情
print(f"\n4. 获取 artifact 详情: GET /api/v1/artifacts/art_task_{task_id}_meeting_minutes_v1")
artifact_id = f"art_{task_id}_meeting_minutes_v1"
response = requests.get(
    f"http://localhost:8000/api/v1/artifacts/{artifact_id}",
    headers=headers
)

print(f"   Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    artifact = data.get('artifact', {})
    content = artifact.get('content', {})
    
    print(f"   ✓ Artifact ID: {artifact.get('artifact_id')}")
    print(f"   ✓ 版本: {artifact.get('version')}")
    print(f"   ✓ Content 类型: {type(content)}")
    
    if isinstance(content, dict):
        # 检查说话人名称
        import json
        content_str = json.dumps(content, ensure_ascii=False)
        
        if "林煜东" in content_str:
            print(f"   ✓ 包含真实姓名: 林煜东")
        if "蓝为一" in content_str:
            print(f"   ✓ 包含真实姓名: 蓝为一")
        
        # 显示会议概要
        summary = content.get("overall_summary", content.get("会议概要", ""))
        if summary:
            print(f"\n   会议概要（前 200 字）:")
            print(f"   {summary[:200]}...")
    else:
        print(f"   ⚠️  Content 不是字典类型")
else:
    print(f"   ❌ 错误: {response.text}")

print("\n" + "=" * 60)
