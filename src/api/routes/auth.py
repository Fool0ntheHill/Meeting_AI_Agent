# -*- coding: utf-8 -*-
"""Authentication endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.config.loader import get_config
from src.database.models import User
from src.database.repositories import UserRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class DevLoginRequest(BaseModel):
    """开发环境登录请求"""
    username: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    expires_in: int  # 秒


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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=config.jwt_expire_hours)
    
    payload = {
        "sub": user_id,  # Subject (用户 ID)
        "tenant_id": tenant_id,
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
    }
    
    token = jwt.encode(
        payload,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )
    
    return token


# ============================================================================
# Endpoints
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
