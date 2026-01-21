"""Unit tests for utility modules."""

import tempfile
from pathlib import Path

import pytest

from src.utils.cost import CostTracker

# Logger tests are optional (require structlog)
try:
    from src.utils.logger import filter_sensitive_info, setup_logger, STRUCTLOG_AVAILABLE
    HAS_STRUCTLOG = STRUCTLOG_AVAILABLE
except ImportError:
    HAS_STRUCTLOG = False


# ============================================================================
# Cost Tracker Tests
# ============================================================================


def test_cost_tracker_estimate_task_cost():
    """Test CostTracker.estimate_task_cost()"""
    import asyncio
    
    tracker = CostTracker()
    
    # 测试基本成本估算
    cost = asyncio.run(tracker.estimate_task_cost(
        audio_duration=600,  # 10 分钟
        enable_speaker_recognition=True,
        asr_provider="volcano",
    ))
    
    assert "asr" in cost
    assert "voiceprint" in cost
    assert "llm" in cost
    assert "total" in cost
    assert cost["total"] > 0
    # 使用近似比较避免浮点数精度问题
    assert abs(cost["total"] - (cost["asr"] + cost["voiceprint"] + cost["llm"])) < 0.0001


def test_cost_tracker_estimate_without_speaker_recognition():
    """Test cost estimation without speaker recognition"""
    import asyncio
    
    tracker = CostTracker()
    
    cost = asyncio.run(tracker.estimate_task_cost(
        audio_duration=600,
        enable_speaker_recognition=False,
        asr_provider="volcano",
    ))
    
    assert cost["voiceprint"] == 0.0
    assert cost["total"] == cost["asr"] + cost["llm"]


def test_cost_tracker_calculate_asr_cost():
    """Test CostTracker.calculate_asr_cost()"""
    tracker = CostTracker()
    
    # Volcano ASR
    cost_volcano = tracker.calculate_asr_cost(duration=100, provider="volcano")
    assert cost_volcano == 100 * 0.00005
    
    # Azure ASR
    cost_azure = tracker.calculate_asr_cost(duration=100, provider="azure")
    assert cost_azure == 100 * 0.00006


def test_cost_tracker_calculate_voiceprint_cost():
    """Test CostTracker.calculate_voiceprint_cost()"""
    tracker = CostTracker()
    
    # 声纹识别按次计费：10万次200元，即每次0.002元
    cost = tracker.calculate_voiceprint_cost(speaker_count=3)
    expected = round(3 * 0.002, 4)
    assert cost == expected


def test_cost_tracker_calculate_llm_cost():
    """Test CostTracker.calculate_llm_cost()"""
    tracker = CostTracker()
    
    cost = tracker.calculate_llm_cost(token_count=1000)
    assert cost == 1000 * 0.00002


def test_cost_tracker_estimate_tokens():
    """Test CostTracker.estimate_tokens_from_duration()"""
    tracker = CostTracker()
    
    tokens = tracker.estimate_tokens_from_duration(duration=60)
    assert tokens == 600  # 60 * 10


# ============================================================================
# Logger Tests (optional, require structlog)
# ============================================================================


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_filter_sensitive_info_password():
    """Test filtering password from log messages"""
    message = 'Connecting to database with password="secret123"'
    filtered = filter_sensitive_info(message)
    assert "secret123" not in filtered
    assert "password=***" in filtered


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_filter_sensitive_info_api_key():
    """Test filtering API key from log messages"""
    message = "Using api_key: abc123xyz"
    filtered = filter_sensitive_info(message)
    assert "abc123xyz" not in filtered
    assert "api_key=***" in filtered


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_filter_sensitive_info_bearer_token():
    """Test filtering Bearer token from log messages"""
    message = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    filtered = filter_sensitive_info(message)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in filtered
    assert "Bearer ***" in filtered


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_filter_sensitive_info_multiple_patterns():
    """Test filtering multiple sensitive patterns"""
    message = 'Config: password="pass123", api_key="key456", token="tok789"'
    filtered = filter_sensitive_info(message)
    assert "pass123" not in filtered
    assert "key456" not in filtered
    assert "tok789" not in filtered
    assert "password=***" in filtered
    assert "api_key=***" in filtered
    assert "token=***" in filtered


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_setup_logger_stdout():
    """Test setting up logger with stdout output"""
    logger = setup_logger(
        level="INFO",
        format_type="json",
        output="stdout",
        filter_sensitive=True,
    )
    assert logger is not None


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_setup_logger_file():
    """Test setting up logger with file output"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        log_file = f.name
    
    try:
        logger = setup_logger(
            level="DEBUG",
            format_type="text",
            output="file",
            file_path=log_file,
            filter_sensitive=True,
        )
        assert logger is not None
        assert Path(log_file).exists()
    finally:
        # Clean up - close all handlers first to release file lock
        import logging
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        # Now we can delete the file
        try:
            Path(log_file).unlink(missing_ok=True)
        except PermissionError:
            # On Windows, file might still be locked, ignore
            pass


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_setup_logger_invalid_output():
    """Test setup_logger raises error for invalid output"""
    with pytest.raises(ValueError, match="不支持的输出类型"):
        setup_logger(output="invalid")


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_setup_logger_file_without_path():
    """Test setup_logger raises error when file output without path"""
    with pytest.raises(ValueError, match="output=file 时必须指定 file_path"):
        setup_logger(output="file")
