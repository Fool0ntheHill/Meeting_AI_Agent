"""测试音频文件和 artifact 内容"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from scripts.auth_helper import get_auth_headers

headers = get_auth_headers("test_user")
base_url = "http://localhost:8000"

print("=" * 60)
print("1. 测试音频文件访问")
print("=" * 60)

audio_url = f"{base_url}/uploads/user_test_user/82598a9424d0495e.ogg"
r = requests.get(audio_url)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    print(f"✅ 音频文件可访问")
    print(f"Content-Type: {r.headers.get('content-type')}")
    print(f"Content-Length: {r.headers.get('content-length')} bytes")
else:
    print(f"❌ 音频文件不可访问")
    print(f"Response: {r.text[:200]}")

print("\n" + "=" * 60)
print("2. 测试 Artifact Content 解析")
print("=" * 60)

artifact_id = "art_task_07cb88970c3848c4_meeting_minutes_v1"
r = requests.get(f"{base_url}/api/v1/artifacts/{artifact_id}", headers=headers)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    content = data['artifact']['content']
    
    print(f"Content type: {type(content)}")
    
    if isinstance(content, dict):
        print(f"✅ Content 是字典对象")
        print(f"Keys: {list(content.keys())}")
        print(f"\n会议概要: {content.get('会议概要', 'N/A')[:100]}...")
    elif isinstance(content, str):
        print(f"⚠️  Content 还是字符串")
        print(f"First 100 chars: {content[:100]}")
        
        # 尝试解析
        import json
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                print(f"✅ 可以手动解析为字典")
                print(f"Keys: {list(parsed.keys())}")
            else:
                print(f"❌ 解析后还是 {type(parsed)}")
        except:
            print(f"❌ 无法解析为 JSON")
else:
    print(f"❌ 请求失败")
    print(f"Response: {r.text}")
