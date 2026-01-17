# -*- coding: utf-8 -*-
"""Database repositories for data access."""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.database.models import (
    User,
    Task,
    TranscriptRecord,
    SpeakerMapping,
    GeneratedArtifactRecord,
    PromptTemplateRecord,
)
from src.core.models import (
    TranscriptionResult,
    Segment,
    MeetingMinutes,
    GeneratedArtifact,
    PromptInstance,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserRepository:
    """用户仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        user_id: str,
        username: str,
        tenant_id: str,
        is_active: bool = True,
    ) -> User:
        """创建用户"""
        user = User(
            user_id=user_id,
            username=username,
            tenant_id=tenant_id,
            is_active=is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        return self.session.query(User).filter(User.user_id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.session.query(User).filter(User.username == username).first()

    def update_last_login(self, user_id: str) -> Optional[User]:
        """更新最后登录时间"""
        user = self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            self.session.flush()
        return user

    def deactivate(self, user_id: str) -> Optional[User]:
        """停用用户"""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            self.session.flush()
        return user


class TaskRepository:
    """任务仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        task_id: str,
        user_id: str,
        tenant_id: str,
        meeting_type: str,
        audio_files: List[str],
        file_order: List[int],
        asr_language: str = "zh-CN+en-US",
        output_language: str = "zh-CN",
        skip_speaker_recognition: bool = False,
        hotword_set_id: Optional[str] = None,
        preferred_asr_provider: str = "volcano",
    ) -> Task:
        """创建任务"""
        task = Task(
            task_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            meeting_type=meeting_type,
            audio_files=json.dumps(audio_files),
            file_order=json.dumps(file_order),
            asr_language=asr_language,
            output_language=output_language,
            skip_speaker_recognition=skip_speaker_recognition,
            hotword_set_id=hotword_set_id,
            preferred_asr_provider=preferred_asr_provider,
            state="pending",
            progress=0.0,
        )
        self.session.add(task)
        self.session.flush()
        logger.info(f"Task created: {task_id}")
        return task

    def get_by_id(self, task_id: str) -> Optional[Task]:
        """根据 ID 获取任务"""
        return self.session.query(Task).filter(Task.task_id == task_id).first()

    def get_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """获取用户的任务列表"""
        return (
            self.session.query(Task)
            .filter(Task.user_id == user_id)
            .order_by(desc(Task.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def update_state(
        self,
        task_id: str,
        state: str,
        progress: Optional[float] = None,
        error_details: Optional[str] = None,
    ) -> None:
        """更新任务状态"""
        task = self.get_by_id(task_id)
        if task:
            task.state = state
            if progress is not None:
                task.progress = progress
            if error_details is not None:
                task.error_details = error_details
            task.updated_at = datetime.utcnow()
            
            if state in ["success", "failed", "partial_success"]:
                task.completed_at = datetime.utcnow()
            
            self.session.flush()
            logger.info(f"Task state updated: {task_id} -> {state}")

    def delete(self, task_id: str) -> bool:
        """删除任务"""
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.flush()
            logger.info(f"Task deleted: {task_id}")
            return True
        return False

    def confirm_task(
        self,
        task_id: str,
        confirmation_items: Dict[str, bool],
        confirmed_by: str,
        confirmed_by_name: str,
    ) -> Optional[Task]:
        """确认任务并归档"""
        task = self.get_by_id(task_id)
        if not task:
            return None
        
        # 更新确认信息
        task.is_confirmed = True
        task.confirmed_by = confirmed_by
        task.confirmed_by_name = confirmed_by_name
        task.confirmed_at = datetime.utcnow()
        task.set_confirmation_items_dict(confirmation_items)
        
        # 更新任务状态为 ARCHIVED
        task.state = "archived"
        task.updated_at = datetime.utcnow()
        
        self.session.flush()
        logger.info(f"Task confirmed and archived: {task_id} by {confirmed_by_name}")
        return task


class TranscriptRepository:
    """转写记录仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        transcript_id: str,
        task_id: str,
        transcript_result: TranscriptionResult,
    ) -> TranscriptRecord:
        """创建转写记录"""
        # 序列化 segments
        segments_data = [seg.model_dump() for seg in transcript_result.segments]

        record = TranscriptRecord(
            transcript_id=transcript_id,
            task_id=task_id,
            segments=json.dumps(segments_data, ensure_ascii=False),
            full_text=transcript_result.full_text,
            duration=transcript_result.duration,
            language=transcript_result.language,
            provider=transcript_result.provider,
        )
        self.session.add(record)
        self.session.flush()
        logger.info(f"Transcript created: {transcript_id} for task {task_id}")
        return record

    def get_by_task_id(self, task_id: str) -> Optional[TranscriptRecord]:
        """获取任务的转写记录"""
        return (
            self.session.query(TranscriptRecord)
            .filter(TranscriptRecord.task_id == task_id)
            .first()
        )

    def to_transcription_result(self, record: TranscriptRecord) -> TranscriptionResult:
        """将数据库记录转换为 TranscriptionResult"""
        segments_data = record.get_segments_list()
        segments = [Segment(**seg) for seg in segments_data]

        return TranscriptionResult(
            segments=segments,
            full_text=record.full_text,
            duration=record.duration,
            language=record.language,
            provider=record.provider,
            created_at=record.created_at,
        )

    def update_full_text(
        self,
        task_id: str,
        full_text: str,
        is_corrected: bool = True,
    ) -> None:
        """更新转写文本"""
        record = self.get_by_task_id(task_id)
        if record:
            record.full_text = full_text
            record.is_corrected = is_corrected
            self.session.flush()
            logger.info(f"Transcript full_text updated for task {task_id}")

    def update_segments(
        self,
        task_id: str,
        segments: List[Dict],
    ) -> None:
        """更新转写片段"""
        record = self.get_by_task_id(task_id)
        if record:
            record.segments = json.dumps(segments, ensure_ascii=False)
            self.session.flush()
            logger.info(f"Transcript segments updated for task {task_id}")


class SpeakerMappingRepository:
    """说话人映射仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create_or_update(
        self,
        task_id: str,
        speaker_label: str,
        speaker_name: str,
        speaker_id: Optional[str] = None,
        confidence: Optional[float] = None,
        is_corrected: bool = False,
        corrected_by: Optional[str] = None,
    ) -> SpeakerMapping:
        """创建或更新说话人映射"""
        # 查找现有映射
        mapping = (
            self.session.query(SpeakerMapping)
            .filter(
                SpeakerMapping.task_id == task_id,
                SpeakerMapping.speaker_label == speaker_label,
            )
            .first()
        )

        if mapping:
            # 更新现有映射
            mapping.speaker_name = speaker_name
            mapping.speaker_id = speaker_id
            mapping.confidence = confidence
            mapping.is_corrected = is_corrected
            if is_corrected:
                mapping.corrected_by = corrected_by
                mapping.corrected_at = datetime.utcnow()
        else:
            # 创建新映射
            mapping = SpeakerMapping(
                task_id=task_id,
                speaker_label=speaker_label,
                speaker_name=speaker_name,
                speaker_id=speaker_id,
                confidence=confidence,
                is_corrected=is_corrected,
                corrected_by=corrected_by,
                corrected_at=datetime.utcnow() if is_corrected else None,
            )
            self.session.add(mapping)

        self.session.flush()
        logger.info(f"Speaker mapping saved: {task_id} - {speaker_label} -> {speaker_name}")
        return mapping

    def get_by_task_id(self, task_id: str) -> List[SpeakerMapping]:
        """获取任务的所有说话人映射"""
        return (
            self.session.query(SpeakerMapping)
            .filter(SpeakerMapping.task_id == task_id)
            .all()
        )

    def get_mapping_dict(self, task_id: str) -> Dict[str, str]:
        """获取任务的说话人映射字典"""
        mappings = self.get_by_task_id(task_id)
        return {m.speaker_label: m.speaker_name for m in mappings}

    def update_speaker_name(
        self,
        task_id: str,
        speaker_label: str,
        speaker_name: str,
    ) -> None:
        """更新说话人名称"""
        mapping = (
            self.session.query(SpeakerMapping)
            .filter(
                SpeakerMapping.task_id == task_id,
                SpeakerMapping.speaker_label == speaker_label,
            )
            .first()
        )
        
        if mapping:
            mapping.speaker_name = speaker_name
            mapping.is_corrected = True
            mapping.corrected_at = datetime.utcnow()
            self.session.flush()
            logger.info(f"Speaker name updated: {task_id} - {speaker_label} -> {speaker_name}")


class ArtifactRepository:
    """生成内容仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        artifact_id: str,
        task_id: str,
        artifact_type: str,
        version: int,
        prompt_instance: Dict,  # 已经是字典
        content: Dict,  # 内容字典
        created_by: str,
        metadata: Optional[Dict] = None,
    ) -> GeneratedArtifactRecord:
        """创建生成内容记录"""
        record = GeneratedArtifactRecord(
            artifact_id=artifact_id,
            task_id=task_id,
            artifact_type=artifact_type,
            version=version,
            prompt_instance=json.dumps(prompt_instance, ensure_ascii=False),
            content=json.dumps(content, ensure_ascii=False),
            artifact_metadata=json.dumps(metadata, ensure_ascii=False) if metadata else None,
            created_by=created_by,
        )
        self.session.add(record)
        self.session.flush()
        logger.info(f"Artifact created: {artifact_id} for task {task_id}")
        return record

    def get_by_id(self, artifact_id: str) -> Optional[GeneratedArtifactRecord]:
        """根据 ID 获取生成内容"""
        return (
            self.session.query(GeneratedArtifactRecord)
            .filter(GeneratedArtifactRecord.artifact_id == artifact_id)
            .first()
        )

    def get_by_task_id(
        self,
        task_id: str,
        artifact_type: Optional[str] = None,
    ) -> List[GeneratedArtifactRecord]:
        """获取任务的所有生成内容"""
        query = self.session.query(GeneratedArtifactRecord).filter(
            GeneratedArtifactRecord.task_id == task_id
        )

        if artifact_type:
            query = query.filter(GeneratedArtifactRecord.artifact_type == artifact_type)

        return query.order_by(desc(GeneratedArtifactRecord.version)).all()

    def get_latest_by_task(
        self,
        task_id: str,
        artifact_type: str = "meeting_minutes",
    ) -> Optional[GeneratedArtifactRecord]:
        """获取任务的最新版本生成内容"""
        return (
            self.session.query(GeneratedArtifactRecord)
            .filter(
                GeneratedArtifactRecord.task_id == task_id,
                GeneratedArtifactRecord.artifact_type == artifact_type,
            )
            .order_by(desc(GeneratedArtifactRecord.version))
            .first()
        )

    def get_by_task_and_type(
        self,
        task_id: str,
        artifact_type: str,
    ) -> List[GeneratedArtifactRecord]:
        """获取任务指定类型的所有版本"""
        return (
            self.session.query(GeneratedArtifactRecord)
            .filter(
                GeneratedArtifactRecord.task_id == task_id,
                GeneratedArtifactRecord.artifact_type == artifact_type,
            )
            .order_by(desc(GeneratedArtifactRecord.version))
            .all()
        )

    def to_generated_artifact(self, record: GeneratedArtifactRecord) -> GeneratedArtifact:
        """将数据库记录转换为 GeneratedArtifact"""
        prompt_instance_dict = record.get_prompt_instance_dict()
        prompt_instance = PromptInstance(**prompt_instance_dict)

        return GeneratedArtifact(
            artifact_id=record.artifact_id,
            task_id=record.task_id,
            artifact_type=record.artifact_type,
            version=record.version,
            prompt_instance=prompt_instance,
            content=record.content,
            created_at=record.created_at,
            created_by=record.created_by,
        )


class PromptTemplateRepository:
    """提示词模板仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        template_id: str,
        title: str,
        prompt_body: str,
        artifact_type: str,
        supported_languages: List[str],
        parameter_schema: Dict[str, Any],
        description: Optional[str] = None,
        is_system: bool = True,
        scope: str = "global",
        scope_id: Optional[str] = None,
    ) -> PromptTemplateRecord:
        """创建提示词模板"""
        template = PromptTemplateRecord(
            template_id=template_id,
            title=title,
            description=description,
            prompt_body=prompt_body,
            artifact_type=artifact_type,
            supported_languages=json.dumps(supported_languages),
            parameter_schema=json.dumps(parameter_schema, ensure_ascii=False),
            is_system=is_system,
            scope=scope,
            scope_id=scope_id,
        )
        self.session.add(template)
        self.session.flush()
        logger.info(f"Prompt template created: {template_id} (scope={scope})")
        return template

    def get_by_id(self, template_id: str) -> Optional[PromptTemplateRecord]:
        """根据 ID 获取模板"""
        return (
            self.session.query(PromptTemplateRecord)
            .filter(PromptTemplateRecord.template_id == template_id)
            .first()
        )

    def get_by_type(self, artifact_type: str) -> List[PromptTemplateRecord]:
        """根据类型获取模板列表"""
        return (
            self.session.query(PromptTemplateRecord)
            .filter(PromptTemplateRecord.artifact_type == artifact_type)
            .order_by(desc(PromptTemplateRecord.created_at))
            .all()
        )

    def get_all(self, is_system: Optional[bool] = None, scope: Optional[str] = None, scope_id: Optional[str] = None) -> List[PromptTemplateRecord]:
        """获取所有模板"""
        query = self.session.query(PromptTemplateRecord)

        if is_system is not None:
            query = query.filter(PromptTemplateRecord.is_system == is_system)
        
        if scope is not None:
            query = query.filter(PromptTemplateRecord.scope == scope)
        
        if scope_id is not None:
            query = query.filter(PromptTemplateRecord.scope_id == scope_id)

        return query.order_by(desc(PromptTemplateRecord.created_at)).all()
    
    def update(
        self,
        template_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        prompt_body: Optional[str] = None,
        supported_languages: Optional[List[str]] = None,
        parameter_schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[PromptTemplateRecord]:
        """更新提示词模板"""
        template = self.get_by_id(template_id)
        if not template:
            return None
        
        if title is not None:
            template.title = title
        if description is not None:
            template.description = description
        if prompt_body is not None:
            template.prompt_body = prompt_body
        if supported_languages is not None:
            template.set_supported_languages_list(supported_languages)
        if parameter_schema is not None:
            template.set_parameter_schema_dict(parameter_schema)
        
        template.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Prompt template updated: {template_id}")
        return template
    
    def delete(self, template_id: str) -> bool:
        """删除提示词模板"""
        template = self.get_by_id(template_id)
        if not template:
            return False
        
        self.session.delete(template)
        self.session.flush()
        logger.info(f"Prompt template deleted: {template_id}")
        return True


class AuditLogRepository:
    """审计日志仓库"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_user(
        self,
        user_id: str,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["AuditLogRecord"]:
        """获取用户的审计日志"""
        from src.database.models import AuditLogRecord

        query = self.session.query(AuditLogRecord).filter(
            AuditLogRecord.user_id == user_id
        )

        if action:
            query = query.filter(AuditLogRecord.action == action)

        if resource_type:
            query = query.filter(AuditLogRecord.resource_type == resource_type)

        return (
            query.order_by(desc(AuditLogRecord.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_by_tenant(
        self,
        tenant_id: str,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["AuditLogRecord"]:
        """获取租户的审计日志"""
        from src.database.models import AuditLogRecord

        query = self.session.query(AuditLogRecord).filter(
            AuditLogRecord.tenant_id == tenant_id
        )

        if action:
            query = query.filter(AuditLogRecord.action == action)

        if resource_type:
            query = query.filter(AuditLogRecord.resource_type == resource_type)

        return (
            query.order_by(desc(AuditLogRecord.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List["AuditLogRecord"]:
        """获取资源的审计日志"""
        from src.database.models import AuditLogRecord

        return (
            self.session.query(AuditLogRecord)
            .filter(
                AuditLogRecord.resource_type == resource_type,
                AuditLogRecord.resource_id == resource_id,
            )
            .order_by(desc(AuditLogRecord.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_cost_summary(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, float]:
        """获取成本汇总"""
        from src.database.models import AuditLogRecord
        from sqlalchemy import func

        query = self.session.query(
            func.sum(AuditLogRecord.cost_amount).label("total_cost")
        ).filter(AuditLogRecord.action == "cost_usage")

        if user_id:
            query = query.filter(AuditLogRecord.user_id == user_id)

        if tenant_id:
            query = query.filter(AuditLogRecord.tenant_id == tenant_id)

        result = query.first()
        total_cost = result[0] if result and result[0] else 0.0

        return {"total_cost": total_cost, "currency": "USD"}


class HotwordSetRepository:
    """热词集仓库"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        hotword_set_id: str,
        name: str,
        provider: str,
        provider_resource_id: str,
        scope: str,
        asr_language: str,
        scope_id: Optional[str] = None,
        description: Optional[str] = None,
        word_count: Optional[int] = None,
        word_size: Optional[int] = None,
    ) -> "HotwordSetRecord":
        """创建热词集"""
        from src.database.models import HotwordSetRecord
        
        hotword_set = HotwordSetRecord(
            hotword_set_id=hotword_set_id,
            name=name,
            provider=provider,
            provider_resource_id=provider_resource_id,
            scope=scope,
            scope_id=scope_id,
            asr_language=asr_language,
            description=description,
            word_count=word_count,
            word_size=word_size,
        )
        self.session.add(hotword_set)
        self.session.flush()
        logger.info(f"Hotword set created: {hotword_set_id}")
        return hotword_set

    def get_by_id(self, hotword_set_id: str) -> Optional["HotwordSetRecord"]:
        """根据 ID 获取热词集"""
        from src.database.models import HotwordSetRecord
        
        return (
            self.session.query(HotwordSetRecord)
            .filter(HotwordSetRecord.hotword_set_id == hotword_set_id)
            .first()
        )

    def get_by_scope(
        self,
        scope: str,
        scope_id: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> List["HotwordSetRecord"]:
        """根据作用域获取热词集列表"""
        from src.database.models import HotwordSetRecord
        
        query = self.session.query(HotwordSetRecord).filter(
            HotwordSetRecord.scope == scope
        )

        if scope_id:
            query = query.filter(HotwordSetRecord.scope_id == scope_id)

        if provider:
            query = query.filter(HotwordSetRecord.provider == provider)

        return query.order_by(desc(HotwordSetRecord.created_at)).all()

    def get_all(
        self,
        provider: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["HotwordSetRecord"]:
        """获取所有热词集"""
        from src.database.models import HotwordSetRecord
        
        query = self.session.query(HotwordSetRecord)

        if provider:
            query = query.filter(HotwordSetRecord.provider == provider)

        return (
            query.order_by(desc(HotwordSetRecord.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def update(
        self,
        hotword_set_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        word_count: Optional[int] = None,
        word_size: Optional[int] = None,
    ) -> Optional["HotwordSetRecord"]:
        """更新热词集"""
        from src.database.models import HotwordSetRecord
        from datetime import datetime
        
        hotword_set = self.get_by_id(hotword_set_id)
        if hotword_set:
            if name is not None:
                hotword_set.name = name
            if description is not None:
                hotword_set.description = description
            if word_count is not None:
                hotword_set.word_count = word_count
            if word_size is not None:
                hotword_set.word_size = word_size
            hotword_set.updated_at = datetime.utcnow()
            self.session.flush()
            logger.info(f"Hotword set updated: {hotword_set_id}")
        return hotword_set

    def delete(self, hotword_set_id: str) -> bool:
        """删除热词集"""
        from src.database.models import HotwordSetRecord
        
        hotword_set = self.get_by_id(hotword_set_id)
        if hotword_set:
            self.session.delete(hotword_set)
            self.session.flush()
            logger.info(f"Hotword set deleted: {hotword_set_id}")
            return True
        return False
