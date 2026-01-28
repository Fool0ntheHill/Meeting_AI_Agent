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

from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
import json
import asyncio
import os

from src.api.dependencies import get_db, get_current_user_id, get_llm_provider, verify_task_ownership
from src.database.models import Task
from src.api.schemas import (
    ListArtifactsResponse,
    ArtifactInfo,
    ListArtifactVersionsResponse,
    ArtifactDetailResponse,
    GenerateArtifactRequest,
    GenerateArtifactResponse,
    RenameArtifactRequest,
    RenameArtifactResponse,
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
from src.utils.wecom_notification import get_wecom_service
from src.config.loader import get_config

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
        display_name=record.display_name,  # 添加 display_name
        state=record.state if hasattr(record, 'state') and record.state else "success",  # 添加 state，向后兼容
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


def _resolve_task_name(task: Task) -> Optional[str]:
    """Resolve task name for notifications with filename fallback."""
    if task.name:
        return task.name
    try:
        filenames = task.get_original_filenames_list()
    except Exception:
        filenames = None
    if filenames:
        return os.path.splitext(filenames[0])[0]
    return None


# ============================================================================
# Async Generation Background Task
# ============================================================================


async def _generate_artifact_async(
    artifact_id: str,
    task_id: str,
    artifact_type: str,
    prompt_instance: PromptInstance,
    display_name: str,
    user_id: str,
    meeting_date: Optional[str],
    meeting_time: Optional[str],
    task_name: str,
):
    """
    异步生成 artifact 内容
    
    在后台执行实际的 LLM 生成，完成后更新 artifact 的 content 和 state。
    
    Args:
        artifact_id: Artifact ID
        task_id: 任务 ID
        artifact_type: Artifact 类型
        prompt_instance: 提示词实例
        display_name: 显示名称
        user_id: 用户 ID
        meeting_date: 会议日期
        meeting_time: 会议时间
        task_name: 任务名称
    """
    from src.database.session import get_session
    from src.database.repositories import (
        ArtifactRepository,
        TranscriptRepository,
        SpeakerMappingRepository,
        PromptTemplateRepository,
        TaskRepository,
    )
    from src.services.artifact_generation import ArtifactGenerationService
    from src.services.correction import CorrectionService
    from src.core.models import OutputLanguage
    from src.config.loader import get_config
    from src.utils.error_handler import classify_exception
    
    logger.info(f"Starting async generation for artifact {artifact_id}")
    
    # 创建独立的数据库会话
    db = get_session()
    
    try:
        # 获取转写结果
        transcript_repo = TranscriptRepository(db)
        transcript = transcript_repo.get_by_task_id(task_id)
        
        if not transcript:
            raise Exception("转写记录不存在")
        
        # 转换转写记录为 TranscriptionResult
        transcript_result = transcript_repo.to_transcription_result(transcript)
        
        # 获取说话人映射并应用到转写结果
        speaker_mapping_repo = SpeakerMappingRepository(db)
        speaker_mapping = speaker_mapping_repo.get_mapping_dict(task_id)
        logger.info(f"Retrieved speaker mapping for task {task_id}: {speaker_mapping}")
        
        # 应用说话人映射
        if speaker_mapping:
            correction_service = CorrectionService()
            transcript_result = await correction_service.correct_speakers(transcript_result, speaker_mapping)
            logger.info(f"Applied speaker mapping to transcript")
        
        # 创建 LLM provider
        config = get_config()
        from src.providers.gemini_llm import GeminiLLM
        llm_provider = GeminiLLM(config.gemini)
        
        # 创建 ArtifactGenerationService
        template_repo = PromptTemplateRepository(db)
        artifact_repo = ArtifactRepository(db)
        
        artifact_service = ArtifactGenerationService(
            llm_provider=llm_provider,
            template_repo=template_repo,
            artifact_repo=artifact_repo,
        )
        
        # 调用服务生成内容
        output_lang = OutputLanguage.ZH_CN if prompt_instance.language == "zh-CN" else OutputLanguage.EN_US
        generated_artifact = await artifact_service.generate_artifact(
            task_id=task_id,
            transcript=transcript_result,
            artifact_type=artifact_type,
            prompt_instance=prompt_instance,
            output_language=output_lang,
            user_id=user_id,
            template=None,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            artifact_id=artifact_id,  # 使用已创建的 artifact_id
        )
        
        # 更新占位 artifact 的内容和状态
        artifact_repo.update_content_and_state(
            artifact_id=artifact_id,
            content=generated_artifact.get_content_dict(),
            state="success",
        )
        
        # 更新 display_name
        artifact_record = artifact_repo.get_by_id(artifact_id)
        if artifact_record:
            artifact_record.display_name = display_name
        
        # 更新任务的内容最后修改时间
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if task:
            task.last_content_modified_at = datetime.now()
        
        db.commit()
        
        logger.info(f"Artifact {artifact_id} generated successfully (async)")
        
        # 发送成功通知
        await _send_success_notification(
            task_id=task_id,
            task_name=task_name,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            display_name=display_name,
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Failed to generate artifact {artifact_id} (async): {e}", exc_info=True)
        
        # 分类错误
        error_info = classify_exception(e)
        
        # 更新 artifact 为失败状态（错误信息直接放在 content 中）
        artifact_repo = ArtifactRepository(db)
        
        error_content = {
            "error_code": error_info.error_code,
            "error_message": error_info.error_message,  # 修正：使用 error_message 而不是 user_message
            "hint": "可在 Workspace 首版纪要查看已有内容"
        }
        
        artifact_repo.update_content_and_state(
            artifact_id=artifact_id,
            content=error_content,
            state="failed",
        )
        
        db.commit()
        
        # 发送失败通知
        await _send_failure_notification(
            task_id=task_id,
            task_name=task_name,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            error_code=error_info.error_code,
            error_message=error_info.error_message,  # 修正：使用 error_message 而不是 user_message
            user_id=user_id
        )
        
    finally:
        db.close()


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


@standalone_router.get("/{artifact_id}/status")
async def get_artifact_status(
    artifact_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    获取 artifact 生成状态（轻量级接口，用于前端轮询）
    
    返回 artifact 的当前状态，不包含完整内容。
    适用于前端轮询检查生成是否完成。
    
    Args:
        artifact_id: Artifact ID
        user_id: 当前用户 ID (来自依赖注入)
        db: 数据库会话
        
    Returns:
        ArtifactStatusResponse: 状态信息
        
    Raises:
        HTTPException: 404 如果 artifact 不存在
        HTTPException: 403 如果无权访问
    """
    logger.info(f"Getting artifact status: {artifact_id} for user {user_id}")
    
    # 获取 artifact
    artifact_repo = ArtifactRepository(db)
    artifact = artifact_repo.get_by_id(artifact_id)
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact 不存在")
    
    # 验证所属任务的所有权
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(artifact.task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="关联的任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此 artifact")
    
    # 获取状态信息
    status = artifact_repo.get_status(artifact_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="无法获取 artifact 状态")
    
    logger.info(f"Artifact status retrieved: {artifact_id}, state={status['state']}")
    
    return status


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
    metadata["last_edited_at"] = datetime.now().isoformat()
    metadata["last_edited_by"] = user_id
    artifact.set_metadata_dict(metadata)
    
    # 更新任务的 last_content_modified_at
    task.last_content_modified_at = datetime.now()
    db.commit()
    
    logger.info(f"Artifact updated: {artifact_id}")
    
    return {
        "success": True,
        "artifact_id": artifact_id,
        "message": "内容已更新"
    }
@standalone_router.patch("/{artifact_id}", response_model=RenameArtifactResponse)
async def rename_artifact(
    artifact_id: str,
    request: RenameArtifactRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    重命名 artifact（更新 display_name）
    """
    display_name = request.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name is required")

    artifact_repo = ArtifactRepository(db)
    artifact = artifact_repo.get_by_id(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact 不存在")

    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(artifact.task_id)

    if not task:
        raise HTTPException(status_code=404, detail="关联任务不存在")

    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此 artifact")

    artifact.display_name = display_name
    task.last_content_modified_at = datetime.now()
    db.commit()

    logger.info(f"Artifact renamed: {artifact_id} -> {display_name}")

    return RenameArtifactResponse(
        success=True,
        artifact_id=artifact_id,
        display_name=display_name,
        message="Artifact renamed",
    )


@router.post(
    "/{task_id}/artifacts/{artifact_type}/generate",
    response_model=GenerateArtifactResponse,
    status_code=202,  # 202 Accepted - 异步处理
)
async def generate_artifact(
    artifact_type: str,
    request: GenerateArtifactRequest,
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    """
    生成新版本的衍生内容（异步）
    
    流程:
    1. 立即创建占位 artifact（state=processing）
    2. 返回 artifact_id 给前端
    3. 异步执行实际生成
    4. 生成完成后更新 artifact 的 content 和 state
    
    前端可以通过 GET /api/v1/artifacts/{artifact_id}/status 轮询状态。
    
    Args:
        artifact_type: 衍生内容类型 (meeting_minutes, action_items, summary_notes)
        request: 生成请求(包含 prompt_instance)
        task: 已验证的任务对象 (来自依赖注入)
        db: 数据库会话
        llm_provider: LLM 提供商
        
    Returns:
        GenerateArtifactResponse: 生成响应（立即返回，state=processing）
        
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
    
    # 校验 display_name 必填
    if not request.name or not request.name.strip():
        raise HTTPException(
            status_code=400,
            detail="display_name (name) is required"
        )
    
    display_name = request.name.strip()
    
    # 获取当前最大版本号（按 display_name 而不是 artifact_type）
    artifact_repo = ArtifactRepository(db)
    existing_artifacts = artifact_repo.get_by_task_and_name(task.task_id, display_name)
    max_version = max([a.version for a in existing_artifacts], default=0)
    new_version = max_version + 1
    
    # 生成 artifact_id
    artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"
    
    # 立即创建占位 artifact（state=processing）
    placeholder_artifact = artifact_repo.create_placeholder(
        artifact_id=artifact_id,
        task_id=task.task_id,
        artifact_type=artifact_type,
        version=new_version,
        prompt_instance=request.prompt_instance.model_dump(),
        created_by=task.user_id,
        display_name=display_name,
        metadata={"generated_via_api": True, "async": True},
    )
    
    # 提交占位 artifact
    db.commit()
    
    logger.info(f"Placeholder artifact created: {artifact_id} (state=processing)")
    
    # 异步执行实际生成
    asyncio.create_task(_generate_artifact_async(
        artifact_id=artifact_id,
        task_id=task.task_id,
        artifact_type=artifact_type,
        prompt_instance=request.prompt_instance,
        display_name=display_name,
        user_id=task.user_id,
        meeting_date=task.meeting_date,
        meeting_time=task.meeting_time,
        task_name=_resolve_task_name(task),
    ))
    
    # 立即返回占位响应
    return GenerateArtifactResponse(
        success=True,
        artifact_id=artifact_id,
        version=new_version,
        content={"status": "generating", "message": "内容生成中，请稍候..."},
        display_name=display_name,
        state="processing",
        message=f"衍生内容生成已启动 (版本 {new_version})，请稍候...",
    )


# ============================================================================
# DELETE Artifact
# ============================================================================


@router.delete("/{task_id}/artifacts/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    删除指定的 artifact
    
    功能:
    - 删除指定 ID 的 artifact
    - 验证 artifact 属于当前任务
    - 验证用户权限
    
    Args:
        artifact_id: Artifact ID
        task: 任务对象（已验证所有权）
        db: 数据库会话
        
    Returns:
        删除成功消息
        
    Raises:
        HTTPException: 404 如果 artifact 不存在
        HTTPException: 403 如果 artifact 不属于此任务
    """
    artifact_repo = ArtifactRepository(db)
    
    # 获取 artifact
    artifact = artifact_repo.get_by_id(artifact_id)
    
    if not artifact:
        logger.warning(f"Artifact not found: {artifact_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Artifact 不存在: {artifact_id}"
        )
    
    # 验证 artifact 属于此任务
    if artifact.task_id != task.task_id:
        logger.warning(
            f"Artifact {artifact_id} does not belong to task {task.task_id}, "
            f"belongs to {artifact.task_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="无权删除此 artifact"
        )
    
    # 删除 artifact
    success = artifact_repo.delete(artifact_id)
    
    if not success:
        logger.error(f"Failed to delete artifact: {artifact_id}")
        raise HTTPException(
            status_code=500,
            detail="删除 artifact 失败"
        )
    
    # 更新内容最后修改时间
    task.last_content_modified_at = datetime.now()
    db.commit()
    
    logger.info(f"Artifact {artifact_id} deleted successfully")
    
    return {
        "success": True,
        "message": f"Artifact {artifact_id} 已删除",
        "artifact_id": artifact_id
    }


# ============================================================================
# Helper Functions for WeCom Notifications
# ============================================================================


async def _send_success_notification(
    task_id: str,
    task_name: str,
    meeting_date: str,
    meeting_time: str,
    artifact_id: str,
    artifact_type: str,
    display_name: str,
    user_id: str
):
    """
    异步发送成功通知
    
    Args:
        task_id: 任务 ID
        task_name: 任务名称
        meeting_date: 会议日期
        meeting_time: 会议时间
        artifact_id: Artifact ID
        artifact_type: Artifact 类型
        display_name: 自定义显示名称
        user_id: 用户 ID
    """
    try:
        config = get_config()
        
        # 检查是否启用企微通知
        if not config.wecom or not config.wecom.enabled:
            logger.debug("WeCom notification disabled, skipping")
            return
        
        if not config.frontend:
            logger.warning("Frontend config not found, cannot send notification")
            return
        
        # 创建新的数据库会话（异步任务需要独立的 Session）
        from src.database.session import get_session
        from src.database.repositories import UserRepository
        
        db = get_session()
        try:
            user_repo = UserRepository(db)
            user = user_repo.get_by_id(user_id)
            
            if not user:
                logger.warning(f"User not found: {user_id}, cannot send notification")
                return
            
            # username 就是企微英文账号（如 lorenzolin）
            user_account = user.username
            
            # 获取企微服务
            wecom_service = get_wecom_service(
                api_url=config.wecom.api_url,
                frontend_base_url=config.frontend.base_url
            )
            
            # 发送通知
            wecom_service.send_artifact_success_notification(
                user_account=user_account,
                task_id=task_id,
                task_name=task_name,
                meeting_date=meeting_date,
                meeting_time=meeting_time,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                display_name=display_name
            )
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Failed to send WeCom success notification: {e}", exc_info=True)


async def _send_failure_notification(
    task_id: str,
    task_name: str,
    meeting_date: str,
    meeting_time: str,
    error_code: str,
    error_message: str,
    user_id: str
):
    """
    异步发送失败通知
    
    Args:
        task_id: 任务 ID
        task_name: 任务名称
        meeting_date: 会议日期
        meeting_time: 会议时间
        error_code: 错误码
        error_message: 错误消息
        user_id: 用户 ID
    """
    try:
        config = get_config()
        
        # 检查是否启用企微通知
        if not config.wecom or not config.wecom.enabled:
            logger.debug("WeCom notification disabled, skipping")
            return
        
        if not config.frontend:
            logger.warning("Frontend config not found, cannot send notification")
            return
        
        # 创建新的数据库会话（异步任务需要独立的 Session）
        from src.database.session import get_session
        from src.database.repositories import UserRepository
        
        db = get_session()
        try:
            user_repo = UserRepository(db)
            user = user_repo.get_by_id(user_id)
            
            if not user:
                logger.warning(f"User not found: {user_id}, cannot send notification")
                return
            
            # username 就是企微英文账号（如 lorenzolin）
            user_account = user.username
            
            # 获取企微服务
            wecom_service = get_wecom_service(
                api_url=config.wecom.api_url,
                frontend_base_url=config.frontend.base_url
            )
            
            # 发送通知
            wecom_service.send_artifact_failure_notification(
                user_account=user_account,
                task_id=task_id,
                task_name=task_name,
                meeting_date=meeting_date,
                meeting_time=meeting_time,
                error_code=error_code,
                error_message=error_message
            )
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Failed to send WeCom failure notification: {e}", exc_info=True)
