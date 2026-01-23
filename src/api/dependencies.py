# -*- coding: utf-8 -*-
"""FastAPI dependencies for dependency injection."""

from typing import Generator, Tuple

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.config.loader import get_config
from src.core.providers import LLMProvider
from src.database.session import get_session
from src.database.repositories import UserRepository
from src.providers.gemini_llm import GeminiLLM
from src.utils.logger import get_logger

logger = get_logger(__name__)

# OAuth2 Bearer Token Scheme
security = HTTPBearer()


# ============================================================================
# Database Dependencies
# ============================================================================


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话依赖
    
    使用方式:
        @router.get("/tasks")
        async def list_tasks(db: Session = Depends(get_db)):
            ...
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tuple[str, str]:
    """
    验证 JWT Token (开发环境使用)
    
    Args:
        credentials: HTTP Bearer Token
        db: 数据库会话
        
    Returns:
        Tuple[str, str]: (user_id, tenant_id)
        
    Raises:
        HTTPException: 401 如果 Token 无效或过期
    """
    config = get_config()
    
    try:
        # 解码 JWT Token
        payload = jwt.decode(
            credentials.credentials,
            config.jwt_secret_key,
            algorithms=[config.jwt_algorithm]
        )
        
        # 提取用户信息
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=401,
                detail="Token payload 缺少必需字段"
            )
        
        # 验证用户是否存在且活跃
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="用户不存在"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="用户已被停用"
            )
        
        # 更新最后登录时间
        # 注意：在 SQLite 环境下，这会导致 database locked 错误
        # 因为每次请求都会触发写操作，与 Worker 冲突
        # 临时禁用，迁移到 PostgreSQL 后可以重新启用
        # user_repo.update_last_login(user_id)
        
        logger.debug(f"JWT verified: user_id={user_id}, tenant_id={tenant_id}")
        return user_id, tenant_id
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="无效的 Token"
        )


async def verify_gsuc_session(
    token: str = Header(None, alias="Token"),
    db: Session = Depends(get_db)
) -> Tuple[str, str]:
    """
    验证 GSUC SESSIONID (生产环境使用)
    
    流程:
    1. 前端从 Cookie 中读取 SESSIONID
    2. 前端将 SESSIONID 放入 Token header 发送给后端
    3. 后端从 Token header 提取 SESSIONID
    4. 后端验证 SESSIONID (调用 GSUC API 或查询 Redis 缓存)
    5. 返回 user_id 和 tenant_id
    
    Args:
        token: Token header 中的 SESSIONID (前端从 Cookie 读取后发送)
        db: 数据库会话
        
    Returns:
        Tuple[str, str]: (user_id, tenant_id)
        
    Raises:
        HTTPException: 401 如果 Session 无效或过期
        
    注意:
        - SESSIONID 由 GSUC 服务器生成并设置到 Cookie
        - 前端需要从 Cookie 读取 SESSIONID 并放入 Token header
        - 不是 Authorization header，是 Token header
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="未登录：缺少 Token header (SESSIONID)"
        )
    
    # TODO: 实现 GSUC Session 验证
    # 方案 A: 调用 GSUC API 验证 Session
    # from src.providers.gsuc_session import GSUCSessionManager
    # session_manager = GSUCSessionManager()
    # user_info = await session_manager.verify_session(token)
    
    # 方案 B: 从 Redis 缓存中获取 Session 信息
    # user_info = get_session_from_redis(token)
    
    # 临时实现：直接从数据库查询
    # 生产环境需要实现真实的 GSUC Session 验证
    logger.warning("GSUC Session verification not implemented, using mock")
    
    # Mock implementation for development
    # 实际生产环境需要调用 GSUC API 或查询 Redis
    user_info = {
        "user_id": "user_gsuc_mock",
        "tenant_id": "tenant_gsuc_mock"
    }
    
    # 验证用户是否存在
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_info["user_id"])
    
    if not user:
        # 如果用户不存在，创建新用户
        user = user_repo.create(
            user_id=user_info["user_id"],
            username="gsuc_mock_user",
            tenant_id=user_info["tenant_id"],
            is_active=True
        )
        logger.info(f"Created new GSUC user: {user_info['user_id']}")
    
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="用户已被停用"
        )
    
    logger.debug(f"GSUC Session verified: user_id={user_info['user_id']}, tenant_id={user_info['tenant_id']}")
    return user_info["user_id"], user_info["tenant_id"]


async def get_current_user_id(
    auth_result: Tuple[str, str] = Depends(verify_jwt_token)
) -> str:
    """
    获取当前用户 ID
    
    Args:
        auth_result: JWT 验证结果 (user_id, tenant_id)
        
    Returns:
        str: 用户 ID
    """
    user_id, _ = auth_result
    return user_id


async def get_current_tenant_id(
    auth_result: Tuple[str, str] = Depends(verify_jwt_token)
) -> str:
    """
    获取当前租户 ID
    
    Args:
        auth_result: JWT 验证结果 (user_id, tenant_id)
        
    Returns:
        str: 租户 ID
    """
    _, tenant_id = auth_result
    return tenant_id


# ============================================================================
# Legacy Authentication Dependencies (Deprecated)
# ============================================================================


async def verify_api_key(authorization: str = Header(None)) -> str:
    """
    验证 API Key (已弃用，请使用 verify_jwt_token)
    
    Args:
        authorization: Authorization 头 (格式: "Bearer <api_key>")
        
    Returns:
        str: 用户 ID
        
    Raises:
        HTTPException: 401 如果认证失败
        HTTPException: 429 如果配额超限
        
    Deprecated:
        此方法已弃用，请使用 verify_jwt_token
    """
    logger.warning("verify_api_key is deprecated, please use verify_jwt_token")
    
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization 头")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的 Authorization 格式")
    
    api_key = authorization[7:]  # 移除 "Bearer " 前缀
    
    # TODO: 实现真实的 API Key 验证逻辑
    # 当前为简化实现,直接返回 api_key 作为 user_id
    # 生产环境需要:
    # 1. 查询数据库验证 API Key
    # 2. 检查配额是否超限
    # 3. 返回关联的 user_id
    
    if not api_key:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    
    # 简化实现: 使用 api_key 作为 user_id
    user_id = api_key
    
    logger.info(f"API Key verified: user_id={user_id}")
    return user_id


async def get_tenant_id(user_id: str = Depends(verify_api_key)) -> str:
    """
    获取租户 ID (已弃用，请使用 get_current_tenant_id)
    
    Args:
        user_id: 用户 ID (来自 verify_api_key)
        
    Returns:
        str: 租户 ID
        
    Deprecated:
        此方法已弃用，请使用 get_current_tenant_id
    """
    logger.warning("get_tenant_id is deprecated, please use get_current_tenant_id")
    
    # TODO: 实现真实的租户 ID 查询逻辑
    # 当前为简化实现,直接使用 user_id 作为 tenant_id
    # 生产环境需要查询数据库获取用户所属租户
    
    tenant_id = f"tenant_{user_id}"
    return tenant_id


# ============================================================================
# Optional Authentication Dependencies
# ============================================================================


async def optional_api_key(authorization: str = Header(None)) -> str | None:
    """
    可选的 API Key 验证
    
    用于不强制要求认证的端点(如健康检查)
    
    Returns:
        str | None: 用户 ID 或 None
    """
    if not authorization:
        return None
    
    try:
        return await verify_api_key(authorization)
    except HTTPException:
        return None


# ============================================================================
# Ownership Verification Dependencies
# ============================================================================


async def verify_task_ownership(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    验证任务所有权
    
    用于保护任务相关端点，防止 IDOR (Insecure Direct Object Reference) 攻击。
    验证任务存在且当前用户有权访问该任务。
    
    Args:
        task_id: 任务 ID (来自路径参数)
        user_id: 用户 ID (来自 JWT 认证)
        db: 数据库会话
        
    Returns:
        Task: 任务对象
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问此任务
        
    使用方式:
        @router.get("/{task_id}")
        async def get_task(task: Task = Depends(verify_task_ownership)):
            # task 已经过权限验证
            return task
    """
    from src.database.repositories import TaskRepository
    
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    
    if not task:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(
            status_code=404,
            detail="任务不存在"
        )
    
    # 验证所有权
    if task.user_id != user_id:
        logger.warning(
            f"Unauthorized access attempt: user {user_id} tried to access task {task_id} "
            f"owned by {task.user_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="无权访问此任务"
        )
    
    logger.debug(f"Task ownership verified: {task_id} for user {user_id}")
    return task


# ============================================================================
# LLM Provider Dependencies
# ============================================================================


def get_llm_provider() -> LLMProvider:
    """
    获取 LLM 提供商依赖
    
    使用方式:
        @router.post("/generate")
        async def generate(llm: LLMProvider = Depends(get_llm_provider)):
            result = await llm.generate(...)
    
    Returns:
        LLMProvider: LLM 提供商实例
        
    注意:
        当前实现返回 GeminiLLM，未来可以根据配置或请求参数
        动态选择不同的 LLM 提供商（如 OpenAI, Claude 等）
    """
    config = get_config()
    
    # TODO: 支持多 LLM 提供商
    # 可以根据配置或请求参数选择不同的提供商
    # 例如: config.default_llm_provider
    
    return GeminiLLM(config.gemini)
