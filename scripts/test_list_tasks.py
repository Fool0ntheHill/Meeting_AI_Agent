#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试任务列表 API
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from scripts.auth_helper import get_jwt_token


def test_list_tasks():
    """测试列出任务"""
    print("=" * 80)
    print("  测试任务列表 API")
    print("=" * 80)
    print()
    
    # 获取测试 token
    token = get_jwt_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    base_url = "http://localhost:8000/api/v1"
    
    # 1. 列出所有任务
    print("1. 列出所有任务...")
    response = requests.get(
        f"{base_url}/tasks",
        headers=headers,
    )
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"   ✅ 找到 {len(tasks)} 个任务")
        print()
        
        # 查找我们创建的任务
        target_task_id = "task_completed_a8232248"
        found = False
        
        for task in tasks:
            if task["task_id"] == target_task_id:
                found = True
                print(f"   ✅ 找到目标任务: {target_task_id}")
                print(f"      - 名称: {task.get('name')}")
                print(f"      - 状态: {task['state']}")
                print(f"      - 用户: {task['user_id']}")
                print(f"      - 创建时间: {task['created_at']}")
                break
        
        if not found:
            print(f"   ❌ 未找到目标任务: {target_task_id}")
            print()
            print("   前 5 个任务:")
            for i, task in enumerate(tasks[:5], 1):
                print(f"   {i}. {task['task_id']}")
                print(f"      - 名称: {task.get('name')}")
                print(f"      - 状态: {task['state']}")
                print(f"      - 用户: {task['user_id']}")
                print(f"      - 创建时间: {task['created_at']}")
                print()
    else:
        print(f"   ❌ 请求失败")
        print(f"   响应: {response.text}")
    
    print()
    
    # 2. 按状态筛选
    print("2. 筛选 success 状态的任务...")
    response = requests.get(
        f"{base_url}/tasks",
        headers=headers,
        params={"state": "success"},
    )
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"   ✅ 找到 {len(tasks)} 个成功的任务")
        
        # 查找我们创建的任务
        target_task_id = "task_completed_a8232248"
        found = False
        
        for task in tasks:
            if task["task_id"] == target_task_id:
                found = True
                print(f"   ✅ 找到目标任务: {target_task_id}")
                break
        
        if not found:
            print(f"   ❌ 未找到目标任务: {target_task_id}")
    else:
        print(f"   ❌ 请求失败")
        print(f"   响应: {response.text}")
    
    print()
    
    # 3. 直接获取任务详情
    print("3. 直接获取任务详情...")
    target_task_id = "task_completed_a8232248"
    response = requests.get(
        f"{base_url}/tasks/{target_task_id}",
        headers=headers,
    )
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        task = response.json()
        print(f"   ✅ 成功获取任务详情")
        print(f"      - 任务 ID: {task['task_id']}")
        print(f"      - 名称: {task.get('name')}")
        print(f"      - 状态: {task['state']}")
        print(f"      - 用户: {task['user_id']}")
        print(f"      - 创建时间: {task['created_at']}")
    elif response.status_code == 403:
        print(f"   ❌ 无权访问（403）")
        print(f"   这说明任务存在，但 user_id 不匹配")
    elif response.status_code == 404:
        print(f"   ❌ 任务不存在（404）")
    else:
        print(f"   ❌ 请求失败")
        print(f"   响应: {response.text}")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    test_list_tasks()
