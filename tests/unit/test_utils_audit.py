# -*- coding: utf-8 -*-
"""审计日志工具单元测试"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.utils.audit import AuditLogger


@pytest.fixture
def mock_session():
    """创建模拟数据库会话"""
    session = Mock()
    session.add = Mock()
    session.flush = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def audit_logger(mock_session):
    """创建审计日志记录器"""
    return AuditLogger(mock_session)


class TestAuditLogger:
    """审计日志记录器测试"""

    def test_log_task_created(self, audit_logger, mock_session):
        """测试记录任务创建"""
        log_id = audit_logger.log_task_created(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"meeting_type": "daily_standup"},
        )

        # 验证日志 ID 生成
        assert log_id is not None
        assert isinstance(log_id, str)

        # 验证数据库操作
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # 验证日志记录内容
        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "task_created"
        assert log_record.resource_type == "task"
        assert log_record.resource_id == "task-123"
        assert log_record.user_id == "user-456"
        assert log_record.tenant_id == "tenant-789"

    def test_log_task_updated(self, audit_logger, mock_session):
        """测试记录任务更新"""
        log_id = audit_logger.log_task_updated(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"state": "processing", "progress": 0.5},
        )

        assert log_id is not None
        mock_session.add.assert_called_once()

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "task_updated"
        assert log_record.resource_type == "task"

    def test_log_task_confirmed(self, audit_logger, mock_session):
        """测试记录任务确认"""
        log_id = audit_logger.log_task_confirmed(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"confirmed_by_name": "张三"},
        )

        assert log_id is not None
        mock_session.add.assert_called_once()

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "task_confirmed"
        assert log_record.resource_type == "task"

    def test_log_artifact_generated(self, audit_logger, mock_session):
        """测试记录衍生内容生成"""
        log_id = audit_logger.log_artifact_generated(
            artifact_id="artifact-123",
            task_id="task-456",
            user_id="user-789",
            tenant_id="tenant-012",
            artifact_type="meeting_minutes",
            details={"version": 1},
        )

        assert log_id is not None
        mock_session.add.assert_called_once()

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "artifact_generated"
        assert log_record.resource_type == "artifact"
        assert log_record.resource_id == "artifact-123"

        # 验证 details 包含 task_id 和 artifact_type
        import json
        details = json.loads(log_record.details)
        assert details["task_id"] == "task-456"
        assert details["artifact_type"] == "meeting_minutes"
        assert details["version"] == 1

    def test_log_api_call_success(self, audit_logger, mock_session):
        """测试记录成功的 API 调用"""
        log_id = audit_logger.log_api_call(
            provider="gemini",
            api_name="generate_content",
            user_id="user-123",
            tenant_id="tenant-456",
            task_id="task-789",
            success=True,
            details={"duration_ms": 1500},
        )

        assert log_id is not None
        mock_session.add.assert_called_once()

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "api_call"
        assert log_record.resource_type == "api"
        assert log_record.resource_id == "gemini:generate_content"

        # 验证 details
        import json
        details = json.loads(log_record.details)
        assert details["provider"] == "gemini"
        assert details["api_name"] == "generate_content"
        assert details["success"] is True
        assert details["task_id"] == "task-789"
        assert details["duration_ms"] == 1500

    def test_log_api_call_failure(self, audit_logger, mock_session):
        """测试记录失败的 API 调用"""
        log_id = audit_logger.log_api_call(
            provider="volcano",
            api_name="submit_transcription",
            user_id="user-123",
            tenant_id="tenant-456",
            success=False,
            details={"error": "rate_limit"},
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        import json
        details = json.loads(log_record.details)
        assert details["success"] is False
        assert details["error"] == "rate_limit"

    def test_log_cost_usage(self, audit_logger, mock_session):
        """测试记录成本使用"""
        log_id = audit_logger.log_cost_usage(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            cost_amount=0.05,
            cost_currency="USD",
            details={"asr_cost": 0.02, "llm_cost": 0.03},
        )

        assert log_id is not None
        mock_session.add.assert_called_once()

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "cost_usage"
        assert log_record.resource_type == "task"
        assert log_record.resource_id == "task-123"
        assert log_record.cost_amount == 0.05
        assert log_record.cost_currency == "USD"

    def test_log_hotword_created(self, audit_logger, mock_session):
        """测试记录热词集创建"""
        log_id = audit_logger.log_hotword_created(
            hotword_set_id="hotword-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"name": "医疗术语", "word_count": 100},
        )

        assert log_id is not None
        mock_session.add.assert_called_once()

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "hotword_created"
        assert log_record.resource_type == "hotword_set"
        assert log_record.resource_id == "hotword-123"

    def test_log_hotword_deleted(self, audit_logger, mock_session):
        """测试记录热词集删除"""
        log_id = audit_logger.log_hotword_deleted(
            hotword_set_id="hotword-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"name": "医疗术语"},
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "hotword_deleted"
        assert log_record.resource_type == "hotword_set"

    def test_log_template_created(self, audit_logger, mock_session):
        """测试记录提示词模板创建"""
        log_id = audit_logger.log_template_created(
            template_id="template-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"title": "自定义摘要模板"},
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "template_created"
        assert log_record.resource_type == "prompt_template"

    def test_log_template_updated(self, audit_logger, mock_session):
        """测试记录提示词模板更新"""
        log_id = audit_logger.log_template_updated(
            template_id="template-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"updated_fields": ["title", "prompt_body"]},
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "template_updated"

    def test_log_template_deleted(self, audit_logger, mock_session):
        """测试记录提示词模板删除"""
        log_id = audit_logger.log_template_deleted(
            template_id="template-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        assert log_record.action == "template_deleted"

    def test_log_without_details(self, audit_logger, mock_session):
        """测试不带详细信息的日志记录"""
        log_id = audit_logger.log_task_created(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        assert log_record.details is None

    def test_log_with_empty_details(self, audit_logger, mock_session):
        """测试带空详细信息的日志记录"""
        log_id = audit_logger.log_task_created(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={},
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        # 空字典应该被序列化为 JSON
        assert log_record.details == "{}"

    def test_log_with_complex_details(self, audit_logger, mock_session):
        """测试带复杂详细信息的日志记录"""
        complex_details = {
            "nested": {
                "field1": "value1",
                "field2": [1, 2, 3],
            },
            "list": ["a", "b", "c"],
            "number": 123,
            "boolean": True,
            "null": None,
        }

        log_id = audit_logger.log_task_created(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details=complex_details,
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        import json
        parsed_details = json.loads(log_record.details)
        assert parsed_details == complex_details

    def test_log_with_chinese_characters(self, audit_logger, mock_session):
        """测试带中文字符的日志记录"""
        log_id = audit_logger.log_task_created(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            details={"会议类型": "每日站会", "参与者": ["张三", "李四"]},
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        import json
        parsed_details = json.loads(log_record.details)
        assert parsed_details["会议类型"] == "每日站会"
        assert "张三" in parsed_details["参与者"]

    def test_multiple_logs_different_ids(self, audit_logger, mock_session):
        """测试多次记录生成不同的日志 ID"""
        log_id1 = audit_logger.log_task_created(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        log_id2 = audit_logger.log_task_created(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        # 每次调用应该生成不同的日志 ID
        assert log_id1 != log_id2

    def test_log_cost_with_default_currency(self, audit_logger, mock_session):
        """测试使用默认货币的成本记录"""
        log_id = audit_logger.log_cost_usage(
            task_id="task-123",
            user_id="user-456",
            tenant_id="tenant-789",
            cost_amount=0.05,
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        assert log_record.cost_currency == "USD"

    def test_log_api_call_without_task_id(self, audit_logger, mock_session):
        """测试不带任务 ID 的 API 调用记录"""
        log_id = audit_logger.log_api_call(
            provider="gemini",
            api_name="generate_content",
            user_id="user-123",
            tenant_id="tenant-456",
            success=True,
        )

        assert log_id is not None

        log_record = mock_session.add.call_args[0][0]
        import json
        details = json.loads(log_record.details)
        assert "task_id" not in details


class TestAuditLogRepository:
    """审计日志仓库测试"""

    def test_get_by_user(self):
        """测试获取用户的审计日志"""
        from src.database.repositories import AuditLogRepository
        from src.database.models import AuditLogRecord

        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        repo = AuditLogRepository(mock_session)
        logs = repo.get_by_user("user-123")

        assert logs == []
        mock_session.query.assert_called_once_with(AuditLogRecord)

    def test_get_by_user_with_filters(self):
        """测试带过滤条件获取用户的审计日志"""
        from src.database.repositories import AuditLogRepository

        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        repo = AuditLogRepository(mock_session)
        logs = repo.get_by_user(
            "user-123",
            action="task_created",
            resource_type="task",
            limit=50,
            offset=10,
        )

        assert logs == []
        # 验证过滤条件被应用
        assert mock_query.filter.call_count >= 1

    def test_get_by_tenant(self):
        """测试获取租户的审计日志"""
        from src.database.repositories import AuditLogRepository

        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        repo = AuditLogRepository(mock_session)
        logs = repo.get_by_tenant("tenant-456")

        assert logs == []

    def test_get_by_resource(self):
        """测试获取资源的审计日志"""
        from src.database.repositories import AuditLogRepository

        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        repo = AuditLogRepository(mock_session)
        logs = repo.get_by_resource("task", "task-123")

        assert logs == []

    def test_get_cost_summary_no_data(self):
        """测试获取成本汇总 - 无数据"""
        from src.database.repositories import AuditLogRepository

        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = (None,)

        repo = AuditLogRepository(mock_session)
        summary = repo.get_cost_summary()

        assert summary["total_cost"] == 0.0
        assert summary["currency"] == "USD"

    def test_get_cost_summary_with_data(self):
        """测试获取成本汇总 - 有数据"""
        from src.database.repositories import AuditLogRepository

        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = (123.45,)

        repo = AuditLogRepository(mock_session)
        summary = repo.get_cost_summary(user_id="user-123")

        assert summary["total_cost"] == 123.45
        assert summary["currency"] == "USD"

    def test_get_cost_summary_by_tenant(self):
        """测试按租户获取成本汇总"""
        from src.database.repositories import AuditLogRepository

        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = (456.78,)

        repo = AuditLogRepository(mock_session)
        summary = repo.get_cost_summary(tenant_id="tenant-456")

        assert summary["total_cost"] == 456.78
