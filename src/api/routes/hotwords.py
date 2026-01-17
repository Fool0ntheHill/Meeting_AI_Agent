# -*- coding: utf-8 -*-
"""Hotword set management endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_user_id
from src.api.schemas import (
    CreateHotwordSetResponse,
    DeleteHotwordSetResponse,
    HotwordSetInfo,
    ListHotwordSetsResponse,
    UpdateHotwordSetResponse,
)
from src.config.loader import get_config
from src.database.repositories import HotwordSetRepository
from src.providers.volcano_hotword import VolcanoHotwordClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_volcano_client() -> VolcanoHotwordClient:
    """获取火山引擎热词客户端"""
    config = get_config()
    return VolcanoHotwordClient(
        app_id=str(config.volcano.app_id),
        access_key=config.volcano.access_key,
        secret_key=config.volcano.secret_key,
    )


@router.post("", response_model=CreateHotwordSetResponse, status_code=201)
async def create_hotword_set(
    name: str = Form(..., description="热词集名称"),
    scope: str = Form(..., description="作用域 (global/tenant/user)"),
    asr_language: str = Form(..., description="ASR 语言"),
    hotwords_file: UploadFile = File(..., description="热词文件 (TXT 格式,每行一个热词)"),
    scope_id: Optional[str] = Form(None, description="作用域 ID"),
    description: Optional[str] = Form(None, description="描述"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    创建热词集
    
    功能:
    1. 验证作用域(global/tenant/user)
    2. 读取热词文件内容
    3. 调用火山引擎 API 创建热词库
    4. 获取 BoostingTableID
    5. 保存到数据库
    
    Args:
        name: 热词集名称
        scope: 作用域
        asr_language: ASR 语言
        hotwords_file: 热词文件
        scope_id: 作用域 ID
        description: 描述
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        CreateHotwordSetResponse: 创建响应
        
    Raises:
        HTTPException: 400 如果参数无效
        HTTPException: 500 如果火山 API 调用失败
    """
    # 验证作用域
    valid_scopes = ["global", "tenant", "user"]
    if scope not in valid_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"无效的作用域: {scope},有效值: {valid_scopes}",
        )
    
    # 验证作用域 ID
    if scope in ["tenant", "user"] and not scope_id:
        raise HTTPException(
            status_code=400,
            detail=f"作用域为 {scope} 时必须提供 scope_id",
        )
    
    # 读取热词文件
    try:
        hotwords_content = await hotwords_file.read()
        hotwords_text = hotwords_content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取热词文件失败: {str(e)}")
    
    logger.info(f"Creating hotword set: {name} (scope={scope}, {len(hotwords_text)} bytes)")
    
    # 调用火山引擎 API 创建热词库
    try:
        volcano_client = get_volcano_client()
        result = volcano_client.create_boosting_table(
            name=name,
            hotwords_content=hotwords_text,
        )
        
        boosting_table_id = result.get("BoostingTableID")
        word_count = result.get("WordCount", 0)
        word_size = result.get("WordSize", 0)
        
        logger.info(
            f"Boosting table created: {boosting_table_id} "
            f"(words={word_count}, size={word_size})"
        )
        
    except Exception as e:
        logger.error(f"Failed to create boosting table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建热词库失败: {str(e)}")
    
    # 生成热词集 ID
    hotword_set_id = f"hs_{uuid.uuid4().hex[:16]}"
    
    # 保存到数据库
    hotword_repo = HotwordSetRepository(db)
    hotword_repo.create(
        hotword_set_id=hotword_set_id,
        name=name,
        provider="volcano",
        provider_resource_id=boosting_table_id,
        scope=scope,
        scope_id=scope_id,
        asr_language=asr_language,
        description=description,
        word_count=word_count,
        word_size=word_size,
    )
    
    db.commit()
    
    logger.info(f"Hotword set created: {hotword_set_id}")
    
    return CreateHotwordSetResponse(
        success=True,
        hotword_set_id=hotword_set_id,
        boosting_table_id=boosting_table_id,
        word_count=word_count,
        message="热词集已创建",
    )


@router.get("", response_model=ListHotwordSetsResponse)
async def list_hotword_sets(
    scope: Optional[str] = Query(None, description="作用域过滤 (global/tenant/user)"),
    scope_id: Optional[str] = Query(None, description="作用域 ID 过滤"),
    provider: Optional[str] = Query(None, description="提供商过滤 (volcano/azure)"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    列出热词集
    
    功能:
    1. 支持按作用域过滤
    2. 支持按提供商过滤
    3. 支持分页
    
    Args:
        scope: 作用域过滤
        scope_id: 作用域 ID 过滤
        provider: 提供商过滤
        limit: 返回数量限制
        offset: 偏移量
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        ListHotwordSetsResponse: 热词集列表
    """
    hotword_repo = HotwordSetRepository(db)
    
    # 根据过滤条件查询
    if scope:
        hotword_sets = hotword_repo.get_by_scope(
            scope=scope,
            scope_id=scope_id,
            provider=provider,
        )
    else:
        hotword_sets = hotword_repo.get_all(
            provider=provider,
            limit=limit,
            offset=offset,
        )
    
    # 转换为响应格式
    hotword_set_infos = [
        HotwordSetInfo(
            hotword_set_id=hs.hotword_set_id,
            name=hs.name,
            provider=hs.provider,
            provider_resource_id=hs.provider_resource_id,
            scope=hs.scope,
            scope_id=hs.scope_id,
            asr_language=hs.asr_language,
            description=hs.description,
            word_count=hs.word_count,
            word_size=hs.word_size,
            created_at=hs.created_at,
            updated_at=hs.updated_at,
        )
        for hs in hotword_sets
    ]
    
    logger.info(f"Listed {len(hotword_set_infos)} hotword sets")
    
    return ListHotwordSetsResponse(
        hotword_sets=hotword_set_infos,
        total=len(hotword_set_infos),
    )


@router.get("/{hotword_set_id}", response_model=HotwordSetInfo)
async def get_hotword_set(
    hotword_set_id: str,
    include_preview: bool = Query(False, description="是否包含热词预览"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    获取热词集详情
    
    Args:
        hotword_set_id: 热词集 ID
        include_preview: 是否包含热词预览
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        HotwordSetInfo: 热词集信息
        
    Raises:
        HTTPException: 404 如果热词集不存在
    """
    hotword_repo = HotwordSetRepository(db)
    hotword_set = hotword_repo.get_by_id(hotword_set_id)
    
    if not hotword_set:
        raise HTTPException(status_code=404, detail="热词集不存在")
    
    preview = None
    if include_preview and hotword_set.provider == "volcano":
        try:
            volcano_client = get_volcano_client()
            result = volcano_client.get_boosting_table(hotword_set.provider_resource_id)
            preview = result.get("Preview", [])
        except Exception as e:
            logger.warning(f"Failed to get preview: {str(e)}")
    
    return HotwordSetInfo(
        hotword_set_id=hotword_set.hotword_set_id,
        name=hotword_set.name,
        provider=hotword_set.provider,
        provider_resource_id=hotword_set.provider_resource_id,
        scope=hotword_set.scope,
        scope_id=hotword_set.scope_id,
        asr_language=hotword_set.asr_language,
        description=hotword_set.description,
        word_count=hotword_set.word_count,
        word_size=hotword_set.word_size,
        preview=preview,
        created_at=hotword_set.created_at,
        updated_at=hotword_set.updated_at,
    )


@router.put("/{hotword_set_id}", response_model=UpdateHotwordSetResponse)
async def update_hotword_set(
    hotword_set_id: str,
    name: Optional[str] = Form(None, description="新名称"),
    description: Optional[str] = Form(None, description="新描述"),
    hotwords_file: Optional[UploadFile] = File(None, description="新热词文件"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    更新热词集
    
    功能:
    1. 验证热词集存在
    2. 如果提供了热词文件,调用火山 API 更新
    3. 更新数据库记录
    
    Args:
        hotword_set_id: 热词集 ID
        name: 新名称
        description: 新描述
        hotwords_file: 新热词文件
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        UpdateHotwordSetResponse: 更新响应
        
    Raises:
        HTTPException: 404 如果热词集不存在
        HTTPException: 500 如果火山 API 调用失败
    """
    hotword_repo = HotwordSetRepository(db)
    hotword_set = hotword_repo.get_by_id(hotword_set_id)
    
    if not hotword_set:
        raise HTTPException(status_code=404, detail="热词集不存在")
    
    word_count = hotword_set.word_count
    word_size = hotword_set.word_size
    
    # 如果提供了热词文件,更新火山引擎热词库
    if hotwords_file:
        try:
            hotwords_content = await hotwords_file.read()
            hotwords_text = hotwords_content.decode("utf-8")
            
            volcano_client = get_volcano_client()
            result = volcano_client.update_boosting_table(
                boosting_table_id=hotword_set.provider_resource_id,
                name=name,
                hotwords_content=hotwords_text,
            )
            
            word_count = result.get("WordCount", word_count)
            word_size = result.get("WordSize", word_size)
            
            logger.info(f"Boosting table updated: {hotword_set.provider_resource_id}")
            
        except Exception as e:
            logger.error(f"Failed to update boosting table: {str(e)}")
            raise HTTPException(status_code=500, detail=f"更新热词库失败: {str(e)}")
    
    # 更新数据库记录
    hotword_repo.update(
        hotword_set_id=hotword_set_id,
        name=name,
        description=description,
        word_count=word_count,
        word_size=word_size,
    )
    
    db.commit()
    
    logger.info(f"Hotword set updated: {hotword_set_id}")
    
    return UpdateHotwordSetResponse(
        success=True,
        word_count=word_count or 0,
        message="热词集已更新",
    )


@router.delete("/{hotword_set_id}", response_model=DeleteHotwordSetResponse)
async def delete_hotword_set(
    hotword_set_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    删除热词集
    
    功能:
    1. 验证热词集存在
    2. 调用火山 API 删除热词库
    3. 删除数据库记录
    
    Args:
        hotword_set_id: 热词集 ID
        user_id: 用户 ID (来自认证)
        db: 数据库会话
        
    Returns:
        DeleteHotwordSetResponse: 删除响应
        
    Raises:
        HTTPException: 404 如果热词集不存在
        HTTPException: 500 如果火山 API 调用失败
    """
    hotword_repo = HotwordSetRepository(db)
    
    # 验证热词集存在
    hotword_set = hotword_repo.get_by_id(hotword_set_id)
    if not hotword_set:
        raise HTTPException(status_code=404, detail="热词集不存在")
    
    logger.info(f"Deleting hotword set: {hotword_set_id}")
    
    # 调用火山 API 删除热词库
    if hotword_set.provider == "volcano":
        try:
            volcano_client = get_volcano_client()
            volcano_client.delete_boosting_table(hotword_set.provider_resource_id)
            logger.info(f"Boosting table deleted: {hotword_set.provider_resource_id}")
        except Exception as e:
            logger.error(f"Failed to delete boosting table: {str(e)}")
            # 继续删除数据库记录,即使火山 API 调用失败
            logger.warning("Continuing to delete database record despite API failure")
    
    # 删除数据库记录
    hotword_repo.delete(hotword_set_id)
    db.commit()
    
    logger.info(f"Hotword set deleted: {hotword_set_id}")
    
    return DeleteHotwordSetResponse(
        success=True,
        message="热词集已删除",
    )
