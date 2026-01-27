#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 GSUC 登录完整流程

步骤：
1. 调用 /api/v1/auth/gsuc/login 获取登录 URL
2. 打印登录 URL，让用户在浏览器中打开
3. 用户扫码后，GSUC 会回调到后端
4. 后端处理完成后，会重定向到前端
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests


def test_gsuc_login_flow():
    """测试 GSUC 登录流程"""
    
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("GSUC 登录流程测试")
    print("=" * 60)
    print()
    
    # 步骤 1: 获取登录 URL
    print("步骤 1: 获取 GSUC 登录 URL...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/gsuc/login",
            json={
                "frontend_callback_url": "http://localhost:5173/login"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        login_url = data["login_url"]
        state = data["state"]
        
        print(f"✓ 登录 URL 获取成功")
        print(f"  State: {state}")
        print()
        
    except Exception as e:
        print(f"✗ 获取登录 URL 失败: {e}")
        return
    
    # 步骤 2: 打印登录 URL
    print("步骤 2: 请在浏览器中打开以下 URL 进行扫码登录：")
    print()
    print(f"  {login_url}")
    print()
    print("=" * 60)
    print()
    print("扫码后，GSUC 会回调到后端：")
    print(f"  {base_url}/api/v1/auth/callback")
    print()
    print("后端处理完成后，会重定向到前端：")
    print(f"  http://localhost:5173/login?access_token=xxx&...")
    print()
    print("请查看后端日志，确认回调是否成功。")
    print()
    print("关键日志：")
    print("  [debug] Encryption key length: 32 bytes")
    print("  [debug] GSUC response status: 200")
    print("  [info] GSUC auth success: uid=xxx, account=xxx")
    print()
    print("如果看到 500 错误，请检查：")
    print("  1. encryption_key 是否与 GSUC 服务器配置一致")
    print("  2. 回调地址是否在 GSUC 白名单中")
    print("  3. 是否是浏览器预取导致 code 被提前消耗")
    print()
    print("=" * 60)


if __name__ == "__main__":
    test_gsuc_login_flow()
