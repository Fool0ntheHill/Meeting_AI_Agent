#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证新创建的任务"""

import requests
from scripts.auth_helper import get_jwt_token

# 新创建的任务 ID
TASK_ID = "task_completed_33798af4"

token = get_jwt_token()
headers = {"Authorization": f"Bearer {token}"}
base_url = "http://localhost:8000/api/v1"

print(f"验证任务: {TASK_ID}")
print()

# 1. 列出所有任务
print("1. 检查任务列表...")
response = requests.get(f"{base_url}/tasks", headers=headers)
if response.status_code == 200:
    tasks = response.json()
    found = any(t["task_id"] == TASK_ID for t in tasks)
    if found:
        print(f"   ✅ 在列表中找到任务")
    else:
        print(f"   ❌ 列表中没有找到任务")
        print(f"   总共 {len(tasks)} 个任务")
else:
    print(f"   ❌ 请求失败: {response.status_code}")

print()

# 2. 按状态筛选
print("2. 筛选 success 状态...")
response = requests.get(f"{base_url}/tasks?state=success", headers=headers)
if response.status_code == 200:
    tasks = response.json()
    found = any(t["task_id"] == TASK_ID for t in tasks)
    if found:
        print(f"   ✅ 在 success 列表中找到任务")
    else:
        print(f"   ❌ success 列表中没有找到任务")
        print(f"   总共 {len(tasks)} 个 success 任务")
else:
    print(f"   ❌ 请求失败: {response.status_code}")

print()

# 3. 直接获取任务
print("3. 直接获取任务详情...")
response = requests.get(f"{base_url}/tasks/{TASK_ID}", headers=headers)
if response.status_code == 200:
    task = response.json()
    print(f"   ✅ 成功获取任务")
    print(f"   - 状态: {task['state']}")
    print(f"   - 用户: {task['user_id']}")
elif response.status_code == 403:
    print(f"   ❌ 无权访问 (user_id 不匹配)")
elif response.status_code == 404:
    print(f"   ❌ 任务不存在")
else:
    print(f"   ❌ 请求失败: {response.status_code}")
