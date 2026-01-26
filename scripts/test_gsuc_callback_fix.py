#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 GSUC 回调修复

验证兼容路由是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("GSUC 回调修复测试")
print("=" * 60)

# 1. 检查配置
print("\n1. 检查 GSUC 配置...")
try:
    from src.config.loader import get_config
    config = get_config()
    
    if config.gsuc and config.gsuc.enabled:
        print("✓ GSUC 配置已启用")
        print(f"  APP ID: {config.gsuc.appid}")
        print(f"  回调地址: {config.gsuc.callback_url}")
    else:
        print("✗ GSUC 配置未启用")
        print("  请检查 config/development.yaml")
        sys.exit(1)
except Exception as e:
    print(f"✗ 配置加载失败: {e}")
    sys.exit(1)

# 2. 检查路由
print("\n2. 检查路由...")
try:
    from src.api.routes.auth import router
    
    # 获取所有路由
    routes = [route.path for route in router.routes]
    
    if "/callback" in routes:
        print("✓ 兼容路由已添加: /api/v1/auth/callback")
    else:
        print("✗ 兼容路由未找到")
        print(f"  现有路由: {routes}")
        sys.exit(1)
    
    if "/gsuc/callback" in routes:
        print("✓ 标准路由存在: /api/v1/auth/gsuc/callback")
    else:
        print("⚠ 标准路由未找到")
        
except Exception as e:
    print(f"✗ 路由检查失败: {e}")
    sys.exit(1)

# 3. 检查加密算法
print("\n3. 检查加密算法...")
try:
    from src.providers.gsuc_auth import GSUCAuthProvider
    
    provider = GSUCAuthProvider(
        appid=config.gsuc.appid,
        appsecret=config.gsuc.appsecret,
        encryption_key=config.gsuc.encryption_key
    )
    
    # 测试加密
    test_code = "test_code_12345"
    access_token = provider._encrypt_access_token(test_code)
    
    if access_token:
        print("✓ 加密算法正常")
        print(f"  测试 Token (前50字符): {access_token[:50]}...")
    else:
        print("✗ 加密失败")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ 加密测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 测试说明
print("\n" + "=" * 60)
print("✓ 所有检查通过！")
print("=" * 60)
print("\n下一步:")
print("1. 重启后端服务:")
print("   uvicorn src.api.app:app --reload")
print()
print("2. 再次扫码登录")
print()
print("3. 应该会自动重定向到:")
print("   http://localhost:5173/login?access_token=xxx&user_id=xxx&...")
print()
print("4. 前端需要在登录页面读取 URL 参数:")
print("   const urlParams = new URLSearchParams(window.location.search);")
print("   const accessToken = urlParams.get('access_token');")
print("   localStorage.setItem('access_token', accessToken);")
print()
print("=" * 60)
