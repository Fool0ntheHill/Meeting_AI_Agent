"""测试异步 artifact 生成修复"""

import sys
import os
import time
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token

BASE_URL = "http://localhost:8000"

def test_async_generation():
    """测试异步生成是否正常工作"""
    
    # 1. 获取 token
    print("1. 获取测试 token...")
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 使用已存在的任务
    task_id = "task_dadac03a8f3048ef"
    print(f"\n2. 使用任务: {task_id}")
    
    # 3. 发起异步生成请求
    print("\n3. 发起异步生成请求...")
    generate_data = {
        "artifact_type": "meeting_minutes",
        "prompt_instance": {
            "template_id": "__blank__",
            "language": "zh-CN",
            "parameters": {},
            "prompt_text": "请统计每个说话人的发言句数"
        },
        "display_name": "测试异步修复"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/tasks/{task_id}/artifacts/generate",
        json=generate_data,
        headers=headers
    )
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    
    if response.status_code != 202:
        print(f"❌ 期望状态码 202，实际 {response.status_code}")
        return False
    
    result = response.json()
    artifact_id = result["artifact_id"]
    print(f"\n✅ 占位 artifact 已创建: {artifact_id}")
    print(f"   状态: {result['state']}")
    
    # 4. 轮询检查状态
    print("\n4. 轮询检查生成状态...")
    max_attempts = 30
    for i in range(max_attempts):
        time.sleep(2)
        
        status_response = requests.get(
            f"{BASE_URL}/api/v1/artifacts/{artifact_id}/status",
            headers=headers
        )
        
        if status_response.status_code != 200:
            print(f"❌ 状态查询失败: {status_response.status_code}")
            continue
        
        status = status_response.json()
        print(f"   [{i+1}/{max_attempts}] 状态: {status['state']}")
        
        if status["state"] == "success":
            print(f"\n✅ 生成成功！")
            print(f"   内容预览: {str(status.get('content', {}))[:200]}...")
            return True
        elif status["state"] == "failed":
            print(f"\n❌ 生成失败")
            print(f"   错误: {status.get('content', {})}")
            return False
        elif status["state"] == "processing":
            continue
        else:
            print(f"\n❓ 未知状态: {status['state']}")
            return False
    
    print(f"\n❌ 超时：{max_attempts * 2} 秒后仍未完成")
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("测试异步 Artifact 生成修复")
    print("=" * 60)
    
    success = test_async_generation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
