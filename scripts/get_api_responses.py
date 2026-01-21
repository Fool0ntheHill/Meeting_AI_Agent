"""获取 API 响应体"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
from scripts.auth_helper import get_auth_headers

headers = get_auth_headers("test_user")
task_id = "task_07cb88970c3848c4"

print("=" * 80)
print("1. GET /api/v1/tasks/{task_id}")
print("=" * 80)
r1 = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}", headers=headers)
print(f"Status: {r1.status_code}")
print(json.dumps(r1.json(), indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("2. GET /api/v1/tasks/{task_id}/transcript")
print("=" * 80)
r2 = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}/transcript", headers=headers)
print(f"Status: {r2.status_code}")
data = r2.json()
# 只显示前3个 segments
if 'segments' in data and len(data['segments']) > 3:
    segments = data['segments'][:3]
    data['segments'] = segments + [f"... (省略 {len(r2.json()['segments']) - 3} 个片段)"]
print(json.dumps(data, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("3. GET /api/v1/tasks/{task_id}/artifacts")
print("=" * 80)
r3 = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}/artifacts", headers=headers)
print(f"Status: {r3.status_code}")
print(json.dumps(r3.json(), indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("4. GET /api/v1/artifacts/{artifact_id}")
print("=" * 80)
artifact_id = "art_task_07cb88970c3848c4_meeting_minutes_v1"
r4 = requests.get(f"http://localhost:8000/api/v1/artifacts/{artifact_id}", headers=headers)
print(f"Status: {r4.status_code}")
print(json.dumps(r4.json(), indent=2, ensure_ascii=False))
