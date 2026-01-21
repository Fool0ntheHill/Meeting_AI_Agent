"""测试新任务的 artifacts"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from scripts.auth_helper import get_auth_headers

# 获取 headers
headers = get_auth_headers("test_user")

# 测试新任务
task_id = "task_07cb88970c3848c4"

print(f"测试任务: {task_id}")
print("=" * 60)

# 获取 artifacts
response = requests.get(
    f"http://localhost:8000/api/v1/tasks/{task_id}/artifacts",
    headers=headers
)

print(f"Status: {response.status_code}")
data = response.json()

print(f"\nArtifacts:")
print(f"  total_count: {data.get('total_count', 0)}")
print(f"  artifacts_by_type: {list(data.get('artifacts_by_type', {}).keys())}")

for artifact_type, versions in data.get('artifacts_by_type', {}).items():
    print(f"\n  {artifact_type}:")
    for version in versions:
        print(f"    版本 {version['version']}:")
        print(f"      artifact_id: {version['artifact_id']}")
        print(f"      created_at: {version['created_at']}")
        
        # 显示内容的前200个字符
        content = version.get('content', {})
        if isinstance(content, dict):
            for key, value in list(content.items())[:3]:
                value_str = str(value)[:100]
                print(f"      {key}: {value_str}...")
