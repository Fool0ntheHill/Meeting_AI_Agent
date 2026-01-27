#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Artifact 异步生成机制

测试流程:
1. 创建占位 artifact（state=processing）
2. 立即返回 artifact_id
3. 轮询状态直到完成（success/failed）
4. 验证最终内容
"""

import sys
import time
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.auth_helper import get_test_token

# API 配置
BASE_URL = "http://localhost:8000/api/v1"


def test_async_generation():
    """测试异步生成流程"""
    print("=" * 80)
    print("测试 Artifact 异步生成机制")
    print("=" * 80)
    
    # 获取测试 token
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 使用已知的成功任务（需要先创建一个）
    task_id = input("请输入一个已完成的任务 ID (或按回车使用默认): ").strip()
    if not task_id:
        # 列出最近的任务
        print("\n获取最近的任务...")
        response = requests.get(
            f"{BASE_URL}/tasks",
            headers=headers,
            params={"limit": 5}
        )
        
        if response.status_code == 200:
            tasks = response.json().get("tasks", [])
            if tasks:
                print("\n最近的任务:")
                for i, task in enumerate(tasks):
                    print(f"{i+1}. {task['task_id']} - {task['state']} - {task.get('name', 'N/A')}")
                
                choice = input("\n选择任务编号 (1-5): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(tasks):
                    task_id = tasks[int(choice) - 1]["task_id"]
                else:
                    print("无效选择，退出")
                    return
            else:
                print("没有找到任务，退出")
                return
        else:
            print(f"获取任务列表失败: {response.status_code}")
            return
    
    print(f"\n使用任务: {task_id}")
    
    # Step 1: 发起生成请求
    print("\n" + "=" * 80)
    print("Step 1: 发起异步生成请求")
    print("=" * 80)
    
    generate_request = {
        "prompt_instance": {
            "template_id": "tpl_meeting_minutes_zh",
            "language": "zh-CN",
            "parameters": {}
        },
        "name": "异步生成测试纪要"
    }
    
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/artifacts/meeting_minutes/generate",
        headers=headers,
        json=generate_request
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code != 201:
        print(f"生成请求失败: {response.text}")
        return
    
    result = response.json()
    print(f"响应: {result}")
    
    artifact_id = result.get("artifact_id")
    state = result.get("state")
    
    print(f"\n✓ Artifact ID: {artifact_id}")
    print(f"✓ 初始状态: {state}")
    print(f"✓ 消息: {result.get('message')}")
    
    if state != "processing":
        print(f"\n⚠️  警告: 期望状态为 'processing'，实际为 '{state}'")
    
    # Step 2: 轮询状态
    print("\n" + "=" * 80)
    print("Step 2: 轮询生成状态")
    print("=" * 80)
    
    max_polls = 60  # 最多轮询 60 次（60秒）
    poll_interval = 1  # 每秒轮询一次
    
    for i in range(max_polls):
        print(f"\n轮询 {i+1}/{max_polls}...")
        
        response = requests.get(
            f"{BASE_URL}/artifacts/{artifact_id}/status",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"获取状态失败: {response.status_code} - {response.text}")
            break
        
        status = response.json()
        current_state = status.get("state")
        
        print(f"当前状态: {current_state}")
        
        if current_state == "success":
            print("\n✓ 生成成功!")
            break
        elif current_state == "failed":
            print("\n✗ 生成失败!")
            error = status.get("error", {})
            print(f"错误码: {error.get('code')}")
            print(f"错误消息: {error.get('message')}")
            break
        elif current_state == "processing":
            print("生成中...")
            time.sleep(poll_interval)
        else:
            print(f"未知状态: {current_state}")
            break
    else:
        print("\n⚠️  超时: 生成未在预期时间内完成")
    
    # Step 3: 获取完整内容
    print("\n" + "=" * 80)
    print("Step 3: 获取完整 Artifact 内容")
    print("=" * 80)
    
    response = requests.get(
        f"{BASE_URL}/artifacts/{artifact_id}",
        headers=headers
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        artifact = response.json().get("artifact", {})
        content = artifact.get("content", {})
        
        print(f"\n✓ Artifact 类型: {artifact.get('artifact_type')}")
        print(f"✓ 版本: {artifact.get('version')}")
        print(f"✓ 显示名称: {artifact.get('display_name', 'N/A')}")
        print(f"✓ 创建时间: {artifact.get('created_at')}")
        
        print(f"\n内容预览:")
        if isinstance(content, dict):
            for key, value in list(content.items())[:3]:
                if isinstance(value, str):
                    preview = value[:100] + "..." if len(value) > 100 else value
                    print(f"  {key}: {preview}")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"  {content}")
    else:
        print(f"获取内容失败: {response.text}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_async_generation()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()
