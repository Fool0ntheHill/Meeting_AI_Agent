# -*- coding: utf-8 -*-
"""SQLAlchemy database models."""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Folder(Base):
    """文件夹表"""

    __tablename__ = "folders"

    # 主键
    folder_id = Column(String(64), primary_key=True, index=True)

    # 文件夹信息
    name = Column(String(256), nullable=False)
    parent_id = Column(String(64), ForeignKey("folders.folder_id", ondelete="CASCADE"), nullable=True, index=True)

    # 所有者信息
    owner_user_id = Column(String(64), nullable=False, index=True)
    owner_tenant_id = Column(String(64), nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    parent = relationship("Folder", remote_side="Folder.folder_id", backref="children")
    tasks = relationship("Task", back_populates="folder")

    # 索引
    __table_args__ = (
        Index("idx_folder_owner_user", "owner_user_id"),
        Index("idx_folder_owner_tenant", "owner_tenant_id"),
        Index("idx_folder_parent", "parent_id"),
    )


class User(Base):
    """用户表"""

    __tablename__ = "users"

    # 主键
    user_id = Column(String(64), primary_key=True, index=True)

    # 用户信息
    username = Column(String(128), nullable=False, unique=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_user_tenant", "tenant_id"),
    )


class Task(Base):
    """任务表"""

    __tablename__ = "tasks"

    # 主键
    task_id = Column(String(64), primary_key=True, index=True)

    # 任务元数据
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # 任务名称（可选）
    meeting_type = Column(String(64), nullable=False)

    # 音频文件信息 (JSON 数组)
    audio_files = Column(Text, nullable=False)  # JSON: ["file1.ogg", "file2.ogg"]
    file_order = Column(Text, nullable=False)  # JSON: [0, 1]

    # 语言配置
    asr_language = Column(String(32), nullable=False, default="zh-CN+en-US")
    output_language = Column(String(32), nullable=False, default="zh-CN")

    # 任务配置
    skip_speaker_recognition = Column(Boolean, nullable=False, default=False)
    hotword_set_id = Column(String(64), nullable=True)
    preferred_asr_provider = Column(String(32), nullable=False, default="volcano")

    # 任务状态
    state = Column(String(32), nullable=False, default="pending", index=True)
    progress = Column(Float, nullable=False, default=0.0)
    estimated_time = Column(Integer, nullable=True)  # 秒
    error_details = Column(Text, nullable=True)

    # 确认和归档
    is_confirmed = Column(Boolean, nullable=False, default=False)
    confirmed_by = Column(String(64), nullable=True)  # 确认人 ID
    confirmed_by_name = Column(String(128), nullable=True)  # 确认人姓名
    confirmed_at = Column(DateTime, nullable=True)
    confirmation_items = Column(Text, nullable=True)  # JSON: {"key_conclusions": true, "responsible_persons": true}

    # 文件夹和回收站
    folder_id = Column(String(64), ForeignKey("folders.folder_id", ondelete="SET NULL"), nullable=True, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    last_content_modified_at = Column(DateTime, nullable=True, index=True)  # 内容最后修改时间

    # 关系
    transcripts = relationship("TranscriptRecord", back_populates="task", cascade="all, delete-orphan")
    speaker_mappings = relationship("SpeakerMapping", back_populates="task", cascade="all, delete-orphan")
    artifacts = relationship("GeneratedArtifactRecord", back_populates="task", cascade="all, delete-orphan")
    folder = relationship("Folder", back_populates="tasks")

    # 索引
    __table_args__ = (
        Index("idx_task_user_created", "user_id", "created_at"),
        Index("idx_task_tenant_created", "tenant_id", "created_at"),
        Index("idx_task_state_created", "state", "created_at"),
        Index("idx_task_folder", "folder_id"),
        Index("idx_task_deleted", "is_deleted", "deleted_at"),
        Index("idx_task_content_modified", "last_content_modified_at"),
    )

    def get_audio_files_list(self) -> list[str]:
        """解析 audio_files JSON"""
        return json.loads(self.audio_files) if self.audio_files else []

    def get_file_order_list(self) -> list[int]:
        """解析 file_order JSON"""
        return json.loads(self.file_order) if self.file_order else []

    def set_audio_files_list(self, files: list[str]) -> None:
        """设置 audio_files JSON"""
        self.audio_files = json.dumps(files)

    def set_file_order_list(self, order: list[int]) -> None:
        """设置 file_order JSON"""
        self.file_order = json.dumps(order)

    def get_confirmation_items_dict(self) -> dict:
        """解析 confirmation_items JSON"""
        return json.loads(self.confirmation_items) if self.confirmation_items else {}

    def set_confirmation_items_dict(self, items: dict) -> None:
        """设置 confirmation_items JSON"""
        self.confirmation_items = json.dumps(items, ensure_ascii=False)


class TranscriptRecord(Base):
    """转写记录表"""

    __tablename__ = "transcripts"

    # 主键
    transcript_id = Column(String(64), primary_key=True)

    # 外键
    task_id = Column(String(64), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)

    # 转写内容 (JSON)
    segments = Column(Text, nullable=False)  # JSON: [{"text": "...", "start_time": 0.0, ...}]
    full_text = Column(Text, nullable=False)

    # 元数据
    duration = Column(Float, nullable=False)
    language = Column(String(32), nullable=False, default="zh-CN")
    provider = Column(String(32), nullable=False)

    # 是否人工修正
    is_corrected = Column(Boolean, nullable=False, default=False)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    task = relationship("Task", back_populates="transcripts")

    def get_segments_list(self) -> list[dict]:
        """解析 segments JSON"""
        return json.loads(self.segments) if self.segments else []

    def set_segments_list(self, segments: list[dict]) -> None:
        """设置 segments JSON"""
        self.segments = json.dumps(segments, ensure_ascii=False)


class SpeakerMapping(Base):
    """说话人映射表"""

    __tablename__ = "speaker_mappings"

    # 主键
    mapping_id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键
    task_id = Column(String(64), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)

    # 映射关系
    speaker_label = Column(String(64), nullable=False)  # "Speaker 0", "Speaker 1"
    speaker_name = Column(String(128), nullable=False)  # "张三", "李四"
    speaker_id = Column(String(64), nullable=True)  # 声纹特征 ID
    confidence = Column(Float, nullable=True)  # 识别置信度

    # 是否人工修正
    is_corrected = Column(Boolean, nullable=False, default=False)
    corrected_by = Column(String(64), nullable=True)
    corrected_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    task = relationship("Task", back_populates="speaker_mappings")

    # 唯一约束
    __table_args__ = (
        Index("idx_speaker_task_label", "task_id", "speaker_label", unique=True),
    )


class PromptTemplateRecord(Base):
    """提示词模板表"""

    __tablename__ = "prompt_templates"

    # 主键
    template_id = Column(String(64), primary_key=True)

    # 模板信息
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    prompt_body = Column(Text, nullable=False)

    # 类型和语言
    artifact_type = Column(String(64), nullable=False, index=True)
    supported_languages = Column(Text, nullable=False)  # JSON: ["zh-CN", "en-US"]

    # 参数定义 (JSON)
    parameter_schema = Column(Text, nullable=False)  # JSON: {"param1": {"type": "string", ...}}

    # 系统模板标记
    is_system = Column(Boolean, nullable=False, default=True)

    # 作用域
    scope = Column(String(32), nullable=False, default="global", index=True)  # global/private
    scope_id = Column(String(64), nullable=True, index=True)  # user_id for private templates

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_supported_languages_list(self) -> list[str]:
        """解析 supported_languages JSON"""
        return json.loads(self.supported_languages) if self.supported_languages else []

    def set_supported_languages_list(self, languages: list[str]) -> None:
        """设置 supported_languages JSON"""
        self.supported_languages = json.dumps(languages)

    def get_parameter_schema_dict(self) -> dict:
        """解析 parameter_schema JSON"""
        return json.loads(self.parameter_schema) if self.parameter_schema else {}

    def set_parameter_schema_dict(self, schema: dict) -> None:
        """设置 parameter_schema JSON"""
        self.parameter_schema = json.dumps(schema, ensure_ascii=False)


class GeneratedArtifactRecord(Base):
    """生成内容记录表"""

    __tablename__ = "generated_artifacts"

    # 主键
    artifact_id = Column(String(64), primary_key=True)

    # 外键
    task_id = Column(String(64), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)

    # 内容类型和版本
    artifact_type = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)

    # 提示词实例 (JSON)
    prompt_instance = Column(Text, nullable=False)  # JSON: {"template_id": "...", "language": "...", "parameters": {...}}

    # 生成内容 (JSON 字符串)
    content = Column(Text, nullable=False)

    # 元数据 (JSON)
    artifact_metadata = Column(Text, nullable=True)  # JSON: {"regenerated": true, ...}

    # 创建信息
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # 关系
    task = relationship("Task", back_populates="artifacts")

    # 索引
    __table_args__ = (
        Index("idx_artifact_task_type", "task_id", "artifact_type"),
        Index("idx_artifact_task_version", "task_id", "version"),
    )

    def get_prompt_instance_dict(self) -> dict:
        """解析 prompt_instance JSON"""
        return json.loads(self.prompt_instance) if self.prompt_instance else {}

    def set_prompt_instance_dict(self, instance: dict) -> None:
        """设置 prompt_instance JSON"""
        self.prompt_instance = json.dumps(instance, ensure_ascii=False)

    def get_content_dict(self) -> dict:
        """解析 content JSON"""
        return json.loads(self.content) if self.content else {}

    def set_content_dict(self, content: dict) -> None:
        """设置 content JSON"""
        self.content = json.dumps(content, ensure_ascii=False)

    def get_metadata_dict(self) -> dict:
        """解析 artifact_metadata JSON"""
        return json.loads(self.artifact_metadata) if self.artifact_metadata else {}

    def set_metadata_dict(self, metadata: dict) -> None:
        """设置 artifact_metadata JSON"""
        self.artifact_metadata = json.dumps(metadata, ensure_ascii=False)


class HotwordSetRecord(Base):
    """热词集记录表"""

    __tablename__ = "hotword_sets"

    # 主键
    hotword_set_id = Column(String(64), primary_key=True)

    # 基本信息
    name = Column(String(256), nullable=False)
    provider = Column(String(32), nullable=False, index=True, default="volcano")  # volcano, azure
    provider_resource_id = Column(String(256), nullable=False)  # 提供商资源 ID (如火山的 BoostingTableID)
    
    # 作用域
    scope = Column(String(32), nullable=False, index=True)  # global, tenant, user
    scope_id = Column(String(64), nullable=True, index=True)  # tenant_id 或 user_id
    
    # 语言和描述
    asr_language = Column(String(32), nullable=False)  # zh-CN, en-US, zh-CN+en-US
    description = Column(Text, nullable=True)
    
    # 统计信息
    word_count = Column(Integer, nullable=True)  # 热词数量
    word_size = Column(Integer, nullable=True)  # 热词总字符数
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index("idx_hotword_scope_provider", "scope", "provider"),
        Index("idx_hotword_scope_id", "scope_id"),
    )


class AuditLogRecord(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    # 主键
    log_id = Column(String(64), primary_key=True)

    # 操作信息
    action = Column(String(64), nullable=False, index=True)  # task_created, task_updated, api_call, cost_usage
    resource_type = Column(String(64), nullable=False, index=True)  # task, artifact, hotword_set, etc.
    resource_id = Column(String(64), nullable=False, index=True)  # 资源 ID

    # 用户信息
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    # 操作详情 (JSON)
    details = Column(Text, nullable=True)  # JSON: {"field": "value", ...}

    # 成本信息
    cost_amount = Column(Float, nullable=True)  # 操作产生的成本
    cost_currency = Column(String(8), nullable=True, default="USD")

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # 索引
    __table_args__ = (
        Index("idx_audit_user_created", "user_id", "created_at"),
        Index("idx_audit_tenant_created", "tenant_id", "created_at"),
        Index("idx_audit_action_created", "action", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )

    def get_details_dict(self) -> dict:
        """解析 details JSON"""
        return json.loads(self.details) if self.details else {}

    def set_details_dict(self, details: dict) -> None:
        """设置 details JSON"""
        self.details = json.dumps(details, ensure_ascii=False)
