# -*- coding: utf-8 -*-
"""测试 JWT 认证功能"""

import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"


def test_dev_login():
    """测试开发环境登录"""
    print("=" * 60)
    print("测试 1: 开发环境登录")
    print("=" * 60)
    
    # 登录
    response = requests.post(
        f"{BASE_URL}/auth/dev/login",
        json={"username": "test_user"}
    )
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ 登录成功!")
        print(f"   User ID: {data['user_id']}")
        print(f"   Tenant ID: {data['tenant_id']}")
        print(f"   Token: {data['access_token'][:50]}...")
        print(f"   Expires in: {data['expires_in']} seconds")
        return data['access_token']
    else:
        print(f"\n❌ 登录失败!")
        return None


def test_protected_endpoint(token):
    """测试受保护的端点"""
    print("\n" + "=" * 60)
    print("测试 2: 访问受保护的端点 (任务列表)")
    print("=" * 60)
    
    # 不带 Token
    print("\n2.1 不带 Token 访问:")
    response = requests.get(f"{BASE_URL}/tasks")
    print(f"状态码: {response.status_code}")
    if response.status_code == 401:
        print("✅ 正确拒绝未认证请求")
    else:
        print("❌ 应该返回 401")
    
    # 带 Token
    print("\n2.2 带 Token 访问:")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/tasks", headers=headers)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print("✅ 成功访问受保护端点")
        print(f"响应: {response.json()}")
    else:
        print(f"❌ 访问失败: {response.text}")


def test_invalid_token():
    """测试无效 Token"""
    print("\n" + "=" * 60)
    print("测试 3: 无效 Token")
    print("=" * 60)
    
    headers = {"Authorization": "Bearer invalid_token_12345"}
    response = requests.get(f"{BASE_URL}/tasks", headers=headers)
    print(f"状态码: {response.status_code}")
    if response.status_code == 401:
        print("✅ 正确拒绝无效 Token")
    else:
        print("❌ 应该返回 401")


def main():
    """主函数"""
    print("\n🔐 JWT 认证功能测试\n")
    
    try:
        # 测试登录
        token = test_dev_login()
        
        if not token:
            print("\n❌ 登录失败，终止测试")
            sys.exit(1)
        
        # 测试受保护端点
        test_protected_endpoint(token)
        
        # 测试无效 Token
        test_invalid_token()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务器，请确保服务器正在运行:")
        print("   python main.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
