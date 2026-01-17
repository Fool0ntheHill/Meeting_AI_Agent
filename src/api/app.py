# -*- coding: utf-8 -*-
"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware import ErrorHandlerMiddleware, LoggingMiddleware
from src.api.routes import api_router
from src.core.exceptions import MeetingAgentError
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        FastAPI: 配置好的应用实例
    """
    app = FastAPI(
        title="Meeting Minutes Agent API",
        description="会议纪要 Agent - 自动生成会议纪要的 AI 服务",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 自定义中间件
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)

    # 注册路由
    app.include_router(api_router, prefix="/api/v1")

    # 全局异常处理 - 业务异常
    @app.exception_handler(MeetingAgentError)
    async def meeting_agent_error_handler(request: Request, exc: MeetingAgentError):
        """处理自定义业务异常"""
        logger.error(
            f"Business error: {exc.message}",
            extra={
                "error_type": exc.__class__.__name__,
                "provider": exc.provider,
                "details": exc.details,
            },
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "provider": exc.provider,
                "details": exc.details,
            },
        )

    # 全局异常处理 - 未预期异常
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
            },
        )

    @app.on_event("startup")
    async def startup_event():
        """应用启动事件"""
        logger.info("Meeting Minutes Agent API starting up...")
        
        # TODO: 初始化数据库连接池
        # TODO: 初始化 Redis 连接
        # TODO: 初始化消息队列
        
        logger.info("Meeting Minutes Agent API started successfully")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭事件"""
        logger.info("Meeting Minutes Agent API shutting down...")
        
        # TODO: 关闭数据库连接
        # TODO: 关闭 Redis 连接
        # TODO: 关闭消息队列连接
        
        logger.info("Meeting Minutes Agent API shut down successfully")

    logger.info("FastAPI application created successfully")
    return app
