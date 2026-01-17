# -*- coding: utf-8 -*-
"""Unit tests for ASR providers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config.models import AzureConfig, VolcanoConfig
from src.core.exceptions import (
    ASRError,
    AudioFormatError,
    AuthenticationError,
    RateLimitError,
    SensitiveContentError,
)
from src.core.models import ASRLanguage, HotwordSet
from src.providers.azure_asr import AzureASR
from src.providers.volcano_asr import VolcanoASR


# Use anyio for async tests
pytestmark = pytest.mark.anyio


# ============================================================================
# Volcano ASR Tests
# ============================================================================


@pytest.fixture
def volcano_config():
    """Volcano 配置 fixture"""
    return VolcanoConfig(
        access_key="test_access_key",
        secret_key="test_secret_key",
        app_id="test_app_id",
        cluster_id="test_cluster_id",
        tos_bucket="test_bucket",
        tos_region="cn-beijing",
    )


@pytest.fixture
def volcano_asr(volcano_config):
    """Volcano ASR provider fixture"""
    return VolcanoASR(volcano_config)


async def test_volcano_submit_task_success(volcano_asr):
    """测试火山引擎提交任务成功 (V3 API)"""
    mock_response = MagicMock()
    mock_response.headers = {
        "X-Api-Status-Code": "20000000",
        "X-Api-Message": "Success",
        "X-Tt-Logid": "test_logid_123",
    }
    mock_response.json.return_value = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        task_id, x_tt_logid = await volcano_asr._submit_task(
            "http://example.com/audio.wav", ASRLanguage.ZH_CN, None
        )

        assert task_id is not None  # UUID generated
        assert x_tt_logid == "test_logid_123"


async def test_volcano_submit_task_auth_error(volcano_asr):
    """测试火山引擎认证失败 (V3 API)"""
    mock_response = MagicMock()
    mock_response.headers = {
        "X-Api-Status-Code": "40000001",
        "X-Api-Message": "Authentication failed",
        "X-Tt-Logid": "",
    }
    mock_response.json.return_value = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(AuthenticationError):
            await volcano_asr._submit_task(
                "http://example.com/audio.wav", ASRLanguage.ZH_CN, None
            )


async def test_volcano_submit_task_rate_limit(volcano_asr):
    """测试火山引擎速率限制 (V3 API)"""
    mock_response = MagicMock()
    mock_response.headers = {
        "X-Api-Status-Code": "50000003",
        "X-Api-Message": "Rate limit exceeded",
        "X-Tt-Logid": "",
    }
    mock_response.json.return_value = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(ASRError):  # V3 API uses generic ASRError for server errors
            await volcano_asr._submit_task(
                "http://example.com/audio.wav", ASRLanguage.ZH_CN, None
            )


async def test_volcano_submit_task_audio_format_error(volcano_asr):
    """测试火山引擎音频格式错误 (V3 API)"""
    mock_response = MagicMock()
    mock_response.headers = {
        "X-Api-Status-Code": "45000006",
        "X-Api-Message": "Invalid audio format",
        "X-Tt-Logid": "",
    }
    mock_response.json.return_value = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(ASRError):  # V3 API uses generic ASRError for client errors
            await volcano_asr._submit_task(
                "http://example.com/audio.wav", ASRLanguage.ZH_CN, None
            )


async def test_volcano_poll_result_success(volcano_asr):
    """测试火山引擎轮询结果成功 (V3 API)"""
    mock_response = MagicMock()
    mock_response.headers = {
        "X-Api-Status-Code": "20000000",
        "X-Api-Message": "Success",
    }
    mock_response.json.return_value = {
        "result": {
            "text": "测试文本",
            "utterances": [
                {
                    "text": "测试文本",
                    "start_time": 0,
                    "end_time": 1000,
                    "additions": {"speaker": "1"},
                }
            ],
        }
    }
    mock_response.text = "some text"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await volcano_asr._poll_result("task_123", "logid_123")

        assert result["text"] == "测试文本"
        assert len(result["utterances"]) == 1


async def test_volcano_poll_result_processing(volcano_asr):
    """测试火山引擎轮询处理中状态 (V3 API)"""
    # 第一次返回处理中,第二次返回成功
    mock_response_processing = MagicMock()
    mock_response_processing.headers = {
        "X-Api-Status-Code": "20000001",
        "X-Api-Message": "Processing",
    }
    mock_response_processing.json.return_value = {}
    mock_response_processing.text = ""

    mock_response_success = MagicMock()
    mock_response_success.headers = {
        "X-Api-Status-Code": "20000000",
        "X-Api-Message": "Success",
    }
    mock_response_success.json.return_value = {
        "result": {
            "text": "测试文本",
            "utterances": [],
        }
    }
    mock_response_success.text = "some text"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=[mock_response_processing, mock_response_success]
        )

        result = await volcano_asr._poll_result("task_123", "logid_123")

        assert result["text"] == "测试文本"


def test_volcano_parse_result_success(volcano_asr):
    """测试火山引擎解析结果成功 (V3 API)"""
    result = {
        "text": "这是测试文本",
        "utterances": [
            {
                "text": "这是测试",
                "start_time": 0,
                "end_time": 1000,
                "additions": {"speaker": "1"},
            },
            {
                "text": "文本",
                "start_time": 1000,
                "end_time": 2000,
                "additions": {"speaker": "2"},
            },
        ],
    }

    transcription = volcano_asr._parse_result(result, "http://example.com/audio.wav")

    assert transcription.full_text == "这是测试文本"
    assert len(transcription.segments) == 2
    assert transcription.segments[0].text == "这是测试"
    assert transcription.segments[0].start_time == 0.0
    assert transcription.segments[0].end_time == 1.0
    assert transcription.segments[0].speaker == "Speaker 1"  # V3 API formats as "Speaker {id}"
    assert transcription.provider == "volcano"


def test_volcano_parse_result_sensitive_content(volcano_asr):
    """测试火山引擎检测敏感内容"""
    result = {
        "text": "这是***敏感内容",
        "utterances": [],
    }

    with pytest.raises(SensitiveContentError):
        volcano_asr._parse_result(result, "http://example.com/audio.wav")


def test_volcano_map_language(volcano_asr):
    """测试火山引擎语言映射"""
    assert volcano_asr._map_language(ASRLanguage.ZH_CN) == "zh-CN"
    assert volcano_asr._map_language(ASRLanguage.EN_US) == "en-US"
    assert volcano_asr._map_language(ASRLanguage.ZH_EN) == ""  # 中英混合使用空字符串
    assert volcano_asr._map_language(ASRLanguage.JA_JP) == "ja-JP"
    assert volcano_asr._map_language(ASRLanguage.KO_KR) == "ko-KR"


def test_volcano_get_provider_name(volcano_asr):
    """测试获取提供商名称"""
    assert volcano_asr.get_provider_name() == "volcano"


# ============================================================================
# Azure ASR Tests
# ============================================================================


@pytest.fixture
def azure_config():
    """Azure 配置 fixture"""
    return AzureConfig(
        subscription_keys=["key1", "key2"],
        region="eastus",
    )


@pytest.fixture
def azure_asr(azure_config):
    """Azure ASR provider fixture"""
    return AzureASR(azure_config)


async def test_azure_transcribe_short_audio(azure_asr):
    """测试 Azure 转写短音频"""
    mock_audio_data = b"fake_audio_data"

    with patch.object(azure_asr, "_download_audio", return_value=mock_audio_data):
        with patch.object(azure_asr.audio_processor, "get_duration", return_value=60.0):
            with patch.object(azure_asr, "_transcribe_audio", return_value=[]):
                result = await azure_asr.transcribe("http://example.com/audio.wav")

                assert result.provider == "azure"


def test_azure_parse_result(azure_asr):
    """测试 Azure 解析结果"""
    result = {
        "phrases": [
            {
                "text": "Hello world",
                "offsetMilliseconds": 0,
                "durationMilliseconds": 1000,
                "confidence": 0.95,
                "speaker": 0,
            },
            {
                "text": "How are you",
                "offsetMilliseconds": 1000,
                "durationMilliseconds": 1500,
                "confidence": 0.92,
                "speaker": 1,
            },
        ]
    }

    segments = azure_asr._parse_result(result, offset=0.0)

    assert len(segments) == 2
    assert segments[0].text == "Hello world"
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 1.0
    assert segments[0].speaker == "Speaker 0"
    assert segments[0].confidence == 0.95

    assert segments[1].text == "How are you"
    assert segments[1].start_time == 1.0
    assert segments[1].end_time == 2.5
    assert segments[1].speaker == "Speaker 1"


def test_azure_parse_result_with_offset(azure_asr):
    """测试 Azure 解析结果(带时间偏移)"""
    result = {
        "phrases": [
            {
                "text": "Hello",
                "offsetMilliseconds": 0,
                "durationMilliseconds": 1000,
                "confidence": 0.95,
                "speaker": 0,
            }
        ]
    }

    segments = azure_asr._parse_result(result, offset=10.0)

    assert segments[0].start_time == 10.0
    assert segments[0].end_time == 11.0


def test_azure_map_language(azure_asr):
    """测试 Azure 语言映射"""
    assert azure_asr._map_language(ASRLanguage.ZH_CN) == "zh-CN"
    assert azure_asr._map_language(ASRLanguage.EN_US) == "en-US"
    assert azure_asr._map_language(ASRLanguage.ZH_EN) == "zh-CN"
    assert azure_asr._map_language(ASRLanguage.JA_JP) == "ja-JP"
    assert azure_asr._map_language(ASRLanguage.KO_KR) == "ko-KR"


def test_azure_map_language_to_locales(azure_asr):
    """测试 Azure 语言映射到 locales 数组"""
    assert azure_asr._map_language_to_locales(ASRLanguage.ZH_CN) == ["zh-CN"]
    assert azure_asr._map_language_to_locales(ASRLanguage.EN_US) == ["en-US"]
    assert azure_asr._map_language_to_locales(ASRLanguage.ZH_EN) == ["zh-CN", "en-US"]


def test_azure_get_endpoint_default(azure_asr):
    """测试 Azure 获取默认端点"""
    endpoint = azure_asr._get_endpoint()
    assert endpoint == "https://eastus.api.cognitive.microsoft.com"


def test_azure_get_endpoint_custom(azure_config):
    """测试 Azure 获取自定义端点"""
    azure_config.endpoint = "https://custom.endpoint.com"
    azure_asr = AzureASR(azure_config)
    endpoint = azure_asr._get_endpoint()
    assert endpoint == "https://custom.endpoint.com"


def test_azure_key_rotation(azure_asr):
    """测试 Azure 密钥轮换"""
    assert azure_asr._get_current_key() == "key1"
    azure_asr._rotate_key()
    assert azure_asr._get_current_key() == "key2"
    azure_asr._rotate_key()
    assert azure_asr._get_current_key() == "key1"  # 循环回到第一个


def test_azure_get_provider_name(azure_asr):
    """测试获取提供商名称"""
    assert azure_asr.get_provider_name() == "azure"


def test_azure_get_task_status_not_implemented(azure_asr):
    """测试 Azure 不支持异步状态查询"""
    with pytest.raises(NotImplementedError):
        asyncio.run(azure_asr.get_task_status("task_123"))
