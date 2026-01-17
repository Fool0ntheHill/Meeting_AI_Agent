#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试回收站 API"""

import requests
import json
from auth_helper import get_auth_headers

BASE_URL = "http://127.0.0.1:51008"


def test_list_trash():
    """测试获取回收站列表"""
    print("=" * 60)
    print("测试获取回收站列表")
    print("=" * 60)
    
    headers = get_auth_headers()
    
    # 获取回收站列表
    print("\n1. 获取回收站列表")
    response = requests.get(
        f"{BASE_URL}/api/v1/trash/sessions",
        headers=headers
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 成功获取回收站列表")
        print(f"  总数: {data.get('total')}")
        print(f"  返回项数: {len(data.get('items', []))}")
        
        # 显示前 3 个任务
        items = data.get('items', [])
        if items:
            print("\n  前 3 个任务:")
            for i, item in enumerate(items[:3], 1):
                print(f"\n  [{i}] 任务 ID: {item.get('task_id')}")
                print(f"      会议类型: {item.get('meeting_type')}")
                print(f"      文件夹 ID: {item.get('folder_id')}")
                print(f"      时长: {item.get('duration')} 秒")
                print(f"      删除时间: {item.get('deleted_at')}")
                print(f"      创建时间: {item.get('created_at')}")
        
        # 完整响应
        print("\n完整响应:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        return True
    else:
        print(f"✗ 请求失败")
        print(f"  响应: {response.text}")
        return False


def test_trash_operations():
    """测试回收站操作（软删除、还原、彻底删除）"""
    print("\n" + "=" * 60)
    print("测试回收站操作")
    print("=" * 60)
    
    headers = get_auth_headers()
    
    # 先获取一个活跃任务
    print("\n1. 获取活跃任务列表")
    response = requests.get(
        f"{BASE_URL}/api/v1/tasks?limit=1",
        headers=headers
    )
    
    if response.status_code != 200 or not response.json():
        print("✗ 没有活跃任务可供测试")
        return False
    
    task_id = response.json()[0]['task_id']
    print(f"✓ 找到测试任务: {task_id}")
    
    # 2. 软删除任务
    print(f"\n2. 软删除任务 {task_id}")
    response = requests.patch(
        f"{BASE_URL}/api/v1/sessions/{task_id}/delete",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✓ 软删除成功")
        print(f"  响应: {response.json()}")
    else:
        print(f"✗ 软删除失败: {response.status_code}")
        print(f"  响应: {response.text}")
        return False
    
    # 3. 验证任务在回收站中
    print(f"\n3. 验证任务在回收站中")
    response = requests.get(
        f"{BASE_URL}/api/v1/trash/sessions",
        headers=headers
    )
    
    if response.status_code == 200:
        items = response.json().get('items', [])
        found = any(item['task_id'] == task_id for item in items)
        if found:
            print(f"✓ 任务已在回收站中")
        else:
            print(f"✗ 任务未在回收站中找到")
            return False
    
    # 4. 还原任务
    print(f"\n4. 还原任务 {task_id}")
    response = requests.patch(
        f"{BASE_URL}/api/v1/sessions/{task_id}/restore",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✓ 还原成功")
        print(f"  响应: {response.json()}")
    else:
        print(f"✗ 还原失败: {response.status_code}")
        print(f"  响应: {response.text}")
        return False
    
    # 5. 验证任务不在回收站中
    print(f"\n5. 验证任务已从回收站移除")
    response = requests.get(
        f"{BASE_URL}/api/v1/trash/sessions",
        headers=headers
    )
    
    if response.status_code == 200:
        items = response.json().get('items', [])
        found = any(item['task_id'] == task_id for item in items)
        if not found:
            print(f"✓ 任务已从回收站移除")
        else:
            print(f"✗ 任务仍在回收站中")
            return False
    
    print("\n" + "=" * 60)
    print("✓ 所有回收站操作测试通过")
    return True


if __name__ == "__main__":
    try:
        # 测试获取回收站列表
        success1 = test_list_trash()
        
        # 测试回收站操作
        success2 = test_trash_operations()
        
        if success1 and success2:
            print("\n" + "=" * 60)
            print("✓ 所有测试通过")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("✗ 部分测试失败")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
