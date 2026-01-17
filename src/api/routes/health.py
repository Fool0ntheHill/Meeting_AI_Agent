# -*- coding: utf-8 -*-
"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas import HealthCheckResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    健康检查端点
    
    检查项:
    - API 服务状态
    - 数据库连接
    - 版本信息
    
    Returns:
        HealthCheckResponse: 健康状态信息
    """
    dependencies = {}
    
    # 检查数据库连接
    try:
        # 执行简单查询测试连接
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        dependencies["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        dependencies["database"] = "unhealthy"
    
    # TODO: 添加其他依赖检查
    # - Redis 连接
    # - 外部 API 可用性
    
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(),
        dependencies=dependencies,
    )


@router.get("/")
async def root():
    """
    根端点
    
    Returns:
        dict: 欢迎信息
    """
    return {
        "message": "Meeting Minutes Agent API",
        "version": "1.0.0",
        "docs": "/docs",
    }
