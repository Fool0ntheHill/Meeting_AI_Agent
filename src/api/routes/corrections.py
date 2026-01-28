# -*- coding: utf-8 -*-
"""Transcript and speaker correction endpoints."""

import uuid
from datetime import datetime
from typing import List, Optional
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_user_id, get_llm_provider, verify_task_ownership
from src.api.schemas import (
    ConfirmTaskRequest,
    ConfirmTaskResponse,
    CorrectSpeakersRequest,
    CorrectSpeakersResponse,
    CorrectTranscriptRequest,
    CorrectTranscriptResponse,
    GenerateArtifactRequest,
    GenerateArtifactResponse,
)
from src.core.models import TaskState
from src.core.providers import LLMProvider
from src.database.models import Task
from src.database.repositories import (
    ArtifactRepository,
    SpeakerMappingRepository,
    TaskRepository,
    TranscriptRepository,
)
from src.services.artifact_generation import ArtifactGenerationService
from src.utils.logger import get_logger
from src.utils.wecom_notification import get_wecom_service
from src.config.loader import get_config

logger = get_logger(__name__)

router = APIRouter()


@router.put("/{task_id}/transcript", response_model=CorrectTranscriptResponse)
async def correct_transcript(
    task: Task = Depends(verify_task_ownership),
    request: CorrectTranscriptRequest = None,
    db: Session = Depends(get_db),
):
    """
    修正转写文本
    
    功能:
    1. 验证任务存在且有权限 (已通过 verify_task_ownership)
    2. 更新转写结果（full_text 和/或 segments）
    3. 可选: 重新生成衍生内容
    
    使用场景:
    - 用户在 Workspace 中编辑单个 segment 的 speaker → 发送完整的 segments 数组
    - 用户修改整个转写文本 → 发送 corrected_text
    
    Args:
        task: 任务对象 (已验证所有权)
        request: 修正请求
        db: 数据库会话
        
    Returns:
        CorrectTranscriptResponse: 修正响应
        
    Raises:
        HTTPException: 400 如果任务状态不允许修正
    """
    # 验证任务状态(只有成功或部分成功的任务才能修正)
    if task.state not in [TaskState.SUCCESS, TaskState.PARTIAL_SUCCESS]:
        raise HTTPException(
            status_code=400,
            detail=f"任务状态为 {task.state},无法修正转写文本",
        )
    
    # 获取转写记录
    transcript_repo = TranscriptRepository(db)
    transcript = transcript_repo.get_by_task_id(task.task_id)
    
    if not transcript:
        raise HTTPException(status_code=404, detail="转写记录不存在")
    
    # 保存修正历史
    original_text = transcript.full_text
    logger.info(
        f"Correcting transcript for task {task.task_id}: "
        f"text_length={len(original_text)} -> {len(request.corrected_text)}, "
        f"segments_provided={request.segments is not None}"
    )
    
    # 更新转写文本
    transcript_repo.update_full_text(
        task_id=task.task_id,
        full_text=request.corrected_text,
        is_corrected=True,
    )
    
    # 如果提供了 segments，也更新 segments
    if request.segments is not None:
        transcript_repo.update_segments(
            task_id=task.task_id,
            segments=request.segments,
        )
        logger.info(f"Transcript segments updated for task {task.task_id} ({len(request.segments)} segments)")
    
    # 更新内容最后修改时间
    task.last_content_modified_at = datetime.now()
    db.commit()
    
    logger.info(f"Transcript corrected for task {task.task_id}")
    
    # 重新生成衍生内容
    regenerated_artifacts = []
    if request.regenerate_artifacts:
        logger.info(f"Regenerating artifacts for task {task.task_id}")
        
        # TODO: 实现重新生成逻辑
        # 1. 获取所有现有的衍生内容
        # 2. 对每个类型重新生成新版本
        # 3. 使用原来的 prompt_instance
        
        logger.warning("Artifact regeneration not yet implemented (Phase 2)")
    
    return CorrectTranscriptResponse(
        success=True,
        message="转写文本已修正",
        regenerated_artifacts=regenerated_artifacts if regenerated_artifacts else None,
    )


@router.patch("/{task_id}/speakers", response_model=CorrectSpeakersResponse)
async def correct_speakers(
    task: Task = Depends(verify_task_ownership),
    request: CorrectSpeakersRequest = None,
    db: Session = Depends(get_db),
):
    """
    批量修正说话人（应用到该说话人的所有段落）
    
    功能:
    1. 验证任务存在且有权限 (已通过 verify_task_ownership)
    2. 更新 SpeakerMapping 表（记录映射关系）
    3. **批量更新** transcript.segments 中所有匹配的 speaker 字段
    4. 可选: 重新生成衍生内容
    
    使用场景:
    - Workbench 批量修改：用户选择 "应用到该说话人所有段落"
    - 会修改所有 speaker 字段匹配的 segments
    
    与 PUT /tasks/{task_id}/transcript 的区别:
    - 本接口：批量修改（所有匹配的 segments）
    - PUT transcript：单个修改（只修改用户编辑的那一条）
    
    Args:
        task: 任务对象 (已验证所有权)
        request: 修正请求 (speaker_mapping: {"林煜东": "张三"})
        db: 数据库会话
        
    Returns:
        CorrectSpeakersResponse: 修正响应
        
    Raises:
        HTTPException: 400 如果任务状态不允许修正
    """
    # 验证任务状态
    if task.state not in [TaskState.SUCCESS, TaskState.PARTIAL_SUCCESS]:
        raise HTTPException(
            status_code=400,
            detail=f"任务状态为 {task.state},无法修正说话人映射",
        )
    
    # 获取转写记录
    transcript_repo = TranscriptRepository(db)
    transcript = transcript_repo.get_by_task_id(task.task_id)
    
    if not transcript:
        raise HTTPException(status_code=404, detail="转写记录不存在")
    
    logger.info(f"Batch correcting speakers for task {task.task_id}: {request.speaker_mapping}")
    
    # 批量更新 segments 中的 speaker 字段
    segments = transcript.get_segments_list()
    updated_count = 0
    
    for segment in segments:
        current_speaker = segment.get("speaker")
        if current_speaker in request.speaker_mapping:
            new_speaker = request.speaker_mapping[current_speaker]
            segment["speaker"] = new_speaker
            updated_count += 1
    
    # 保存更新后的 segments
    transcript_repo.update_segments(task.task_id, segments)
    logger.info(f"Batch updated {updated_count} segments for task {task.task_id}")
    
    # 同时更新 SpeakerMapping 表（用于记录和追踪）
    speaker_mapping_repo = SpeakerMappingRepository(db)
    mappings = speaker_mapping_repo.get_by_task_id(task.task_id)
    
    for mapping in mappings:
        # mapping.speaker_name 是当前的名字（如 "林煜东"）
        if mapping.speaker_name in request.speaker_mapping:
            new_name = request.speaker_mapping[mapping.speaker_name]
            speaker_mapping_repo.update_speaker_name(
                task_id=task.task_id,
                speaker_label=mapping.speaker_label,
                speaker_name=new_name,
            )
            logger.info(
                f"Updated SpeakerMapping: {mapping.speaker_label} ({mapping.speaker_name} -> {new_name})"
            )
    
    # 更新内容最后修改时间
    task.last_content_modified_at = datetime.now()
    db.commit()
    
    # 重新生成衍生内容
    regenerated_artifacts = []
    if request.regenerate_artifacts:
        logger.info(f"Regenerating artifacts for task {task.task_id}")
        
        # TODO: 实现重新生成逻辑
        logger.warning("Artifact regeneration not yet implemented (Phase 2)")
    
    return CorrectSpeakersResponse(
        success=True,
        message=f"说话人已批量修正（更新了 {updated_count} 个段落）",
        regenerated_artifacts=regenerated_artifacts if regenerated_artifacts else None,
    )


@router.post(
    "/{task_id}/artifacts/{artifact_type}/regenerate",
    response_model=GenerateArtifactResponse,
    status_code=202,  # 202 Accepted - 异步处理
)
async def regenerate_artifact(
    artifact_type: str,
    task: Task = Depends(verify_task_ownership),
    request: GenerateArtifactRequest = None,
    db: Session = Depends(get_db),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    """
    重新生成衍生内容（异步）
    
    流程:
    1. 立即创建占位 artifact（state=processing）
    2. 返回 artifact_id 给前端
    3. 异步执行实际生成
    4. 生成完成后更新 artifact 的 content 和 state
    
    前端可以通过 GET /api/v1/artifacts/{artifact_id}/status 轮询状态。
    
    Args:
        artifact_type: 衍生内容类型 (meeting_minutes, action_items, summary_notes)
        task: 任务对象 (已验证所有权)
        request: 生成请求
        db: 数据库会话
        llm_provider: LLM 提供商
        
    Returns:
        GenerateArtifactResponse: 生成响应（立即返回，state=processing）
        
    Raises:
        HTTPException: 400 如果任务状态不允许重新生成
    """
    # 验证任务状态
    if task.state not in [TaskState.SUCCESS, TaskState.PARTIAL_SUCCESS]:
        raise HTTPException(
            status_code=400,
            detail=f"任务状态为 {task.state},无法重新生成衍生内容",
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
    
    logger.info(
        f"Regenerating artifact {artifact_type} for task {task.task_id} "
        f"with prompt template {request.prompt_instance.template_id}"
    )
    
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
        metadata={"regenerated": True, "async": True},
    )
    
    # 提交占位 artifact
    db.commit()
    
    logger.info(f"Placeholder artifact created for regeneration: {artifact_id} (state=processing)")
    
    # 异步执行实际生成（复用 artifacts.py 的函数）
    from src.api.routes.artifacts import _generate_artifact_async, _resolve_task_name
    
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
        content={"status": "generating", "message": "内容重新生成中，请稍候..."},
        display_name=display_name,
        state="processing",
        message=f"衍生内容重新生成已启动 (版本 {new_version})，请稍候...",
    )


@router.post(
    "/{task_id}/confirm",
    response_model=ConfirmTaskResponse,
)
async def confirm_task(
    task: Task = Depends(verify_task_ownership),
    request: ConfirmTaskRequest = None,
    db: Session = Depends(get_db),
):
    """
    确认任务并归档
    
    功能:
    1. 验证任务存在且有权限 (已通过 verify_task_ownership)
    2. 验证所有必需的确认项都已勾选
    3. 注入责任人水印到衍生内容元数据
    4. 更新任务状态为 ARCHIVED
    5. 记录确认人和确认时间
    
    Args:
        task: 任务对象 (已验证所有权)
        request: 确认请求
        db: 数据库会话
        
    Returns:
        ConfirmTaskResponse: 确认响应
        
    Raises:
        HTTPException: 400 如果确认项未完成或任务状态不允许确认
    """
    # 验证任务状态(只有成功或部分成功的任务才能确认)
    if task.state not in [TaskState.SUCCESS, TaskState.PARTIAL_SUCCESS]:
        raise HTTPException(
            status_code=400,
            detail=f"任务状态为 {task.state},无法确认任务",
        )
    
    # 验证任务未被确认过
    if task.is_confirmed:
        raise HTTPException(
            status_code=400,
            detail="任务已被确认,无法重复确认",
        )
    
    # 验证所有必需的确认项都已勾选
    required_items = ["key_conclusions", "responsible_persons"]
    missing_items = []
    
    for item in required_items:
        if item not in request.confirmation_items or not request.confirmation_items[item]:
            missing_items.append(item)
    
    if missing_items:
        raise HTTPException(
            status_code=400,
            detail=f"以下确认项未完成: {', '.join(missing_items)}",
        )
    
    # 验证责任人信息
    if "id" not in request.responsible_person or "name" not in request.responsible_person:
        raise HTTPException(
            status_code=400,
            detail="责任人信息不完整,需要包含 id 和 name",
        )
    
    logger.info(
        f"Confirming task {task.task_id} by {request.responsible_person['name']} "
        f"({request.responsible_person['id']})"
    )
    
    # 注入责任人水印到所有衍生内容的元数据
    artifact_repo = ArtifactRepository(db)
    artifacts = artifact_repo.get_by_task_id(task.task_id)
    
    watermark = {
        "confirmed_by_id": request.responsible_person["id"],
        "confirmed_by_name": request.responsible_person["name"],
        "confirmed_at": datetime.now().isoformat(),
        "confirmation_items": request.confirmation_items,
    }
    
    for artifact in artifacts:
        # 获取现有元数据
        metadata = artifact.get_metadata_dict() or {}
        # 添加水印
        metadata["watermark"] = watermark
        # 更新元数据
        artifact.set_metadata_dict(metadata)
        logger.info(f"Watermark injected to artifact {artifact.artifact_id}")
    
    # 确认任务并归档
    task_repo = TaskRepository(db)
    confirmed_task = task_repo.confirm_task(
        task_id=task.task_id,
        confirmation_items=request.confirmation_items,
        confirmed_by=request.responsible_person["id"],
        confirmed_by_name=request.responsible_person["name"],
    )
    
    if not confirmed_task:
        raise HTTPException(status_code=500, detail="任务确认失败")
    
    # 提交数据库事务
    db.commit()
    
    logger.info(f"Task {task.task_id} confirmed and archived successfully")
    
    return ConfirmTaskResponse(
        success=True,
        task_id=task.task_id,
        state=confirmed_task.state,
        confirmed_by=confirmed_task.confirmed_by,
        confirmed_by_name=confirmed_task.confirmed_by_name,
        confirmed_at=confirmed_task.confirmed_at,
        message="任务已确认并归档",
    )



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
