#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 GSUC 回调是否包含 account 字段

验证:
1. 回调 URL 包含 account 参数
2. account 值为英文账号 (如 lorenzolin)
3. username 值为中文名 (如 林晋辉)
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.app import app
from src.database.models import Base, User


async def test_gsuc_callback_account_field():
    """测试 GSUC 回调是否包含 account 字段"""
    
    # 创建测试数据库
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    
    # 覆盖依赖
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    from src.api.dependencies import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    # 创建测试客户端
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    
    # Mock GSUC 认证提供商
    mock_user_info = {
        "uid": 1231,
        "account": "lorenzolin",
        "username": "林晋辉",
        "avatar": "https://example.com/avatar.jpg",
        "thumb_avatar": "https://example.com/thumb.jpg"
    }
    
    with patch("src.api.routes.auth.GSUCAuthProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.verify_and_get_user = AsyncMock(return_value=mock_user_info)
        
        # 测试兼容路由 /api/v1/auth/callback
        print("\n" + "="*60)
        print("测试 GSUC 回调 - 兼容路由")
        print("="*60)
        
        response = await client.get(
            "/api/v1/auth/callback",
            params={
                "code": "test_code_123",
                "appid": "app_meeting_agent",
                "gsuc_auth_type": "wecom",
                "state": ""
            },
            follow_redirects=False
        )
        
        await client.aclose()
        
        print(f"\n状态码: {response.status_code}")
        assert response.status_code == 307, f"期望 307，实际 {response.status_code}"
        
        # 解析重定向 URL
        redirect_url = response.headers.get("location")
        print(f"重定向 URL: {redirect_url}")
        
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        
        print("\n回调参数:")
        for key, value in params.items():
            print(f"  {key}: {value[0]}")
        
        # 验证必需字段
        print("\n验证字段:")
        
        assert "access_token" in params, "❌ 缺少 access_token"
        print("  ✅ access_token 存在")
        
        assert "user_id" in params, "❌ 缺少 user_id"
        assert params["user_id"][0] == "user_gsuc_1231", f"❌ user_id 错误: {params['user_id'][0]}"
        print(f"  ✅ user_id: {params['user_id'][0]}")
        
        assert "tenant_id" in params, "❌ 缺少 tenant_id"
        assert params["tenant_id"][0] == "tenant_gsuc_1231", f"❌ tenant_id 错误: {params['tenant_id'][0]}"
        print(f"  ✅ tenant_id: {params['tenant_id'][0]}")
        
        assert "username" in params, "❌ 缺少 username"
        assert params["username"][0] == "林晋辉", f"❌ username 错误: {params['username'][0]}"
        print(f"  ✅ username: {params['username'][0]} (中文名)")
        
        # 关键验证: account 字段
        assert "account" in params, "❌ 缺少 account 字段"
        assert params["account"][0] == "lorenzolin", f"❌ account 错误: {params['account'][0]}"
        print(f"  ✅ account: {params['account'][0]} (英文账号)")
        
        assert "avatar" in params, "❌ 缺少 avatar"
        print(f"  ✅ avatar: {params['avatar'][0]}")
        
        assert "expires_in" in params, "❌ 缺少 expires_in"
        print(f"  ✅ expires_in: {params['expires_in'][0]}")
        
        print("\n" + "="*60)
        print("✅ 所有验证通过！")
        print("="*60)
        
        # 验证数据库中的用户
        db = TestingSessionLocal()
        user = db.query(User).filter(User.user_id == "user_gsuc_1231").first()
        
        print("\n数据库中的用户:")
        print(f"  user_id: {user.user_id}")
        print(f"  username: {user.username} (存储的是 account)")
        print(f"  tenant_id: {user.tenant_id}")
        
        db.close()
        
        print("\n前端使用建议:")
        print("  - 显示用户名: 使用 username 参数 (林晋辉)")
        print("  - 显示 ID: 使用 account 参数 (lorenzolin)")
        print("  - 用户标识: 使用 user_id 参数 (user_gsuc_1231)")


if __name__ == "__main__":
    import asyncio
    
    try:
        asyncio.run(test_gsuc_callback_account_field())
        print("\n✅ 测试完成")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
