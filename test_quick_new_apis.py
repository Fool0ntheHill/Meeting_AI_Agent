#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试新增的 API 接口"""

import requests

BASE_URL = "http://localhost:8000/api/v1"

def get_token():
    """获取测试 token"""
    response = requests.post(
        f"{BASE_URL}/auth/dev/login",
        json={"username": "test_user"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"登录失败: {response.text}")

def test_task_list_filtering():
    """测试任务列表筛选"""
    print("\n=== 测试任务列表筛选 ===")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试不带筛选
    print("\n1. 获取所有任务")
    r = requests.get(f"{BASE_URL}/tasks", headers=headers)
    print(f"   状态码: {r.status_code}")
    if r.status_code == 200:
        tasks = r.json()
        print(f"   ✅ 成功! 找到 {len(tasks)} 个任务")
    
    # 测试带状态筛选
    print("\n2. 筛选 success 状态的任务")
    r = requests.get(f"{BASE_URL}/tasks?state=success", headers=headers)
    print(f"   状态码: {r.status_code}")
    if r.status_code == 200:
        tasks = r.json()
        print(f"   ✅ 成功! 找到 {len(tasks)} 个已完成任务")
        if tasks:
            # 验证筛选结果
            all_success = all(t["state"] == "success" for t in tasks)
            print(f"   验证: {'✅ 所有任务都是 success 状态' if all_success else '❌ 筛选有误'}")

def test_get_transcript():
    """测试获取转写文本"""
    print("\n=== 测试获取转写文本 ===")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 先获取一个已完成的任务
    print("\n1. 查找已完成的任务")
    r = requests.get(f"{BASE_URL}/tasks?state=success&limit=1", headers=headers)
    if r.status_code == 200:
        tasks = r.json()
        if tasks:
            task_id = tasks[0]["task_id"]
            print(f"   ✅ 找到任务: {task_id}")
            
            # 获取转写文本
            print(f"\n2. 获取转写文本")
            r = requests.get(f"{BASE_URL}/tasks/{task_id}/transcript", headers=headers)
            print(f"   状态码: {r.status_code}")
            
            if r.status_code == 200:
                data = r.json()
                print(f"   ✅ 成功!")
                print(f"   - 片段数: {len(data['segments'])}")
                print(f"   - 时长: {data['duration']}s")
                print(f"   - 语言: {data['language']}")
                print(f"   - 提供商: {data['provider']}")
            elif r.status_code == 400:
                print(f"   ⚠️  任务尚未完成转写")
            elif r.status_code == 404:
                print(f"   ⚠️  转写文本不存在")
        else:
            print("   ⚠️  没有已完成的任务")
    else:
        print(f"   ❌ 获取任务列表失败: {r.status_code}")

def test_upload_route_exists():
    """测试上传路由是否存在"""
    print("\n=== 测试上传路由 ===")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试路由是否存在（不实际上传文件）
    print("\n1. 检查上传路由")
    r = requests.post(f"{BASE_URL}/upload", headers=headers)
    print(f"   状态码: {r.status_code}")
    
    # 422 表示路由存在但缺少必需参数（file）
    # 404 表示路由不存在
    if r.status_code == 422:
        print(f"   ✅ 上传路由已注册（缺少 file 参数）")
    elif r.status_code == 404:
        print(f"   ❌ 上传路由未注册")
    else:
        print(f"   状态: {r.status_code}")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 快速测试新增 API 接口")
    print("=" * 60)
    
    try:
        test_task_list_filtering()
        test_get_transcript()
        test_upload_route_exists()
        
        print("\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
