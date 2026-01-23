# -*- coding: utf-8 -*-
"""测试 GSUC OAuth2.0 认证流程"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.providers.gsuc_auth import GSUCAuthProvider, GSUCAuthError


async def test_login_url():
    """测试生成登录 URL"""
    print("=" * 80)
    print("测试 1: 生成 GSUC 登录 URL")
    print("=" * 80)
    
    # 配置 (需要替换为实际值)
    appid = "gs10001"
    appsecret = "your-appsecret"
    encryption_key = "your-encryption-key"
    
    # 创建提供商
    provider = GSUCAuthProvider(appid, appsecret, encryption_key)
    
    # 生成登录 URL
    redirect_uri = "http://localhost:8000/api/v1/auth/gsuc/callback"
    state = "test-state-123"
    login_url = provider.get_login_url(redirect_uri, state)
    
    print(f"\n✓ 登录 URL 生成成功:")
    print(f"  {login_url}")
    print(f"\n参数说明:")
    print(f"  - appid: {appid}")
    print(f"  - redirect_uri: {redirect_uri}")
    print(f"  - state: {state}")
    
    return login_url


async def test_user_info():
    """测试获取用户信息"""
    print("\n" + "=" * 80)
    print("测试 2: 获取用户信息")
    print("=" * 80)
    
    # 配置 (需要替换为实际值)
    appid = "gs10001"
    appsecret = "your-appsecret"
    encryption_key = "your-encryption-key"
    
    # 创建提供商
    provider = GSUCAuthProvider(appid, appsecret, encryption_key)
    
    print("\n请按照以下步骤操作:")
    print("1. 在浏览器中打开上面生成的登录 URL")
    print("2. 使用企业微信扫码登录")
    print("3. 登录后，GSUC 会重定向到回调地址")
    print("4. 从浏览器地址栏复制 code 参数")
    print("\n示例: http://localhost:8000/api/v1/auth/gsuc/callback?code=ABC123&state=test-state-123")
    print("      复制 ABC123 部分")
    
    # 手动输入 code
    code = input("\n请输入 code (或按 Enter 跳过): ").strip()
    
    if not code:
        print("\n⊘ 跳过用户信息测试")
        return
    
    try:
        # 获取用户信息
        user_info = await provider.get_user_info(code)
        
        print(f"\n✓ 用户信息获取成功:")
        print(f"  - rc: {user_info.get('rc')}")
        print(f"  - msg: {user_info.get('msg')}")
        print(f"  - appid: {user_info.get('appid')}")
        print(f"  - uid: {user_info.get('uid')}")
        print(f"  - account: {user_info.get('account')}")
        print(f"  - username: {user_info.get('username')}")
        print(f"  - avatar: {user_info.get('avatar', '')[:50]}...")
        
        # 测试简化接口
        print("\n测试简化接口:")
        simple_info = await provider.verify_and_get_user(code)
        print(f"  - uid: {simple_info['uid']}")
        print(f"  - account: {simple_info['account']}")
        print(f"  - username: {simple_info['username']}")
        
    except GSUCAuthError as e:
        print(f"\n✗ GSUC 认证失败:")
        print(f"  - 错误码: {e.error_code}")
        print(f"  - 错误信息: {e.message}")
        
    except Exception as e:
        print(f"\n✗ 请求失败: {e}")


async def test_encryption():
    """测试 access_token 加密"""
    print("\n" + "=" * 80)
    print("测试 3: access_token 加密")
    print("=" * 80)
    
    # 配置 (需要替换为实际值)
    appid = "gs10001"
    appsecret = "your-appsecret"
    encryption_key = "your-encryption-key"
    
    # 创建提供商
    provider = GSUCAuthProvider(appid, appsecret, encryption_key)
    
    # 测试加密
    test_code = "TEST_CODE_123"
    access_token = provider._encrypt_access_token(test_code)
    
    print(f"\n✓ access_token 加密成功:")
    print(f"  - 输入: {test_code}{appid}{appsecret}")
    print(f"  - 输出: {access_token[:50]}...")
    print(f"  - 长度: {len(access_token)} 字符")


async def main():
    """主测试流程"""
    print("\n" + "=" * 80)
    print("GSUC OAuth2.0 认证测试")
    print("=" * 80)
    
    print("\n注意事项:")
    print("1. 需要向运维申请 appid, appsecret, encryption_key")
    print("2. 需要将回调地址加入 GSUC 白名单")
    print("3. 本地测试使用 http://localhost:8000/api/v1/auth/gsuc/callback")
    print("4. 生产环境使用 https://your-domain.com/api/v1/auth/gsuc/callback")
    
    print("\n配置说明:")
    print("请编辑 scripts/test_gsuc_auth.py，替换以下配置:")
    print("  - appid: 应用 ID")
    print("  - appsecret: 应用密钥")
    print("  - encryption_key: 加密密钥")
    
    # 测试 1: 生成登录 URL
    login_url = await test_login_url()
    
    # 测试 2: 获取用户信息
    await test_user_info()
    
    # 测试 3: 加密测试
    await test_encryption()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    print("\n下一步:")
    print("1. 配置 config/development.yaml 中的 GSUC 配置")
    print("2. 启动后端: python main.py")
    print("3. 测试完整登录流程:")
    print("   - POST /api/v1/auth/gsuc/login")
    print("   - 浏览器打开返回的 login_url")
    print("   - 扫码登录")
    print("   - 验证回调处理")


if __name__ == "__main__":
    asyncio.run(main())
