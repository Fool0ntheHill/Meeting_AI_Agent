#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GSUC 配置诊断脚本

用于排查 GSUC 认证第一次就失败的问题
"""

import base64
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.loader import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def diagnose_gsuc_config():
    """诊断 GSUC 配置"""
    
    print("=" * 60)
    print("GSUC 配置诊断")
    print("=" * 60)
    print()
    
    # 1. 加载配置
    print("1. 加载配置文件...")
    try:
        config = get_config()
        print("   ✓ 配置文件加载成功")
    except Exception as e:
        print(f"   ✗ 配置文件加载失败: {e}")
        return
    
    print()
    
    # 2. 检查 GSUC 是否启用
    print("2. 检查 GSUC 是否启用...")
    if not config.gsuc or not config.gsuc.enabled:
        print("   ✗ GSUC 未启用")
        print("   提示: 在 config/development.yaml 中设置 gsuc.enabled: true")
        return
    print("   ✓ GSUC 已启用")
    print()
    
    # 3. 检查必需配置项
    print("3. 检查必需配置项...")
    
    required_fields = {
        "appid": config.gsuc.appid,
        "appsecret": config.gsuc.appsecret,
        "encryption_key": config.gsuc.encryption_key,
        "login_url": config.gsuc.login_url,
        "userinfo_url": config.gsuc.userinfo_url,
        "callback_url": config.gsuc.callback_url,
    }
    
    all_ok = True
    for field, value in required_fields.items():
        if not value:
            print(f"   ✗ {field}: 未配置")
            all_ok = False
        else:
            # 隐藏敏感信息
            if field in ["appsecret", "encryption_key"]:
                display_value = f"{value[:10]}..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"   ✓ {field}: {display_value}")
    
    if not all_ok:
        print()
        print("   提示: 请在 config/development.yaml 中配置缺失的字段")
        return
    
    print()
    
    # 4. 验证 encryption_key
    print("4. 验证 encryption_key...")
    try:
        key = base64.b64decode(config.gsuc.encryption_key)
        key_length = len(key)
        
        if key_length == 32:
            print(f"   ✓ 密钥长度正确: {key_length} 字节")
        else:
            print(f"   ✗ 密钥长度错误: {key_length} 字节 (期望 32 字节)")
            print("   提示: encryption_key 必须是 Base64 编码的 32 字节密钥")
            print("   请联系 GSUC 运维确认密钥是否正确")
            all_ok = False
    except Exception as e:
        print(f"   ✗ 密钥解码失败: {e}")
        print("   提示: encryption_key 必须是有效的 Base64 字符串")
        all_ok = False
    
    print()
    
    # 5. 测试加密功能
    print("5. 测试加密功能...")
    try:
        from src.providers.gsuc_auth import GSUCAuthProvider
        
        provider = GSUCAuthProvider(
            appid=config.gsuc.appid,
            appsecret=config.gsuc.appsecret,
            encryption_key=config.gsuc.encryption_key,
            login_url=config.gsuc.login_url,
            userinfo_url=config.gsuc.userinfo_url,
        )
        
        # 测试加密（使用假的 code）
        test_code = "test_code_12345"
        access_token = provider._encrypt_access_token(test_code)
        
        print(f"   ✓ 加密功能正常")
        print(f"   测试 access_token: {access_token[:50]}...")
    except Exception as e:
        print(f"   ✗ 加密功能异常: {e}")
        all_ok = False
    
    print()
    
    # 6. 生成登录 URL
    print("6. 生成登录 URL...")
    try:
        login_url = provider.get_login_url(
            redirect_uri=config.gsuc.callback_url,
            state="test_state_123"
        )
        print(f"   ✓ 登录 URL 生成成功")
        print(f"   URL: {login_url}")
    except Exception as e:
        print(f"   ✗ 登录 URL 生成失败: {e}")
        all_ok = False
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✓ 所有检查通过")
        print()
        print("如果仍然遇到 500 错误，可能的原因：")
        print("1. GSUC 服务器配置与本地配置不匹配")
        print("   - 请联系 GSUC 运维确认 appid、appsecret、encryption_key")
        print("2. 回调地址未在 GSUC 白名单中")
        print("   - 请联系 GSUC 运维添加回调地址到白名单")
        print("3. 浏览器预取导致 code 被提前消耗")
        print("   - 尝试在隐私模式下测试")
        print("   - 禁用浏览器插件后测试")
        print()
        print("调试建议：")
        print("1. 重启后端服务，查看详细日志")
        print("2. 使用全新的 code（重新扫码）测试")
        print("3. 检查后端日志中的 'GSUC response status' 和 'Response body'")
    else:
        print("✗ 发现配置问题，请修复后重试")
    
    print("=" * 60)


if __name__ == "__main__":
    diagnose_gsuc_config()
