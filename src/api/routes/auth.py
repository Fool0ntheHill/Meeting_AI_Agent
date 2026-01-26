# -*- coding: utf-8 -*-
"""Authentication endpoints."""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.config.loader import get_config
from src.database.models import User
from src.database.repositories import UserRepository
from src.providers.gsuc_auth import GSUCAuthProvider, GSUCAuthError
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class DevLoginRequest(BaseModel):
    """开发环境登录请求"""
    username: str


class GSUCLoginRequest(BaseModel):
    """GSUC 登录请求"""
    frontend_callback_url: str  # 前端回调地址


class GSUCLoginResponse(BaseModel):
    """GSUC 登录响应"""
    login_url: str  # GSUC 登录页面 URL
    state: str  # 状态参数 (用于防止 CSRF)


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    expires_in: int  # 秒
    username: Optional[str] = None  # 用户名 (GSUC 登录时返回)
    avatar: Optional[str] = None  # 头像 URL (GSUC 登录时返回)


# ============================================================================
# Helper Functions
# ============================================================================


def create_access_token(
    user_id: str,
    tenant_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT Access Token
    
    Args:
        user_id: 用户 ID
        tenant_id: 租户 ID
        expires_delta: 过期时间增量
        
    Returns:
        str: JWT Token
    """
    config = get_config()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(hours=config.jwt_expire_hours)
    
    payload = {
        "sub": user_id,  # Subject (用户 ID)
        "tenant_id": tenant_id,
        "exp": expire,  # Expiration time
        "iat": datetime.now(),  # Issued at
    }
    
    token = jwt.encode(
        payload,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )
    
    return token


# ============================================================================
# Endpoints - Development Login
# ============================================================================


@router.post("/dev/login", response_model=LoginResponse)
async def dev_login(
    request: DevLoginRequest,
    db: Session = Depends(get_db)
):
    """
    开发环境登录接口
    
    功能:
    1. 接受用户名
    2. 查找或创建用户记录
    3. 签发 JWT Token
    
    注意:
    - 仅用于开发环境
    - 生产环境应使用企业微信等第三方认证
    
    Args:
        request: 登录请求
        db: 数据库会话
        
    Returns:
        LoginResponse: 包含 JWT Token 的响应
    """
    config = get_config()
    
    # 生产环境禁用此接口
    if config.env == "production":
        raise HTTPException(
            status_code=403,
            detail="开发登录接口在生产环境不可用"
        )
    
    user_repo = UserRepository(db)
    
    # 查找或创建用户
    user = user_repo.get_by_username(request.username)
    
    if not user:
        # 创建新用户
        user_id = f"user_{request.username}"
        tenant_id = f"tenant_{request.username}"
        
        user = user_repo.create(
            user_id=user_id,
            username=request.username,
            tenant_id=tenant_id,
            is_active=True
        )
        
        logger.info(f"Created new user: {user_id}")
    else:
        logger.info(f"User login: {user.user_id}")
    
    # 签发 JWT Token
    expires_delta = timedelta(hours=config.jwt_expire_hours)
    access_token = create_access_token(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        expires_delta=expires_delta
    )
    
    return LoginResponse(
        access_token=access_token,
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        expires_in=config.jwt_expire_hours * 3600
    )


# ============================================================================
# Endpoints - GSUC OAuth2.0 Login
# ============================================================================


@router.post("/gsuc/login", response_model=GSUCLoginResponse)
async def gsuc_login(request: GSUCLoginRequest):
    """
    GSUC OAuth2.0 登录 - 第一步：生成登录 URL
    
    功能:
    1. 生成 GSUC 登录页面 URL
    2. 生成 state 参数防止 CSRF 攻击
    3. 前端将用户重定向到 GSUC 登录页面
    
    流程:
    1. 前端调用此接口，传入前端回调地址
    2. 后端生成 GSUC 登录 URL 和 state
    3. 前端将用户重定向到 GSUC 登录页面
    4. 用户扫码登录后，GSUC 重定向到后端回调地址（携带 code）
    5. 后端处理回调，获取用户信息，签发 JWT
    6. 后端重定向到前端回调地址，携带 JWT
    
    Args:
        request: 登录请求 (包含前端回调地址)
        
    Returns:
        GSUCLoginResponse: 包含 GSUC 登录 URL 和 state
        
    Raises:
        HTTPException: 403 如果 GSUC 未启用
    """
    config = get_config()
    
    # 检查 GSUC 是否启用
    if not config.gsuc or not config.gsuc.enabled:
        raise HTTPException(
            status_code=403,
            detail="GSUC 认证未启用"
        )
    
    # 生成随机 state (用于防止 CSRF)
    state = secrets.token_urlsafe(32)
    
    # 创建 GSUC 认证提供商
    provider = GSUCAuthProvider(
        appid=config.gsuc.appid,
        appsecret=config.gsuc.appsecret,
        encryption_key=config.gsuc.encryption_key,
        login_url=config.gsuc.login_url,
        userinfo_url=config.gsuc.userinfo_url,
        timeout=config.gsuc.timeout
    )
    
    # 生成 GSUC 登录 URL
    # 回调地址为后端的 /api/v1/auth/gsuc/callback
    # 并携带前端回调地址作为参数
    backend_callback = f"{config.gsuc.callback_url}?frontend_callback={request.frontend_callback_url}&state={state}"
    login_url = provider.get_login_url(backend_callback, state)
    
    logger.info(f"Generated GSUC login URL: state={state}")
    
    return GSUCLoginResponse(
        login_url=login_url,
        state=state
    )


@router.get("/gsuc/callback")
async def gsuc_callback(
    code: str = Query(..., description="GSUC 返回的授权 code"),
    state: str = Query(..., description="状态参数"),
    frontend_callback: str = Query(..., description="前端回调地址"),
    db: Session = Depends(get_db)
):
    """
    GSUC OAuth2.0 回调 - 第二步：处理 GSUC 回调
    
    功能:
    1. 接收 GSUC 返回的 code 和 state
    2. 验证 state 参数 (防止 CSRF)
    3. 使用 code 获取用户信息
    4. 查找或创建用户记录
    5. 签发 JWT Token
    6. 重定向到前端回调地址，携带 JWT
    
    Args:
        code: GSUC 返回的授权 code
        state: 状态参数
        frontend_callback: 前端回调地址
        db: 数据库会话
        
    Returns:
        RedirectResponse: 重定向到前端回调地址
        
    Raises:
        HTTPException: 400 如果参数无效
        HTTPException: 401 如果认证失败
    """
    config = get_config()
    
    # 检查 GSUC 是否启用
    if not config.gsuc or not config.gsuc.enabled:
        raise HTTPException(
            status_code=403,
            detail="GSUC 认证未启用"
        )
    
    # TODO: 验证 state 参数
    # 实际生产环境需要将 state 存储在 Redis 中，并在此处验证
    # 当前简化实现，仅检查 state 是否存在
    if not state:
        raise HTTPException(
            status_code=400,
            detail="缺少 state 参数"
        )
    
    # 创建 GSUC 认证提供商
    provider = GSUCAuthProvider(
        appid=config.gsuc.appid,
        appsecret=config.gsuc.appsecret,
        encryption_key=config.gsuc.encryption_key,
        login_url=config.gsuc.login_url,
        userinfo_url=config.gsuc.userinfo_url,
        timeout=config.gsuc.timeout
    )
    
    try:
        # 获取用户信息
        user_info = await provider.verify_and_get_user(code)
        
        logger.info(f"GSUC user info: uid={user_info['uid']}, account={user_info['account']}")
        
        # 查找或创建用户
        user_repo = UserRepository(db)
        
        # 使用 GSUC uid 作为用户 ID
        user_id = f"user_gsuc_{user_info['uid']}"
        tenant_id = f"tenant_gsuc_{user_info['uid']}"
        
        user = user_repo.get_by_id(user_id)
        
        if not user:
            # 创建新用户
            user = user_repo.create(
                user_id=user_id,
                username=user_info['account'],
                tenant_id=tenant_id,
                is_active=True
            )
            logger.info(f"Created new GSUC user: {user_id}")
        else:
            logger.info(f"GSUC user login: {user_id}")
        
        # 签发 JWT Token
        expires_delta = timedelta(hours=config.jwt_expire_hours)
        access_token = create_access_token(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            expires_delta=expires_delta
        )
        
        # 重定向到前端回调地址，携带 JWT 和用户信息
        from fastapi.responses import RedirectResponse
        from urllib.parse import urlencode
        
        params = {
            "access_token": access_token,
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "username": user_info['username'],
            "account": user_info['account'],
            "avatar": user_info.get('avatar', ''),
            "expires_in": str(config.jwt_expire_hours * 3600)
        }
        
        redirect_url = f"{frontend_callback}?{urlencode(params)}"
        
        logger.info(f"Redirecting to frontend: {frontend_callback}")
        return RedirectResponse(url=redirect_url)
        
    except GSUCAuthError as e:
        logger.error(f"GSUC auth failed: {e.message}")
        raise HTTPException(
            status_code=401,
            detail=f"GSUC 认证失败: {e.message}"
        )
    except Exception as e:
        logger.error(f"GSUC callback error: {e}")
        raise HTTPException(
            status_code=500,
            detail="GSUC 认证处理失败"
        )


# ============================================================================
# Endpoints - Token Refresh
# ============================================================================


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    user_id: str = Depends(lambda: None),  # TODO: 从当前 token 提取
    db: Session = Depends(get_db)
):
    """
    刷新 Token
    
    功能:
    1. 验证当前 Token
    2. 签发新的 Token
    
    注意:
    - Phase 2 实现
    - 需要从当前 Token 提取用户信息
    """
    raise HTTPException(
        status_code=501,
        detail="Token 刷新功能将在 Phase 2 实现"
    )


# ============================================================================
# Endpoints - GSUC Callback Compatibility (兼容路由)
# ============================================================================


@router.get("/callback")
async def gsuc_callback_compat(
    code: str = Query(..., description="GSUC 返回的授权 code"),
    appid: str = Query(None, description="GSUC 返回的 appid"),
    gsuc_auth_type: str = Query(None, description="认证类型"),
    state: str = Query("", description="状态参数"),
    db: Session = Depends(get_db)
):
    """
    GSUC OAuth2.0 回调 - 兼容路由
    
    兼容 GSUC 直接回调到 /api/v1/auth/callback 的情况
    
    功能:
    1. 接收 GSUC 返回的 code
    2. 使用 code 获取用户信息
    3. 查找或创建用户记录
    4. 签发 JWT Token
    5. 重定向到前端，携带 JWT
    
    Args:
        code: GSUC 返回的授权 code
        appid: GSUC 返回的 appid (可选)
        gsuc_auth_type: 认证类型 (可选)
        state: 状态参数 (可选)
        db: 数据库会话
        
    Returns:
        RedirectResponse: 重定向到前端
        
    Raises:
        HTTPException: 401 如果认证失败
        HTTPException: 403 如果 GSUC 未启用
    """
    config = get_config()
    
    # 检查 GSUC 是否启用
    if not config.gsuc or not config.gsuc.enabled:
        raise HTTPException(
            status_code=403,
            detail="GSUC 认证未启用"
        )
    
    logger.info(f"GSUC callback (compat): code={code[:20]}..., appid={appid}, auth_type={gsuc_auth_type}")
    
    # 创建 GSUC 认证提供商
    provider = GSUCAuthProvider(
        appid=config.gsuc.appid,
        appsecret=config.gsuc.appsecret,
        encryption_key=config.gsuc.encryption_key,
        login_url=config.gsuc.login_url,
        userinfo_url=config.gsuc.userinfo_url,
        timeout=config.gsuc.timeout
    )
    
    try:
        # 获取用户信息
        user_info = await provider.verify_and_get_user(code)
        
        logger.info(f"GSUC user info: uid={user_info['uid']}, account={user_info['account']}")
        
        # 查找或创建用户
        user_repo = UserRepository(db)
        user_id = f"user_gsuc_{user_info['uid']}"
        tenant_id = f"tenant_gsuc_{user_info['uid']}"
        
        user = user_repo.get_by_id(user_id)
        
        if not user:
            user = user_repo.create(
                user_id=user_id,
                username=user_info['account'],
                tenant_id=tenant_id,
                is_active=True
            )
            logger.info(f"Created new GSUC user: {user_id}")
        else:
            logger.info(f"GSUC user login: {user_id}")
        
        # 签发 JWT Token
        expires_delta = timedelta(hours=config.jwt_expire_hours)
        access_token = create_access_token(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            expires_delta=expires_delta
        )
        
        # 重定向到前端
        from fastapi.responses import RedirectResponse
        from urllib.parse import urlencode
        
        # 前端地址 (可以从环境变量或配置读取)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173/login")
        
        params = {
            "access_token": access_token,
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "username": user_info['username'],
            "account": user_info['account'],
            "avatar": user_info.get('avatar', ''),
            "expires_in": str(config.jwt_expire_hours * 3600)
        }
        
        redirect_url = f"{frontend_url}?{urlencode(params)}"
        
        logger.info(f"Redirecting to frontend: {frontend_url}")
        return RedirectResponse(url=redirect_url)
        
    except GSUCAuthError as e:
        logger.error(f"GSUC auth failed: {e.message}")
        # 重定向到前端错误页面
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173/login")
        error_url = f"{frontend_url}?error=auth_failed&message={e.message}"
        return RedirectResponse(url=error_url)
    except Exception as e:
        logger.error(f"GSUC callback error: {e}")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173/login")
        error_url = f"{frontend_url}?error=server_error"
        return RedirectResponse(url=error_url)

