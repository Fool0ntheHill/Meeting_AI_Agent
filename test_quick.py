import requests
import json

# 登录获取 token
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/dev/login",
    json={"username": "test_user"}
)
print(f"登录状态: {login_response.status_code}")
token = login_response.json()["access_token"]

# 创建任务
task_data = {
    "audio_files": ["test_audio.wav"],
    "file_order": [0],
    "meeting_type": "integration_test",  # 添加必需字段
    "prompt_instance": {
        "template_id": "tpl_meeting_minutes_001",
        "language": "zh-CN",
        "parameters": {
            "meeting_description": "集成测试会议"
        }
    },
    "asr_language": "zh-CN+en-US",
    "output_language": "zh-CN",
    "skip_speaker_recognition": True,
}

response = requests.post(
    "http://localhost:8000/api/v1/tasks",
    json=task_data,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
)

print(f"\n状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
