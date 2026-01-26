"""Core data models for the Meeting Minutes Agent."""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enumerations
# ============================================================================


class ASRLanguage(str, Enum):
    """ASR 识别语言"""

    ZH_CN = "zh-CN"  # 中文
    EN_US = "en-US"  # 英文
    ZH_EN = "zh-CN+en-US"  # 中英文混合(默认)
    JA_JP = "ja-JP"  # 日文
    KO_KR = "ko-KR"  # 韩文


class OutputLanguage(str, Enum):
    """输出语言(纪要生成)"""

    ZH_CN = "zh-CN"  # 中文(默认)
    EN_US = "en-US"  # 英文
    JA_JP = "ja-JP"  # 日文
    KO_KR = "ko-KR"  # 韩文


class TaskState(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    TRANSCRIBING = "transcribing"
    IDENTIFYING = "identifying"
    CORRECTING = "correcting"
    SUMMARIZING = "summarizing"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    CONFIRMED = "confirmed"  # 已确认
    ARCHIVED = "archived"  # 已归档
    CANCELLED = "cancelled"  # 已取消


class StepState(str, Enum):
    """Pipeline Step 状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# ============================================================================
# Core Data Models
# ============================================================================


class Segment(BaseModel):
    """转写片段"""

    text: str = Field(..., description="文本内容")
    start_time: float = Field(..., ge=0, description="开始时间(秒)")
    end_time: float = Field(..., ge=0, description="结束时间(秒)")
    speaker: str = Field(..., description="说话人标签或姓名")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="置信度")

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "大家好,今天我们讨论产品规划",
                "start_time": 0.0,
                "end_time": 3.5,
                "speaker": "张三",
                "confidence": 0.95,
            }
        }
    }


class TranscriptionResult(BaseModel):
    """转写结果"""

    segments: List[Segment] = Field(..., description="片段列表")
    full_text: str = Field(..., description="完整文本")
    duration: float = Field(..., ge=0, description="音频时长(秒)")
    language: str = Field(default="zh-CN", description="语言")
    provider: str = Field(..., description="ASR 提供商")
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def speakers(self) -> List[str]:
        """获取唯一说话人列表"""
        return list(set(seg.speaker for seg in self.segments))


class SpeakerIdentity(BaseModel):
    """说话人身份"""

    speaker_id: str = Field(..., description="说话人唯一标识")
    name: str = Field(..., description="说话人姓名")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class MeetingMinutes(BaseModel):
    """
    会议纪要(结构化对象)

    注: 当作为 GeneratedArtifact.content 存储时,
    应序列化为 JSON 字符串: artifact.content = meeting_minutes.model_dump_json()
    """

    title: str = Field(..., description="会议标题")
    participants: List[str] = Field(..., description="参与者列表")
    summary: str = Field(..., description="会议摘要")
    key_points: List[str] = Field(..., description="关键要点")
    action_items: List[str] = Field(..., description="行动项")
    created_at: datetime = Field(default_factory=datetime.now)
    responsible_person: Optional[str] = Field(None, description="责任人")


# ============================================================================
# Prompt Template Models
# ============================================================================


class PromptTemplate(BaseModel):
    """提示词模板"""

    template_id: str = Field(..., description="模板唯一标识")
    title: str = Field(..., description="模板标题")
    description: str = Field(..., description="用户可读说明")
    prompt_body: str = Field(..., description="提示词正文(含占位符,如 {meeting_description})")
    artifact_type: str = Field(
        ..., description="生成内容类型(meeting_minutes/action_items/summary_notes)"
    )
    supported_languages: List[str] = Field(
        default=["zh-CN", "en-US"], description="支持的语言列表"
    )
    parameter_schema: Dict[str, Any] = Field(
        ..., description="参数定义(参数名 -> {type, required, default})"
    )
    is_system: bool = Field(default=True, description="是否为系统预置模板")
    scope: str = Field(default="global", description="作用域(global/private)")
    scope_id: Optional[str] = Field(None, description="作用域 ID(user_id)")
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_schema_extra": {
            "example": {
                "template_id": "tpl_001",
                "title": "标准会议纪要",
                "description": "生成包含摘要、关键要点和行动项的标准会议纪要",
                "prompt_body": "你是一个专业的会议纪要助手。\n\n会议信息:\n{meeting_description}\n\n请根据以下会议转写生成纪要...",
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
                "is_system": True,
            }
        }
    }


class PromptInstance(BaseModel):
    """提示词实例 - 用户实际使用的提示词"""

    template_id: str = Field(..., description="模板 ID（可以是 __blank__ 表示空白模板）")
    language: str = Field(default="zh-CN", description="语言")
    prompt_text: Optional[str] = Field(default=None, description="用户编辑后的完整提示词文本（如果提供，则优先使用此文本而不是从模板加载）")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数值（用于模板占位符替换）")
    custom_instructions: Optional[str] = Field(default=None, description="用户补充指令（追加到提示词之后）")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "场景1: 使用模板，不修改",
                    "value": {
                        "template_id": "tpl_001",
                        "language": "zh-CN",
                        "parameters": {
                            "meeting_description": "产品规划会议"
                        }
                    }
                },
                {
                    "description": "场景2: 使用模板，但用户修改了提示词",
                    "value": {
                        "template_id": "tpl_001",
                        "language": "zh-CN",
                        "prompt_text": "请生成简洁的会议纪要，重点关注决策事项。\n\n会议转写：\n{transcript}",
                        "parameters": {}
                    }
                },
                {
                    "description": "场景3: 空白模板，用户完全自定义",
                    "value": {
                        "template_id": "__blank__",
                        "language": "zh-CN",
                        "prompt_text": "请分析这次会议，提取关键技术决策和风险点。\n\n{transcript}",
                        "parameters": {}
                    }
                }
            ]
        }
    }


# ============================================================================
# Generated Artifact Models
# ============================================================================


class GeneratedArtifact(BaseModel):
    """
    会议衍生内容

    设计说明:
    - content 字段类型为 str,存储 JSON 序列化后的字符串
    - 优势: 灵活支持不同类型的 artifact,数据库存储统一
    - 前端使用: 接收后使用 JSON.parse() 解析
    - 后端使用: 提供 get_meeting_minutes() 等辅助方法解析为强类型对象
    """

    artifact_id: str = Field(..., description="内容唯一标识")
    task_id: str = Field(..., description="关联的任务 ID")
    artifact_type: str = Field(
        ..., description="内容类型(meeting_minutes/action_items/summary_notes)"
    )
    version: int = Field(..., description="版本号")
    prompt_instance: PromptInstance = Field(..., description="使用的提示词实例")
    content: str = Field(..., description="生成的内容(JSON 字符串,前端需 JSON.parse 解析)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据(如 grounding_metadata)")
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(..., description="创建者")

    def get_meeting_minutes(self) -> Optional[MeetingMinutes]:
        """
        当 artifact_type = meeting_minutes 时,解析 content 为 MeetingMinutes 对象

        Returns:
            MeetingMinutes: 解析后的会议纪要对象
            None: 如果 artifact_type 不是 meeting_minutes 或解析失败
        """
        if self.artifact_type != "meeting_minutes":
            return None
        try:
            return MeetingMinutes.model_validate_json(self.content)
        except Exception:
            return None

    def get_content_dict(self) -> Dict[str, Any]:
        """
        解析 content 为字典对象(用于 API 响应)

        Returns:
            Dict[str, Any]: 解析后的内容字典

        Raises:
            ValueError: 如果 content 不是有效的 JSON
        """
        try:
            return json.loads(self.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content: {e}")

    model_config = {
        "json_schema_extra": {
            "example": {
                "artifact_id": "art_001",
                "task_id": "task_123",
                "artifact_type": "meeting_minutes",
                "version": 1,
                "prompt_instance": {
                    "template_id": "tpl_001",
                    "language": "zh-CN",
                    "parameters": {"meeting_description": "会议标题: 产品规划会议"},
                },
                "content": '{"title": "产品规划会议", "participants": ["张三", "李四"], "summary": "讨论了 Q2 产品路线图", "key_points": [], "action_items": []}',
                "created_by": "user_456",
            }
        }
    }


# ============================================================================
# HotwordSet Models
# ============================================================================


class HotwordSet(BaseModel):
    """
    热词集 - 提供商特定的词汇增强资源引用

    不存储原始短语列表,仅存储提供商资源 ID
    """

    hotword_set_id: str = Field(..., description="唯一标识")
    name: str = Field(..., description="名称(用于展示)")
    provider: str = Field(..., description="提供商 (volcano/azure)")
    provider_resource_id: str = Field(..., description="提供商资源 ID (热词库 ID 或模型 ID)")
    scope: str = Field(..., description="作用域 (global/tenant/user)")
    scope_id: Optional[str] = Field(None, description="作用域 ID (tenant_id 或 user_id)")
    asr_language: ASRLanguage = Field(..., description="热词集适配的 ASR 语言")
    description: Optional[str] = Field(None, description="描述")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """验证提供商"""
        allowed = ["volcano", "azure"]
        if v not in allowed:
            raise ValueError(f"provider 必须是 {allowed} 之一")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "hotword_set_id": "hs_123",
                "name": "医疗术语",
                "provider": "volcano",
                "provider_resource_id": "lib_medical_001",
                "scope": "tenant",
                "scope_id": "tenant_456",
                "asr_language": "zh-CN+en-US",
            }
        }
    }


# ============================================================================
# Task Models
# ============================================================================


class TaskMetadata(BaseModel):
    """任务元数据"""

    task_id: str = Field(..., description="任务唯一标识")
    audio_files: List[str] = Field(..., description="音频文件列表")
    file_order: List[int] = Field(..., description="文件排序索引")
    meeting_type: str = Field(..., description="会议类型")
    asr_language: ASRLanguage = Field(default=ASRLanguage.ZH_EN, description="ASR 识别语言")
    output_language: OutputLanguage = Field(default=OutputLanguage.ZH_CN, description="输出语言")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词(已废弃,使用 prompt_instance)")
    user_id: str = Field(..., description="用户 ID")
    tenant_id: str = Field(..., description="租户 ID")
    hotword_set_id: Optional[str] = Field(None, description="热词集 ID")
    preferred_asr_provider: str = Field(default="volcano", description="首选 ASR 提供商")
    skip_speaker_recognition: bool = Field(default=False, description="跳过说话人识别")
    created_at: datetime = Field(default_factory=datetime.now)


class TaskStatus(BaseModel):
    """任务状态"""

    task_id: str
    state: TaskState
    progress: float = Field(..., ge=0, le=100, description="进度百分比")
    estimated_time: Optional[int] = Field(None, description="预计剩余时间(秒)")
    error_details: Optional[str] = Field(None, description="错误详情")
    updated_at: datetime = Field(default_factory=datetime.now)


class TaskHistoryEntry(BaseModel):
    """任务历史条目"""

    timestamp: datetime
    state: TaskState
    message: str
    details: Optional[dict] = None


class TaskHistory(BaseModel):
    """任务历史"""

    task_id: str
    entries: List[TaskHistoryEntry] = Field(default_factory=list)

    def add_entry(
        self, state: TaskState, message: str, details: Optional[dict] = None
    ) -> None:
        """添加历史条目"""
        self.entries.append(
            TaskHistoryEntry(timestamp=datetime.now(), state=state, message=message, details=details)
        )


# ============================================================================
# API Request/Response Models
# ============================================================================


class CreateTaskRequest(BaseModel):
    """创建任务请求"""

    audio_files: List[str] = Field(..., min_length=1, description="音频文件列表")
    file_order: Optional[List[int]] = Field(None, description="文件排序索引")
    meeting_type: str = Field(..., description="会议类型")
    asr_language: Optional[str] = Field(default="zh-CN+en-US", description="ASR 识别语言")
    output_language: Optional[str] = Field(default="zh-CN", description="输出语言")
    prompt_instance: Optional[PromptInstance] = Field(None, description="提示词实例")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词(已废弃,使用 prompt_instance)")
    skip_speaker_recognition: bool = Field(default=False)

    @field_validator("file_order")
    @classmethod
    def validate_file_order(cls, v: Optional[List[int]], info) -> Optional[List[int]]:
        """验证文件排序索引"""
        if v is not None:
            audio_files = info.data.get("audio_files", [])
            if len(v) != len(audio_files):
                raise ValueError("file_order 长度必须与 audio_files 相同")
            if sorted(v) != list(range(len(v))):
                raise ValueError("file_order 必须是 0 到 n-1 的排列")
        return v


class CreateTaskResponse(BaseModel):
    """创建任务响应"""

    success: bool
    task_id: str
    message: str = "任务已创建"


class EstimateCostRequest(BaseModel):
    """成本预估请求"""

    audio_duration: float = Field(..., gt=0, description="音频时长(秒)")
    meeting_type: str = Field(..., description="会议类型")
    enable_speaker_recognition: bool = Field(default=True)


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


class GenerateArtifactRequest(BaseModel):
    """生成衍生内容请求"""

    prompt_instance: PromptInstance = Field(..., description="提示词实例")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt_instance": {
                    "template_id": "tpl_001",
                    "language": "zh-CN",
                    "parameters": {
                        "meeting_description": "会议标题: 产品规划会议\n会议主题: Q2 产品路线图讨论\n关注重点: 重点关注用户反馈和竞品分析"
                    },
                }
            }
        }
    }


class GenerateArtifactResponse(BaseModel):
    """生成衍生内容响应"""

    success: bool
    artifact_id: str
    version: int
    content: str
    message: str = "内容已生成"


class ListArtifactsResponse(BaseModel):
    """列出衍生内容响应"""

    artifacts: Dict[str, List[GeneratedArtifact]] = Field(..., description="按类型分组的衍生内容")

    model_config = {
        "json_schema_extra": {
            "example": {
                "artifacts": {
                    "meeting_minutes": [
                        {
                            "artifact_id": "art_001",
                            "version": 2,
                            "created_at": "2026-01-13T10:00:00Z",
                        },
                        {
                            "artifact_id": "art_002",
                            "version": 1,
                            "created_at": "2026-01-13T09:00:00Z",
                        },
                    ],
                    "action_items": [
                        {
                            "artifact_id": "art_003",
                            "version": 1,
                            "created_at": "2026-01-13T10:30:00Z",
                        }
                    ],
                }
            }
        }
    }


class ListPromptTemplatesResponse(BaseModel):
    """列出提示词模板响应"""

    templates: List[PromptTemplate] = Field(..., description="提示词模板列表")
