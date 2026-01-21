#!/usr/bin/env python3
import requests

task_id = "task_ab07a64f9e8d4f69"

# 使用正确的 username 登录
print("1. 登录...")
login_response = requests.post(
    'http://localhost:8000/api/v1/auth/dev/login',
    json={'username': 'test_user'}
)
token_data = login_response.json()
print(f"   user_id: {token_data['user_id']}")
print(f"   tenant_id: {token_data['tenant_id']}")

token = token_data['access_token']
headers = {"Authorization": f"Bearer {token}"}

# 测试 transcript API
print(f"\n2. 获取 transcript...")
url = f"http://localhost:8000/api/v1/tasks/{task_id}/transcript"
response = requests.get(url, headers=headers)

print(f"   Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    speaker_mapping = data.get("speaker_mapping")
    
    print(f"\n3. speaker_mapping:")
    if speaker_mapping:
        print(f"   类型: {type(speaker_mapping)}")
        for label, name in speaker_mapping.items():
            print(f"   {label} -> {name}")
        print("\n✅ 成功！前端应该能看到真实姓名了")
    else:
        print("   ❌ speaker_mapping 为空")
else:
    print(f"   错误: {response.text}")
