# -*- coding: utf-8 -*-
"""
错误处理工具

自动识别异常类型并映射到正确的错误码
"""

import re
from typing import Tuple, Optional
from src.core.error_codes import ErrorCode, TaskError, create_error


def classify_exception(exception: Exception, context: str = "") -> TaskError:
    """
    分类异常并返回结构化错误信息
    
    Args:
        exception: 捕获的异常
        context: 上下文信息（如 "ASR", "LLM", "Voiceprint"）
    
    Returns:
        TaskError: 结构化的错误信息
    """
    error_str = str(exception).lower()
    exception_type = type(exception).__name__
    original_error = str(exception)  # 保留原始错误消息
    
    # 1. 网络相关错误
    if _is_network_error(error_str, exception_type):
        if "timeout" in error_str or "timed out" in error_str:
            return create_error(
                error_code=ErrorCode.NETWORK_TIMEOUT,
                error_message=original_error,
                error_details=f"{context}: {exception_type}: {original_error}",
            )
        elif "dns" in error_str or "name resolution" in error_str:
            return create_error(
                error_code=ErrorCode.NETWORK_DNS,
                error_message=original_error,
                error_details=f"{context}: {exception_type}: {original_error}",
            )
        else:
            return create_error(
                error_code=ErrorCode.NETWORK_TIMEOUT,
                error_message=original_error,
                error_details=f"{context}: {exception_type}: {original_error}",
            )
    
    # 2. SSL/TLS 错误
    if _is_ssl_error(error_str, exception_type):
        return create_error(
            error_code=ErrorCode.NETWORK_TIMEOUT,
            error_message=original_error,
            error_details=f"{context}: SSL/TLS error: {original_error}",
        )
    
    # 3. 鉴权错误
    if _is_auth_error(error_str, exception_type):
        if context.upper() == "ASR":
            return create_error(
                error_code=ErrorCode.ASR_AUTH_ERROR,
                error_message=original_error,
                error_details=f"ASR authentication failed: {original_error}",
            )
        elif context.upper() == "LLM":
            return create_error(
                error_code=ErrorCode.LLM_AUTH_ERROR,
                error_message=original_error,
                error_details=f"LLM authentication failed: {original_error}",
            )
        elif context.upper() == "VOICEPRINT":
            return create_error(
                error_code=ErrorCode.VOICEPRINT_AUTH_ERROR,
                error_message=original_error,
                error_details=f"Voiceprint authentication failed: {original_error}",
            )
        else:
            return create_error(
                error_code=ErrorCode.AUTH_FAILED,
                error_message=original_error,
                error_details=f"{context}: {original_error}",
            )
    
    # 4. 频率限制
    if _is_rate_limit_error(error_str, exception_type):
        return create_error(
            error_code=ErrorCode.RATE_LIMITED,
            error_message=original_error,
            error_details=f"{context}: {original_error}",
        )
    
    # 5. 文件相关错误
    if _is_file_error(error_str, exception_type):
        if "not found" in error_str or "no such file" in error_str:
            return create_error(
                error_code=ErrorCode.INPUT_MISSING_FILE,
                error_message=original_error,
                error_details=f"{context}: {original_error}",
            )
        elif "unsupported" in error_str or "invalid format" in error_str:
            return create_error(
                error_code=ErrorCode.INPUT_UNSUPPORTED_FORMAT,
                error_message=original_error,
                error_details=f"{context}: {original_error}",
            )
        elif "too large" in error_str or "size limit" in error_str:
            return create_error(
                error_code=ErrorCode.INPUT_TOO_LARGE,
                error_message=original_error,
                error_details=f"{context}: {original_error}",
            )
        elif "corrupted" in error_str or "damaged" in error_str:
            return create_error(
                error_code=ErrorCode.INPUT_CORRUPTED,
                error_message=original_error,
                error_details=f"{context}: {original_error}",
            )
    
    # 6. 上游服务错误（基于上下文）
    if context.upper() == "ASR":
        return create_error(
            error_code=ErrorCode.ASR_SERVICE_ERROR,
            error_message=original_error,
            error_details=f"ASR service error: {original_error}",
        )
    elif context.upper() == "LLM":
        if "content" in error_str and ("blocked" in error_str or "filtered" in error_str):
            return create_error(
                error_code=ErrorCode.LLM_CONTENT_BLOCKED,
                error_message=original_error,
                error_details=f"LLM content blocked: {original_error}",
            )
        return create_error(
            error_code=ErrorCode.LLM_SERVICE_ERROR,
            error_message=original_error,
            error_details=f"LLM service error: {original_error}",
        )
    elif context.upper() == "VOICEPRINT":
        return create_error(
            error_code=ErrorCode.VOICEPRINT_SERVICE_ERROR,
            error_message=original_error,
            error_details=f"Voiceprint service error: {original_error}",
        )
    
    # 7. 数据库错误
    if _is_database_error(error_str, exception_type):
        return create_error(
            error_code=ErrorCode.DB_ERROR,
            error_message=original_error,
            error_details=f"Database error: {original_error}",
        )
    
    # 8. 默认：内部错误
    return create_error(
        error_code=ErrorCode.INTERNAL_ERROR,
        error_message=original_error,
        error_details=f"{context}: {exception_type}: {original_error}",
    )


def _is_network_error(error_str: str, exception_type: str) -> bool:
    """判断是否为网络错误"""
    network_keywords = [
        "timeout", "timed out", "connection", "network",
        "dns", "name resolution", "unreachable",
        "connection refused", "connection reset",
    ]
    network_exceptions = [
        "TimeoutError", "ConnectionError", "ConnectionRefusedError",
        "ConnectionResetError", "ConnectionAbortedError",
    ]
    
    return (
        any(keyword in error_str for keyword in network_keywords) or
        exception_type in network_exceptions
    )


def _is_ssl_error(error_str: str, exception_type: str) -> bool:
    """判断是否为 SSL/TLS 错误"""
    ssl_keywords = [
        "ssl", "tls", "certificate", "eof occurred",
        "handshake", "ssl: unexpected eof",
    ]
    ssl_exceptions = ["SSLError", "SSLEOFError"]
    
    return (
        any(keyword in error_str for keyword in ssl_keywords) or
        exception_type in ssl_exceptions
    )


def _is_auth_error(error_str: str, exception_type: str) -> bool:
    """判断是否为鉴权错误"""
    auth_keywords = [
        "auth", "authentication", "unauthorized", "401",
        "forbidden", "403", "permission denied",
        "invalid key", "invalid token", "api key",
    ]
    auth_exceptions = ["AuthenticationError", "PermissionError"]
    
    return (
        any(keyword in error_str for keyword in auth_keywords) or
        exception_type in auth_exceptions
    )


def _is_rate_limit_error(error_str: str, exception_type: str) -> bool:
    """判断是否为频率限制错误"""
    rate_limit_keywords = [
        "rate limit", "too many requests", "429",
        "quota exceeded", "throttle",
    ]
    
    return any(keyword in error_str for keyword in rate_limit_keywords)


def _is_file_error(error_str: str, exception_type: str) -> bool:
    """判断是否为文件相关错误"""
    file_keywords = [
        "file", "not found", "no such file",
        "unsupported", "invalid format", "corrupted",
        "too large", "size limit",
    ]
    file_exceptions = ["FileNotFoundError", "IOError", "OSError"]
    
    return (
        any(keyword in error_str for keyword in file_keywords) or
        exception_type in file_exceptions
    )


def _is_database_error(error_str: str, exception_type: str) -> bool:
    """判断是否为数据库错误"""
    db_keywords = [
        "database", "sql", "sqlite", "postgresql",
        "connection pool", "deadlock", "lock",
        "db error", "database connection",
    ]
    db_exceptions = [
        "DatabaseError", "OperationalError", "IntegrityError",
        "ProgrammingError",
    ]
    
    # 检查关键字时排除 "connection" 单独出现的情况（避免与网络错误混淆）
    has_db_keyword = False
    for keyword in db_keywords:
        if keyword in error_str:
            # 如果是 "connection"，确保前后有 "database" 或 "db"
            if keyword == "connection":
                if "database" in error_str or "db" in error_str:
                    has_db_keyword = True
                    break
            else:
                has_db_keyword = True
                break
    
    return has_db_keyword or exception_type in db_exceptions
