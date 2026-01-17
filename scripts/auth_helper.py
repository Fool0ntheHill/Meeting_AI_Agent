"""
测试脚本认证辅助函数

提供统一的 JWT 认证支持，避免每个测试脚本重复实现登录逻辑。

使用方法:
    from auth_helper import get_auth_headers
    
    headers = get_auth_headers()
    response = requests.get(f"{BASE_URL}/tasks", headers=headers)
"""

import requests
from typing import Optional

# API 基础 URL
BASE_URL = "http://localhost:8000/api/v1"

# 全局 token 缓存（避免每次请求都登录）
_token_cache: Optional[str] = None
_username_cache: Optional[str] = None


def get_jwt_token(username: str = "test_user", force_refresh: bool = False) -> str:
    """
    获取 JWT token
    
    Args:
        username: 用户名（默认 test_user）
        force_refresh: 是否强制刷新 token（默认 False）
        
    Returns:
        JWT token 字符串
        
    Raises:
        Exception: 登录失败时抛出异常
        
    Example:
        >>> token = get_jwt_token("my_user")
        >>> print(f"Token: {token[:20]}...")
    """
    global _token_cache, _username_cache
    
    # 如果缓存存在且用户名相同，且不强制刷新，则返回缓存
    if not force_refresh and _token_cache and _username_cache == username:
        return _token_cache
    
    # 调用登录接口
    try:
        response = requests.post(
            f"{BASE_URL}/auth/dev/login",
            json={"username": username},
            timeout=10
        )
        
        if response.status_code != 200:
            raise Exception(
                f"登录失败: {response.status_code}\n"
                f"响应: {response.text}"
            )
        
        data = response.json()
        token = data["access_token"]
        
        # 更新缓存
        _token_cache = token
        _username_cache = username
        
        return token
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"登录请求失败: {e}")


def get_auth_headers(username: str = "test_user", force_refresh: bool = False) -> dict:
    """
    获取认证 headers（推荐使用）
    
    Args:
        username: 用户名（默认 test_user）
        force_refresh: 是否强制刷新 token（默认 False）
        
    Returns:
        包含 Authorization header 的字典
        
    Example:
        >>> headers = get_auth_headers()
        >>> response = requests.get(f"{BASE_URL}/tasks", headers=headers)
    """
    token = get_jwt_token(username, force_refresh)
    return {"Authorization": f"Bearer {token}"}


def clear_token_cache():
    """
    清除 token 缓存
    
    在需要切换用户或 token 过期时调用
    """
    global _token_cache, _username_cache
    _token_cache = None
    _username_cache = None


def login_and_print_info(username: str = "test_user") -> dict:
    """
    登录并打印用户信息（用于调试）
    
    Args:
        username: 用户名
        
    Returns:
        完整的登录响应数据
    """
    response = requests.post(
        f"{BASE_URL}/auth/dev/login",
        json={"username": username},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ 登录失败: {response.status_code}")
        print(f"响应: {response.text}")
        return {}
    
    data = response.json()
    
    print("✅ 登录成功!")
    print(f"用户 ID: {data.get('user_id')}")
    print(f"租户 ID: {data.get('tenant_id')}")
    print(f"Token 类型: {data.get('token_type')}")
    print(f"过期时间: {data.get('expires_in')} 秒")
    print(f"Token: {data.get('access_token')[:50]}...")
    
    return data


if __name__ == "__main__":
    """
    测试认证辅助函数
    
    运行: python scripts/auth_helper.py
    """
    print("=" * 80)
    print("  测试认证辅助函数")
    print("=" * 80)
    print()
    
    # 测试登录
    print("测试 1: 登录并获取 token")
    print("-" * 80)
    try:
        login_and_print_info("test_user")
        print()
    except Exception as e:
        print(f"❌ 错误: {e}")
        print()
    
    # 测试获取 headers
    print("测试 2: 获取认证 headers")
    print("-" * 80)
    try:
        headers = get_auth_headers("test_user")
        print(f"✅ Headers: {headers}")
        print()
    except Exception as e:
        print(f"❌ 错误: {e}")
        print()
    
    # 测试缓存
    print("测试 3: 测试 token 缓存")
    print("-" * 80)
    try:
        token1 = get_jwt_token("test_user")
        token2 = get_jwt_token("test_user")  # 应该使用缓存
        print(f"✅ Token 缓存工作正常: {token1 == token2}")
        print()
    except Exception as e:
        print(f"❌ 错误: {e}")
        print()
    
    # 测试清除缓存
    print("测试 4: 清除缓存并重新获取")
    print("-" * 80)
    try:
        clear_token_cache()
        token3 = get_jwt_token("test_user")
        print(f"✅ 缓存已清除，获取新 token: {token3[:50]}...")
        print()
    except Exception as e:
        print(f"❌ 错误: {e}")
        print()
    
    print("=" * 80)
    print("  测试完成")
    print("=" * 80)
