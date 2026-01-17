#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试任务重命名功能"""

import sys
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.auth_helper import get_jwt_token

BASE_URL = "http://localhost:8000/api/v1"


def test_rename_task():
    """测试任务重命名功能"""
    
    # 获取测试 Token
    print("1. 获取测试 Token...")
    token = get_jwt_token("test_user")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   ✅ Token: {token[:20]}...")
    
    # 创建测试任务
    print("\n2. 创建测试任务...")
    response = requests.post(
        f"{BASE_URL}/tasks",
        json={
            "audio_files": ["test_audio.wav"],
            "meeting_type": "weekly_sync",
            "asr_language": "zh-CN",
            "output_language": "zh-CN",
        },
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 201:
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"   ✅ 任务已创建: {task_id}")
    else:
        print(f"   ❌ 创建失败: {response.text}")
        return
    
    # 获取任务详情（检查初始名称）
    print("\n3. 获取任务详情（检查初始名称）...")
    response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        task = response.json()
        print(f"   ✅ 初始名称: {task.get('name', 'null')}")
    else:
        print(f"   ❌ 获取失败: {response.text}")
    
    # 重命名任务
    print("\n4. 重命名任务...")
    new_name = "2024年Q1产品规划会议"
    response = requests.patch(
        f"{BASE_URL}/tasks/{task_id}/rename",
        json={"name": new_name},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ {result['message']}")
    else:
        print(f"   ❌ 重命名失败: {response.text}")
        return
    
    # 再次获取任务详情（验证名称已更新）
    print("\n5. 验证名称已更新...")
    response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        task = response.json()
        if task.get('name') == new_name:
            print(f"   ✅ 名称已更新: {task['name']}")
        else:
            print(f"   ❌ 名称未更新: {task.get('name')}")
    else:
        print(f"   ❌ 获取失败: {response.text}")
    
    # 测试空名称
    print("\n6. 测试空名称...")
    response = requests.patch(
        f"{BASE_URL}/tasks/{task_id}/rename",
        json={"name": ""},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 422:
        print(f"   ✅ 正确拒绝空名称")
    else:
        print(f"   ⚠️  状态码: {response.status_code}")
    
    # 测试超长名称
    print("\n7. 测试超长名称...")
    long_name = "A" * 256
    response = requests.patch(
        f"{BASE_URL}/tasks/{task_id}/rename",
        json={"name": long_name},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 422:
        print(f"   ✅ 正确拒绝超长名称")
    else:
        print(f"   ⚠️  状态码: {response.status_code}")
    
    # 清理：删除测试任务
    print("\n8. 清理测试数据...")
    requests.patch(f"{BASE_URL}/sessions/{task_id}/delete", headers=headers)
    requests.delete(f"{BASE_URL}/sessions/{task_id}", headers=headers)
    print(f"   ✅ 清理完成")
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("任务重命名功能测试")
    print("="*60)
    print("\n⚠️  请确保 API 服务器正在运行: python main.py")
    print()
    
    try:
        test_rename_task()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 API 服务器")
        print("   请先启动服务器: python main.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
