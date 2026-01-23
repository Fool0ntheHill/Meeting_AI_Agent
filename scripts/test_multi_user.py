#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试多用户数据隔离"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import time

BASE_URL = "http://localhost:8000"


def login(username: str):
    """用户登录获取 Token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/dev/login",
        json={"username": username}
    )
    response.raise_for_status()
    data = response.json()
    print(f"✓ 用户 {username} 登录成功")
    print(f"  - user_id: {data['user_id']}")
    print(f"  - tenant_id: {data['tenant_id']}")
    return data["access_token"]


def create_task(token: str, meeting_name: str):
    """创建任务"""
    response = requests.post(
        f"{BASE_URL}/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "audio_files": ["test_data/meeting.ogg"],
            "meeting_type": meeting_name,
            "audio_duration": 60.0,
            "asr_language": "zh-CN",
            "output_language": "zh-CN",
            "skip_speaker_recognition": True
        }
    )
    # 201 Created 是正确的状态码
    if response.status_code not in [200, 201]:
        print(f"✗ 创建任务失败: {response.status_code}")
        print(f"  响应: {response.text}")
        response.raise_for_status()
    data = response.json()
    print(f"✓ 创建任务成功: {data['task_id']}")
    return data


def get_task(token: str, task_id: str):
    """获取任务详情"""
    response = requests.get(
        f"{BASE_URL}/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response


def list_tasks(token: str):
    """列出用户的所有任务"""
    response = requests.get(
        f"{BASE_URL}/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()


def main():
    """主测试流程"""
    print("=" * 80)
    print("多用户数据隔离测试")
    print("=" * 80)
    print()
    
    # 测试 1: 用户 A 登录
    print("[1/6] 用户 A (zhangsan) 登录...")
    token_a = login("zhangsan")
    print()
    
    # 测试 2: 用户 B 登录
    print("[2/6] 用户 B (lisi) 登录...")
    token_b = login("lisi")
    print()
    
    # 测试 3: 用户 A 创建任务
    print("[3/6] 用户 A 创建任务...")
    task_a = create_task(token_a, "张三的会议")
    print()
    
    # 测试 4: 用户 B 创建任务
    print("[4/6] 用户 B 创建任务...")
    task_b = create_task(token_b, "李四的会议")
    print()
    
    # 测试 5: 验证数据隔离 - 用户 A 不能访问用户 B 的任务
    print("[5/6] 验证数据隔离 - 用户 A 访问用户 B 的任务...")
    response = get_task(token_a, task_b["task_id"])
    # 403 Forbidden 或 404 Not Found 都是正确的（表示无权访问）
    if response.status_code in [403, 404]:
        print(f"✓ 正确：用户 A 无法访问用户 B 的任务 ({response.status_code})")
    else:
        print(f"✗ 错误：用户 A 可以访问用户 B 的任务 (状态码: {response.status_code})")
        print("  数据隔离失败！")
        sys.exit(1)
    print()
    
    # 测试 6: 验证数据隔离 - 用户 B 不能访问用户 A 的任务
    print("[6/6] 验证数据隔离 - 用户 B 访问用户 A 的任务...")
    response = get_task(token_b, task_a["task_id"])
    # 403 Forbidden 或 404 Not Found 都是正确的（表示无权访问）
    if response.status_code in [403, 404]:
        print(f"✓ 正确：用户 B 无法访问用户 A 的任务 ({response.status_code})")
    else:
        print(f"✗ 错误：用户 B 可以访问用户 A 的任务 (状态码: {response.status_code})")
        print("  数据隔离失败！")
        sys.exit(1)
    print()
    
    # 测试 7: 验证用户只能看到自己的任务
    print("[7/7] 验证用户只能看到自己的任务...")
    
    # 用户 A 的任务列表
    tasks_a = list_tasks(token_a)
    # API 返回的是列表，不是字典
    task_ids_a = [t["task_id"] for t in tasks_a]
    print(f"✓ 用户 A 有 {len(task_ids_a)} 个任务")
    print(f"  - 包含自己的任务: {task_a['task_id'] in task_ids_a}")
    print(f"  - 不包含用户 B 的任务: {task_b['task_id'] not in task_ids_a}")
    
    # 用户 B 的任务列表
    tasks_b = list_tasks(token_b)
    task_ids_b = [t["task_id"] for t in tasks_b]
    print(f"✓ 用户 B 有 {len(task_ids_b)} 个任务")
    print(f"  - 包含自己的任务: {task_b['task_id'] in task_ids_b}")
    print(f"  - 不包含用户 A 的任务: {task_a['task_id'] not in task_ids_b}")
    print()
    
    # 验证结果
    if (task_a['task_id'] in task_ids_a and 
        task_b['task_id'] not in task_ids_a and
        task_b['task_id'] in task_ids_b and 
        task_a['task_id'] not in task_ids_b):
        print("=" * 80)
        print("✓ 所有测试通过！多用户数据隔离正常工作")
        print("=" * 80)
    else:
        print("=" * 80)
        print("✗ 测试失败！数据隔离存在问题")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("✗ 错误：无法连接到后端服务")
        print("  请确保后端服务正在运行: python main.py")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
