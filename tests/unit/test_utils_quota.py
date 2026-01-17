# -*- coding: utf-8 -*-
"""Unit tests for quota manager."""

from datetime import datetime, timedelta

import pytest

from src.core.exceptions import QuotaExceededError, RateLimitError
from src.utils.quota import APIKeyInfo, KeyStatus, QuotaManager


class TestAPIKeyInfo:
    """测试 APIKeyInfo 数据类"""
    
    def test_create_key_info(self):
        """测试创建密钥信息"""
        key_info = APIKeyInfo(
            key="test_key_123",
            provider="gemini",
        )
        
        assert key_info.key == "test_key_123"
        assert key_info.provider == "gemini"
        assert key_info.status == KeyStatus.ACTIVE
        assert key_info.failure_count == 0
        assert key_info.total_requests == 0
    
    def test_key_info_with_quota(self):
        """测试带配额的密钥信息"""
        key_info = APIKeyInfo(
            key="test_key_123",
            provider="gemini",
            quota_limit=1000.0,
        )
        
        assert key_info.quota_limit == 1000.0
        assert key_info.quota_used == 0.0


class TestQuotaManager:
    """测试 QuotaManager"""
    
    @pytest.fixture
    def quota_manager(self):
        """创建配额管理器"""
        return QuotaManager(
            failure_threshold=3,
            circuit_open_duration=60,
            rate_limit_window=30,
        )
    
    def test_register_keys(self, quota_manager):
        """测试注册密钥"""
        keys = ["key1", "key2", "key3"]
        quota_manager.register_keys("gemini", keys, quota_limit=1000.0)
        
        assert "gemini" in quota_manager.provider_keys
        assert len(quota_manager.provider_keys["gemini"]) == 3
        
        # 检查密钥信息
        for idx, key in enumerate(keys):
            key_id = f"gemini:key{idx}"
            assert key_id in quota_manager.keys
            assert quota_manager.keys[key_id].quota_limit == 1000.0
    
    def test_get_available_key(self, quota_manager):
        """测试获取可用密钥"""
        keys = ["key1", "key2", "key3"]
        quota_manager.register_keys("gemini", keys)
        
        # 获取可用密钥
        available_key = quota_manager.get_available_key("gemini")
        assert available_key in keys
    
    def test_get_available_key_load_balancing(self, quota_manager):
        """测试负载均衡 - 选择最少使用的密钥"""
        keys = ["key1", "key2", "key3"]
        quota_manager.register_keys("gemini", keys)
        
        # 第一次调用,应该选择 key1 (都是 0 次)
        key1 = quota_manager.get_available_key("gemini")
        
        # 第二次调用,应该选择 key2 (key1 已经 1 次)
        key2 = quota_manager.get_available_key("gemini")
        
        # 第三次调用,应该选择 key3
        key3 = quota_manager.get_available_key("gemini")
        
        # 第四次调用,应该回到 key1 (都是 1 次)
        key4 = quota_manager.get_available_key("gemini")
        
        assert key1 != key2
        assert key2 != key3
        assert key1 == key4
    
    def test_record_success(self, quota_manager):
        """测试记录成功请求"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys)
        
        key_id = "gemini:key0"
        key_info = quota_manager.keys[key_id]
        
        # 模拟失败
        key_info.failure_count = 2
        
        # 记录成功
        quota_manager.record_success("gemini", "key1", quota_used=10.0)
        
        # 失败计数应该重置
        assert key_info.failure_count == 0
        assert key_info.quota_used == 10.0
    
    def test_record_success_quota_exceeded(self, quota_manager):
        """测试记录成功但配额超限"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys, quota_limit=100.0)
        
        key_id = "gemini:key0"
        key_info = quota_manager.keys[key_id]
        
        # 使用 90 配额
        quota_manager.record_success("gemini", "key1", quota_used=90.0)
        assert key_info.status == KeyStatus.ACTIVE
        
        # 再使用 20 配额,超过 100
        quota_manager.record_success("gemini", "key1", quota_used=20.0)
        assert key_info.status == KeyStatus.QUOTA_EXCEEDED
        assert key_info.quota_reset_at is not None
    
    def test_record_failure_rate_limit(self, quota_manager):
        """测试记录速率限制失败"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys)
        
        key_id = "gemini:key0"
        
        # 记录速率限制
        quota_manager.record_failure("gemini", "key1", error_type="rate_limit")
        
        key_info = quota_manager.keys[key_id]
        assert key_info.status == KeyStatus.RATE_LIMITED
        assert key_info.rate_limit_reset_at is not None
    
    def test_record_failure_quota_exceeded(self, quota_manager):
        """测试记录配额超限失败"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys)
        
        key_id = "gemini:key0"
        
        # 记录配额超限
        quota_manager.record_failure("gemini", "key1", error_type="quota_exceeded")
        
        key_info = quota_manager.keys[key_id]
        assert key_info.status == KeyStatus.QUOTA_EXCEEDED
        assert key_info.quota_reset_at is not None
    
    def test_record_failure_circuit_breaker(self, quota_manager):
        """测试熔断机制"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys)
        
        key_id = "gemini:key0"
        key_info = quota_manager.keys[key_id]
        
        # 记录 3 次失败(达到阈值)
        for i in range(3):
            quota_manager.record_failure("gemini", "key1", error_type="other")
        
        # 应该触发熔断
        assert key_info.status == KeyStatus.CIRCUIT_OPEN
        assert key_info.circuit_open_at is not None
        assert key_info.failure_count == 3
    
    def test_circuit_breaker_recovery(self, quota_manager):
        """测试熔断恢复"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys)
        
        key_id = "gemini:key0"
        key_info = quota_manager.keys[key_id]
        
        # 触发熔断
        for i in range(3):
            quota_manager.record_failure("gemini", "key1", error_type="other")
        
        assert key_info.status == KeyStatus.CIRCUIT_OPEN
        
        # 模拟时间过去(超过熔断持续时间)
        key_info.circuit_open_at = datetime.now() - timedelta(seconds=61)
        
        # 再次获取密钥,应该恢复
        available_key = quota_manager.get_available_key("gemini")
        assert available_key == "key1"
        assert key_info.status == KeyStatus.ACTIVE
        assert key_info.failure_count == 0
    
    def test_rate_limit_recovery(self, quota_manager):
        """测试速率限制恢复"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys)
        
        key_id = "gemini:key0"
        key_info = quota_manager.keys[key_id]
        
        # 触发速率限制
        quota_manager.record_failure("gemini", "key1", error_type="rate_limit")
        assert key_info.status == KeyStatus.RATE_LIMITED
        
        # 模拟时间过去(超过速率限制窗口)
        key_info.rate_limit_reset_at = datetime.now() - timedelta(seconds=1)
        
        # 再次获取密钥,应该恢复
        available_key = quota_manager.get_available_key("gemini")
        assert available_key == "key1"
        assert key_info.status == KeyStatus.ACTIVE
    
    def test_quota_recovery(self, quota_manager):
        """测试配额恢复"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys, quota_limit=100.0)
        
        key_id = "gemini:key0"
        key_info = quota_manager.keys[key_id]
        
        # 触发配额超限
        quota_manager.record_failure("gemini", "key1", error_type="quota_exceeded")
        assert key_info.status == KeyStatus.QUOTA_EXCEEDED
        
        # 模拟时间过去(配额重置)
        key_info.quota_reset_at = datetime.now() - timedelta(seconds=1)
        
        # 再次获取密钥,应该恢复
        available_key = quota_manager.get_available_key("gemini")
        assert available_key == "key1"
        assert key_info.status == KeyStatus.ACTIVE
        assert key_info.quota_used == 0.0
    
    def test_no_available_keys_quota_exceeded(self, quota_manager):
        """测试所有密钥配额超限"""
        keys = ["key1", "key2"]
        quota_manager.register_keys("gemini", keys)
        
        # 所有密钥都配额超限
        for key in keys:
            quota_manager.record_failure("gemini", key, error_type="quota_exceeded")
        
        # 应该抛出 QuotaExceededError
        with pytest.raises(QuotaExceededError):
            quota_manager.get_available_key("gemini")
    
    def test_no_available_keys_rate_limited(self, quota_manager):
        """测试所有密钥速率限制"""
        keys = ["key1", "key2"]
        quota_manager.register_keys("gemini", keys)
        
        # 所有密钥都速率限制
        for key in keys:
            quota_manager.record_failure("gemini", key, error_type="rate_limit")
        
        # 应该抛出 RateLimitError
        with pytest.raises(RateLimitError):
            quota_manager.get_available_key("gemini")
    
    def test_no_available_keys_circuit_open(self, quota_manager):
        """测试所有密钥熔断"""
        keys = ["key1", "key2"]
        quota_manager.register_keys("gemini", keys)
        
        # 所有密钥都熔断
        for key in keys:
            for i in range(3):
                quota_manager.record_failure("gemini", key, error_type="other")
        
        # 应该抛出 RateLimitError
        with pytest.raises(RateLimitError):
            quota_manager.get_available_key("gemini")
    
    def test_key_rotation_on_failure(self, quota_manager):
        """测试失败时自动切换密钥"""
        keys = ["key1", "key2", "key3"]
        quota_manager.register_keys("gemini", keys)
        
        # 第一个密钥失败
        key1 = quota_manager.get_available_key("gemini")
        quota_manager.record_failure("gemini", key1, error_type="rate_limit")
        
        # 应该切换到第二个密钥
        key2 = quota_manager.get_available_key("gemini")
        assert key2 != key1
        
        # 第二个密钥也失败
        quota_manager.record_failure("gemini", key2, error_type="rate_limit")
        
        # 应该切换到第三个密钥
        key3 = quota_manager.get_available_key("gemini")
        assert key3 != key1
        assert key3 != key2
    
    def test_get_provider_stats(self, quota_manager):
        """测试获取提供商统计信息"""
        keys = ["key1", "key2", "key3"]
        quota_manager.register_keys("gemini", keys)
        
        # 模拟一些操作
        quota_manager.get_available_key("gemini")
        quota_manager.record_success("gemini", "key1")
        quota_manager.record_failure("gemini", "key2", error_type="rate_limit")
        
        # 获取统计信息
        stats = quota_manager.get_provider_stats("gemini")
        
        assert stats["total_keys"] == 3
        assert stats["active_keys"] == 2
        assert stats["rate_limited_keys"] == 1
        assert stats["total_requests"] == 1
        assert stats["total_failures"] == 1
    
    def test_disable_enable_key(self, quota_manager):
        """测试禁用和启用密钥"""
        keys = ["key1", "key2"]
        quota_manager.register_keys("gemini", keys)
        
        # 禁用 key1
        quota_manager.disable_key("gemini", "key1")
        
        key_id = "gemini:key0"
        assert quota_manager.keys[key_id].status == KeyStatus.DISABLED
        
        # 获取可用密钥,应该是 key2
        available_key = quota_manager.get_available_key("gemini")
        assert available_key == "key2"
        
        # 启用 key1
        quota_manager.enable_key("gemini", "key1")
        assert quota_manager.keys[key_id].status == KeyStatus.ACTIVE
    
    def test_get_key_status(self, quota_manager):
        """测试获取密钥状态"""
        keys = ["key1"]
        quota_manager.register_keys("gemini", keys)
        
        # 初始状态
        status = quota_manager.get_key_status("gemini", "key1")
        assert status == KeyStatus.ACTIVE
        
        # 触发速率限制
        quota_manager.record_failure("gemini", "key1", error_type="rate_limit")
        status = quota_manager.get_key_status("gemini", "key1")
        assert status == KeyStatus.RATE_LIMITED
    
    def test_multiple_providers(self, quota_manager):
        """测试多个提供商"""
        quota_manager.register_keys("gemini", ["gemini_key1", "gemini_key2"])
        quota_manager.register_keys("volcano", ["volcano_key1", "volcano_key2"])
        
        # 获取不同提供商的密钥
        gemini_key = quota_manager.get_available_key("gemini")
        volcano_key = quota_manager.get_available_key("volcano")
        
        assert gemini_key.startswith("gemini")
        assert volcano_key.startswith("volcano")
        
        # 统计信息应该独立
        gemini_stats = quota_manager.get_provider_stats("gemini")
        volcano_stats = quota_manager.get_provider_stats("volcano")
        
        assert gemini_stats["total_keys"] == 2
        assert volcano_stats["total_keys"] == 2
