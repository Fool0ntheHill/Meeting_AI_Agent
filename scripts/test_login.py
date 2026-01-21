#!/usr/bin/env python3
import requests

# 测试不同的 username
usernames = ["test_user", "user_test_user"]

for username in usernames:
    print(f"\n测试 username: {username}")
    r = requests.post('http://localhost:8000/api/v1/auth/dev/login', json={'username': username})
    if r.status_code == 200:
        data = r.json()
        print(f"  返回的 user_id: {data['user_id']}")
        print(f"  返回的 tenant_id: {data['tenant_id']}")
    else:
        print(f"  错误: {r.status_code}")
