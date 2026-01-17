#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 API 缓存功能"""

import requests
import time
import json
from auth_helper import get_auth_headers, BASE_URL as API_BASE_URL

BASE_URL = API_BASE_URL
USERNAME = "test_user"


def get_headers():
    """获取认证 headers"""
    headers = get_auth_headers(USERNAME)
    headers["Content-Type"] = "application/json"
    return headers


def test_task_status_cache():
    """测试任务状态查询的缓存功能"""
    print("\n" + "=" * 60)
    print("测试任务状态查询缓存")
    print("=" * 60)
    
    # 1. 创建任务
    print("\n1. 创建测试任务...")
    create_data = {
        "audio_files": ["test_audio_1.wav"],
        "meeting_type": "common",
        "asr_language": "zh-CN+en-US",
        "output_language": "zh-CN",
        "skip_speaker_recognition": True,
    }
    
    response = requests.post(
        f"{BASE_URL}/tasks",
        headers=get_headers(),
        json=create_data,
    )
    
    if response.status_code != 201:
        print(f"❌ 创建任务失败: {response.status_code}")
        print(response.text)
        return
    
    task_id = response.json()["task_id"]
    print(f"✅ 任务创建成功: {task_id}")
    
    # 2. 第一次查询(Cache Miss)
    print("\n2. 第一次查询任务状态(Cache Miss)...")
    start_time = time.time()
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/status",
        headers=get_headers(),
    )
    first_query_time = time.time() - start_time
    
    if response.status_code != 200:
        print(f"❌ 查询失败: {response.status_code}")
        print(response.text)
        return
    
    print(f"✅ 查询成功 (耗时: {first_query_time*1000:.2f}ms)")
    print(f"   状态: {response.json()['state']}")
    
    # 3. 第二次查询(Cache Hit)
    print("\n3. 第二次查询任务状态(Cache Hit)...")
    start_time = time.time()
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/status",
        headers=get_headers(),
    )
    second_query_time = time.time() - start_time
    
    if response.status_code != 200:
        print(f"❌ 查询失败: {response.status_code}")
        print(response.text)
        return
    
    print(f"✅ 查询成功 (耗时: {second_query_time*1000:.2f}ms)")
    print(f"   状态: {response.json()['state']}")
    
    # 4. 性能对比
    print("\n4. 性能对比:")
    print(f"   第一次查询(Cache Miss): {first_query_time*1000:.2f}ms")
    print(f"   第二次查询(Cache Hit):  {second_query_time*1000:.2f}ms")
    if first_query_time > 0:
        speedup = first_query_time / second_query_time
        print(f"   加速比: {speedup:.2f}x")
    
    # 5. 等待缓存过期
    print("\n5. 等待缓存过期(60秒)...")
    print("   (可以按 Ctrl+C 跳过)")
    try:
        for i in range(60, 0, -1):
            print(f"\r   剩余 {i} 秒...", end="", flush=True)
            time.sleep(1)
        print("\r   ✅ 缓存已过期" + " " * 20)
    except KeyboardInterrupt:
        print("\n   ⏭️  跳过等待")
    
    # 6. 缓存过期后查询
    print("\n6. 缓存过期后查询(Cache Miss)...")
    start_time = time.time()
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/status",
        headers=get_headers(),
    )
    third_query_time = time.time() - start_time
    
    if response.status_code != 200:
        print(f"❌ 查询失败: {response.status_code}")
        print(response.text)
        return
    
    print(f"✅ 查询成功 (耗时: {third_query_time*1000:.2f}ms)")
    print(f"   状态: {response.json()['state']}")


def main():
    """主函数"""
    print("=" * 60)
    print("API 缓存功能测试")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    
    # 测试健康检查
    print("\n检查 API 服务...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API 服务正常")
        else:
            print(f"⚠️  API 服务异常: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到 API 服务: {e}")
        print("\n请先启动 API 服务:")
        print("  python main.py")
        return
    
    # 运行测试
    test_task_status_cache()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
