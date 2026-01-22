# -*- coding: utf-8 -*-
"""
错误码定义

为前端提供结构化的错误信息，便于：
1. 友好的用户提示
2. 错误分类和统计
3. 自动重试判断
4. 企微告警推送
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """错误码枚举"""
    
    # ============================================================================
    # 网络/基础设施错误 (可重试)
    # ============================================================================
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    """网络超时 - 上游服务或内网请求超时"""
    
    NETWORK_DNS = "NETWORK_DNS"
    """DNS解析失败 - 域名无法解析"""
    
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    """存储不可用 - 对象存储或磁盘暂时不可用"""
    
    # ============================================================================
    # 鉴权/配额错误 (需检查配置)
    # ============================================================================
    AUTH_FAILED = "AUTH_FAILED"
    """鉴权失败 - AK/SK/JWT/Token 校验失败"""
    
    PERMISSION_DENIED = "PERMISSION_DENIED"
    """权限不足 - 无权访问该资源"""
    
    RATE_LIMITED = "RATE_LIMITED"
    """频率限制 - 请求频率或配额超限"""
    
    BILLING_EXCEEDED = "BILLING_EXCEEDED"
    """账单超限 - 余额不足或账期限制"""
    
    # ============================================================================
    # 输入/数据问题 (需用户处理)
    # ============================================================================
    INPUT_MISSING_FILE = "INPUT_MISSING_FILE"
    """文件缺失 - 任务缺少音频文件"""
    
    INPUT_UNSUPPORTED_FORMAT = "INPUT_UNSUPPORTED_FORMAT"
    """格式不支持 - 音频编码或格式不支持"""
    
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    """文件过大 - 超过大小或时长限制"""
    
    INPUT_CORRUPTED = "INPUT_CORRUPTED"
    """文件损坏 - 文件损坏或无法解析"""
    
    INPUT_INVALID = "INPUT_INVALID"
    """输入无效 - 参数格式错误或不符合要求"""
    
    # ============================================================================
    # 上游模型/服务错误
    # ============================================================================
    ASR_SERVICE_ERROR = "ASR_SERVICE_ERROR"
    """ASR服务异常 - 转写服务返回错误"""
    
    ASR_AUTH_ERROR = "ASR_AUTH_ERROR"
    """ASR鉴权失败 - ASR服务鉴权失败"""
    
    ASR_TIMEOUT = "ASR_TIMEOUT"
    """ASR超时 - 转写服务响应超时"""
    
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"
    """LLM服务异常 - 生成接口返回错误"""
    
    LLM_AUTH_ERROR = "LLM_AUTH_ERROR"
    """LLM鉴权失败 - LLM服务鉴权失败"""
    
    LLM_TIMEOUT = "LLM_TIMEOUT"
    """LLM超时 - 生成服务响应超时"""
    
    LLM_CONTENT_BLOCKED = "LLM_CONTENT_BLOCKED"
    """内容被拦截 - 内容审查拦截"""
    
    VOICEPRINT_SERVICE_ERROR = "VOICEPRINT_SERVICE_ERROR"
    """声纹服务异常 - 声纹识别服务返回错误"""
    
    VOICEPRINT_AUTH_ERROR = "VOICEPRINT_AUTH_ERROR"
    """声纹鉴权失败 - 声纹服务鉴权失败"""
    
    # ============================================================================
    # 业务流程错误
    # ============================================================================
    SPEAKER_RECOGNITION_FAILED = "SPEAKER_RECOGNITION_FAILED"
    """声纹识别失败 - 无法识别说话人"""
    
    CORRECTION_FAILED = "CORRECTION_FAILED"
    """校正失败 - 说话人校正失败"""
    
    SUMMARY_FAILED = "SUMMARY_FAILED"
    """生成失败 - 生成会议纪要失败"""
    
    TRANSCRIPTION_EMPTY = "TRANSCRIPTION_EMPTY"
    """转写为空 - 转写结果为空或无有效内容"""
    
    # ============================================================================
    # 系统内部错误 (联系管理员)
    # ============================================================================
    INTERNAL_ERROR = "INTERNAL_ERROR"
    """内部错误 - 未分类的服务器错误"""
    
    DB_ERROR = "DB_ERROR"
    """数据库错误 - 数据库读写异常"""
    
    CACHE_ERROR = "CACHE_ERROR"
    """缓存错误 - 缓存访问异常"""
    
    QUEUE_ERROR = "QUEUE_ERROR"
    """队列错误 - 消息队列异常"""


class TaskError(BaseModel):
    """任务错误信息"""
    
    error_code: ErrorCode
    """错误码 - 用于前端分类处理"""
    
    error_message: str
    """错误消息 - 用户可读的简要原因"""
    
    error_details: Optional[str] = None
    """错误详情 - 更长的调试信息，前端可隐藏或用于企微告警"""
    
    retryable: bool = False
    """是否可重试 - 前端据此决定是否显示重试按钮"""
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "ASR_SERVICE_ERROR",
                "error_message": "转写服务暂时不可用",
                "error_details": "火山引擎 ASR API 返回 500 错误: Internal Server Error",
                "retryable": True,
            }
        }
    }


# ============================================================================
# 错误码分类配置
# ============================================================================

# 可重试的错误码
RETRYABLE_ERROR_CODES = {
    ErrorCode.NETWORK_TIMEOUT,
    ErrorCode.NETWORK_DNS,
    ErrorCode.STORAGE_UNAVAILABLE,
    ErrorCode.RATE_LIMITED,
    ErrorCode.ASR_SERVICE_ERROR,
    ErrorCode.ASR_TIMEOUT,
    ErrorCode.LLM_SERVICE_ERROR,
    ErrorCode.LLM_TIMEOUT,
    ErrorCode.VOICEPRINT_SERVICE_ERROR,
    ErrorCode.SPEAKER_RECOGNITION_FAILED,
    ErrorCode.CORRECTION_FAILED,
    ErrorCode.SUMMARY_FAILED,
    ErrorCode.CACHE_ERROR,
}

# 需要检查配置的错误码
CONFIG_ERROR_CODES = {
    ErrorCode.AUTH_FAILED,
    ErrorCode.ASR_AUTH_ERROR,
    ErrorCode.LLM_AUTH_ERROR,
    ErrorCode.VOICEPRINT_AUTH_ERROR,
    ErrorCode.LLM_CONTENT_BLOCKED,
}

# 需要用户处理的错误码
USER_ACTION_ERROR_CODES = {
    ErrorCode.INPUT_MISSING_FILE,
    ErrorCode.INPUT_UNSUPPORTED_FORMAT,
    ErrorCode.INPUT_TOO_LARGE,
    ErrorCode.INPUT_CORRUPTED,
    ErrorCode.INPUT_INVALID,
}

# 需要联系管理员的错误码
ADMIN_ERROR_CODES = {
    ErrorCode.PERMISSION_DENIED,
    ErrorCode.BILLING_EXCEEDED,
    ErrorCode.INTERNAL_ERROR,
    ErrorCode.DB_ERROR,
    ErrorCode.QUEUE_ERROR,
}


def is_retryable(error_code: ErrorCode) -> bool:
    """判断错误是否可重试"""
    return error_code in RETRYABLE_ERROR_CODES


def create_error(
    error_code: ErrorCode,
    error_message: str,
    error_details: Optional[str] = None,
    retryable: Optional[bool] = None,
) -> TaskError:
    """
    创建错误信息
    
    Args:
        error_code: 错误码
        error_message: 用户可读的错误消息
        error_details: 详细的调试信息（可选）
        retryable: 是否可重试（可选，默认根据错误码判断）
    
    Returns:
        TaskError: 结构化的错误信息
    """
    if retryable is None:
        retryable = is_retryable(error_code)
    
    return TaskError(
        error_code=error_code,
        error_message=error_message,
        error_details=error_details,
        retryable=retryable,
    )


# ============================================================================
# 常用错误消息模板
# ============================================================================

ERROR_MESSAGES = {
    # 网络/基础设施
    ErrorCode.NETWORK_TIMEOUT: "网络连接超时，请稍后重试",
    ErrorCode.NETWORK_DNS: "网络连接失败，请检查网络设置",
    ErrorCode.STORAGE_UNAVAILABLE: "文件存储服务暂时不可用，请稍后重试",
    
    # 鉴权/配额
    ErrorCode.AUTH_FAILED: "身份验证失败，请重新登录",
    ErrorCode.PERMISSION_DENIED: "您没有权限访问此资源",
    ErrorCode.RATE_LIMITED: "请求过于频繁，请稍后再试",
    ErrorCode.BILLING_EXCEEDED: "账户余额不足或已超出配额限制",
    
    # 输入/数据
    ErrorCode.INPUT_MISSING_FILE: "音频文件缺失，请重新上传",
    ErrorCode.INPUT_UNSUPPORTED_FORMAT: "不支持的音频格式，请上传 WAV/MP3/OGG 格式",
    ErrorCode.INPUT_TOO_LARGE: "音频文件过大，请上传小于 2GB 的文件",
    ErrorCode.INPUT_CORRUPTED: "音频文件已损坏，请重新上传",
    ErrorCode.INPUT_INVALID: "输入参数无效，请检查后重试",
    
    # 上游服务
    ErrorCode.ASR_SERVICE_ERROR: "语音识别服务暂时不可用，请稍后重试",
    ErrorCode.ASR_AUTH_ERROR: "语音识别服务鉴权失败，请联系管理员",
    ErrorCode.ASR_TIMEOUT: "语音识别超时，请稍后重试",
    ErrorCode.LLM_SERVICE_ERROR: "AI 生成服务暂时不可用，请稍后重试",
    ErrorCode.LLM_AUTH_ERROR: "AI 生成服务鉴权失败，请联系管理员",
    ErrorCode.LLM_TIMEOUT: "AI 生成超时，请稍后重试",
    ErrorCode.LLM_CONTENT_BLOCKED: "内容包含敏感信息，无法生成",
    ErrorCode.VOICEPRINT_SERVICE_ERROR: "声纹识别服务暂时不可用，请稍后重试",
    ErrorCode.VOICEPRINT_AUTH_ERROR: "声纹识别服务鉴权失败，请联系管理员",
    
    # 业务流程
    ErrorCode.SPEAKER_RECOGNITION_FAILED: "无法识别说话人，请检查音频质量",
    ErrorCode.CORRECTION_FAILED: "说话人校正失败，请稍后重试",
    ErrorCode.SUMMARY_FAILED: "生成会议纪要失败，请稍后重试",
    ErrorCode.TRANSCRIPTION_EMPTY: "转写结果为空，请检查音频内容",
    
    # 系统内部
    ErrorCode.INTERNAL_ERROR: "系统内部错误，请联系管理员",
    ErrorCode.DB_ERROR: "数据库错误，请联系管理员",
    ErrorCode.CACHE_ERROR: "缓存服务异常，请稍后重试",
    ErrorCode.QUEUE_ERROR: "任务队列异常，请联系管理员",
}


def get_error_message(error_code: ErrorCode) -> str:
    """获取错误码对应的默认消息"""
    return ERROR_MESSAGES.get(error_code, "未知错误")
