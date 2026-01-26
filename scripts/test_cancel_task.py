"""测试任务取消功能"""

import time
import requests
from scripts.auth_helper import get_test_token

BASE_URL = "http://localhost:8000/api/v1"


def test_cancel_task():
    """测试取消正在执行的任务"""
    
    # 1. 获取认证 token
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 创建一个新任务
    print("\n=== 创建测试任务 ===")
    create_response = requests.post(
        f"{BASE_URL}/tasks",
        headers=headers,
        json={
            "audio_files": ["test_data/meeting.ogg"],
            "meeting_type": "取消功能测试",
            "asr_language": "zh-CN+en-US",
            "output_language": "zh-CN",
            "skip_speaker_recognition": True,  # 跳过声纹识别，加快测试
            "prompt_instance": {
                "template_id": "__blank__",
                "language": "zh-CN",
                "prompt_text": "请生成简短的会议纪要",
                "parameters": {}
            }
        }
    )
    
    if create_response.status_code != 201:
        print(f"❌ 创建任务失败: {create_response.status_code}")
        print(create_response.text)
        return
    
    task_id = create_response.json()["task_id"]
    print(f"✅ 任务已创建: {task_id}")
    
    # 3. 等待任务开始执行
    print("\n=== 等待任务开始执行 ===")
    time.sleep(5)  # 等待 5 秒让任务开始
    
    # 4. 检查任务状态
    status_response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/status",
        headers=headers
    )
    
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"当前状态: {status['state']}, 进度: {status['progress']}%")
    
    # 5. 取消任务
    print("\n=== 取消任务 ===")
    cancel_response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/cancel",
        headers=headers
    )
    
    if cancel_response.status_code == 200:
        result = cancel_response.json()
        print(f"✅ 任务已取消")
        print(f"   之前状态: {result['previous_state']}")
        print(f"   消息: {result['message']}")
    else:
        print(f"❌ 取消失败: {cancel_response.status_code}")
        print(cancel_response.text)
        return
    
    # 6. 再次检查任务状态
    print("\n=== 验证取消状态 ===")
    time.sleep(2)
    
    status_response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/status",
        headers=headers
    )
    
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"最终状态: {status['state']}")
        
        if status['state'] == 'cancelled':
            print("✅ 任务已成功取消")
        else:
            print(f"⚠️  任务状态为: {status['state']}")
    
    # 7. 尝试取消已完成的任务（应该失败）
    print("\n=== 测试取消已完成任务（应该失败） ===")
    
    # 创建一个已完成的任务
    from scripts.create_completed_task_for_test import create_completed_task
    completed_task_id = create_completed_task()
    
    cancel_response = requests.post(
        f"{BASE_URL}/tasks/{completed_task_id}/cancel",
        headers=headers
    )
    
    if cancel_response.status_code == 400:
        print("✅ 正确拒绝取消已完成的任务")
        print(f"   错误信息: {cancel_response.json()['detail']}")
    else:
        print(f"⚠️  预期状态码 400，实际: {cancel_response.status_code}")


if __name__ == "__main__":
    test_cancel_task()
