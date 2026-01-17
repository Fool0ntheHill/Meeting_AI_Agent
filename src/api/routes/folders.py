# -*- coding: utf-8 -*-
"""Folder management endpoints."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_user_id, get_current_tenant_id
from src.api.schemas import (
    CreateFolderRequest,
    CreateFolderResponse,
    FolderInfo,
    ListFoldersResponse,
    UpdateFolderRequest,
    UpdateFolderResponse,
    DeleteFolderResponse,
)
from src.database.models import Folder, Task
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=ListFoldersResponse)
async def list_folders(
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    列出用户的所有文件夹
    
    返回扁平的文件夹列表（单层结构，无嵌套）
    
    Args:
        user_id: 用户 ID (来自认证)
        tenant_id: 租户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        ListFoldersResponse: 文件夹列表
    """
    folders = db.query(Folder).filter(
        Folder.owner_user_id == user_id,
        Folder.owner_tenant_id == tenant_id,
    ).order_by(Folder.created_at.desc()).all()
    
    folder_infos = [
        FolderInfo(
            folder_id=folder.folder_id,
            name=folder.name,
            parent_id=folder.parent_id,
            owner_user_id=folder.owner_user_id,
            owner_tenant_id=folder.owner_tenant_id,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
        for folder in folders
    ]
    
    return ListFoldersResponse(
        items=folder_infos,
        total=len(folder_infos),
    )


@router.post("", response_model=CreateFolderResponse, status_code=201)
async def create_folder(
    request: CreateFolderRequest,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    创建文件夹
    
    注意：文件夹为扁平结构，不支持嵌套
    
    Args:
        request: 创建文件夹请求
        user_id: 用户 ID (来自认证)
        tenant_id: 租户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        CreateFolderResponse: 创建结果
        
    Raises:
        HTTPException: 409 如果文件夹名称已存在
    """
    # 检查同名文件夹
    existing_folder = db.query(Folder).filter(
        Folder.owner_user_id == user_id,
        Folder.owner_tenant_id == tenant_id,
        Folder.name == request.name,
    ).first()
    
    if existing_folder:
        raise HTTPException(
            status_code=409,
            detail=f"文件夹名称已存在: {request.name}"
        )
    
    # 生成文件夹 ID
    folder_id = f"folder_{uuid.uuid4().hex[:16]}"
    
    # 创建文件夹（parent_id 始终为 None）
    folder = Folder(
        folder_id=folder_id,
        name=request.name,
        parent_id=None,  # 扁平结构，无父文件夹
        owner_user_id=user_id,
        owner_tenant_id=tenant_id,
    )
    
    db.add(folder)
    db.commit()
    
    logger.info(f"Folder created: {folder_id} by user {user_id}")
    
    return CreateFolderResponse(
        success=True,
        folder_id=folder_id,
        message="文件夹已创建",
    )


@router.patch("/{folder_id}", response_model=UpdateFolderResponse)
async def update_folder(
    folder_id: str,
    request: UpdateFolderRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    重命名文件夹
    
    Args:
        folder_id: 文件夹 ID
        request: 更新请求
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        UpdateFolderResponse: 更新结果
        
    Raises:
        HTTPException: 404 如果文件夹不存在
        HTTPException: 403 如果无权访问
        HTTPException: 409 如果新名称与其他文件夹重名
    """
    folder = db.query(Folder).filter(
        Folder.folder_id == folder_id
    ).first()
    
    if not folder:
        raise HTTPException(
            status_code=404,
            detail="文件夹不存在"
        )
    
    if folder.owner_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="无权访问此文件夹"
        )
    
    # 检查新名称是否与其他文件夹重名
    if request.name != folder.name:
        existing_folder = db.query(Folder).filter(
            Folder.owner_user_id == user_id,
            Folder.name == request.name,
            Folder.folder_id != folder_id,  # 排除当前文件夹
        ).first()
        
        if existing_folder:
            raise HTTPException(
                status_code=409,
                detail=f"文件夹名称已存在: {request.name}"
            )
    
    # 更新名称
    folder.name = request.name
    db.commit()
    
    logger.info(f"Folder updated: {folder_id} by user {user_id}")
    
    return UpdateFolderResponse(
        success=True,
        message="文件夹已更新",
    )


@router.delete("/{folder_id}", response_model=DeleteFolderResponse)
async def delete_folder(
    folder_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    删除文件夹
    
    删除文件夹时，该文件夹下的所有会话会被移到"无文件夹"状态（folder_id=NULL）
    
    Args:
        folder_id: 文件夹 ID
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        DeleteFolderResponse: 删除结果
        
    Raises:
        HTTPException: 404 如果文件夹不存在
        HTTPException: 403 如果无权访问
    """
    folder = db.query(Folder).filter(
        Folder.folder_id == folder_id
    ).first()
    
    if not folder:
        raise HTTPException(
            status_code=404,
            detail="文件夹不存在"
        )
    
    if folder.owner_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="无权访问此文件夹"
        )
    
    # 将该文件夹下的所有会话移到"无文件夹"状态
    tasks_in_folder = db.query(Task).filter(
        Task.folder_id == folder_id
    ).all()
    
    for task in tasks_in_folder:
        task.folder_id = None
    
    logger.info(f"Moved {len(tasks_in_folder)} tasks out of folder {folder_id}")
    
    # 删除文件夹
    db.delete(folder)
    db.commit()
    
    logger.info(f"Folder deleted: {folder_id} by user {user_id}")
    
    return DeleteFolderResponse(
        success=True,
        message=f"文件夹已删除，{len(tasks_in_folder)} 个会话已移至根目录",
    )
