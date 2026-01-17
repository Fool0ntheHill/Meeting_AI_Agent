"""
提示词模板管理 API 路由

实现需求:
- 需求 46: 提示词模板管理
- 需求 21: API 层实现 - 提示词模板管理

功能:
- GET /api/v1/prompt-templates - 列出所有可用模板
- GET /api/v1/prompt-templates/{template_id} - 获取模板详情
- POST /api/v1/prompt-templates - 创建私有模板
- PUT /api/v1/prompt-templates/{template_id} - 更新私有模板
- DELETE /api/v1/prompt-templates/{template_id} - 删除私有模板
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from src.api.schemas import (
    ListPromptTemplatesResponse,
    PromptTemplateDetailResponse,
    CreatePromptTemplateRequest,
    CreatePromptTemplateResponse,
    UpdatePromptTemplateRequest,
    UpdatePromptTemplateResponse,
    DeletePromptTemplateResponse,
)
from src.core.models import PromptTemplate
from src.api.dependencies import get_db
from src.database.repositories import PromptTemplateRepository
from src.utils.logger import get_logger
import uuid

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================


def _record_to_model(record) -> PromptTemplate:
    """将数据库记录转换为 PromptTemplate 模型"""
    return PromptTemplate(
        template_id=record.template_id,
        title=record.title,
        description=record.description,
        prompt_body=record.prompt_body,
        artifact_type=record.artifact_type,
        supported_languages=record.get_supported_languages_list(),
        parameter_schema=record.get_parameter_schema_dict(),
        is_system=record.is_system,
        scope=record.scope,
        scope_id=record.scope_id,
        created_at=record.created_at,
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("", response_model=ListPromptTemplatesResponse)
def list_prompt_templates(
    scope: Optional[str] = Query(None, description="作用域过滤 (global/private)"),
    artifact_type: Optional[str] = Query(None, description="内容类型过滤"),
    user_id: Optional[str] = Query(None, description="用户 ID (用于查询私有模板)"),
    db: Session = Depends(get_db),
):
    """
    列出所有可用的提示词模板
    
    - 支持按作用域过滤 (global/private)
    - 支持按内容类型过滤
    - 全局模板对所有用户可见
    - 私有模板只对创建者可见
    """
    logger.info(f"Listing prompt templates: scope={scope}, artifact_type={artifact_type}, user_id={user_id}")
    
    repo = PromptTemplateRepository(db)
    
    # 获取全局模板
    templates = []
    if scope is None or scope == "global":
        global_templates = repo.get_all(scope="global")
        templates.extend(global_templates)
    
    # 获取私有模板 (如果提供了 user_id)
    if user_id and (scope is None or scope == "private"):
        private_templates = repo.get_all(scope="private", scope_id=user_id)
        templates.extend(private_templates)
    
    # 按类型过滤
    if artifact_type:
        templates = [t for t in templates if t.artifact_type == artifact_type]
    
    # 转换为模型
    template_models = [_record_to_model(t) for t in templates]
    
    logger.info(f"Found {len(template_models)} templates")
    return ListPromptTemplatesResponse(templates=template_models)


@router.get("/{template_id}", response_model=PromptTemplateDetailResponse)
def get_prompt_template(
    template_id: str,
    user_id: Optional[str] = Query(None, description="用户 ID (用于验证私有模板权限)"),
    db: Session = Depends(get_db),
):
    """
    获取提示词模板详情
    
    - 全局模板对所有用户可见
    - 私有模板只对创建者可见
    """
    logger.info(f"Getting prompt template: {template_id}")
    
    repo = PromptTemplateRepository(db)
    template = repo.get_by_id(template_id)
    
    if not template:
        logger.warning(f"Template not found: {template_id}")
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    
    # 权限检查: 私有模板只能由创建者访问
    if template.scope == "private" and template.scope_id != user_id:
        logger.warning(f"Access denied: user {user_id} cannot access private template {template_id}")
        raise HTTPException(status_code=403, detail="无权访问此模板")
    
    template_model = _record_to_model(template)
    return PromptTemplateDetailResponse(template=template_model)


@router.post("", response_model=CreatePromptTemplateResponse, status_code=201)
def create_prompt_template(
    request: CreatePromptTemplateRequest,
    user_id: str = Query(..., description="用户 ID (创建者)"),
    db: Session = Depends(get_db),
):
    """
    创建私有提示词模板
    
    - 只能创建私有模板 (scope=private)
    - 模板 ID 自动生成
    - 绑定到创建者的 user_id
    """
    logger.info(f"Creating private prompt template for user {user_id}: {request.title}")
    
    # 生成模板 ID
    template_id = f"tpl_{uuid.uuid4().hex[:12]}"
    
    # 创建模板
    repo = PromptTemplateRepository(db)
    repo.create(
        template_id=template_id,
        title=request.title,
        description=request.description,
        prompt_body=request.prompt_body,
        artifact_type=request.artifact_type,
        supported_languages=request.supported_languages,
        parameter_schema=request.parameter_schema,
        is_system=False,  # 用户创建的模板不是系统模板
        scope="private",
        scope_id=user_id,
    )
    
    logger.info(f"Prompt template created: {template_id}")
    return CreatePromptTemplateResponse(
        success=True,
        template_id=template_id,
        message="提示词模板已创建",
    )


@router.put("/{template_id}", response_model=UpdatePromptTemplateResponse)
def update_prompt_template(
    template_id: str,
    request: UpdatePromptTemplateRequest,
    user_id: str = Query(..., description="用户 ID (用于验证权限)"),
    db: Session = Depends(get_db),
):
    """
    更新私有提示词模板
    
    - 只能更新自己创建的私有模板
    - 不能更新全局模板
    """
    logger.info(f"Updating prompt template: {template_id} by user {user_id}")
    
    repo = PromptTemplateRepository(db)
    template = repo.get_by_id(template_id)
    
    if not template:
        logger.warning(f"Template not found: {template_id}")
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    
    # 权限检查: 只能更新自己的私有模板
    if template.scope != "private" or template.scope_id != user_id:
        logger.warning(f"Access denied: user {user_id} cannot update template {template_id}")
        raise HTTPException(status_code=403, detail="无权修改此模板")
    
    # 更新模板
    repo.update(
        template_id=template_id,
        title=request.title,
        description=request.description,
        prompt_body=request.prompt_body,
        supported_languages=request.supported_languages,
        parameter_schema=request.parameter_schema,
    )
    
    logger.info(f"Prompt template updated: {template_id}")
    return UpdatePromptTemplateResponse(
        success=True,
        message="提示词模板已更新",
    )


@router.delete("/{template_id}", response_model=DeletePromptTemplateResponse)
def delete_prompt_template(
    template_id: str,
    user_id: str = Query(..., description="用户 ID (用于验证权限)"),
    db: Session = Depends(get_db),
):
    """
    删除私有提示词模板
    
    - 只能删除自己创建的私有模板
    - 不能删除全局模板
    """
    logger.info(f"Deleting prompt template: {template_id} by user {user_id}")
    
    repo = PromptTemplateRepository(db)
    template = repo.get_by_id(template_id)
    
    if not template:
        logger.warning(f"Template not found: {template_id}")
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    
    # 权限检查: 只能删除自己的私有模板
    if template.scope != "private" or template.scope_id != user_id:
        logger.warning(f"Access denied: user {user_id} cannot delete template {template_id}")
        raise HTTPException(status_code=403, detail="无权删除此模板")
    
    # 删除模板
    repo.delete(template_id)
    
    logger.info(f"Prompt template deleted: {template_id}")
    return DeletePromptTemplateResponse(
        success=True,
        message="提示词模板已删除",
    )
