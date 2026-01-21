"""
检查任务列表接口返回的 folder_id 字段格式
"""

import requests
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token

def check_task_folder_data():
    """检查任务的 folder_id 数据格式"""
    
    # 获取 token
    token = get_jwt_token()
    
    # 请求任务列表
    url = "http://localhost:8000/api/v1/tasks"
    params = {
        "limit": 200,
        "offset": 0,
        "include_deleted": False
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print("=" * 60)
    print("检查任务列表接口返回的 folder_id 字段")
    print("=" * 60)
    print(f"\nGET {url}")
    print(f"Params: {params}")
    print()
    
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    
    # API 可能直接返回列表或包含 tasks 字段的对象
    if isinstance(data, list):
        tasks = data
    else:
        tasks = data.get("tasks", [])
    
    print(f"✓ 成功获取 {len(tasks)} 个任务\n")
    
    # 统计 folder_id 的类型
    folder_stats = {
        "null": 0,
        "string": 0,
        "number": 0,
        "other": 0
    }
    
    folder_examples = {
        "null": [],
        "string": [],
        "number": [],
        "other": []
    }
    
    for task in tasks:
        folder_id = task.get("folder_id")
        task_id = task.get("task_id", "unknown")
        
        if folder_id is None:
            folder_stats["null"] += 1
            if len(folder_examples["null"]) < 3:
                folder_examples["null"].append({
                    "task_id": task_id,
                    "folder_id": folder_id,
                    "folder": task.get("folder"),
                    "folder_path": task.get("folder_path")
                })
        elif isinstance(folder_id, str):
            folder_stats["string"] += 1
            if len(folder_examples["string"]) < 3:
                folder_examples["string"].append({
                    "task_id": task_id,
                    "folder_id": folder_id,
                    "folder": task.get("folder"),
                    "folder_path": task.get("folder_path")
                })
        elif isinstance(folder_id, (int, float)):
            folder_stats["number"] += 1
            if len(folder_examples["number"]) < 3:
                folder_examples["number"].append({
                    "task_id": task_id,
                    "folder_id": folder_id,
                    "folder": task.get("folder"),
                    "folder_path": task.get("folder_path")
                })
        else:
            folder_stats["other"] += 1
            if len(folder_examples["other"]) < 3:
                folder_examples["other"].append({
                    "task_id": task_id,
                    "folder_id": folder_id,
                    "folder_id_type": type(folder_id).__name__,
                    "folder": task.get("folder"),
                    "folder_path": task.get("folder_path")
                })
    
    # 打印统计结果
    print("folder_id 类型统计:")
    print("-" * 60)
    for type_name, count in folder_stats.items():
        print(f"  {type_name:10s}: {count:3d} 个任务")
    print()
    
    # 打印示例
    for type_name, examples in folder_examples.items():
        if examples:
            print(f"\n{type_name.upper()} 类型示例:")
            print("-" * 60)
            for example in examples:
                print(json.dumps(example, indent=2, ensure_ascii=False))
                print()
    
    # 查找文件夹 ID 为 "123" 或 123 的任务
    print("\n" + "=" * 60)
    print("查找 folder_id = '123' 或 123 的任务:")
    print("=" * 60)
    
    matching_tasks = []
    for task in tasks:
        folder_id = task.get("folder_id")
        if folder_id == "123" or folder_id == 123:
            matching_tasks.append({
                "task_id": task.get("task_id"),
                "display_name": task.get("display_name"),
                "folder_id": folder_id,
                "folder_id_type": type(folder_id).__name__,
                "folder": task.get("folder"),
                "folder_path": task.get("folder_path")
            })
    
    if matching_tasks:
        print(f"\n找到 {len(matching_tasks)} 个任务:")
        for task in matching_tasks:
            print(json.dumps(task, indent=2, ensure_ascii=False))
            print()
    else:
        print("\n❌ 没有找到 folder_id = '123' 或 123 的任务")
        print("\n可用的 folder_id 值:")
        unique_folders = set()
        for task in tasks:
            folder_id = task.get("folder_id")
            if folder_id is not None:
                unique_folders.add(str(folder_id))
        for folder_id in sorted(unique_folders):
            print(f"  - {folder_id}")

if __name__ == "__main__":
    check_task_folder_data()
