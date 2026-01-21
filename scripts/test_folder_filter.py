"""
测试文件夹过滤功能
"""

import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token

def test_folder_filter():
    """测试文件夹过滤"""
    
    token = get_jwt_token()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 测试 1: 使用正确的 folder_id
    print("=" * 60)
    print("测试 1: 使用 folder_id 过滤")
    print("=" * 60)
    
    url = "http://localhost:8000/api/v1/tasks"
    params = {
        "folder_id": "folder_c72bca29edc64433",
        "limit": 200,
        "include_deleted": False
    }
    
    print(f"\nGET {url}")
    print(f"Params: {params}\n")
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"✓ 成功获取 {len(tasks)} 个任务")
        for task in tasks:
            print(f"  - {task['task_id']}: folder_id={task.get('folder_id')}")
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)
    
    # 测试 2: 使用错误的 folder_id (123)
    print("\n" + "=" * 60)
    print("测试 2: 使用错误的 folder_id (123)")
    print("=" * 60)
    
    params["folder_id"] = "123"
    print(f"\nGET {url}")
    print(f"Params: {params}\n")
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"✓ 成功获取 {len(tasks)} 个任务")
        if len(tasks) == 0:
            print("  (没有任务，因为 folder_id='123' 不存在)")
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)
    
    # 测试 3: 不使用 folder_id 过滤
    print("\n" + "=" * 60)
    print("测试 3: 不使用 folder_id 过滤（全部任务）")
    print("=" * 60)
    
    params = {
        "limit": 200,
        "include_deleted": False
    }
    print(f"\nGET {url}")
    print(f"Params: {params}\n")
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"✓ 成功获取 {len(tasks)} 个任务")
        
        # 统计有 folder_id 的任务
        with_folder = [t for t in tasks if t.get('folder_id')]
        print(f"  - 有 folder_id: {len(with_folder)} 个")
        print(f"  - 无 folder_id: {len(tasks) - len(with_folder)} 个")
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_folder_filter()
