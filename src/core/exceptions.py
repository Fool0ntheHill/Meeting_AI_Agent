"""Exception hierarchy for the Meeting Minutes Agent."""

from typing import Optional


class MeetingAgentError(Exception):
    """基础异常类"""

    def __init__(
        self, message: str, provider: Optional[str] = None, details: Optional[dict] = None
    ):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(self.message)


# ============================================================================
# ASR Errors
# ============================================================================


class ASRError(MeetingAgentError):
    """ASR 相关错误"""

    pass


class SensitiveContentError(ASRError):
    """敏感内容被屏蔽"""

    pass


class AudioFormatError(ASRError):
    """音频格式错误"""

    pass


class AudioTooLongError(ASRError):
    """音频时长超限"""

    pass


# ============================================================================
# Voiceprint Errors
# ============================================================================


class VoiceprintError(MeetingAgentError):
    """声纹识别相关错误"""

    pass


class VoiceprintNotFoundError(VoiceprintError):
    """声纹未找到"""

    pass


class VoiceprintQualityError(VoiceprintError):
    """声纹质量不足"""

    pass


# ============================================================================
# LLM Errors
# ============================================================================


class LLMError(MeetingAgentError):
    """LLM 相关错误"""

    pass


class LLMResponseParseError(LLMError):
    """LLM 响应解析错误"""

    pass


class LLMTokenLimitError(LLMError):
    """LLM Token 超限"""

    pass


# ============================================================================
# Configuration Errors
# ============================================================================


class ConfigurationError(MeetingAgentError):
    """配置错误"""

    pass


class MissingConfigError(ConfigurationError):
    """缺少必需配置"""

    pass


class InvalidConfigError(ConfigurationError):
    """无效配置"""

    pass


# ============================================================================
# Authentication Errors
# ============================================================================


class AuthenticationError(MeetingAgentError):
    """认证错误"""

    pass


class InvalidAPIKeyError(AuthenticationError):
    """无效的 API Key"""

    pass


class ExpiredAPIKeyError(AuthenticationError):
    """API Key 已过期"""

    pass


# ============================================================================
# Rate Limit & Quota Errors
# ============================================================================


class RateLimitError(MeetingAgentError):
    """速率限制错误"""

    pass


class QuotaExceededError(MeetingAgentError):
    """配额超限错误"""

    def __init__(self, provider: str, quota_type: str):
        super().__init__(
            message=f"{provider} 配额已超限: {quota_type}",
            provider=provider,
            details={"quota_type": quota_type},
        )


# ============================================================================
# Storage Errors
# ============================================================================


class StorageError(MeetingAgentError):
    """存储相关错误"""

    pass


class FileNotFoundError(StorageError):
    """文件未找到"""

    pass


class UploadError(StorageError):
    """上传失败"""

    pass


class DownloadError(StorageError):
    """下载失败"""

    pass


# ============================================================================
# Task Errors
# ============================================================================


class TaskError(MeetingAgentError):
    """任务相关错误"""

    pass


class TaskNotFoundError(TaskError):
    """任务未找到"""

    pass


class TaskStateError(TaskError):
    """任务状态错误"""

    pass


class TaskTimeoutError(TaskError):
    """任务超时"""

    pass


# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(MeetingAgentError):
    """验证错误"""

    pass


class InvalidInputError(ValidationError):
    """无效输入"""

    pass


class InvalidParameterError(ValidationError):
    """无效参数"""

    pass


# ============================================================================
# Provider Errors
# ============================================================================


class ProviderError(MeetingAgentError):
    """提供商错误"""

    pass


class ProviderUnavailableError(ProviderError):
    """提供商不可用"""

    pass


class ProviderTimeoutError(ProviderError):
    """提供商超时"""

    pass
