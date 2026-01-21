"""检查 workspace 页面需要的数据"""

import requests
import json
from auth_helper import get_jwt_token

BASE_URL = "http://localhost:8000/api/v1"
TASK_ID = "task_40845e189dfa463a"

def check_workspace_data():
    """检查 workspace 需要的所有数据"""
    
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 80)
    print("1. GET /api/v1/tasks/{task_id}")
    print("=" * 80)
    
    response = requests.get(
        f"{BASE_URL}/tasks/{TASK_ID}",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(response.text)
    
    print("\n" + "=" * 80)
    print("2. GET /api/v1/tasks/{task_id}/transcript")
    print("=" * 80)
    
    response = requests.get(
        f"{BASE_URL}/tasks/{TASK_ID}/transcript",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        # 只显示前3个 segments，避免输出太长
        if 'segments' in data and len(data['segments']) > 3:
            segments_count = len(data['segments'])
            data['segments'] = data['segments'][:3]
            data['segments'].append(f"... (省略 {segments_count - 3} 个片段)")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(response.text)
    
    print("\n" + "=" * 80)
    print("3. GET /api/v1/tasks/{task_id}/artifacts")
    print("=" * 80)
    
    response = requests.get(
        f"{BASE_URL}/tasks/{TASK_ID}/artifacts",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(response.text)
    
    print("\n" + "=" * 80)
    print("问题分析")
    print("=" * 80)
    
    # 重新获取数据进行分析
    task_response = requests.get(f"{BASE_URL}/tasks/{TASK_ID}", headers=headers)
    transcript_response = requests.get(f"{BASE_URL}/tasks/{TASK_ID}/transcript", headers=headers)
    artifacts_response = requests.get(f"{BASE_URL}/tasks/{TASK_ID}/artifacts", headers=headers)
    
    if task_response.status_code == 200:
        task = task_response.json()
        audio_files = task.get('audio_files', [])
        
        print("\n音频文件:")
        if audio_files:
            for i, file in enumerate(audio_files, 1):
                print(f"  {i}. {file}")
                if file.startswith('uploads/'):
                    print(f"     ⚠️  这是相对路径，前端需要拼接为完整 URL")
                elif file.startswith('http'):
                    print(f"     ✅ 这是完整 URL，可以直接播放")
        else:
            print("  ❌ 没有音频文件")
    
    if transcript_response.status_code == 200:
        transcript = transcript_response.json()
        segments = transcript.get('segments', [])
        print(f"\n逐字稿:")
        print(f"  片段数: {len(segments)}")
        if segments:
            print(f"  ✅ 有逐字稿数据")
        else:
            print(f"  ❌ 逐字稿为空")
    else:
        print(f"\n逐字稿:")
        print(f"  ❌ 获取失败: {transcript_response.status_code}")
    
    if artifacts_response.status_code == 200:
        artifacts = artifacts_response.json()
        print(f"\n会议纪要:")
        if artifacts:
            for artifact_type, versions in artifacts.items():
                print(f"  {artifact_type}: {len(versions)} 个版本")
        else:
            print(f"  ❌ 没有生成会议纪要")
            print(f"     原因: 任务可能在 LLM 阶段失败（Gemini API key 问题）")
    else:
        print(f"\n会议纪要:")
        print(f"  ❌ 获取失败: {artifacts_response.status_code}")

if __name__ == "__main__":
    check_workspace_data()
