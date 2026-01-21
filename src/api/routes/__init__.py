# -*- coding: utf-8 -*-
"""API routes package."""

from fastapi import APIRouter

from src.api.routes import artifacts, auth, corrections, folders, health, hotwords, prompt_templates, tasks, trash, upload

# 创建主路由器
api_router = APIRouter()

# 注册子路由
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(corrections.router, prefix="/tasks", tags=["corrections"])
api_router.include_router(artifacts.router, prefix="/tasks", tags=["artifacts"])
api_router.include_router(artifacts.standalone_router, prefix="/artifacts", tags=["artifacts"])  # 独立的 artifacts 路由
api_router.include_router(hotwords.router, prefix="/hotword-sets", tags=["hotwords"])
api_router.include_router(prompt_templates.router, prefix="/prompt-templates", tags=["prompt-templates"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(trash.router, tags=["trash"])

__all__ = ["api_router"]
