"""Artifact generation service implementation."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.core.exceptions import LLMError, ValidationError
from src.core.models import (
    GeneratedArtifact,
    OutputLanguage,
    PromptInstance,
    PromptTemplate,
    TranscriptionResult,
)
from src.core.providers import LLMProvider

logger = logging.getLogger(__name__)


class ArtifactGenerationService:
    """
    衍生内容生成服务
    
    支持多类型 Artifact 生成(会议纪要、行动项、摘要笔记等)。
    使用提示词模板系统,支持参数注入和多语言。
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        template_repo=None,
        artifact_repo=None,
    ):
        """
        初始化服务
        
        Args:
            llm_provider: LLM 提供商
            template_repo: 提示词模板仓库(可选,Phase 1 可为 None)
            artifact_repo: 衍生内容仓库(可选,Phase 1 可为 None)
        """
        self.llm = llm_provider
        self.templates = template_repo
        self.artifacts = artifact_repo

    async def generate_artifact(
        self,
        task_id: str,
        transcript: TranscriptionResult,
        artifact_type: str,
        prompt_instance: PromptInstance,
        output_language: OutputLanguage = OutputLanguage.ZH_CN,
        user_id: str = "system",
        template: Optional[PromptTemplate] = None,
        **kwargs,
    ) -> GeneratedArtifact:
        """
        生成衍生内容
        
        流程:
        1. 获取提示词模板
        2. 验证语言支持
        3. 构建完整 Prompt (模板 + 参数 + 转写文本)
        4. 调用 LLM 生成内容
        5. 获取下一个版本号
        6. 创建新版本记录
        7. 保存到数据库(如果有 repo)
        8. 返回生成结果
        
        Args:
            task_id: 任务 ID
            transcript: 转写结果
            artifact_type: 内容类型(meeting_minutes/action_items/summary_notes)
            prompt_instance: 提示词实例
            output_language: 输出语言
            user_id: 创建者 ID
            template: 提示词模板(可选,如果不提供则从 repo 获取)
            **kwargs: 其他参数
            
        Returns:
            GeneratedArtifact: 生成的衍生内容
            
        Raises:
            ValidationError: 模板不存在或语言不支持
            LLMError: LLM 生成失败
        """
        try:
            # 1. 获取模板
            if template is None:
                if self.templates is None:
                    raise ValidationError("Template repository not configured")
                template = await self.templates.get(prompt_instance.template_id)
                if not template:
                    raise ValidationError(f"模板不存在: {prompt_instance.template_id}")
            
            # 2. 验证语言支持
            if prompt_instance.language not in template.supported_languages:
                raise ValidationError(
                    f"模板不支持语言: {prompt_instance.language}. "
                    f"支持的语言: {template.supported_languages}"
                )
            
            # 3. 获取下一个版本号
            next_version = await self._get_next_version(task_id, artifact_type)
            
            # 4. 调用 LLM 生成内容
            artifact = await self.llm.generate_artifact(
                transcript=transcript,
                prompt_instance=prompt_instance,
                output_language=output_language,
                template=template,
                task_id=task_id,
                artifact_id=f"art_{task_id}_{artifact_type}_v{next_version}",
                version=next_version,
                created_by=user_id,
                **kwargs,
            )
            
            # 5. 保存到数据库(如果有 repo)
            if self.artifacts is not None:
                await self.artifacts.create(artifact)
                logger.info(
                    f"Saved artifact to repository: {artifact.artifact_id}, "
                    f"type={artifact.artifact_type}, version={artifact.version}"
                )
            
            logger.info(
                f"Generated artifact: task_id={task_id}, type={artifact_type}, "
                f"version={next_version}, language={prompt_instance.language}"
            )
            
            return artifact
            
        except (ValidationError, LLMError):
            raise
        except Exception as e:
            logger.error(f"Failed to generate artifact: {e}", exc_info=True)
            raise LLMError(f"生成衍生内容失败: {e}", provider="artifact_generation")

    async def _get_next_version(self, task_id: str, artifact_type: str) -> int:
        """
        获取下一个版本号
        
        Args:
            task_id: 任务 ID
            artifact_type: 内容类型
            
        Returns:
            int: 下一个版本号
        """
        # 如果没有 artifact_repo,默认返回版本 1
        if self.artifacts is None:
            return 1
        
        try:
            latest_version = await self.artifacts.get_latest_version(
                task_id=task_id, artifact_type=artifact_type
            )
            return (latest_version.version + 1) if latest_version else 1
        except Exception as e:
            logger.warning(f"Failed to get latest version, defaulting to 1: {e}")
            return 1

    async def list_artifacts(
        self, task_id: str
    ) -> Dict[str, List[GeneratedArtifact]]:
        """
        列出任务的所有衍生内容,按类型分组
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Dict[str, List[GeneratedArtifact]]: 按类型分组的衍生内容
            
        Raises:
            ValidationError: 仓库未配置
        """
        if self.artifacts is None:
            raise ValidationError("Artifact repository not configured")
        
        artifacts = await self.artifacts.list_by_task(task_id)
        
        # 按类型分组
        grouped = {}
        for artifact in artifacts:
            if artifact.artifact_type not in grouped:
                grouped[artifact.artifact_type] = []
            grouped[artifact.artifact_type].append(artifact)
        
        # 每个类型内按版本号排序(最新版本在前)
        for artifact_type in grouped:
            grouped[artifact_type].sort(key=lambda a: a.version, reverse=True)
        
        return grouped

    async def get_versions(
        self, task_id: str, artifact_type: str
    ) -> List[GeneratedArtifact]:
        """
        获取特定类型的所有版本
        
        Args:
            task_id: 任务 ID
            artifact_type: 内容类型
            
        Returns:
            List[GeneratedArtifact]: 版本列表(最新版本在前)
            
        Raises:
            ValidationError: 仓库未配置
        """
        if self.artifacts is None:
            raise ValidationError("Artifact repository not configured")
        
        versions = await self.artifacts.list_by_type(task_id, artifact_type)
        return sorted(versions, key=lambda v: v.version, reverse=True)

    def _extract_participants(self, transcript: TranscriptionResult) -> List[str]:
        """
        从转写结果中提取参与者列表
        
        Args:
            transcript: 转写结果
            
        Returns:
            List[str]: 参与者列表(去重)
        """
        participants = set()
        for segment in transcript.segments:
            if segment.speaker:
                participants.add(segment.speaker)
        return sorted(list(participants))
