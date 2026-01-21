"""
衍生内容管理 API 路由

实现需求:
- 需求 48: 多类型生成内容与版本管理
- Task 22: API 层实现 - 衍生内容管理

功能:
- GET /api/v1/tasks/{task_id}/artifacts - 列出所有衍生内容(按类型分组)
- GET /api/v1/tasks/{task_id}/artifacts/{type}/versions - 列出特定类型的所有版本
- GET /api/v1/tasks/{task_id}/artifacts/{artifact_id} - 获取特定版本详情
- POST /api/v1/tasks/{task_id}/artifacts/{type}/generate - 生成新版本
"""

from typing import Dict, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid

from src.api.dependencies import get_db, get_current_user_id, get_llm_provider, verify_task_ownership
from src.database.models import Task
from src.api.schemas import (
    ListArtifactsResponse,
    ArtifactInfo,
    ListArtifactVersionsResponse,
    ArtifactDetailResponse,
    GenerateArtifactRequest,
    GenerateArtifactResponse,
)
from src.core.models import TaskState, GeneratedArtifact, PromptInstance
from src.core.providers import LLMProvider
from src.database.repositories import (
    TaskRepository,
    ArtifactRepository,
    TranscriptRepository,
    SpeakerMappingRepository,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
standalone_router = APIRouter()  # 独立的 artifacts 路由，不需要 task_id 前缀


# ============================================================================
# Helper Functions
# ============================================================================


def _record_to_artifact_info(record) -> ArtifactInfo:
    """将数据库记录转换为 ArtifactInfo"""
    return ArtifactInfo(
        artifact_id=record.artifact_id,
        task_id=record.task_id,
        artifact_type=record.artifact_type,
        version=record.version,
        prompt_instance=PromptInstance(**record.get_prompt_instance_dict()),
        created_at=record.created_at,
        created_by=record.created_by,
    )


def _group_artifacts_by_type(artifacts: List) -> Dict[str, List[ArtifactInfo]]:
    """按类型分组衍生内容"""
    grouped = {}
    for artifact in artifacts:
        artifact_type = artifact.artifact_type
        if artifact_type not in grouped:
            grouped[artifact_type] = []
        grouped[artifact_type].append(_record_to_artifact_info(artifact))
    return grouped


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/{task_id}/artifacts", response_model=ListArtifactsResponse)
async def list_artifacts(
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    列出任务的所有衍生内容(按类型分组)
    
    返回所有类型的衍生内容,每个类型包含所有版本。
    按类型分组,每个类型内按版本降序排列。
    
    Args:
        task: 已验证的任务对象 (来自依赖注入)
        db: 数据库会话
        
    Returns:
        ListArtifactsResponse: 分组的衍生内容列表
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问
    """
    logger.info(f"Listing artifacts for task {task.task_id}")
    
    # 获取所有衍生内容
    artifact_repo = ArtifactRepository(db)
    artifacts = artifact_repo.get_by_task_id(task.task_id)
    
    # 按类型分组
    grouped = _group_artifacts_by_type(artifacts)
    
    logger.info(f"Found {len(artifacts)} artifacts in {len(grouped)} types")
    
    return ListArtifactsResponse(
        task_id=task.task_id,
        artifacts_by_type=grouped,
        total_count=len(artifacts),
    )


@router.get(
    "/{task_id}/artifacts/{artifact_type}/versions",
    response_model=ListArtifactVersionsResponse,
)
async def list_artifact_versions(
    artifact_type: str,
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    列出特定类型的所有版本
    
    返回指定类型的所有版本,按版本号降序排列(最新版本在前)。
    
    Args:
        artifact_type: 衍生内容类型
        task: 已验证的任务对象 (来自依赖注入)
        db: 数据库会话
        
    Returns:
        ListArtifactVersionsResponse: 版本列表
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问
    """
    logger.info(f"Listing versions for task {task.task_id}, type {artifact_type}")
    
    # 获取指定类型的所有版本
    artifact_repo = ArtifactRepository(db)
    artifacts = artifact_repo.get_by_task_and_type(task.task_id, artifact_type)
    
    versions = [_record_to_artifact_info(a) for a in artifacts]
    
    logger.info(f"Found {len(versions)} versions for type {artifact_type}")
    
    return ListArtifactVersionsResponse(
        task_id=task.task_id,
        artifact_type=artifact_type,
        versions=versions,
        total_count=len(versions),
    )


@router.get("/{task_id}/artifacts/{artifact_id}", response_model=ArtifactDetailResponse)
async def get_artifact_detail(
    artifact_id: str,
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    获取特定版本的详情
    
    返回完整的衍生内容,包括生成的内容、使用的提示词实例等。
    
    Args:
        artifact_id: 衍生内容 ID
        task: 已验证的任务对象 (来自依赖注入)
        db: 数据库会话
        
    Returns:
        ArtifactDetailResponse: 衍生内容详情
        
    Raises:
        HTTPException: 404 如果任务或衍生内容不存在
        HTTPException: 403 如果无权访问
    """
    logger.info(f"Getting artifact detail: {artifact_id} for task {task.task_id}")
    
    # 获取衍生内容
    artifact_repo = ArtifactRepository(db)
    artifact = artifact_repo.get_by_id(artifact_id)
    
    if not artifact:
        raise HTTPException(status_code=404, detail="衍生内容不存在")
    
    # 验证衍生内容属于该任务
    if artifact.task_id != task.task_id:
        raise HTTPException(status_code=404, detail="衍生内容不属于该任务")
    
    # 转换为 GeneratedArtifact 模型
    artifact_model = artifact_repo.to_generated_artifact(artifact)
    
    logger.info(f"Artifact detail retrieved: {artifact_id}")
    
    return ArtifactDetailResponse(artifact=artifact_model)


# ============================================================================
# Standalone Artifact Routes (without task_id in path)
# ============================================================================


@standalone_router.get("/{artifact_id}")
async def get_artifact_by_id(
    artifact_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    通过 artifact_id 直接获取衍生内容详情
    
    这是一个独立的路由，不需要 task_id。
    会验证 artifact 所属的 task 是否属于当前用户。
    
    Args:
        artifact_id: 衍生内容 ID
        user_id: 当前用户 ID (来自依赖注入)
        db: 数据库会话
        
    Returns:
        Dict: 衍生内容详情（content 字段已解析为字典）
        
    Raises:
        HTTPException: 404 如果衍生内容不存在
        HTTPException: 403 如果无权访问
    """
    logger.info(f"Getting artifact by ID: {artifact_id} for user {user_id}")
    
    # 获取衍生内容
    artifact_repo = ArtifactRepository(db)
    artifact = artifact_repo.get_by_id(artifact_id)
    
    if not artifact:
        raise HTTPException(status_code=404, detail="衍生内容不存在")
    
    # 验证所属任务的所有权
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(artifact.task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="关联的任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此衍生内容")
    
    # 转换为 GeneratedArtifact 模型
    artifact_model = artifact_repo.to_generated_artifact(artifact)
    
    # 解析 content 为字典
    import json
    logger.info(f"Original content type: {type(artifact_model.content)}")
    logger.info(f"Original content (first 100 chars): {artifact_model.content[:100]}")
    
    try:
        # 第一次解析
        content_dict = json.loads(artifact_model.content)
        logger.info(f"After first parse type: {type(content_dict)}")
        
        # 如果解析后还是字符串，说明是双重编码，再解析一次
        if isinstance(content_dict, str):
            content_dict = json.loads(content_dict)
            logger.info(f"After second parse type: {type(content_dict)}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse content: {e}")
        content_dict = {"error": "Failed to parse content", "raw": artifact_model.content}
    
    # 创建响应字典
    response = {
        "artifact": {
            "artifact_id": artifact_model.artifact_id,
            "task_id": artifact_model.task_id,
            "artifact_type": artifact_model.artifact_type,
            "version": artifact_model.version,
            "prompt_instance": {
                "template_id": artifact_model.prompt_instance.template_id,
                "language": artifact_model.prompt_instance.language,
                "parameters": artifact_model.prompt_instance.parameters,
            },
            "content": content_dict,  # 解析后的字典
            "metadata": artifact_model.metadata,
            "created_at": artifact_model.created_at.isoformat(),
            "created_by": artifact_model.created_by,
        }
    }
    
    logger.info(f"Response content type: {type(response['artifact']['content'])}")
    logger.info(f"Artifact detail retrieved: {artifact_id}")
    
    return response


@standalone_router.put("/{artifact_id}")
async def update_artifact(
    artifact_id: str,
    content: Dict,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    直接修改 artifact 内容（原地更新）
    
    用于用户手动编辑会议纪要等内容。
    直接更新现有 artifact，不创建新版本。
    
    Args:
        artifact_id: 衍生内容 ID
        content: 新的内容（字典格式）
        user_id: 当前用户 ID (来自依赖注入)
        db: 数据库会话
        
    Returns:
        Dict: 更新确认信息
        
    Raises:
        HTTPException: 404 如果衍生内容不存在
        HTTPException: 403 如果无权访问
    """
    logger.info(f"Updating artifact: {artifact_id} for user {user_id}")
    
    # 获取 artifact
    artifact_repo = ArtifactRepository(db)
    artifact = artifact_repo.get_by_id(artifact_id)
    
    if not artifact:
        raise HTTPException(status_code=404, detail="衍生内容不存在")
    
    # 验证所属任务的所有权
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(artifact.task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="关联的任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权修改此衍生内容")
    
    # 验证任务状态
    if task.state not in [TaskState.SUCCESS, TaskState.PARTIAL_SUCCESS]:
        raise HTTPException(
            status_code=400,
            detail=f"任务状态为 {task.state}，无法修改衍生内容"
        )
    
    # 直接更新 content
    import json
    artifact.content = json.dumps(content, ensure_ascii=False)
    
    # 更新 metadata，标记为手动编辑
    metadata = artifact.get_metadata_dict() or {}
    metadata["manually_edited"] = True
    metadata["last_edited_at"] = datetime.utcnow().isoformat()
    metadata["last_edited_by"] = user_id
    artifact.set_metadata_dict(metadata)
    
    # 更新任务的 last_content_modified_at
    task.last_content_modified_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Artifact updated: {artifact_id}")
    
    return {
        "success": True,
        "artifact_id": artifact_id,
        "message": "内容已更新"
    }


@router.post(
    "/{task_id}/artifacts/{artifact_type}/generate",
    response_model=GenerateArtifactResponse,
    status_code=201,
)
async def generate_artifact(
    artifact_type: str,
    request: GenerateArtifactRequest,
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    """
    生成新版本的衍生内容
    
    使用指定的提示词实例生成新版本的衍生内容。
    版本号自动递增。
    
    Args:
        artifact_type: 衍生内容类型 (meeting_minutes, action_items, summary_notes)
        request: 生成请求(包含 prompt_instance)
        task: 已验证的任务对象 (来自依赖注入)
        db: 数据库会话
        llm_provider: LLM 提供商
        
    Returns:
        GenerateArtifactResponse: 生成响应
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问
        HTTPException: 400 如果任务状态不允许生成或类型无效
    """
    logger.info(
        f"Generating artifact {artifact_type} for task {task.task_id} "
        f"with template {request.prompt_instance.template_id}"
    )
    
    # 验证任务状态
    if task.state not in [TaskState.SUCCESS, TaskState.PARTIAL_SUCCESS]:
        raise HTTPException(
            status_code=400,
            detail=f"任务状态为 {task.state},无法生成衍生内容",
        )
    
    # 验证 artifact_type
    valid_types = ["meeting_minutes", "action_items", "summary_notes"]
    if artifact_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的衍生内容类型: {artifact_type},有效值: {valid_types}",
        )
    
    # 获取转写结果
    transcript_repo = TranscriptRepository(db)
    transcript = transcript_repo.get_by_task_id(task.task_id)
    
    if not transcript:
        raise HTTPException(status_code=404, detail="转写记录不存在")
    
    # Phase 2: 实际调用 LLM 生成内容
    try:
        # 使用依赖注入的 LLM 提供商
        from src.services.artifact_generation import ArtifactGenerationService
        from src.core.models import PromptInstance, OutputLanguage
        
        artifact_service = ArtifactGenerationService(
            llm_provider=llm_provider,  # 使用依赖注入的 provider
            template_repo=None,  # 暂时不使用模板仓库
            artifact_repo=None,  # 直接在这里保存
        )
        
        # 转换转写记录为 TranscriptionResult
        transcript_result = transcript_repo.to_transcription_result(transcript)
        
        # 创建 PromptInstance
        prompt_instance = PromptInstance(
            template_id=request.prompt_instance.template_id,
            language=request.prompt_instance.language,
            parameters=request.prompt_instance.parameters,
        )
        
        # 获取当前最大版本号
        artifact_repo = ArtifactRepository(db)
        existing_artifacts = artifact_repo.get_by_task_and_type(task.task_id, artifact_type)
        max_version = max([a.version for a in existing_artifacts], default=0)
        new_version = max_version + 1
        
        logger.info(f"Generating {artifact_type} version {new_version} using ArtifactGenerationService")
        
        # 生成 artifact_id
        artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"
        
        # 使用 ArtifactGenerationService 生成内容
        from src.services.artifact_generation import ArtifactGenerationService
        from src.database.repositories import PromptTemplateRepository
        
        # 获取模板
        template_repo = PromptTemplateRepository(db)
        template = template_repo.get_by_id(request.prompt_instance.template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"模板不存在: {request.prompt_instance.template_id}")
        
        # 转换为 PromptTemplate 模型
        from src.core.models import PromptTemplate
        template_model = PromptTemplate(
            template_id=template.template_id,
            title=template.title,
            description=template.description,
            prompt_body=template.prompt_body,
            artifact_type=template.artifact_type,
            supported_languages=json.loads(template.supported_languages),
            parameter_schema=json.loads(template.parameter_schema),
            is_system=template.is_system,
        )
        
        # 创建 ArtifactGenerationService
        artifact_service = ArtifactGenerationService(
            llm_provider=llm_provider,
            template_repo=template_repo,
            artifact_repo=artifact_repo,
        )
        
        # 调用服务生成内容
        output_lang = OutputLanguage.ZH_CN if request.prompt_instance.language == "zh-CN" else OutputLanguage.EN_US
        generated_artifact = await artifact_service.generate_artifact(
            task_id=task.task_id,
            transcript=transcript_result,
            artifact_type=artifact_type,
            prompt_instance=prompt_instance,
            output_language=output_lang,
            user_id=task.user_id,
            template=template_model,
        )
        
        logger.info(f"Artifact {generated_artifact.artifact_id} generated successfully (version {generated_artifact.version})")
        
        # 更新内容最后修改时间
        task.last_content_modified_at = datetime.utcnow()
        db.commit()
        
        return GenerateArtifactResponse(
            success=True,
            artifact_id=generated_artifact.artifact_id,
            version=generated_artifact.version,
            content=generated_artifact.get_content_dict(),
            message=f"衍生内容已生成 (版本 {generated_artifact.version})",
        )
        
    except Exception as e:
        logger.error(f"Failed to generate artifact with LLM: {e}", exc_info=True)
        # 降级到占位符
        artifact_repo = ArtifactRepository(db)
        existing_artifacts = artifact_repo.get_by_task_and_type(task.task_id, artifact_type)
        max_version = max([a.version for a in existing_artifacts], default=0)
        new_version = max_version + 1
        
        artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"
        
        placeholder_content = {
            "type": artifact_type,
            "version": new_version,
            "error": str(e),
            "note": "LLM generation failed, using placeholder",
        }
        
        artifact = artifact_repo.create(
            artifact_id=artifact_id,
            task_id=task.task_id,
            artifact_type=artifact_type,
            version=new_version,
            prompt_instance=request.prompt_instance.model_dump(),
            content=placeholder_content,
            metadata={"generated_via_api": True, "error": str(e)},
            created_by=task.user_id,
        )
        
        return GenerateArtifactResponse(
            success=False,
            artifact_id=artifact_id,
            version=new_version,
            content=artifact.get_content_dict(),
            message=f"LLM 生成失败，返回占位符内容: {str(e)}",
        )
