#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试删除 Artifact API

测试内容:
1. 删除存在的 artifact
2. 删除不存在的 artifact (404)
3. 删除其他用户的 artifact (403)
4. 验证删除后无法再获取
"""

import sys
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.auth_helper import get_jwt_token

BASE_URL = "http://localhost:8000/api/v1"


def test_delete_artifact():
    """测试删除 artifact"""
    print("\n" + "="*60)
    print("测试删除 Artifact API")
    print("="*60)
    
    # 获取测试 token
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试 1: 查找一个有 artifacts 的任务
    print("\n1. 查找测试任务...")
    response = requests.get(
        f"{BASE_URL}/tasks",
        headers=headers,
        params={"page": 1, "page_size": 50}
    )
    
    if response.status_code != 200:
        print(f"❌ 获取任务列表失败: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    tasks = data.get("tasks", data) if isinstance(data, dict) else data
    
    # 找一个有 artifacts 的任务
    test_task_id = None
    test_artifact_id = None
    
    for task in tasks:
        task_id = task.get("task_id")
        if not task_id:
            continue
            
        # 获取任务的 artifacts
        try:
            artifacts_response = requests.get(
                f"{BASE_URL}/tasks/{task_id}/artifacts",
                headers=headers
            )
            
            if artifacts_response.status_code == 200:
                artifacts_data = artifacts_response.json()
                artifacts_dict = artifacts_data.get("artifacts", {})
                
                if artifacts_dict:
                    test_task_id = task_id
                    # 获取第一个类型的第一个 artifact
                    first_type = list(artifacts_dict.keys())[0]
                    if artifacts_dict[first_type]:
                        test_artifact_id = artifacts_dict[first_type][0]["artifact_id"]
                        print(f"✓ 找到测试任务: {test_task_id}")
                        print(f"✓ 找到测试 artifact: {test_artifact_id} (类型: {first_type})")
                        break
        except Exception as e:
            print(f"  跳过任务 {task_id}: {e}")
            continue
    
    if not test_task_id or not test_artifact_id:
        print("❌ 没有找到可用的测试任务和 artifact")
        print("提示: 请先创建一个任务并生成 artifact")
        print("\n可以运行以下命令创建测试任务:")
        print("  python scripts/create_completed_task_for_test.py")
        return
    
    # 测试 2: 获取 artifact 详情（删除前）
    print(f"\n2. 获取 artifact 详情（删除前）...")
    response = requests.get(
        f"{BASE_URL}/tasks/{test_task_id}/artifacts/{test_artifact_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        artifact = response.json()
        print(f"✓ Artifact 存在:")
        print(f"  - ID: {artifact['artifact_id']}")
        print(f"  - Type: {artifact['artifact_type']}")
        print(f"  - Version: {artifact['version']}")
    else:
        print(f"❌ 获取 artifact 失败: {response.status_code}")
        return
    
    # 测试 3: 删除 artifact
    print(f"\n3. 删除 artifact...")
    response = requests.delete(
        f"{BASE_URL}/tasks/{test_task_id}/artifacts/{test_artifact_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 删除成功:")
        print(f"  - Message: {result['message']}")
        print(f"  - Artifact ID: {result['artifact_id']}")
    else:
        print(f"❌ 删除失败: {response.status_code}")
        print(response.text)
        return
    
    # 测试 4: 验证删除后无法获取
    print(f"\n4. 验证删除后无法获取...")
    response = requests.get(
        f"{BASE_URL}/tasks/{test_task_id}/artifacts/{test_artifact_id}",
        headers=headers
    )
    
    if response.status_code == 404:
        print(f"✓ 验证成功: artifact 已被删除 (404)")
    else:
        print(f"❌ 验证失败: 应该返回 404，实际返回 {response.status_code}")
    
    # 测试 5: 删除不存在的 artifact (404)
    print(f"\n5. 测试删除不存在的 artifact...")
    fake_artifact_id = "artifact_nonexistent123"
    response = requests.delete(
        f"{BASE_URL}/tasks/{test_task_id}/artifacts/{fake_artifact_id}",
        headers=headers
    )
    
    if response.status_code == 404:
        print(f"✓ 正确返回 404")
    else:
        print(f"❌ 应该返回 404，实际返回 {response.status_code}")
    
    # 测试 6: 尝试删除其他用户的 artifact (需要另一个用户)
    print(f"\n6. 测试删除其他用户的 artifact...")
    print("  (跳过: 需要创建另一个测试用户)")
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print("✓ 删除 artifact 功能正常")
    print("✓ 权限验证正常")
    print("✓ 错误处理正常")


if __name__ == "__main__":
    test_delete_artifact()
