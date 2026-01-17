# -*- coding: utf-8 -*-
"""Trash and session movement endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_user_id, get_current_tenant_id
from src.api.schemas import (
    MoveSessionRequest,
    MoveSessionResponse,
    DeleteSessionResponse,
    RestoreSessionResponse,
    PermanentDeleteSessionResponse,
    TrashSessionInfo,
    ListTrashSessionsResponse,
    BatchMoveSessionsRequest,
    BatchMoveSessionsResponse,
    BatchDeleteSessionsRequest,
    BatchDeleteSessionsResponse,
    BatchRestoreSessionsRequest,
    BatchRestoreSessionsResponse,
)
from src.database.models import Task, Folder
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.patch("/sessions/{task_id}/move", response_model=MoveSessionResponse)
async def move_session(
    task_id: str,
    request: MoveSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    移动会话到文件夹
    
    Args:
        task_id: 任务 ID
        request: 移动请求
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        MoveSessionResponse: 移动结果
        
    Raises:
        HTTPException: 404 如果任务或文件夹不存在
        HTTPException: 403 如果无权访问
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 验证目标文件夹
    if request.folder_id:
        folder = db.query(Folder).filter(
            Folder.folder_id == request.folder_id
        ).first()
        
        if not folder:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")
        
        if folder.owner_user_id != user_id:
            raise HTTPException(status_code=403, detail="无权访问目标文件夹")
    
    # 移动任务
    task.folder_id = request.folder_id
    db.commit()
    
    logger.info(f"Task {task_id} moved to folder {request.folder_id} by user {user_id}")
    
    return MoveSessionResponse(
        success=True,
        message="会话已移动",
    )


@router.patch("/sessions/{task_id}/delete", response_model=DeleteSessionResponse)
async def delete_session(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    软删除会话（移入回收站）
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        DeleteSessionResponse: 删除结果
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 软删除
    task.is_deleted = True
    task.deleted_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Task {task_id} soft deleted by user {user_id}")
    
    return DeleteSessionResponse(
        success=True,
        message="会话已移至回收站",
    )


@router.patch("/sessions/{task_id}/restore", response_model=RestoreSessionResponse)
async def restore_session(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    还原会话
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        RestoreSessionResponse: 还原结果
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 还原
    task.is_deleted = False
    task.deleted_at = None
    db.commit()
    
    logger.info(f"Task {task_id} restored by user {user_id}")
    
    return RestoreSessionResponse(
        success=True,
        message="会话已还原",
    )


@router.delete("/sessions/{task_id}", response_model=PermanentDeleteSessionResponse)
async def permanent_delete_session(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    彻底删除会话
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        PermanentDeleteSessionResponse: 删除结果
        
    Raises:
        HTTPException: 404 如果任务不存在
        HTTPException: 403 如果无权访问
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 彻底删除
    db.delete(task)
    db.commit()
    
    logger.info(f"Task {task_id} permanently deleted by user {user_id}")
    
    return PermanentDeleteSessionResponse(
        success=True,
        message="会话已彻底删除",
    )


@router.get("/trash/sessions", response_model=ListTrashSessionsResponse)
async def list_trash_sessions(
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    列出回收站中的会话
    
    Args:
        user_id: 用户 ID (来自认证)
        tenant_id: 租户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        ListTrashSessionsResponse: 回收站会话列表
    """
    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.tenant_id == tenant_id,
        Task.is_deleted == True,
    ).order_by(Task.deleted_at.desc()).all()
    
    trash_items = []
    for task in tasks:
        # 获取音频时长（从转写记录）
        duration = None
        if task.transcripts:
            duration = task.transcripts[0].duration
        
        trash_items.append(TrashSessionInfo(
            task_id=task.task_id,
            user_id=task.user_id,
            tenant_id=task.tenant_id,
            meeting_type=task.meeting_type,
            folder_id=task.folder_id,
            duration=duration,
            last_content_modified_at=task.last_content_modified_at,
            deleted_at=task.deleted_at,
            created_at=task.created_at,
        ))
    
    return ListTrashSessionsResponse(
        items=trash_items,
        total=len(trash_items),
    )


# ============================================================================
# Batch Operations
# ============================================================================


@router.post("/sessions/batch-move", response_model=BatchMoveSessionsResponse)
async def batch_move_sessions(
    request: BatchMoveSessionsRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    批量移动会话
    
    Args:
        request: 批量移动请求
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        BatchMoveSessionsResponse: 批量移动结果
    """
    # 验证目标文件夹
    if request.folder_id:
        folder = db.query(Folder).filter(
            Folder.folder_id == request.folder_id
        ).first()
        
        if not folder:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")
        
        if folder.owner_user_id != user_id:
            raise HTTPException(status_code=403, detail="无权访问目标文件夹")
    
    # 批量移动
    moved_count = 0
    for task_id in request.task_ids:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        
        if task and task.user_id == user_id:
            task.folder_id = request.folder_id
            moved_count += 1
    
    db.commit()
    
    logger.info(f"Batch moved {moved_count} tasks to folder {request.folder_id} by user {user_id}")
    
    return BatchMoveSessionsResponse(
        success=True,
        moved_count=moved_count,
        message=f"已移动 {moved_count} 个会话",
    )


@router.post("/sessions/batch-delete", response_model=BatchDeleteSessionsResponse)
async def batch_delete_sessions(
    request: BatchDeleteSessionsRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    批量软删除会话
    
    Args:
        request: 批量删除请求
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        BatchDeleteSessionsResponse: 批量删除结果
    """
    deleted_count = 0
    for task_id in request.task_ids:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        
        if task and task.user_id == user_id:
            task.is_deleted = True
            task.deleted_at = datetime.utcnow()
            deleted_count += 1
    
    db.commit()
    
    logger.info(f"Batch deleted {deleted_count} tasks by user {user_id}")
    
    return BatchDeleteSessionsResponse(
        success=True,
        deleted_count=deleted_count,
        message=f"已删除 {deleted_count} 个会话",
    )


@router.post("/sessions/batch-restore", response_model=BatchRestoreSessionsResponse)
async def batch_restore_sessions(
    request: BatchRestoreSessionsRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    批量还原会话
    
    Args:
        request: 批量还原请求
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        BatchRestoreSessionsResponse: 批量还原结果
    """
    restored_count = 0
    for task_id in request.task_ids:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        
        if task and task.user_id == user_id:
            task.is_deleted = False
            task.deleted_at = None
            restored_count += 1
    
    db.commit()
    
    logger.info(f"Batch restored {restored_count} tasks by user {user_id}")
    
    return BatchRestoreSessionsResponse(
        success=True,
        restored_count=restored_count,
        message=f"已还原 {restored_count} 个会话",
    )
