# -*- coding: utf-8 -*-
"""文件上传 API 路由"""

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_user_id
from src.utils.logger import get_logger
from src.utils.audio import AudioProcessor

logger = get_logger(__name__)

router = APIRouter()

# 上传目录配置
UPLOAD_BASE_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".wav", ".opus", ".mp3", ".m4a", ".ogg"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    file_path: str
    original_filename: str  # 原始文件名
    file_size: int
    duration: Optional[float] = None
    message: str = "文件上传成功"


def ensure_upload_dir(user_id: str) -> Path:
    """确保用户上传目录存在"""
    user_dir = UPLOAD_BASE_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def validate_file(file: UploadFile) -> None:
    """验证文件"""
    # 验证文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件格式: {file_ext}，支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_audio(
    file: UploadFile = File(..., description="音频文件"),
    user_id: str = Depends(get_current_user_id),
):
    """
    上传音频文件到服务器
    
    支持的格式: .wav, .opus, .mp3, .m4a, .ogg
    最大文件大小: 500MB
    
    Args:
        file: 上传的音频文件
        user_id: 用户 ID (来自认证)
        
    Returns:
        UploadResponse: 上传结果
        
    Raises:
        HTTPException: 415 不支持的文件格式
        HTTPException: 413 文件过大
        HTTPException: 500 上传失败
    """
    try:
        # 验证文件
        validate_file(file)
        
        # 读取文件内容
        content = await file.read()
        file_size = len(content)
        
        # 验证文件大小
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {file_size / 1024 / 1024:.2f}MB，最大支持 500MB"
            )
        
        # 确保上传目录存在
        user_dir = ensure_upload_dir(user_id)
        
        # 生成唯一文件名
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4().hex[:16]}{file_ext}"
        file_path = user_dir / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File uploaded: {file_path} ({file_size} bytes) by user {user_id}")
        
        # 尝试获取音频时长
        duration = None
        try:
            audio_processor = AudioProcessor()
            duration = audio_processor.get_duration(str(file_path))
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
        
        # 返回相对路径（用于后续 API 调用）
        # 使用正斜杠以保持跨平台兼容性
        relative_path = str(file_path).replace("\\", "/")
        
        return UploadResponse(
            success=True,
            file_path=relative_path,
            original_filename=file.filename,  # 保存原始文件名
            file_size=file_size,
            duration=duration,
            message=f"文件上传成功: {file.filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )


@router.delete("/{file_path:path}", status_code=204)
async def delete_uploaded_file(
    file_path: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    删除已上传的文件
    
    Args:
        file_path: 文件路径
        user_id: 用户 ID (来自认证)
        
    Raises:
        HTTPException: 403 无权删除
        HTTPException: 404 文件不存在
    """
    try:
        # 验证文件路径属于当前用户
        full_path = Path(file_path)
        if not str(full_path).startswith(f"uploads/{user_id}/"):
            raise HTTPException(
                status_code=403,
                detail="无权删除此文件"
            )
        
        # 检查文件是否存在
        if not full_path.exists():
            raise HTTPException(
                status_code=404,
                detail="文件不存在"
            )
        
        # 删除文件
        full_path.unlink()
        
        logger.info(f"File deleted: {file_path} by user {user_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"文件删除失败: {str(e)}"
        )
