# -*- coding: utf-8 -*-
"""FastAPI middleware for request/response processing."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        记录请求和响应信息
        
        记录内容:
        - 请求方法和路径
        - 请求耗时
        - 响应状态码
        - 客户端 IP
        """
        start_time = time.time()
        
        # 获取客户端 IP
        client_ip = request.client.host if request.client else "unknown"
        
        # 记录请求
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
            },
        )
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        duration = time.time() - start_time
        
        # 记录响应
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
                "client_ip": client_ip,
            },
        )
        
        # 添加响应头
        response.headers["X-Process-Time"] = str(duration)
        
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        捕获并处理未预期的异常
        
        将异常转换为标准的 JSON 错误响应
        """
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                },
                exc_info=True,
            )
            
            # 返回标准错误响应
            from fastapi.responses import JSONResponse
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "服务器内部错误",
                    "details": {"error": str(e)},
                },
            )
