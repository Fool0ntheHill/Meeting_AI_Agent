# -*- coding: utf-8 -*-
"""Task management endpoints."""

import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import redis

from src.api.dependencies import get_db, get_current_user_id, get_current_tenant_id, verify_task_ownership
from src.api.schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    EstimateCostRequest,
    EstimateCostResponse,
    RenameTaskRequest,
    RenameTaskResponse,
    TaskDetailResponse,
    TaskStatusResponse,
    TranscriptResponse,
    TranscriptSegment,
)
from src.core.models import TaskState
from src.database.models import Task
from src.database.repositories import TaskRepository
from src.utils.logger import get_logger
from src.queue.manager import QueueManager, QueueBackend

logger = get_logger(__name__)

router = APIRouter()

# 全局队列管理器(在应用启动时初始化)
_queue_manager: Optional[QueueManager] = None
# 全局 Redis 客户端(用于缓存)
_redis_client: Optional[redis.Redis] = None


def get_queue_manager() -> QueueManager:
    """获取队列管理器依赖"""
    global _queue_manager
    if _queue_manager is None:
        # 默认使用 Redis
        # TODO: 从配置文件读取
        try:
            _queue_manager = QueueManager(
                backend=QueueBackend.REDIS,
                redis_url="redis://localhost:6379/0",
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Queue service unavailable: {str(e)}"
            )
    return _queue_manager


def get_redis_client() -> redis.Redis:
    """获取 Redis 客户端依赖(用于缓存)"""
    global _redis_client
    if _redis_client is None:
        # TODO: 从配置文件读取
        try:
            _redis_client = redis.from_url(
                "redis://localhost:6379/0",
                decode_responses=True,
            )
            # 测试连接
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}")
            # 返回 None,降级到仅使用数据库
            return None
    return _redis_client


@router.post("", response_model=CreateTaskResponse, status_code=201)
async def create_task(
    request: CreateTaskRequest,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    queue: QueueManager = Depends(get_queue_manager),
):
    """
    创建任务
    
    流程:
    1. 验证请求参数
    2. 生成任务 ID
    3. 创建任务记录
    4. 推送到消息队列
    5. 立即返回任务 ID
    
    Args:
        request: 创建任务请求
        user_id: 用户 ID (来自认证)
        tenant_id: 租户 ID (来自认证)
        db: 数据库会话
        queue: 队列管理器
        
    Returns:
        CreateTaskResponse: 任务创建响应
    """
    try:
        # 生成任务 ID
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        
        # 处理 file_order
        file_order = request.file_order
        if file_order is None:
            file_order = list(range(len(request.audio_files)))
        
        # 创建任务记录
        task_repo = TaskRepository(db)
        task = task_repo.create(
            task_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            meeting_type=request.meeting_type,
            audio_files=request.audio_files,
            file_order=file_order,
            original_filenames=request.original_filenames,  # 保存原始文件名
            audio_duration=request.audio_duration,  # 保存音频时长（从上传接口获取）
            meeting_date=request.meeting_date,  # 保存会议日期
            meeting_time=request.meeting_time,  # 保存会议时间
            asr_language=request.asr_language,
            output_language=request.output_language,
            skip_speaker_recognition=request.skip_speaker_recognition,
            hotword_set_id=None,  # Phase 2: 热词集解析 (Task 20)
            preferred_asr_provider="volcano",
        )
        
        logger.info(f"Task created: {task_id} by user {user_id}")
        
        # 推送到消息队列
        task_data = {
            "user_id": user_id,  # Add user_id for pipeline
            "tenant_id": tenant_id,  # Add tenant_id for pipeline
            "audio_files": request.audio_files,
            "file_order": file_order,
            "meeting_type": request.meeting_type,
            "enable_speaker_recognition": not request.skip_speaker_recognition,
            "enable_correction": True,
            "prompt_instance": request.prompt_instance.model_dump() if request.prompt_instance else None,
            "hotword_sets": None,  # Phase 2: 热词集解析 (Task 20)
            "asr_language": request.asr_language,
            "output_language": request.output_language,
        }
        
        success = queue.push(
            task_id=task_id,
            task_data=task_data,
            priority=0,  # 默认优先级
        )
        
        if not success:
            logger.error(f"Failed to push task {task_id} to queue")
            raise HTTPException(
                status_code=500,
                detail="任务推送到队列失败",
            )
        
        logger.info(f"Task {task_id} pushed to queue")
        
        return CreateTaskResponse(
            success=True,
            task_id=task_id,
            message="任务已创建并加入处理队列",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"创建任务失败: {str(e)}",
        )


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client: Optional[redis.Redis] = Depends(get_redis_client),
):
    """
    查询任务状态
    
    实现 Cache-Aside 模式:
    1. 先查 Redis 缓存
    2. Cache Miss 则查数据库
    3. 回填缓存(TTL 60秒)
    
    注意: 此端点保留手动检查以优化缓存性能。
    缓存命中时避免额外的数据库查询。
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        redis_client: Redis 客户端(可选)
        
    Returns:
        TaskStatusResponse: 任务状态信息
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问
    """
    cache_key = f"task_status:{task_id}"
    
    # 1. 尝试从 Redis 缓存读取
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for task {task_id}")
                data = json.loads(cached_data)
                
                # 验证权限(缓存中也需要验证)
                if data.get("user_id") != user_id:
                    raise HTTPException(status_code=403, detail="无权访问此任务")
                
                return TaskStatusResponse(
                    task_id=data["task_id"],
                    state=TaskState(data["state"]),
                    progress=data.get("progress", 0.0),
                    estimated_time=data.get("estimated_time"),
                    audio_duration=data.get("audio_duration"),
                    asr_language=data.get("asr_language"),
                    error_code=data.get("error_code"),
                    error_message=data.get("error_message"),
                    error_details=data.get("error_details"),
                    retryable=data.get("retryable"),
                    updated_at=data["updated_at"],
                )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode cached data for task {task_id}: {e}")
        except Exception as e:
            logger.warning(f"Redis cache read failed for task {task_id}: {e}")
    
    # 2. Cache Miss,查询数据库
    logger.debug(f"Cache miss for task {task_id}, querying database")
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证权限
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 获取音频时长（优先从 Task 模型，如果没有则从转写记录）
    audio_duration = task.audio_duration
    if audio_duration is None and task.transcripts:
        audio_duration = task.transcripts[0].duration
    
    # 获取 ASR 识别语言
    asr_language = task.asr_language
    
    # 3. 回填缓存
    # 对于进行中的任务，使用较短的TTL（5秒），确保能及时看到状态更新
    # 对于已完成的任务，使用较长的TTL（60秒）
    if redis_client:
        try:
            cache_data = {
                "task_id": task.task_id,
                "user_id": task.user_id,  # 用于权限验证
                "state": task.state,
                "progress": task.progress,
                "estimated_time": task.estimated_time,
                "audio_duration": audio_duration,
                "asr_language": asr_language,
                "error_code": task.error_code,
                "error_message": task.error_message,
                "error_details": task.error_details,
                "retryable": task.retryable,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
            
            # 根据任务状态设置不同的TTL
            if task.state in ["success", "failed", "partial_success"]:
                ttl = 60  # 已完成的任务，缓存60秒
            else:
                ttl = 5  # 进行中的任务，缓存5秒，确保能及时看到更新
            
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, ensure_ascii=False),
            )
            logger.debug(f"Cached task status for {task_id} (TTL={ttl}s)")
        except Exception as e:
            logger.warning(f"Failed to cache task status for {task_id}: {e}")
    
    return TaskStatusResponse(
        task_id=task.task_id,
        state=TaskState(task.state),
        progress=task.progress,
        estimated_time=task.estimated_time,
        audio_duration=audio_duration,
        asr_language=asr_language,
        error_code=task.error_code,
        error_message=task.error_message,
        error_details=task.error_details,
        retryable=task.retryable,
        updated_at=task.updated_at,
    )


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    获取任务详情
    
    Args:
        task: 任务对象 (已验证所有权)
        db: 数据库会话
        
    Returns:
        TaskDetailResponse: 任务详细信息
    """
    # 获取音频时长（从转写记录）
    duration = None
    if task.transcripts:
        duration = task.transcripts[0].duration
    
    return TaskDetailResponse(
        task_id=task.task_id,
        user_id=task.user_id,
        tenant_id=task.tenant_id,
        name=task.name,
        meeting_type=task.meeting_type,
        audio_files=task.get_audio_files_list(),
        file_order=task.get_file_order_list(),
        asr_language=task.asr_language,
        output_language=task.output_language,
        state=TaskState(task.state),
        progress=task.progress,
        error_code=task.error_code,
        error_message=task.error_message,
        error_details=task.error_details,
        retryable=task.retryable,
        duration=duration,
        folder_id=task.folder_id,  # Add folder_id
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        last_content_modified_at=task.last_content_modified_at,
    )


@router.get("/{task_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    获取任务的转写文本
    
    Args:
        task: 任务对象 (已验证所有权)
        db: 数据库会话
        
    Returns:
        TranscriptResponse: 转写文本信息（包含 speaker_mapping）
        
    Raises:
        HTTPException: 404 如果转写文本不存在
    """
    # 检查任务状态
    if task.state not in ["success", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成转写，当前状态: {task.state}",
        )
    
    # 从 transcripts 关系获取转写记录
    if not task.transcripts or len(task.transcripts) == 0:
        raise HTTPException(
            status_code=404,
            detail="转写文本不存在",
        )
    
    # 获取最新的转写记录
    transcript_record = task.transcripts[0]
    
    # 解析转写片段
    segments = []
    for seg in transcript_record.get_segments_list():
        segments.append(
            TranscriptSegment(
                text=seg.get("text", ""),
                start_time=seg.get("start_time", 0.0),
                end_time=seg.get("end_time", 0.0),
                speaker=seg.get("speaker"),
                confidence=seg.get("confidence"),
            )
        )
    
    # 构建完整文本
    full_text = transcript_record.full_text
    if not full_text and segments:
        full_text = " ".join(seg.text for seg in segments)
    
    # 获取 speaker mapping（声纹 ID -> 真实姓名）
    from src.database.repositories import SpeakerMappingRepository, SpeakerRepository
    
    speaker_mapping_repo = SpeakerMappingRepository(db)
    speaker_repo = SpeakerRepository(db)
    
    # 获取任务的 speaker mappings（Speaker 1 -> speaker_linyudong）
    task_mappings = speaker_mapping_repo.get_by_task_id(task.task_id)
    
    # 构建最终的 speaker_mapping（Speaker 1 -> 林煜东）
    speaker_mapping = {}
    for mapping in task_mappings:
        # mapping.speaker_label: "Speaker 1"
        # mapping.speaker_id: "speaker_linyudong"
        # 查询真实姓名
        display_name = speaker_repo.get_display_name(mapping.speaker_id)
        if display_name:
            speaker_mapping[mapping.speaker_label] = display_name
        else:
            # 如果没有找到真实姓名，使用 speaker_id
            speaker_mapping[mapping.speaker_label] = mapping.speaker_id
    
    return TranscriptResponse(
        task_id=task.task_id,
        segments=segments,
        full_text=full_text,
        duration=transcript_record.duration,
        language=transcript_record.language,
        provider=transcript_record.provider,
        speaker_mapping=speaker_mapping if speaker_mapping else None,
    )


@router.get("", response_model=List[TaskDetailResponse])
async def list_tasks(
    limit: int = 100,
    offset: int = 0,
    state: Optional[str] = None,
    folder_id: Optional[str] = None,
    include_deleted: bool = False,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    列出用户的任务
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
        state: 状态筛选 (pending/running/success/failed)
        folder_id: 文件夹筛选 (null 表示根目录)
        include_deleted: 是否包含已删除的任务
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        List[TaskDetailResponse]: 任务列表
    """
    # 构建查询
    query = db.query(Task).filter(Task.user_id == user_id)
    
    # 默认排除已删除的任务
    if not include_deleted:
        query = query.filter(Task.is_deleted == False)
    
    # 文件夹筛选
    if folder_id is not None:
        if folder_id == "":
            # 空字符串表示根目录（无文件夹）
            query = query.filter(Task.folder_id == None)
        else:
            query = query.filter(Task.folder_id == folder_id)
    
    # 状态筛选
    if state:
        query = query.filter(Task.state == state)
    
    # 排序和分页
    tasks = query.order_by(Task.created_at.desc()).limit(limit).offset(offset).all()
    
    # 构建响应，包含 duration
    result = []
    for task in tasks:
        # 获取音频时长（从转写记录）
        duration = None
        if task.transcripts:
            duration = task.transcripts[0].duration
        
        result.append(TaskDetailResponse(
            task_id=task.task_id,
            user_id=task.user_id,
            tenant_id=task.tenant_id,
            name=task.name,
            meeting_type=task.meeting_type,
            audio_files=task.get_audio_files_list(),
            file_order=task.get_file_order_list(),
            asr_language=task.asr_language,
            output_language=task.output_language,
            state=TaskState(task.state),
            progress=task.progress,
            error_code=task.error_code,
            error_message=task.error_message,
            error_details=task.error_details,
            retryable=task.retryable,
            duration=duration,
            folder_id=task.folder_id,  # Add folder_id
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            last_content_modified_at=task.last_content_modified_at,
        ))
    
    return result


@router.patch("/{task_id}/rename", response_model=RenameTaskResponse)
async def rename_task(
    task_id: str,
    request: RenameTaskRequest,
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    重命名任务
    
    Args:
        task_id: 任务 ID
        request: 重命名请求
        task: 任务对象 (已验证所有权)
        db: 数据库会话
        
    Returns:
        RenameTaskResponse: 重命名结果
    """
    task.name = request.name
    db.commit()
    
    logger.info(f"Task {task_id} renamed to '{request.name}' by user {task.user_id}")
    
    return RenameTaskResponse(
        success=True,
        message="任务已重命名",
    )


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task: Task = Depends(verify_task_ownership),
    db: Session = Depends(get_db),
):
    """
    删除任务
    
    Args:
        task: 任务对象 (已验证所有权)
        db: 数据库会话
    """
    task_repo = TaskRepository(db)
    task_repo.delete(task.task_id)
    
    logger.info(f"Task deleted: {task.task_id} by user {task.user_id}")


@router.post("/estimate", response_model=EstimateCostResponse)
async def estimate_cost(
    request: EstimateCostRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    预估任务成本
    
    Args:
        request: 成本预估请求
        user_id: 用户 ID (来自认证)
        
    Returns:
        EstimateCostResponse: 成本预估结果
    """
    # ASR 成本 (火山引擎单价: 0.00005 元/秒)
    asr_cost = request.audio_duration * 0.00005
    
    # 声纹识别成本 (假设平均 3 个说话人,每人 5 秒样本)
    voiceprint_cost = 0.0
    if request.enable_speaker_recognition:
        avg_speakers = 3
        sample_duration = 5
        voiceprint_cost = avg_speakers * sample_duration * 0.00003  # 0.00003 元/秒
    
    # LLM 成本 (基于预估 Token 数)
    estimated_tokens = request.audio_duration * 10  # 假设每秒 10 个 Token
    llm_cost = estimated_tokens * 0.00002  # 0.00002 元/Token
    
    total_cost = asr_cost + voiceprint_cost + llm_cost
    
    return EstimateCostResponse(
        total_cost=round(total_cost, 4),
        cost_breakdown={
            "asr": round(asr_cost, 4),
            "voiceprint": round(voiceprint_cost, 4),
            "llm": round(llm_cost, 4),
        },
    )
