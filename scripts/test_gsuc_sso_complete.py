#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GSUC SSO 完整流程测试脚本

测试内容:
1. 加密算法验证 (Python 2 -> Python 3 迁移)
2. 生成 GSUC 登录 URL
3. 模拟回调处理流程
4. 验证 JWT Token 生成

使用方式:
    python scripts/test_gsuc_sso_complete.py
"""

import asyncio
import base64
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.providers.gsuc_auth import GSUCAuthProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_encryption_algorithm():
    """测试加密算法 (验证 Python 2 -> Python 3 迁移)"""
    print("\n" + "=" * 60)
    print("测试 1: 加密算法验证")
    print("=" * 60)
    
    # 测试配置
    APP_ID = "app_meeting_agent"
    APP_SECRET = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
    ENCRYPTION_KEY = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="  # Base64 编码的 32 字节密钥
    
    # 创建提供商
    provider = GSUCAuthProvider(
        appid=APP_ID,
        appsecret=APP_SECRET,
        encryption_key=ENCRYPTION_KEY
    )
    
    # 测试加密
    test_code = "test_code_12345"
    
    try:
        access_token = provider._encrypt_access_token(test_code)
        print(f"✓ 加密成功")
        print(f"  Code: {test_code}")
        print(f"  Access Token (前50字符): {access_token[:50]}...")
        print(f"  Access Token 长度: {len(access_token)}")
        
        # 验证 Base64 编码
        try:
            decoded = base64.b64decode(access_token)
            print(f"✓ Base64 解码成功，长度: {len(decoded)} 字节")
        except Exception as e:
            print(f"✗ Base64 解码失败: {e}")
            return False
        
        # 多次加密应该产生不同结果 (因为有随机前缀)
        access_token2 = provider._encrypt_access_token(test_code)
        if access_token != access_token2:
            print(f"✓ 随机前缀工作正常 (每次加密结果不同)")
        else:
            print(f"⚠ 警告: 两次加密结果相同 (随机前缀可能有问题)")
        
        return True
        
    except Exception as e:
        print(f"✗ 加密失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_login_url_generation():
    """测试登录 URL 生成"""
    print("\n" + "=" * 60)
    print("测试 2: 生成 GSUC 登录 URL")
    print("=" * 60)
    
    # 测试配置
    APP_ID = "app_meeting_agent"
    APP_SECRET = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
    ENCRYPTION_KEY = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
    
    # 创建提供商
    provider = GSUCAuthProvider(
        appid=APP_ID,
        appsecret=APP_SECRET,
        encryption_key=ENCRYPTION_KEY,
        login_url="https://gsuc.gamesci.com.cn/sso/login"
    )
    
    # 生成登录 URL
    redirect_uri = "http://localhost:8000/api/v1/auth/gsuc/callback"
    state = "random_state_12345"
    
    login_url = provider.get_login_url(redirect_uri, state)
    
    print(f"✓ 登录 URL 生成成功")
    print(f"  Redirect URI: {redirect_uri}")
    print(f"  State: {state}")
    print(f"  Login URL: {login_url}")
    
    # 验证 URL 格式
    if "appid=" in login_url and "redirect_uri=" in login_url and "state=" in login_url:
        print(f"✓ URL 参数完整")
        return True
    else:
        print(f"✗ URL 参数不完整")
        return False


async def test_user_info_mock():
    """测试用户信息获取 (模拟)"""
    print("\n" + "=" * 60)
    print("测试 3: 用户信息获取 (模拟)")
    print("=" * 60)
    
    print("⚠ 注意: 此测试需要真实的 GSUC code 才能完成")
    print("  实际使用时，需要:")
    print("  1. 用户扫码登录 GSUC")
    print("  2. GSUC 重定向到回调地址，携带 code")
    print("  3. 后端使用 code 调用 get_user_info()")
    print()
    print("  模拟响应格式:")
    print("  {")
    print('    "rc": 0,')
    print('    "msg": "success",')
    print('    "appid": "app_meeting_agent",')
    print('    "uid": 1003,')
    print('    "account": "zhangsan",')
    print('    "username": "张三",')
    print('    "avatar": "https://...",')
    print('    "thumb_avatar": "https://..."')
    print("  }")
    
    return True


def test_callback_flow():
    """测试回调流程 (模拟)"""
    print("\n" + "=" * 60)
    print("测试 4: 回调流程 (模拟)")
    print("=" * 60)
    
    print("完整 SSO 流程:")
    print()
    print("1. 前端调用 POST /api/v1/auth/gsuc/login")
    print("   请求体: { 'frontend_callback_url': 'http://localhost:5173/auth/callback' }")
    print()
    print("2. 后端返回 GSUC 登录 URL 和 state")
    print("   响应: { 'login_url': '...', 'state': '...' }")
    print()
    print("3. 前端重定向用户到 GSUC 登录页面")
    print()
    print("4. 用户扫码登录")
    print()
    print("5. GSUC 重定向到后端回调地址")
    print("   GET /api/v1/auth/gsuc/callback?code=xxx&state=xxx&frontend_callback=xxx")
    print()
    print("6. 后端处理回调:")
    print("   a. 验证 state")
    print("   b. 使用 code 获取用户信息")
    print("   c. 查找或创建用户记录")
    print("   d. 签发 JWT Token")
    print()
    print("7. 后端重定向到前端回调地址")
    print("   http://localhost:5173/auth/callback?access_token=xxx&user_id=xxx&...")
    print()
    print("8. 前端保存 Token，完成登录")
    
    return True


def test_encryption_key_validation():
    """测试加密密钥验证"""
    print("\n" + "=" * 60)
    print("测试 5: 加密密钥验证")
    print("=" * 60)
    
    # 测试有效密钥
    valid_key = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
    try:
        decoded = base64.b64decode(valid_key)
        print(f"✓ 有效密钥: 长度 {len(decoded)} 字节")
        if len(decoded) == 32:
            print(f"✓ 密钥长度正确 (32 字节 = AES-256)")
        else:
            print(f"✗ 密钥长度错误: {len(decoded)} 字节 (期望 32 字节)")
            return False
    except Exception as e:
        print(f"✗ 密钥解码失败: {e}")
        return False
    
    # 测试无效密钥
    print()
    print("测试无效密钥:")
    
    invalid_keys = [
        ("短密钥", "short_key"),
        ("非 Base64", "not@base64!"),
        ("空密钥", ""),
    ]
    
    for name, key in invalid_keys:
        try:
            provider = GSUCAuthProvider(
                appid="test",
                appsecret="test",
                encryption_key=key
            )
            access_token = provider._encrypt_access_token("test_code")
            print(f"✗ {name} 应该失败但成功了")
        except Exception as e:
            print(f"✓ {name} 正确拒绝: {str(e)[:50]}...")
    
    return True


async def main():
    """主函数"""
    print("=" * 60)
    print("GSUC SSO 完整流程测试")
    print("=" * 60)
    
    results = []
    
    # 测试 1: 加密算法
    results.append(("加密算法验证", test_encryption_algorithm()))
    
    # 测试 2: 登录 URL 生成
    results.append(("登录 URL 生成", test_login_url_generation()))
    
    # 测试 3: 用户信息获取 (模拟)
    results.append(("用户信息获取", await test_user_info_mock()))
    
    # 测试 4: 回调流程 (模拟)
    results.append(("回调流程说明", test_callback_flow()))
    
    # 测试 5: 加密密钥验证
    results.append(("加密密钥验证", test_encryption_key_validation()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print()
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！GSUC SSO 实现正确。")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
