#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GSUC 单点登录 (SSO) - 安全加固版本

相比 main.py 的改进:
1. ✅ 添加 State 验证 (防止 CSRF)
2. ✅ 使用 JWT Token (替代简单 SessionID)
3. ✅ 密钥使用环境变量
4. ✅ 添加速率限制
5. ✅ 改进错误处理 (隐藏详细信息)
6. ✅ 强制 HTTPS (生产环境)
7. ✅ 正确的 HTTP 状态码

使用方式:
    # 1. 设置环境变量
    export GSUC_APP_SECRET="G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
    export JWT_SECRET_KEY="your-jwt-secret-key-here"
    export ENVIRONMENT="development"  # 或 production
    
    # 2. 启动服务
    uvicorn main_secure:app --host 0.0.0.0 --port 8000 --reload
"""

import base64
import os
import random
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

import httpx
from Crypto.Cipher import AES
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ============================================================================
# 配置参数 (从环境变量读取)
# ============================================================================

# 环境
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# GSUC 配置
APP_ID = os.getenv("GSUC_APP_ID", "app_meeting_agent")
APP_SECRET = os.getenv("GSUC_APP_SECRET")
GSUC_URL = os.getenv("GSUC_URL", "https://gsuc.gamesci.com.cn/sso/userinfo")

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# 前端配置
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# 验证必需的环境变量
if not APP_SECRET:
    raise ValueError("GSUC_APP_SECRET environment variable is required")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required")

# 生产环境强制 HTTPS
if ENVIRONMENT == "production":
    if not FRONTEND_URL.startswith("https://"):
        raise ValueError("Production environment must use HTTPS for FRONTEND_URL")

# ============================================================================
# 创建 FastAPI 应用
# ============================================================================

app = FastAPI(
    title="GSUC SSO Service (Secure)",
    description="GSUC 单点登录回调服务 - 安全加固版本",
    version="2.0.0"
)

# 添加速率限制
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# State 存储 (生产环境应使用 Redis)
# 这里使用内存存储作为演示
state_store = {}

# ============================================================================
# 加密函数 (与 main.py 相同)
# ============================================================================

def encrypt(text: str, key: str) -> Optional[str]:
    """
    AES-256-CBC 加密函数 (Python 2 -> Python 3)
    
    Args:
        text: 待加密的文本
        key: Base64 编码的 32 字节密钥
        
    Returns:
        str: Base64 编码的加密结果，失败返回 None
    """
    try:
        key_bytes = base64.b64decode(key)
        if len(key_bytes) != 32:
            return None
    except Exception:
        return None
    
    random_prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    text_random = random_prefix + text
    
    add_num = 32 - (len(text_random) % 32)
    if add_num == 0:
        add_num = 32
    
    text_all = text_random + chr(add_num) * add_num
    
    iv = key_bytes[:16]
    cryptor = AES.new(key_bytes, AES.MODE_CBC, iv)
    
    try:
        ciphertext = cryptor.encrypt(text_all.encode('utf-8'))
        return base64.b64encode(ciphertext).decode('utf-8')
    except Exception:
        return None


# ============================================================================
# JWT Token 函数
# ============================================================================

def create_jwt_token(user_id: str, uid: int, account: str, username: str) -> str:
    """
    创建 JWT Token
    
    Args:
        user_id: 用户 ID
        uid: GSUC UID
        account: 账号
        username: 用户名
        
    Returns:
        str: JWT Token
    """
    payload = {
        "sub": user_id,
        "uid": uid,
        "account": account,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    验证 JWT Token
    
    Args:
        token: JWT Token
        
    Returns:
        dict: Token payload，失败返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ============================================================================
# State 管理函数
# ============================================================================

def create_state() -> str:
    """
    创建 State (防止 CSRF)
    
    Returns:
        str: 随机 state
    """
    state = secrets.token_urlsafe(32)
    # 存储 state (5 分钟过期)
    # 生产环境应使用 Redis: r.setex(f"gsuc_state:{state}", 300, "1")
    state_store[state] = datetime.utcnow() + timedelta(minutes=5)
    return state


def verify_state(state: str) -> bool:
    """
    验证 State
    
    Args:
        state: State 参数
        
    Returns:
        bool: 是否有效
    """
    # 生产环境应使用 Redis: return r.exists(f"gsuc_state:{state}")
    if state not in state_store:
        return False
    
    # 检查是否过期
    if datetime.utcnow() > state_store[state]:
        del state_store[state]
        return False
    
    # 使用后删除 (一次性)
    del state_store[state]
    return True


# ============================================================================
# API 路由
# ============================================================================

@app.get("/")
async def root():
    """根路径 - 服务状态"""
    return {
        "service": "GSUC SSO Service (Secure)",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "security_features": [
            "State validation (CSRF protection)",
            "JWT Token",
            "Rate limiting",
            "Environment variables",
            "HTTPS enforcement (production)"
        ]
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "environment": ENVIRONMENT}


@app.get("/api/v1/auth/login")
@limiter.limit("10/minute")  # 限制每分钟 10 次
async def get_login_url(request: Request):
    """
    获取 GSUC 登录 URL
    
    Returns:
        dict: 包含 login_url 和 state
    """
    # 生成 state
    state = create_state()
    
    # 构建 GSUC 登录 URL
    callback_url = f"http://localhost:8000/api/v1/auth/callback?state={state}"
    login_url = f"https://gsuc.gamesci.com.cn/sso/login?appid={APP_ID}&redirect_uri={callback_url}"
    
    return {
        "login_url": login_url,
        "state": state
    }


@app.get("/api/v1/auth/callback")
@limiter.limit("5/minute")  # 限制每分钟 5 次
async def gsuc_callback(
    request: Request,
    code: str = Query(..., description="GSUC 返回的授权 code"),
    state: str = Query(..., description="State 参数 (防止 CSRF)")
):
    """
    GSUC OAuth2.0 回调接口 (安全加固版本)
    
    改进:
    1. ✅ 验证 state 参数
    2. ✅ 使用 JWT Token
    3. ✅ 正确的 HTTP 状态码
    4. ✅ 隐藏详细错误信息 (生产环境)
    5. ✅ 速率限制
    
    Args:
        code: GSUC 返回的授权 code
        state: State 参数
        
    Returns:
        RedirectResponse: 重定向到前端
    """
    # 步骤 1: 验证 state (防止 CSRF)
    if not verify_state(state):
        raise HTTPException(
            status_code=400,  # Bad Request
            detail="Invalid or expired state parameter"
        )
    
    # 步骤 2: 生成 access_token
    text_to_encrypt = code + APP_ID + APP_SECRET
    access_token = encrypt(text_to_encrypt, APP_SECRET)
    
    if not access_token:
        # 加密失败 (服务器配置问题)
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail="Encryption configuration error"
        )
    
    # 步骤 3: 请求 GSUC 用户信息 API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                GSUC_URL,
                params={
                    "code": code,
                    "access_token": access_token
                }
            )
            response.raise_for_status()
            data = response.json()
            
    except httpx.HTTPError as e:
        # GSUC API 请求失败 (上游服务错误)
        error_detail = "GSUC service unavailable" if ENVIRONMENT == "production" else f"GSUC API error: {str(e)}"
        raise HTTPException(
            status_code=502,  # Bad Gateway
            detail=error_detail
        )
    
    # 步骤 4: 验证返回结果
    rc = data.get("rc")
    
    if rc != 0:
        # GSUC 认证失败 (code 无效/过期)
        error_msg = data.get("msg", "Unknown error")
        error_detail = "Authentication failed" if ENVIRONMENT == "production" else f"GSUC auth failed: {error_msg}"
        raise HTTPException(
            status_code=401,  # Unauthorized
            detail=error_detail
        )
    
    # 步骤 5: 提取用户信息
    uid = data.get("uid")
    account = data.get("account")
    username = data.get("username", account)
    
    if not uid or not account:
        # GSUC 返回数据异常
        raise HTTPException(
            status_code=502,  # Bad Gateway
            detail="Invalid response from GSUC"
        )
    
    # 步骤 6: 生成 JWT Token
    user_id = f"user_gsuc_{uid}"
    token = create_jwt_token(user_id, uid, account, username)
    
    # 步骤 7: 重定向到前端
    redirect_url = f"{FRONTEND_URL}?token={token}"
    
    # 记录成功登录 (审计日志)
    print(f"✓ Login success: uid={uid}, account={account}, ip={request.client.host}")
    
    return RedirectResponse(url=redirect_url)


@app.get("/api/v1/auth/verify")
async def verify_token(token: str = Query(..., description="JWT Token")):
    """
    验证 JWT Token
    
    Args:
        token: JWT Token
        
    Returns:
        dict: Token payload
    """
    payload = verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=401,  # Unauthorized
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "uid": payload.get("uid"),
        "account": payload.get("account"),
        "username": payload.get("username"),
        "expires_at": payload.get("exp")
    }


# ============================================================================
# 测试端点 (仅开发环境)
# ============================================================================

if ENVIRONMENT == "development":
    @app.get("/api/v1/auth/test-encrypt")
    async def test_encrypt(
        text: str = Query(..., description="待加密的文本")
    ):
        """测试加密功能 (仅开发环境)"""
        result = encrypt(text, APP_SECRET)
        
        if result:
            return {
                "success": True,
                "input_text": text,
                "encrypted": result
            }
        else:
            return {
                "success": False,
                "error": "加密失败"
            }


# ============================================================================
# 启动说明
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("GSUC SSO 服务启动 (安全加固版本)")
    print("=" * 60)
    print(f"环境: {ENVIRONMENT}")
    print(f"APP_ID: {APP_ID}")
    print(f"GSUC_URL: {GSUC_URL}")
    print(f"FRONTEND_URL: {FRONTEND_URL}")
    print()
    print("安全特性:")
    print("  ✅ State 验证 (防止 CSRF)")
    print("  ✅ JWT Token (有签名、过期时间)")
    print("  ✅ 速率限制 (防止暴力攻击)")
    print("  ✅ 环境变量 (密钥不硬编码)")
    print("  ✅ HTTPS 强制 (生产环境)")
    print("  ✅ 正确的 HTTP 状态码")
    print()
    print("启动命令:")
    print("  uvicorn main_secure:app --host 0.0.0.0 --port 8000 --reload")
    print("=" * 60)
    
    uvicorn.run(
        "main_secure:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
