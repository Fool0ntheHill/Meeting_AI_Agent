# -*- coding: utf-8 -*-
"""Transcript and speaker correction endpoints."""

import uuid
from datetime import datetime
from typing import List, Optional

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
    2. 保存修正历史(原文本 -> 修正文本)
    3. 更新转写结果
    4. 可选: 重新生成衍生内容
    
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
        f"{len(original_text)} -> {len(request.corrected_text)} chars"
    )
    
    # 更新转写文本
    transcript_repo.update_full_text(
        task_id=task.task_id,
        full_text=request.corrected_text,
        is_corrected=True,
    )
    
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
    修正说话人映射
    
    功能:
    1. 验证任务存在且有权限 (已通过 verify_task_ownership)
    2. 应用说话人映射修正
    3. 更新转写结果中的说话人标签
    4. 可选: 重新生成衍生内容
    
    Args:
        task: 任务对象 (已验证所有权)
        request: 修正请求
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
    
    # 获取说话人映射
    speaker_repo = SpeakerMappingRepository(db)
    mappings = speaker_repo.get_by_task_id(task.task_id)
    
    if not mappings:
        raise HTTPException(status_code=404, detail="说话人映射不存在")
    
    logger.info(f"Correcting speaker mappings for task {task.task_id}: {request.speaker_mapping}")
    
    # 应用修正
    for mapping in mappings:
        if mapping.speaker_label in request.speaker_mapping:
            new_name = request.speaker_mapping[mapping.speaker_label]
            speaker_repo.update_speaker_name(
                task_id=task.task_id,
                speaker_label=mapping.speaker_label,
                speaker_name=new_name,
            )
            logger.info(
                f"Updated speaker mapping: {mapping.speaker_label} -> {new_name}"
            )
    
    # 更新转写结果中的说话人标签
    transcript_repo = TranscriptRepository(db)
    transcript = transcript_repo.get_by_task_id(task.task_id)
    
    if transcript:
        # 应用说话人映射到 segments
        segments = transcript.get_segments_list()
        for segment in segments:
            if segment.get("speaker") in request.speaker_mapping:
                segment["speaker"] = request.speaker_mapping[segment["speaker"]]
        
        # 更新转写记录
        transcript_repo.update_segments(task.task_id, segments)
        logger.info(f"Updated transcript segments with new speaker names")
    
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
        message="说话人映射已修正",
        regenerated_artifacts=regenerated_artifacts if regenerated_artifacts else None,
    )


@router.post(
    "/{task_id}/artifacts/{artifact_type}/regenerate",
    response_model=GenerateArtifactResponse,
)
async def regenerate_artifact(
    artifact_type: str,
    task: Task = Depends(verify_task_ownership),
    request: GenerateArtifactRequest = None,
    db: Session = Depends(get_db),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    """
    重新生成衍生内容
    
    功能:
    1. 验证任务存在且有权限 (已通过 verify_task_ownership)
    2. 获取最新的转写结果
    3. 使用新的 prompt_instance 生成内容
    4. 创建新版本的衍生内容
    5. 版本号自动递增
    
    Args:
        artifact_type: 衍生内容类型 (meeting_minutes, action_items, summary_notes)
        task: 任务对象 (已验证所有权)
        request: 生成请求
        db: 数据库会话
        llm_provider: LLM 提供商
        
    Returns:
        GenerateArtifactResponse: 生成响应
        
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
    
    # 获取转写结果
    transcript_repo = TranscriptRepository(db)
    transcript = transcript_repo.get_by_task_id(task.task_id)
    
    if not transcript:
        raise HTTPException(status_code=404, detail="转写记录不存在")
    
    # 获取说话人映射
    speaker_repo = SpeakerMappingRepository(db)
    speaker_mappings = speaker_repo.get_by_task_id(task.task_id)
    
    # 构建说话人映射字典
    speaker_map = {
        mapping.speaker_label: mapping.speaker_name for mapping in speaker_mappings
    }
    
    logger.info(
        f"Regenerating artifact {artifact_type} for task {task.task_id} "
        f"with prompt template {request.prompt_instance.template_id}"
    )
    
    # 使用依赖注入的 LLM 提供商生成内容
    try:
        from src.core.models import PromptInstance, OutputLanguage
        from src.database.repositories import PromptTemplateRepository
        
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
        
        logger.info(f"Regenerating {artifact_type} version {new_version} using ArtifactGenerationService")
        
        # 获取模板
        template_repo = PromptTemplateRepository(db)
        template_record = template_repo.get_by_id(request.prompt_instance.template_id)
        
        if not template_record:
            raise HTTPException(status_code=404, detail=f"模板不存在: {request.prompt_instance.template_id}")
        
        # 转换为 PromptTemplate 模型
        from src.core.models import PromptTemplate
        template_model = PromptTemplate(
            template_id=template_record.template_id,
            title=template_record.title,
            description=template_record.description,
            prompt_body=template_record.prompt_body,
            artifact_type=template_record.artifact_type,
            supported_languages=json.loads(template_record.supported_languages),
            parameter_schema=json.loads(template_record.parameter_schema),
            is_system=template_record.is_system,
        )
        
        # 初始化 ArtifactGenerationService
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
        
        logger.info(f"Artifact {generated_artifact.artifact_id} regenerated successfully (version {generated_artifact.version})")
        
        # 更新内容最后修改时间
        task.last_content_modified_at = datetime.now()
        db.commit()
        
        return GenerateArtifactResponse(
            success=True,
            artifact_id=generated_artifact.artifact_id,
            version=generated_artifact.version,
            content=generated_artifact.get_content_dict(),
            message=f"衍生内容已重新生成 (版本 {generated_artifact.version})",
        )
        
    except Exception as e:
        logger.error(f"Failed to regenerate artifact with LLM: {e}", exc_info=True)
        # 降级到占位符
        artifact_repo = ArtifactRepository(db)
        existing_artifacts = artifact_repo.get_by_task_and_type(task.task_id, artifact_type)
        max_version = max([a.version for a in existing_artifacts], default=0)
        new_version = max_version + 1
        
        artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"
        
        # 创建新版本（带错误信息）
        artifact = artifact_repo.create(
            artifact_id=artifact_id,
            task_id=task.task_id,
            artifact_type=artifact_type,
            version=new_version,
            prompt_instance=request.prompt_instance.model_dump(),
            content={"error": str(e), "placeholder": "LLM generation failed"},
            metadata={"regenerated": True, "error": True},
            created_by=task.user_id,
        )
        
        logger.warning(f"Artifact {artifact_id} created with placeholder due to error")
        
        return GenerateArtifactResponse(
            success=False,
            artifact_id=artifact_id,
            version=new_version,
            content=artifact.get_content_dict(),
            message=f"生成失败，已创建占位符版本 {new_version}: {str(e)}",
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

