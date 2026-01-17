# -*- coding: utf-8 -*-
"""Main entry point for the Meeting Minutes Agent API."""

import uvicorn

from src.api.app import create_app
from src.database.session import init_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 创建 FastAPI 应用
app = create_app()


if __name__ == "__main__":
    # 初始化数据库
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发环境启用热重载
        log_level="info",
    )
