# -*- coding: utf-8 -*-
"""API request and response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.models import (
    GeneratedArtifact,
    PromptInstance,
    PromptTemplate,
    TaskState,
)


# ============================================================================
# Task Management Schemas
# ============================================================================


class CreateTaskRequest(BaseModel):
    """创建任务请求"""

    audio_files: List[str] = Field(..., min_length=1, description="音频文件 URL 列表")
    file_order: Optional[List[int]] = Field(None, description="文件排序索引")
    meeting_type: str = Field(..., description="会议类型")
    asr_language: str = Field(default="zh-CN+en-US", description="ASR 识别语言")
    output_language: str = Field(default="zh-CN", description="输出语言")
    prompt_instance: Optional[PromptInstance] = Field(None, description="提示词实例")
    skip_speaker_recognition: bool = Field(default=False, description="跳过说话人识别")

    model_config = {
        "json_schema_extra": {
            "example": {
                "audio_files": ["https://tos.example.com/meeting.wav"],
                "file_order": [0],
                "meeting_type": "weekly_sync",
                "asr_language": "zh-CN+en-US",
                "output_language": "zh-CN",
                "prompt_instance": {
                    "template_id": "tpl_001",
                    "language": "zh-CN",
                    "parameters": {"meeting_description": "产品规划会议"},
                },
                "skip_speaker_recognition": False,
            }
        }
    }


class CreateTaskResponse(BaseModel):
    """创建任务响应"""

    success: bool
    task_id: str
    message: str = "任务已创建"


class TaskStatusResponse(BaseModel):
    """任务状态响应"""

    task_id: str
    state: TaskState
    progress: float = Field(..., ge=0, le=100, description="进度百分比")
    estimated_time: Optional[int] = Field(None, description="预计剩余时间(秒)")
    error_details: Optional[str] = None
    updated_at: datetime


class TaskDetailResponse(BaseModel):
    """任务详情响应"""

    task_id: str
    user_id: str
    tenant_id: str
    name: Optional[str] = Field(None, description="任务名称")
    meeting_type: str
    audio_files: List[str]
    file_order: List[int]
    asr_language: str
    output_language: str
    state: TaskState
    progress: float
    error_details: Optional[str] = None
    duration: Optional[float] = Field(None, description="音频总时长(秒)")
    folder_id: Optional[str] = Field(None, description="所属文件夹ID")
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    last_content_modified_at: Optional[datetime] = Field(None, description="内容最后修改时间")


class RenameTaskRequest(BaseModel):
    """重命名任务请求"""

    name: str = Field(..., min_length=1, max_length=255, description="新名称")


class RenameTaskResponse(BaseModel):
    """重命名任务响应"""

    success: bool
    message: str = "任务已重命名"


# ============================================================================
# Cost Estimation Schemas
# ============================================================================


class EstimateCostRequest(BaseModel):
    """成本预估请求"""

    audio_duration: float = Field(..., gt=0, description="音频时长(秒)")
    meeting_type: str = Field(..., description="会议类型")
    enable_speaker_recognition: bool = Field(default=True, description="是否启用说话人识别")


class EstimateCostResponse(BaseModel):
    """成本预估响应"""

    total_cost: float = Field(..., description="总成本(元)")
    cost_breakdown: Dict[str, float] = Field(..., description="成本拆分")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_cost": 0.85,
                "cost_breakdown": {"asr": 0.30, "voiceprint": 0.15, "llm": 0.40},
            }
        }
    }


# ============================================================================
# Transcript Correction Schemas
# ============================================================================


class CorrectTranscriptRequest(BaseModel):
    """修正转写文本请求"""

    corrected_text: str = Field(..., description="修正后的完整文本")
    regenerate_artifacts: bool = Field(default=True, description="是否重新生成衍生内容")

    model_config = {
        "json_schema_extra": {
            "example": {
                "corrected_text": "修正后的会议转写文本...",
                "regenerate_artifacts": True,
            }
        }
    }


class CorrectTranscriptResponse(BaseModel):
    """修正转写文本响应"""

    success: bool
    message: str = "转写文本已修正"
    regenerated_artifacts: Optional[List[str]] = Field(None, description="重新生成的衍生内容 ID 列表")


class CorrectSpeakersRequest(BaseModel):
    """修正说话人映射请求"""

    speaker_mapping: Dict[str, str] = Field(..., description="说话人标签映射 (原标签 -> 新名称)")
    regenerate_artifacts: bool = Field(default=True, description="是否重新生成衍生内容")

    model_config = {
        "json_schema_extra": {
            "example": {
                "speaker_mapping": {"Speaker 0": "张三", "Speaker 1": "李四"},
                "regenerate_artifacts": True,
            }
        }
    }


class CorrectSpeakersResponse(BaseModel):
    """修正说话人映射响应"""

    success: bool
    message: str = "说话人映射已修正"
    regenerated_artifacts: Optional[List[str]] = Field(None, description="重新生成的衍生内容 ID 列表")


# ============================================================================
# Artifact Management Schemas
# ============================================================================


class GenerateArtifactRequest(BaseModel):
    """生成衍生内容请求"""

    prompt_instance: PromptInstance = Field(..., description="提示词实例")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt_instance": {
                    "template_id": "tpl_001",
                    "language": "zh-CN",
                    "parameters": {"meeting_description": "产品规划会议"},
                }
            }
        }
    }


class GenerateArtifactResponse(BaseModel):
    """生成衍生内容响应"""

    success: bool
    artifact_id: str
    version: int
    content: Dict
    message: str = "内容已生成"


class ListArtifactsResponse(BaseModel):
    """列出衍生内容响应(按类型分组)"""

    task_id: str = Field(..., description="任务 ID")
    artifacts_by_type: Dict[str, List["ArtifactInfo"]] = Field(..., description="按类型分组的衍生内容")
    total_count: int = Field(..., description="总数量")


class ArtifactInfo(BaseModel):
    """衍生内容基本信息"""

    artifact_id: str
    task_id: str
    artifact_type: str
    version: int
    prompt_instance: PromptInstance
    created_at: datetime
    created_by: str


class ListArtifactVersionsResponse(BaseModel):
    """列出特定类型的所有版本响应"""

    task_id: str = Field(..., description="任务 ID")
    artifact_type: str = Field(..., description="衍生内容类型")
    versions: List[ArtifactInfo] = Field(..., description="版本列表")
    total_count: int = Field(..., description="版本总数")


class ArtifactDetailResponse(BaseModel):
    """衍生内容详情响应"""

    artifact: GeneratedArtifact = Field(..., description="完整的衍生内容")


# ============================================================================
# Prompt Template Schemas
# ============================================================================


class ListPromptTemplatesResponse(BaseModel):
    """列出提示词模板响应"""

    templates: List[PromptTemplate] = Field(..., description="提示词模板列表")


class PromptTemplateDetailResponse(BaseModel):
    """提示词模板详情响应"""

    template: PromptTemplate


class CreatePromptTemplateRequest(BaseModel):
    """创建提示词模板请求"""

    title: str = Field(..., description="模板标题")
    description: Optional[str] = Field(None, description="模板描述")
    prompt_body: str = Field(..., description="提示词正文(含占位符)")
    artifact_type: str = Field(..., description="生成内容类型")
    supported_languages: List[str] = Field(default=["zh-CN"], description="支持的语言列表")
    parameter_schema: Dict[str, Any] = Field(..., description="参数定义")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "我的自定义会议纪要模板",
                "description": "适用于技术团队的会议纪要",
                "prompt_body": "你是一个专业的会议纪要助手。\n\n会议信息:\n{meeting_description}\n\n请生成技术导向的会议纪要...",
                "artifact_type": "meeting_minutes",
                "supported_languages": ["zh-CN", "en-US"],
                "parameter_schema": {
                    "meeting_description": {
                        "type": "string",
                        "required": False,
                        "default": "",
                        "description": "会议描述信息",
                    }
                },
            }
        }
    }


class CreatePromptTemplateResponse(BaseModel):
    """创建提示词模板响应"""

    success: bool
    template_id: str
    message: str = "提示词模板已创建"


class UpdatePromptTemplateRequest(BaseModel):
    """更新提示词模板请求"""

    title: Optional[str] = Field(None, description="模板标题")
    description: Optional[str] = Field(None, description="模板描述")
    prompt_body: Optional[str] = Field(None, description="提示词正文")
    supported_languages: Optional[List[str]] = Field(None, description="支持的语言列表")
    parameter_schema: Optional[Dict[str, Any]] = Field(None, description="参数定义")


class UpdatePromptTemplateResponse(BaseModel):
    """更新提示词模板响应"""

    success: bool
    message: str = "提示词模板已更新"


class DeletePromptTemplateResponse(BaseModel):
    """删除提示词模板响应"""

    success: bool
    message: str = "提示词模板已删除"


# ============================================================================
# Folder Management Schemas
# ============================================================================


class CreateFolderRequest(BaseModel):
    """创建文件夹请求"""

    name: str = Field(..., min_length=1, max_length=256, description="文件夹名称")
    # 注意：文件夹为扁平结构，不支持嵌套

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "项目A",
            }
        }
    }


class CreateFolderResponse(BaseModel):
    """创建文件夹响应"""

    success: bool
    folder_id: str
    message: str = "文件夹已创建"


class FolderInfo(BaseModel):
    """文件夹信息"""

    folder_id: str
    name: str
    parent_id: Optional[str]
    owner_user_id: str
    owner_tenant_id: str
    created_at: datetime
    updated_at: datetime


class ListFoldersResponse(BaseModel):
    """列出文件夹响应"""

    items: List[FolderInfo]
    total: int


class UpdateFolderRequest(BaseModel):
    """更新文件夹请求"""

    name: str = Field(..., min_length=1, max_length=256, description="新文件夹名称")


class UpdateFolderResponse(BaseModel):
    """更新文件夹响应"""

    success: bool
    message: str = "文件夹已更新"


class DeleteFolderResponse(BaseModel):
    """删除文件夹响应"""

    success: bool
    message: str = "文件夹已删除"


# ============================================================================
# Session/Task Movement and Trash Schemas
# ============================================================================


class MoveSessionRequest(BaseModel):
    """移动会话请求"""

    folder_id: Optional[str] = Field(None, description="目标文件夹 ID (null 表示移到根目录)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "folder_id": "folder_abc123",
            }
        }
    }


class MoveSessionResponse(BaseModel):
    """移动会话响应"""

    success: bool
    message: str = "会话已移动"


class DeleteSessionResponse(BaseModel):
    """软删除会话响应"""

    success: bool
    message: str = "会话已移至回收站"


class RestoreSessionResponse(BaseModel):
    """还原会话响应"""

    success: bool
    message: str = "会话已还原"


class PermanentDeleteSessionResponse(BaseModel):
    """彻底删除会话响应"""

    success: bool
    message: str = "会话已彻底删除"


class TrashSessionInfo(BaseModel):
    """回收站会话信息"""

    task_id: str
    user_id: str
    tenant_id: str
    meeting_type: str
    folder_id: Optional[str]
    duration: Optional[float] = Field(None, description="音频总时长(秒)")
    last_content_modified_at: Optional[datetime] = Field(None, description="内容最后修改时间")
    deleted_at: datetime
    created_at: datetime


class ListTrashSessionsResponse(BaseModel):
    """列出回收站会话响应"""

    items: List[TrashSessionInfo]
    total: int


class BatchMoveSessionsRequest(BaseModel):
    """批量移动会话请求"""

    task_ids: List[str] = Field(..., min_length=1, description="任务 ID 列表")
    folder_id: Optional[str] = Field(None, description="目标文件夹 ID")


class BatchMoveSessionsResponse(BaseModel):
    """批量移动会话响应"""

    success: bool
    moved_count: int
    message: str = "批量移动完成"


class BatchDeleteSessionsRequest(BaseModel):
    """批量删除会话请求"""

    task_ids: List[str] = Field(..., min_length=1, description="任务 ID 列表")


class BatchDeleteSessionsResponse(BaseModel):
    """批量删除会话响应"""

    success: bool
    deleted_count: int
    message: str = "批量删除完成"


class BatchRestoreSessionsRequest(BaseModel):
    """批量还原会话请求"""

    task_ids: List[str] = Field(..., min_length=1, description="任务 ID 列表")


class BatchRestoreSessionsResponse(BaseModel):
    """批量还原会话响应"""

    success: bool
    restored_count: int
    message: str = "批量还原完成"


# ============================================================================
# Error Response Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict] = Field(None, description="错误详情")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "validation_error",
                "message": "请求参数验证失败",
                "details": {"field": "audio_files", "issue": "不能为空"},
            }
        }
    }


# ============================================================================
# Health Check Schemas
# ============================================================================


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
    timestamp: datetime = Field(..., description="检查时间")
    dependencies: Dict[str, str] = Field(..., description="依赖服务状态")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2026-01-14T10:00:00Z",
                "dependencies": {
                    "database": "healthy",
                    "redis": "healthy",
                    "volcano_asr": "healthy",
                },
            }
        }
    }


# ============================================================================
# Hotword Set Management Schemas
# ============================================================================


class CreateHotwordSetRequest(BaseModel):
    """创建热词集请求"""

    name: str = Field(..., min_length=1, max_length=256, description="热词集名称")
    scope: str = Field(..., description="作用域 (global/tenant/user)")
    scope_id: Optional[str] = Field(None, description="作用域 ID (tenant_id 或 user_id)")
    asr_language: str = Field(..., description="ASR 语言 (zh-CN, en-US, zh-CN+en-US)")
    description: Optional[str] = Field(None, description="描述")
    # 注意: hotwords_file 通过 FastAPI 的 File 上传,不在这里定义

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "医疗术语热词库",
                "scope": "tenant",
                "scope_id": "tenant_001",
                "asr_language": "zh-CN",
                "description": "包含常用医疗术语的热词库",
            }
        }
    }


class CreateHotwordSetResponse(BaseModel):
    """创建热词集响应"""

    success: bool
    hotword_set_id: str
    boosting_table_id: str
    word_count: int
    message: str = "热词集已创建"


class HotwordSetInfo(BaseModel):
    """热词集信息"""

    hotword_set_id: str
    name: str
    provider: str
    provider_resource_id: str
    scope: str
    scope_id: Optional[str]
    asr_language: str
    description: Optional[str]
    word_count: Optional[int] = None
    word_size: Optional[int] = None
    preview: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


class ListHotwordSetsResponse(BaseModel):
    """列出热词集响应"""

    hotword_sets: List[HotwordSetInfo]
    total: int


class DeleteHotwordSetResponse(BaseModel):
    """删除热词集响应"""

    success: bool
    message: str = "热词集已删除"


class UpdateHotwordSetRequest(BaseModel):
    """更新热词集请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=256, description="新名称")
    description: Optional[str] = Field(None, description="新描述")
    # 注意: hotwords_file 通过 FastAPI 的 File 上传,不在这里定义


class UpdateHotwordSetResponse(BaseModel):
    """更新热词集响应"""

    success: bool
    word_count: int
    message: str = "热词集已更新"


# ============================================================================
# Transcript Schemas
# ============================================================================


class TranscriptSegment(BaseModel):
    """转写片段"""

    text: str = Field(..., description="文本内容")
    start_time: float = Field(..., description="开始时间(秒)")
    end_time: float = Field(..., description="结束时间(秒)")
    speaker: Optional[str] = Field(None, description="说话人")
    confidence: Optional[float] = Field(None, description="置信度")


class TranscriptResponse(BaseModel):
    """转写文本响应"""

    task_id: str = Field(..., description="任务 ID")
    segments: List[TranscriptSegment] = Field(..., description="转写片段列表")
    full_text: str = Field(..., description="完整文本")
    duration: float = Field(..., description="音频时长(秒)")
    language: str = Field(..., description="识别语言")
    provider: str = Field(..., description="ASR 提供商")
    speaker_mapping: Optional[Dict[str, str]] = Field(None, description="说话人映射（Speaker 1 -> 真实姓名）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "task_abc123",
                "segments": [
                    {
                        "text": "大家好",
                        "start_time": 0.0,
                        "end_time": 1.5,
                        "speaker": "张三",
                        "confidence": 0.95,
                    }
                ],
                "full_text": "大家好，今天我们讨论...",
                "duration": 300.5,
                "language": "zh-CN",
                "provider": "volcano",
            }
        }
    }


# ============================================================================
# Upload Schemas
# ============================================================================


class UploadResponse(BaseModel):
    """上传响应"""

    success: bool
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小(字节)")
    duration: Optional[float] = Field(None, description="音频时长(秒)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "file_path": "uploads/user_123/meeting_20260116.wav",
                "file_size": 1024000,
                "duration": 300.5,
            }
        }
    }


class DeleteUploadResponse(BaseModel):
    """删除上传文件响应"""

    success: bool
    message: str = "文件已删除"


# ============================================================================
# Task Confirmation Schemas
# ============================================================================


class ConfirmTaskRequest(BaseModel):
    """确认任务请求"""

    confirmation_items: Dict[str, bool] = Field(..., description="确认项状态 (key_conclusions, responsible_persons, etc.)")
    responsible_person: Dict[str, str] = Field(..., description="责任人信息 (id, name)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "confirmation_items": {
                    "key_conclusions": True,
                    "responsible_persons": True,
                    "action_items": True,
                },
                "responsible_person": {
                    "id": "user_001",
                    "name": "张三",
                },
            }
        }
    }


class ConfirmTaskResponse(BaseModel):
    """确认任务响应"""

    success: bool
    task_id: str
    state: str
    confirmed_by: str
    confirmed_by_name: str
    confirmed_at: datetime
    message: str = "任务已确认并归档"

