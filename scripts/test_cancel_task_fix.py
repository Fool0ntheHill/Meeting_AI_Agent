#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试任务取消功能修复

验证：
1. 取消请求不再返回 500 错误
2. 任务状态正确更新为 cancelled
3. 前端轮询能够检测到状态变化并停止
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from scripts.auth_helper import get_test_token


def test_cancel_task():
    """测试任务取消功能"""
    
    base_url = "http://localhost:8000"
    
    # 获取测试 token
    token = get_test_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("任务取消功能测试")
    print("=" * 60)
    print()
    
    # 步骤 1: 创建一个测试任务
    print("步骤 1: 创建测试任务...")
    try:
        # 使用一个较大的音频文件，确保任务会运行一段时间
        with open("test_data/meeting.ogg", "rb") as f:
            files = {"file": ("meeting.ogg", f, "audio/ogg")}
            data = {
                "task_name": "取消测试任务",
                "enable_speaker_recognition": "false"
            }
            
            response = requests.post(
                f"{base_url}/api/v1/tasks",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            task_data = response.json()
            task_id = task_data["task_id"]
            
            print(f"✓ 任务创建成功: {task_id}")
            print(f"  初始状态: {task_data['state']}")
            print()
    except Exception as e:
        print(f"✗ 创建任务失败: {e}")
        return
    
    # 步骤 2: 等待任务开始运行
    print("步骤 2: 等待任务开始运行...")
    max_wait = 10
    for i in range(max_wait):
        try:
            response = requests.get(
                f"{base_url}/api/v1/tasks/{task_id}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            task = response.json()
            
            if task["state"] in ["running", "transcribing", "identifying", "correcting", "summarizing"]:
                print(f"✓ 任务已开始运行: {task['state']}")
                print(f"  进度: {task.get('progress', 0)}%")
                print()
                break
        except Exception as e:
            print(f"  等待中... ({i+1}/{max_wait})")
        
        time.sleep(1)
    else:
        print("⚠ 任务未在预期时间内开始运行，继续测试取消功能")
        print()
    
    # 步骤 3: 取消任务
    print("步骤 3: 取消任务...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/tasks/{task_id}/cancel",
            headers=headers,
            timeout=10
        )
        
        print(f"  响应状态码: {response.status_code}")
        
        if response.status_code == 500:
            print("✗ 取消请求返回 500 错误（Bug 未修复）")
            print(f"  错误详情: {response.text}")
            return
        
        response.raise_for_status()
        result = response.json()
        
        print(f"✓ 取消请求成功")
        print(f"  消息: {result.get('message')}")
        print(f"  之前状态: {result.get('previous_state')}")
        print()
        
    except Exception as e:
        print(f"✗ 取消请求失败: {e}")
        return
    
    # 步骤 4: 验证任务状态已更新
    print("步骤 4: 验证任务状态...")
    time.sleep(1)  # 等待状态更新
    
    try:
        response = requests.get(
            f"{base_url}/api/v1/tasks/{task_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        task = response.json()
        
        if task["state"] == "cancelled":
            print(f"✓ 任务状态已正确更新为 cancelled")
            print(f"  错误详情: {task.get('error_details', 'N/A')}")
            print()
        else:
            print(f"✗ 任务状态未更新: {task['state']}")
            print(f"  期望: cancelled")
            print(f"  实际: {task['state']}")
            print()
            return
            
    except Exception as e:
        print(f"✗ 获取任务状态失败: {e}")
        return
    
    # 步骤 5: 模拟前端轮询
    print("步骤 5: 模拟前端轮询（应该立即停止）...")
    
    # 前端轮询逻辑：只要状态是 running/queued 等，就继续轮询
    cancellable_states = ["queued", "running", "transcribing", "identifying", "correcting", "summarizing"]
    
    if task["state"] in cancellable_states:
        print(f"✗ 前端会继续轮询（状态仍为 {task['state']}）")
        print("  这会导致前端一直显示进度条")
    else:
        print(f"✓ 前端会停止轮询（状态为 {task['state']}）")
        print("  前端会显示任务已取消")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_cancel_task()
