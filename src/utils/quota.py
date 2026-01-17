# -*- coding: utf-8 -*-
"""配额管理和熔断机制实现"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from src.core.exceptions import QuotaExceededError, RateLimitError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class KeyStatus(Enum):
    """API 密钥状态"""
    ACTIVE = "active"  # 正常可用
    RATE_LIMITED = "rate_limited"  # 速率限制中
    QUOTA_EXCEEDED = "quota_exceeded"  # 配额超限
    CIRCUIT_OPEN = "circuit_open"  # 熔断开启
    DISABLED = "disabled"  # 已禁用


@dataclass
class APIKeyInfo:
    """API 密钥信息"""
    key: str
    provider: str
    status: KeyStatus = KeyStatus.ACTIVE
    
    # 速率限制相关
    rate_limit_reset_at: Optional[datetime] = None
    rate_limit_count: int = 0
    
    # 配额相关
    quota_used: float = 0.0  # 已使用配额
    quota_limit: Optional[float] = None  # 配额上限
    quota_reset_at: Optional[datetime] = None  # 配额重置时间
    
    # 熔断相关
    failure_count: int = 0  # 连续失败次数
    circuit_open_at: Optional[datetime] = None  # 熔断开启时间
    circuit_open_duration: int = 300  # 熔断持续时间(秒),默认 5 分钟
    
    # 统计信息
    total_requests: int = 0
    total_failures: int = 0
    last_used_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


class QuotaManager:
    """配额管理器 - 统一管理 API 密钥的配额、速率限制和熔断"""
    
    def __init__(
        self,
        failure_threshold: int = 5,  # 连续失败多少次触发熔断
        circuit_open_duration: int = 300,  # 熔断持续时间(秒)
        rate_limit_window: int = 60,  # 速率限制窗口(秒)
    ):
        """
        初始化配额管理器
        
        Args:
            failure_threshold: 连续失败阈值
            circuit_open_duration: 熔断持续时间(秒)
            rate_limit_window: 速率限制窗口(秒)
        """
        self.failure_threshold = failure_threshold
        self.circuit_open_duration = circuit_open_duration
        self.rate_limit_window = rate_limit_window
        
        # 存储所有 API 密钥信息
        self.keys: Dict[str, APIKeyInfo] = {}
        
        # 按提供商分组的密钥索引
        self.provider_keys: Dict[str, List[str]] = {}
        
        logger.info(
            f"QuotaManager initialized: failure_threshold={failure_threshold}, "
            f"circuit_open_duration={circuit_open_duration}s"
        )
    
    def register_keys(
        self,
        provider: str,
        keys: List[str],
        quota_limit: Optional[float] = None,
    ) -> None:
        """
        注册 API 密钥
        
        Args:
            provider: 提供商名称
            keys: API 密钥列表
            quota_limit: 配额上限(可选)
        """
        if provider not in self.provider_keys:
            self.provider_keys[provider] = []
        
        for idx, key in enumerate(keys):
            # 使用 provider:index 作为唯一标识
            key_id = f"{provider}:key{idx}"
            
            if key_id not in self.keys:
                self.keys[key_id] = APIKeyInfo(
                    key=key,
                    provider=provider,
                    quota_limit=quota_limit,
                    circuit_open_duration=self.circuit_open_duration,
                )
                self.provider_keys[provider].append(key_id)
                logger.info(f"Registered API key: {key_id}")
    
    def get_available_key(self, provider: str) -> Optional[str]:
        """
        获取可用的 API 密钥
        
        Args:
            provider: 提供商名称
        
        Returns:
            Optional[str]: 可用的 API 密钥,如果没有则返回 None
        
        Raises:
            QuotaExceededError: 所有密钥配额超限
            RateLimitError: 所有密钥速率限制中
        """
        if provider not in self.provider_keys:
            logger.warning(f"No keys registered for provider: {provider}")
            return None
        
        key_ids = self.provider_keys[provider]
        now = datetime.now()
        
        # 尝试找到可用的密钥
        available_keys = []
        rate_limited_keys = []
        quota_exceeded_keys = []
        circuit_open_keys = []
        
        for key_id in key_ids:
            key_info = self.keys[key_id]
            
            # 检查熔断状态
            if key_info.status == KeyStatus.CIRCUIT_OPEN:
                if key_info.circuit_open_at:
                    elapsed = (now - key_info.circuit_open_at).total_seconds()
                    if elapsed >= key_info.circuit_open_duration:
                        # 熔断时间已过,恢复为 ACTIVE
                        key_info.status = KeyStatus.ACTIVE
                        key_info.failure_count = 0
                        key_info.circuit_open_at = None
                        logger.info(f"Circuit closed for key: {key_id}")
                    else:
                        circuit_open_keys.append(key_id)
                        continue
            
            # 检查速率限制
            if key_info.status == KeyStatus.RATE_LIMITED:
                if key_info.rate_limit_reset_at and now >= key_info.rate_limit_reset_at:
                    # 速率限制已过期,恢复为 ACTIVE
                    key_info.status = KeyStatus.ACTIVE
                    key_info.rate_limit_count = 0
                    key_info.rate_limit_reset_at = None
                    logger.info(f"Rate limit reset for key: {key_id}")
                else:
                    rate_limited_keys.append(key_id)
                    continue
            
            # 检查配额
            if key_info.status == KeyStatus.QUOTA_EXCEEDED:
                if key_info.quota_reset_at and now >= key_info.quota_reset_at:
                    # 配额已重置
                    key_info.status = KeyStatus.ACTIVE
                    key_info.quota_used = 0.0
                    key_info.quota_reset_at = None
                    logger.info(f"Quota reset for key: {key_id}")
                else:
                    quota_exceeded_keys.append(key_id)
                    continue
            
            # 检查是否禁用
            if key_info.status == KeyStatus.DISABLED:
                continue
            
            # 可用密钥
            if key_info.status == KeyStatus.ACTIVE:
                available_keys.append((key_id, key_info))
        
        # 如果有可用密钥,选择最少使用的
        if available_keys:
            # 按使用次数排序,选择最少使用的
            available_keys.sort(key=lambda x: x[1].total_requests)
            key_id, key_info = available_keys[0]
            
            # 更新使用信息
            key_info.last_used_at = now
            key_info.total_requests += 1
            
            logger.debug(f"Selected key: {key_id} (total_requests={key_info.total_requests})")
            return key_info.key
        
        # 没有可用密钥,抛出异常
        if quota_exceeded_keys:
            raise QuotaExceededError(
                provider=provider,
                quota_type="all_keys_quota_exceeded"
            )
        elif rate_limited_keys:
            raise RateLimitError(
                message=f"All API keys for {provider} are rate limited",
                provider=provider,
                details={"rate_limited_keys": len(rate_limited_keys)}
            )
        elif circuit_open_keys:
            raise RateLimitError(
                message=f"All API keys for {provider} are in circuit breaker state",
                provider=provider,
                details={"circuit_open_keys": len(circuit_open_keys)}
            )
        else:
            logger.warning(f"No available keys for provider: {provider}")
            return None
    
    def record_success(self, provider: str, key: str, quota_used: float = 0.0) -> None:
        """
        记录成功请求
        
        Args:
            provider: 提供商名称
            key: API 密钥
            quota_used: 本次请求使用的配额
        """
        # 查找匹配的 key_id
        key_id = self._find_key_id(provider, key)
        
        if not key_id:
            logger.warning(f"Key not registered: {key_id}")
            return
        
        key_info = self.keys[key_id]
        
        # 重置失败计数
        key_info.failure_count = 0
        
        # 更新配额使用
        if quota_used > 0:
            key_info.quota_used += quota_used
            
            # 检查是否超过配额
            if key_info.quota_limit and key_info.quota_used >= key_info.quota_limit:
                key_info.status = KeyStatus.QUOTA_EXCEEDED
                # 设置配额重置时间(假设每月重置)
                key_info.quota_reset_at = datetime.now() + timedelta(days=30)
                logger.warning(
                    f"Quota exceeded for key: {key_id} "
                    f"(used={key_info.quota_used}, limit={key_info.quota_limit})"
                )
        
        logger.debug(f"Recorded success for key: {key_id}")
    
    def record_failure(
        self,
        provider: str,
        key: str,
        error_type: str,
        reset_at: Optional[datetime] = None
    ) -> None:
        """
        记录失败请求
        
        Args:
            provider: 提供商名称
            key: API 密钥
            error_type: 错误类型 (rate_limit, quota_exceeded, other)
            reset_at: 限制重置时间(可选)
        """
        # 查找匹配的 key_id
        key_id = self._find_key_id(provider, key)
        
        if not key_id:
            logger.warning(f"Key not registered: {key_id}")
            return
        
        key_info = self.keys[key_id]
        key_info.total_failures += 1
        
        if error_type == "rate_limit":
            # 速率限制
            key_info.status = KeyStatus.RATE_LIMITED
            key_info.rate_limit_count += 1
            key_info.rate_limit_reset_at = reset_at or (
                datetime.now() + timedelta(seconds=self.rate_limit_window)
            )
            logger.warning(
                f"Rate limit hit for key: {key_id}, "
                f"reset_at={key_info.rate_limit_reset_at}"
            )
        
        elif error_type == "quota_exceeded":
            # 配额超限
            key_info.status = KeyStatus.QUOTA_EXCEEDED
            key_info.quota_reset_at = reset_at or (
                datetime.now() + timedelta(days=30)
            )
            logger.warning(
                f"Quota exceeded for key: {key_id}, "
                f"reset_at={key_info.quota_reset_at}"
            )
        
        else:
            # 其他错误,增加失败计数
            key_info.failure_count += 1
            
            # 检查是否触发熔断
            if key_info.failure_count >= self.failure_threshold:
                key_info.status = KeyStatus.CIRCUIT_OPEN
                key_info.circuit_open_at = datetime.now()
                logger.warning(
                    f"Circuit breaker opened for key: {key_id} "
                    f"(failures={key_info.failure_count})"
                )
    
    def _find_key_id(self, provider: str, key: str) -> Optional[str]:
        """
        查找密钥 ID
        
        Args:
            provider: 提供商名称
            key: API 密钥
        
        Returns:
            Optional[str]: 密钥 ID
        """
        if provider not in self.provider_keys:
            return None
        
        for key_id in self.provider_keys[provider]:
            if self.keys[key_id].key == key:
                return key_id
        
        return None
    
    def get_key_status(self, provider: str, key: str) -> Optional[KeyStatus]:
        """
        获取密钥状态
        
        Args:
            provider: 提供商名称
            key: API 密钥
        
        Returns:
            Optional[KeyStatus]: 密钥状态
        """
        key_id = self._find_key_id(provider, key)
        
        if not key_id:
            return None
        
        return self.keys[key_id].status
    
    def get_provider_stats(self, provider: str) -> Dict:
        """
        获取提供商统计信息
        
        Args:
            provider: 提供商名称
        
        Returns:
            Dict: 统计信息
        """
        if provider not in self.provider_keys:
            return {}
        
        key_ids = self.provider_keys[provider]
        
        stats = {
            "total_keys": len(key_ids),
            "active_keys": 0,
            "rate_limited_keys": 0,
            "quota_exceeded_keys": 0,
            "circuit_open_keys": 0,
            "disabled_keys": 0,
            "total_requests": 0,
            "total_failures": 0,
        }
        
        for key_id in key_ids:
            key_info = self.keys[key_id]
            
            if key_info.status == KeyStatus.ACTIVE:
                stats["active_keys"] += 1
            elif key_info.status == KeyStatus.RATE_LIMITED:
                stats["rate_limited_keys"] += 1
            elif key_info.status == KeyStatus.QUOTA_EXCEEDED:
                stats["quota_exceeded_keys"] += 1
            elif key_info.status == KeyStatus.CIRCUIT_OPEN:
                stats["circuit_open_keys"] += 1
            elif key_info.status == KeyStatus.DISABLED:
                stats["disabled_keys"] += 1
            
            stats["total_requests"] += key_info.total_requests
            stats["total_failures"] += key_info.total_failures
        
        return stats
    
    def disable_key(self, provider: str, key: str) -> None:
        """
        禁用密钥
        
        Args:
            provider: 提供商名称
            key: API 密钥
        """
        key_id = self._find_key_id(provider, key)
        
        if not key_id:
            logger.warning(f"Key not registered: {provider}:{key[:8]}")
            return
        
        self.keys[key_id].status = KeyStatus.DISABLED
        logger.info(f"Disabled key: {key_id}")
    
    def enable_key(self, provider: str, key: str) -> None:
        """
        启用密钥
        
        Args:
            provider: 提供商名称
            key: API 密钥
        """
        key_id = self._find_key_id(provider, key)
        
        if not key_id:
            logger.warning(f"Key not registered: {provider}:{key[:8]}")
            return
        
        key_info = self.keys[key_id]
        key_info.status = KeyStatus.ACTIVE
        key_info.failure_count = 0
        key_info.circuit_open_at = None
        logger.info(f"Enabled key: {key_id}")
