# -*- coding: utf-8 -*-
"""测试任务确认 API"""

import os
import sys
import time
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from auth_helper import get_auth_headers, BASE_URL as API_BASE_URL

# 测试用户名
USERNAME = "test_user"


def get_headers():
    """获取认证 headers"""
    headers = get_auth_headers(USERNAME)
    headers["Content-Type"] = "application/json"
    return headers


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_task_confirmation():
    """测试任务确认流程"""
    
    # 1. 创建测试任务
    print_section("创建测试任务")
    
    create_payload = {
        "audio_files": ["https://example.com/test.wav"],
        "file_order": [0],
        "meeting_type": "weekly_sync",
        "asr_language": "zh-CN",
        "output_language": "zh-CN",
        "skip_speaker_recognition": False,
    }
    
    response = requests.post(
        f"{API_BASE_URL}/tasks",
        json=create_payload,
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ 创建任务失败: {response.text}")
        return
    
    result = response.json()
    task_id = result["task_id"]
    print(f"✅ 任务已创建: {task_id}")
    
    # 2. 模拟任务完成(直接更新数据库状态)
    print_section("模拟任务完成")
    print("⚠️  注意: 需要手动将任务状态更新为 'success' 才能测试确认功能")
    print(f"   可以使用 SQL: UPDATE tasks SET state='success' WHERE task_id='{task_id}'")
    
    # 等待用户确认
    input("\n按 Enter 继续测试确认功能...")
    
    # 3. 测试确认任务(缺少必需项)
    print_section("测试确认任务 - 缺少必需项")
    
    confirm_payload_incomplete = {
        "confirmation_items": {
            "key_conclusions": True,
            # 缺少 responsible_persons
        },
        "responsible_person": {
            "id": "user_001",
            "name": "张三",
        },
    }
    
    response = requests.post(
        f"{API_BASE_URL}/tasks/{task_id}/confirm",
        json=confirm_payload_incomplete,
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 400:
        print(f"✅ 正确拒绝: {response.json()['detail']}")
    else:
        print(f"❌ 应该返回 400 错误")
    
    # 4. 测试确认任务(完整确认项)
    print_section("测试确认任务 - 完整确认项")
    
    confirm_payload = {
        "confirmation_items": {
            "key_conclusions": True,
            "responsible_persons": True,
            "action_items": True,
        },
        "responsible_person": {
            "id": "user_001",
            "name": "张三",
        },
    }
    
    response = requests.post(
        f"{API_BASE_URL}/tasks/{task_id}/confirm",
        json=confirm_payload,
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 任务已确认:")
        print(f"   任务 ID: {result['task_id']}")
        print(f"   状态: {result['state']}")
        print(f"   确认人: {result['confirmed_by_name']} ({result['confirmed_by']})")
        print(f"   确认时间: {result['confirmed_at']}")
    else:
        print(f"❌ 确认失败: {response.text}")
        return
    
    # 5. 测试重复确认
    print_section("测试重复确认")
    
    response = requests.post(
        f"{API_BASE_URL}/tasks/{task_id}/confirm",
        json=confirm_payload,
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 400:
        print(f"✅ 正确拒绝重复确认: {response.json()['detail']}")
    else:
        print(f"❌ 应该返回 400 错误")
    
    # 6. 查询任务状态验证
    print_section("查询任务状态验证")
    
    response = requests.get(
        f"{API_BASE_URL}/tasks/{task_id}/status",
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 任务状态:")
        print(f"   任务 ID: {result['task_id']}")
        print(f"   状态: {result['state']}")
        print(f"   进度: {result['progress']}%")
    else:
        print(f"❌ 查询失败: {response.text}")
    
    print_section("✅ 所有测试完成")


def test_confirmation_without_task():
    """测试不存在的任务确认"""
    print_section("测试不存在的任务确认")
    
    confirm_payload = {
        "confirmation_items": {
            "key_conclusions": True,
            "responsible_persons": True,
        },
        "responsible_person": {
            "id": "user_001",
            "name": "张三",
        },
    }
    
    response = requests.post(
        f"{API_BASE_URL}/tasks/nonexistent_task_id/confirm",
        json=confirm_payload,
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 404:
        print(f"✅ 正确返回 404: {response.json()['detail']}")
    else:
        print(f"❌ 应该返回 404 错误")


def test_confirmation_invalid_responsible_person():
    """测试无效的责任人信息"""
    print_section("测试无效的责任人信息")
    
    # 创建测试任务
    create_payload = {
        "audio_files": ["https://example.com/test.wav"],
        "file_order": [0],
        "meeting_type": "weekly_sync",
        "asr_language": "zh-CN",
        "output_language": "zh-CN",
    }
    
    response = requests.post(
        f"{API_BASE_URL}/tasks",
        json=create_payload,
        headers=get_headers(),
    )
    
    if response.status_code != 200:
        print(f"❌ 创建任务失败")
        return
    
    task_id = response.json()["task_id"]
    print(f"任务已创建: {task_id}")
    
    # 测试缺少 name 的责任人信息
    confirm_payload = {
        "confirmation_items": {
            "key_conclusions": True,
            "responsible_persons": True,
        },
        "responsible_person": {
            "id": "user_001",
            # 缺少 name
        },
    }
    
    response = requests.post(
        f"{API_BASE_URL}/tasks/{task_id}/confirm",
        json=confirm_payload,
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 400:
        print(f"✅ 正确拒绝无效责任人信息: {response.json()['detail']}")
    else:
        print(f"❌ 应该返回 400 错误")


if __name__ == "__main__":
    print("=" * 60)
    print("任务确认 API 测试")
    print("=" * 60)
    print(f"API 地址: {API_BASE_URL}")
    print(f"API Key: {API_KEY}")
    
    try:
        # 测试主流程
        test_task_confirmation()
        
        # 测试边界情况
        test_confirmation_without_task()
        test_confirmation_invalid_responsible_person()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 API 服务器")
        print("   请确保 API 服务器正在运行: python main.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
