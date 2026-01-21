import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
from scripts.auth_helper import get_auth_headers

headers = get_auth_headers("test_user")
artifact_id = "art_task_07cb88970c3848c4_meeting_minutes_v1"

r = requests.get(f"http://localhost:8000/api/v1/artifacts/{artifact_id}", headers=headers)
data = r.json()

content = data['artifact']['content']
print(f"Type: {type(content)}")
print(f"Is dict: {isinstance(content, dict)}")
print(f"Is str: {isinstance(content, str)}")

if isinstance(content, str):
    print(f"\nFirst 100 chars: {content[:100]}")
    # Try to parse it
    try:
        parsed = json.loads(content)
        print(f"Can be parsed to dict: {isinstance(parsed, dict)}")
    except:
        print("Cannot be parsed as JSON")
elif isinstance(content, dict):
    print(f"\nKeys: {list(content.keys())}")
