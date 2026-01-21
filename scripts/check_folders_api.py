"""
检查文件夹列表 API
"""

import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token

def check_folders_api():
    """检查文件夹列表 API"""
    
    token = get_jwt_token()
    
    url = "http://localhost:8000/api/v1/folders"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print("=" * 60)
    print("检查文件夹列表 API")
    print("=" * 60)
    print(f"\nGET {url}\n")
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)
        return
    
    folders = response.json()
    
    print(f"✓ 成功获取 {len(folders)} 个文件夹\n")
    print(json.dumps(folders, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    check_folders_api()
