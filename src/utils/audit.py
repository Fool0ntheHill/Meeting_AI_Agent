# -*- coding: utf-8 -*-
"""审计日志工具"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, session: Session):
        """
        初始化审计日志记录器

        Args:
            session: 数据库会话
        """
        self.session = session

    def log_task_created(
        self,
        task_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录任务创建

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="task_created",
            resource_type="task",
            resource_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_task_updated(
        self,
        task_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录任务更新

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="task_updated",
            resource_type="task",
            resource_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_task_confirmed(
        self,
        task_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录任务确认

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="task_confirmed",
            resource_type="task",
            resource_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_artifact_generated(
        self,
        artifact_id: str,
        task_id: str,
        user_id: str,
        tenant_id: str,
        artifact_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录衍生内容生成

        Args:
            artifact_id: 衍生内容 ID
            task_id: 任务 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            artifact_type: 衍生内容类型
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        if details is None:
            details = {}
        details["task_id"] = task_id
        details["artifact_type"] = artifact_type

        return self._create_log(
            action="artifact_generated",
            resource_type="artifact",
            resource_id=artifact_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_api_call(
        self,
        provider: str,
        api_name: str,
        user_id: str,
        tenant_id: str,
        task_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录 API 调用

        Args:
            provider: 提供商名称
            api_name: API 名称
            user_id: 用户 ID
            tenant_id: 租户 ID
            task_id: 任务 ID (可选)
            success: 是否成功
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        if details is None:
            details = {}
        details["provider"] = provider
        details["api_name"] = api_name
        details["success"] = success
        if task_id:
            details["task_id"] = task_id

        return self._create_log(
            action="api_call",
            resource_type="api",
            resource_id=f"{provider}:{api_name}",
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_cost_usage(
        self,
        task_id: str,
        user_id: str,
        tenant_id: str,
        cost_amount: float,
        cost_currency: str = "USD",
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录成本使用

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            cost_amount: 成本金额
            cost_currency: 货币单位
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="cost_usage",
            resource_type="task",
            resource_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            cost_amount=cost_amount,
            cost_currency=cost_currency,
            details=details,
        )

    def log_hotword_created(
        self,
        hotword_set_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录热词集创建

        Args:
            hotword_set_id: 热词集 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="hotword_created",
            resource_type="hotword_set",
            resource_id=hotword_set_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_hotword_deleted(
        self,
        hotword_set_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录热词集删除

        Args:
            hotword_set_id: 热词集 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="hotword_deleted",
            resource_type="hotword_set",
            resource_id=hotword_set_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_template_created(
        self,
        template_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录提示词模板创建

        Args:
            template_id: 模板 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="template_created",
            resource_type="prompt_template",
            resource_id=template_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_template_updated(
        self,
        template_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录提示词模板更新

        Args:
            template_id: 模板 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="template_updated",
            resource_type="prompt_template",
            resource_id=template_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def log_template_deleted(
        self,
        template_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录提示词模板删除

        Args:
            template_id: 模板 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息

        Returns:
            str: 日志 ID
        """
        return self._create_log(
            action="template_deleted",
            resource_type="prompt_template",
            resource_id=template_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
        )

    def _create_log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        tenant_id: str,
        details: Optional[Dict[str, Any]] = None,
        cost_amount: Optional[float] = None,
        cost_currency: str = "USD",
    ) -> str:
        """
        创建审计日志记录

        Args:
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源 ID
            user_id: 用户 ID
            tenant_id: 租户 ID
            details: 详细信息
            cost_amount: 成本金额
            cost_currency: 货币单位

        Returns:
            str: 日志 ID
        """
        from src.database.models import AuditLogRecord
        import json

        log_id = str(uuid.uuid4())

        log_record = AuditLogRecord(
            log_id=log_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            tenant_id=tenant_id,
            details=json.dumps(details, ensure_ascii=False) if details is not None else None,
            cost_amount=cost_amount,
            cost_currency=cost_currency,
        )

        self.session.add(log_record)
        self.session.flush()

        logger.info(
            f"Audit log created: {action} on {resource_type}:{resource_id} by {user_id}"
        )

        return log_id
