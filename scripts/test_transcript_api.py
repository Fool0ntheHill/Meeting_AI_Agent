"""测试 transcript API"""

import requests
from auth_helper import get_jwt_token

BASE_URL = "http://localhost:8000/api/v1"

def test_transcript_api():
    """测试获取转写文本接口"""
    
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取任务列表，找一个成功的任务
    print("=" * 60)
    print("获取任务列表...")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/tasks",
        headers=headers,
        params={"limit": 10, "state": "success"}
    )
    
    if response.status_code != 200:
        print(f"❌ 获取任务列表失败: {response.status_code}")
        print(response.text)
        return
    
    tasks = response.json()
    if not tasks:
        print("⚠️  没有找到成功的任务")
        return
    
    print(f"✅ 找到 {len(tasks)} 个成功的任务\n")
    
    # 测试第一个任务的 transcript
    task = tasks[0]
    task_id = task["task_id"]
    
    print(f"测试任务: {task_id}")
    print(f"  状态: {task['state']}")
    print(f"  时长: {task.get('duration', 'N/A')} 秒")
    print()
    
    # 获取转写文本
    print("=" * 60)
    print(f"获取转写文本: {task_id}")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/transcript",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ 获取转写文本失败: {response.status_code}")
        print(response.text)
        return
    
    transcript = response.json()
    
    print(f"✅ 成功获取转写文本")
    print(f"  任务ID: {transcript['task_id']}")
    print(f"  时长: {transcript['duration']} 秒")
    print(f"  语言: {transcript['language']}")
    print(f"  提供商: {transcript['provider']}")
    print(f"  片段数: {len(transcript['segments'])}")
    print(f"  完整文本长度: {len(transcript['full_text'])} 字符")
    print()
    
    # 显示前3个片段
    if transcript['segments']:
        print("前3个片段:")
        for i, seg in enumerate(transcript['segments'][:3], 1):
            print(f"  {i}. [{seg['start_time']:.1f}s - {seg['end_time']:.1f}s] "
                  f"{seg.get('speaker', 'Unknown')}: {seg['text'][:50]}...")
    
    print("\n✅ Transcript API 测试通过！")

if __name__ == "__main__":
    test_transcript_api()
