"""Structured logging utilities with sensitive information filtering."""

import logging
import re
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


# 敏感信息模式
SENSITIVE_PATTERNS = [
    (re.compile(r"(password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***"),
    (re.compile(r"(api[_-]?key|apikey|access[_-]?key)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***"),
    (re.compile(r"(secret[_-]?key|secretkey)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***"),
    (re.compile(r"(token|auth)[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.I), r"\1=***"),
    (re.compile(r"Bearer\s+([A-Za-z0-9\-._~+/]+=*)", re.I), r"Bearer ***"),
]


def filter_sensitive_info(message: str) -> str:
    """
    过滤敏感信息

    Args:
        message: 原始消息

    Returns:
        str: 过滤后的消息
    """
    filtered = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        filtered = pattern.sub(replacement, filtered)
    return filtered


class SensitiveInfoFilter(logging.Filter):
    """敏感信息过滤器"""

    def __init__(self, max_length: int = 1000):
        """
        初始化过滤器
        
        Args:
            max_length: 日志消息最大长度
        """
        super().__init__()
        self.max_length = max_length

    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录中的敏感信息

        Args:
            record: 日志记录

        Returns:
            bool: 是否保留该记录
        """
        if hasattr(record, "msg") and isinstance(record.msg, str):
            # 过滤敏感信息
            record.msg = filter_sensitive_info(record.msg)
            
            # 限制输出长度
            if len(record.msg) > self.max_length:
                # 检查是否包含二进制数据特征
                if any(char in record.msg for char in ['\x00', '\xff', '\xfe']):
                    record.msg = f"[BINARY DATA DETECTED - Length: {len(record.msg)} bytes] {record.msg[:200]}... [TRUNCATED]"
                else:
                    record.msg = f"{record.msg[:self.max_length]}... [TRUNCATED - Total length: {len(record.msg)}]"
        return True


def setup_logger(
    level: str = "INFO",
    format_type: str = "json",
    output: str = "stdout",
    file_path: Optional[str] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    filter_sensitive: bool = True,
):
    """
    设置结构化日志

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        format_type: 日志格式 (json/text)
        output: 输出目标 (stdout/file)
        file_path: 日志文件路径 (output=file 时必需)
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量
        filter_sensitive: 是否过滤敏感信息

    Returns:
        日志记录器 (structlog.BoundLogger 或 logging.Logger)
    """
    if not STRUCTLOG_AVAILABLE:
        # Fallback to standard logging
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 配置 structlog 处理器
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # 配置 structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准库 logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 添加处理器
    if output == "stdout":
        handler = logging.StreamHandler()
    elif output == "file":
        if not file_path:
            raise ValueError("output=file 时必须指定 file_path")
        handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:
        raise ValueError(f"不支持的输出类型: {output}")

    # 设置格式化器
    if format_type == "json":
        formatter = logging.Formatter("%(message)s")
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    handler.setFormatter(formatter)

    # 添加敏感信息过滤器
    if filter_sensitive:
        handler.addFilter(SensitiveInfoFilter())

    root_logger.addHandler(handler)

    # 返回 structlog logger
    return structlog.get_logger()


def get_logger(name: Optional[str] = None):
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器 (structlog.BoundLogger 或 logging.Logger)
    """
    if STRUCTLOG_AVAILABLE:
        if name:
            return structlog.get_logger(name)
        return structlog.get_logger()
    else:
        # Fallback to standard logging when structlog is not available
        logger = logging.getLogger(name or __name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
