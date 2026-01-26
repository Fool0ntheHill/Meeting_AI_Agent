"""
测试 artifact display_name 功能

测试场景：
1. 生成 artifact 时提供自定义名称
2. 重新生成 artifact 时提供自定义名称
3. 列出 artifacts 时返回 display_name
4. 不提供名称时，display_name 为 None
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from scripts.auth_helper import get_test_token

BASE_URL = "http://localhost:8000/api/v1"


def test_generate_with_name():
    """测试生成 artifact 时提供自定义名称"""
    print("\n" + "=" * 80)
    print("测试 1: 生成 artifact 时提供自定义名称")
    print("=" * 80)
    
    # 获取测试 token
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 使用已完成的任务
    task_id = input("请输入已完成的任务 ID (或按回车使用默认): ").strip()
    if not task_id:
        task_id = "task_1c8f2c5d561048db"  # 默认任务
    
    # 生成 artifact 请求
    payload = {
        "prompt_instance": {
            "template_id": "__blank__",
            "language": "zh-CN",
            "prompt_text": "请生成一份简短的会议纪要",
            "parameters": {}
        },
        "name": "测试会议纪要 - 自定义名称"  # 自定义名称
    }
    
    print(f"\n📤 发送请求: POST {BASE_URL}/tasks/{task_id}/artifacts/meeting_minutes/generate")
    print(f"   自定义名称: {payload['name']}")
    
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/artifacts/meeting_minutes/generate",
        json=payload,
        headers=headers
    )
    
    print(f"\n📥 响应状态: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ 生成成功")
        print(f"   artifact_id: {data['artifact_id']}")
        print(f"   version: {data['version']}")
        print(f"   display_name: {data.get('display_name', 'None')}")
        
        if data.get('display_name') == payload['name']:
            print(f"✅ display_name 正确返回")
        else:
            print(f"❌ display_name 不匹配")
            print(f"   期望: {payload['name']}")
            print(f"   实际: {data.get('display_name')}")
        
        return task_id, data['artifact_id']
    else:
        print(f"❌ 生成失败: {response.text}")
        return None, None


def test_list_artifacts(task_id):
    """测试列出 artifacts 时返回 display_name"""
    print("\n" + "=" * 80)
    print("测试 2: 列出 artifacts 时返回 display_name")
    print("=" * 80)
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n📤 发送请求: GET {BASE_URL}/tasks/{task_id}/artifacts")
    
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/artifacts",
        headers=headers
    )
    
    print(f"\n📥 响应状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功")
        print(f"   总数: {data['total_count']}")
        
        # 检查 meeting_minutes 类型的 artifacts
        if 'meeting_minutes' in data['artifacts_by_type']:
            artifacts = data['artifacts_by_type']['meeting_minutes']
            print(f"\n📋 meeting_minutes artifacts:")
            for artifact in artifacts:
                print(f"   - artifact_id: {artifact['artifact_id']}")
                print(f"     version: {artifact['version']}")
                print(f"     display_name: {artifact.get('display_name', 'None')}")
                print()
        else:
            print(f"⚠️  没有 meeting_minutes 类型的 artifacts")
    else:
        print(f"❌ 获取失败: {response.text}")


def test_generate_without_name():
    """测试生成 artifact 时不提供名称"""
    print("\n" + "=" * 80)
    print("测试 3: 生成 artifact 时不提供名称")
    print("=" * 80)
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    task_id = input("请输入已完成的任务 ID (或按回车使用默认): ").strip()
    if not task_id:
        task_id = "task_1c8f2c5d561048db"
    
    # 生成 artifact 请求（不提供 name）
    payload = {
        "prompt_instance": {
            "template_id": "__blank__",
            "language": "zh-CN",
            "prompt_text": "请生成一份简短的会议纪要",
            "parameters": {}
        }
        # 不提供 name 字段
    }
    
    print(f"\n📤 发送请求: POST {BASE_URL}/tasks/{task_id}/artifacts/meeting_minutes/generate")
    print(f"   不提供 name 字段")
    
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/artifacts/meeting_minutes/generate",
        json=payload,
        headers=headers
    )
    
    print(f"\n📥 响应状态: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ 生成成功")
        print(f"   artifact_id: {data['artifact_id']}")
        print(f"   version: {data['version']}")
        print(f"   display_name: {data.get('display_name', 'None')}")
        
        if data.get('display_name') is None:
            print(f"✅ display_name 正确为 None")
        else:
            print(f"⚠️  display_name 不为 None: {data.get('display_name')}")
    else:
        print(f"❌ 生成失败: {response.text}")


def test_regenerate_with_name():
    """测试重新生成 artifact 时提供自定义名称"""
    print("\n" + "=" * 80)
    print("测试 4: 重新生成 artifact 时提供自定义名称")
    print("=" * 80)
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    task_id = input("请输入已完成的任务 ID (或按回车使用默认): ").strip()
    if not task_id:
        task_id = "task_1c8f2c5d561048db"
    
    # 重新生成 artifact 请求
    payload = {
        "prompt_instance": {
            "template_id": "__blank__",
            "language": "zh-CN",
            "prompt_text": "请生成一份详细的会议纪要",
            "parameters": {}
        },
        "name": "重新生成的会议纪要 - 自定义名称"  # 自定义名称
    }
    
    print(f"\n📤 发送请求: POST {BASE_URL}/tasks/{task_id}/corrections/regenerate/meeting_minutes")
    print(f"   自定义名称: {payload['name']}")
    
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/corrections/regenerate/meeting_minutes",
        json=payload,
        headers=headers
    )
    
    print(f"\n📥 响应状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 重新生成成功")
        print(f"   artifact_id: {data['artifact_id']}")
        print(f"   version: {data['version']}")
        print(f"   display_name: {data.get('display_name', 'None')}")
        
        if data.get('display_name') == payload['name']:
            print(f"✅ display_name 正确返回")
        else:
            print(f"❌ display_name 不匹配")
            print(f"   期望: {payload['name']}")
            print(f"   实际: {data.get('display_name')}")
    else:
        print(f"❌ 重新生成失败: {response.text}")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Artifact Display Name 功能测试")
    print("=" * 80)
    
    # 测试 1: 生成 artifact 时提供自定义名称
    task_id, artifact_id = test_generate_with_name()
    
    if task_id:
        # 测试 2: 列出 artifacts 时返回 display_name
        test_list_artifacts(task_id)
    
    # 测试 3: 生成 artifact 时不提供名称
    test_generate_without_name()
    
    # 测试 4: 重新生成 artifact 时提供自定义名称
    test_regenerate_with_name()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
