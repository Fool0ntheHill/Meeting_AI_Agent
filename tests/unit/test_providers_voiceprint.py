# -*- coding: utf-8 -*-
"""Unit tests for voiceprint providers."""

import base64
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.config.models import IFlyTekConfig
from src.core.exceptions import (
    AuthenticationError,
    RateLimitError,
    VoiceprintError,
    VoiceprintQualityError,
)
from src.core.models import Segment, SpeakerIdentity, TranscriptionResult
from src.providers.iflytek_voiceprint import IFlyTekVoiceprint


@pytest.fixture
def iflytek_config():
    """iFLYTEK 配置 fixture"""
    return IFlyTekConfig(
        app_id="test_app_id",
        api_key="test_api_key",
        api_secret="test_api_secret",
        group_id="test_group_id",
        api_endpoint="https://api.xf-yun.com/v1/private/s1aa729d0",
        timeout=30,
    )


@pytest.fixture
def iflytek_provider(iflytek_config):
    """iFLYTEK 提供商 fixture"""
    return IFlyTekVoiceprint(iflytek_config)


@pytest.fixture
def sample_transcript():
    """示例转写结果 fixture"""
    return TranscriptionResult(
        segments=[
            Segment(text="大家好", start_time=0.0, end_time=2.0, speaker="spk_0"),
            Segment(text="今天讨论产品规划", start_time=2.0, end_time=5.0, speaker="spk_0"),
            Segment(text="我同意", start_time=5.5, end_time=7.0, speaker="spk_1"),
            Segment(text="我们需要关注用户反馈", start_time=7.5, end_time=11.0, speaker="spk_1"),
        ],
        full_text="大家好 今天讨论产品规划 我同意 我们需要关注用户反馈",
        duration=11.0,
        language="zh-CN",
        provider="volcano",
    )


@pytest.fixture
def known_speakers():
    """已知说话人列表 fixture"""
    return [
        SpeakerIdentity(
            speaker_id="feat_001",
            name="张三",
            confidence=0.95,
        ),
        SpeakerIdentity(
            speaker_id="feat_002",
            name="李四",
            confidence=0.90,
        ),
    ]


class TestIFlyTekVoiceprint:
    """iFLYTEK 声纹识别提供商测试"""

    def test_provider_name(self, iflytek_provider):
        """测试提供商名称"""
        assert iflytek_provider.get_provider_name() == "iflytek"

    def test_initialization(self, iflytek_config):
        """测试初始化"""
        provider = IFlyTekVoiceprint(iflytek_config)
        assert provider.config == iflytek_config
        assert provider.api_url == iflytek_config.api_endpoint
        assert provider.host == "api.xf-yun.com"
        assert provider.score_threshold == 0.58
        assert provider.min_accept_score == 0.40
        assert provider.gap_threshold == 0.15

    def test_generate_auth_params(self, iflytek_provider):
        """测试鉴权参数生成"""
        auth_params = iflytek_provider._generate_auth_params()

        # 验证必需参数存在
        assert "host" in auth_params
        assert "date" in auth_params
        assert "authorization" in auth_params

        # 验证 host
        assert auth_params["host"] == "api.xf-yun.com"

        # 验证 date 格式 (RFC1123)
        assert "GMT" in auth_params["date"]

        # 验证 authorization 是 Base64 编码
        try:
            decoded = base64.b64decode(auth_params["authorization"]).decode("utf-8")
            assert "api_key=" in decoded
            assert "algorithm=" in decoded
            assert "signature=" in decoded
        except Exception as e:
            pytest.fail(f"Authorization 解码失败: {e}")

    @pytest.mark.anyio
    async def test_identify_speakers_success(
        self, iflytek_provider, sample_transcript, known_speakers
    ):
        """测试说话人识别成功"""
        # Mock _extract_speaker_sample
        with patch.object(
            iflytek_provider, "_extract_speaker_sample", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = b"fake_audio_data"

            # Mock _search_speaker - 使用字典映射确保正确的说话人匹配
            search_results = {
                "spk_0": {"name": "张三", "score": 0.85, "speaker_id": "feat_001"},
                "spk_1": {"name": "李四", "score": 0.78, "speaker_id": "feat_002"},
            }

            async def mock_search_side_effect(audio_sample, known_speakers_list):
                # 根据调用次数返回不同结果
                # 由于 speakers 是 set，顺序不确定，我们需要根据实际调用来返回
                call_count = mock_search.call_count
                speakers_list = list(sample_transcript.speakers)
                if call_count <= len(speakers_list):
                    speaker = speakers_list[call_count - 1]
                    return search_results.get(speaker)
                return None

            with patch.object(
                iflytek_provider, "_search_speaker", new_callable=AsyncMock
            ) as mock_search:
                mock_search.side_effect = mock_search_side_effect

                result = await iflytek_provider.identify_speakers(
                    sample_transcript, "http://example.com/audio.wav", known_speakers
                )

                # 验证结果 - 两个说话人都应该被识别
                assert len(result) == 2
                assert "spk_0" in result
                assert "spk_1" in result
                # 验证映射正确（不依赖顺序）
                assert result["spk_0"] in ["张三", "李四"]
                assert result["spk_1"] in ["张三", "李四"]
                assert result["spk_0"] != result["spk_1"]  # 两个说话人应该不同
                assert mock_extract.call_count == 2
                assert mock_search.call_count == 2

    @pytest.mark.anyio
    async def test_identify_speakers_not_found(
        self, iflytek_provider, sample_transcript, known_speakers
    ):
        """测试说话人未识别到"""
        with patch.object(
            iflytek_provider, "_extract_speaker_sample", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = b"fake_audio_data"

            with patch.object(
                iflytek_provider, "_search_speaker", new_callable=AsyncMock
            ) as mock_search:
                # 返回 None 表示未找到
                mock_search.return_value = None

                result = await iflytek_provider.identify_speakers(
                    sample_transcript, "http://example.com/audio.wav", known_speakers
                )

                # 验证保留原标签
                assert result == {"spk_0": "spk_0", "spk_1": "spk_1"}

    @pytest.mark.anyio
    async def test_identify_speakers_partial_failure(
        self, iflytek_provider, sample_transcript, known_speakers
    ):
        """测试部分说话人识别失败"""
        call_count = 0

        async def mock_extract_side_effect(transcript, audio_url, speaker_label):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b"fake_audio_data"
            else:
                raise VoiceprintQualityError("音频质量不足")

        with patch.object(
            iflytek_provider, "_extract_speaker_sample", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.side_effect = mock_extract_side_effect

            with patch.object(
                iflytek_provider, "_search_speaker", new_callable=AsyncMock
            ) as mock_search:
                mock_search.return_value = {"name": "张三", "score": 0.85, "speaker_id": "feat_001"}

                result = await iflytek_provider.identify_speakers(
                    sample_transcript, "http://example.com/audio.wav", known_speakers
                )

                # 验证结果 - 一个识别成功，一个保留原标签
                assert len(result) == 2
                assert "spk_0" in result
                assert "spk_1" in result
                # 其中一个应该是 "张三"，另一个应该保留原标签
                values = list(result.values())
                assert "张三" in values
                # 另一个应该是原标签（spk_0 或 spk_1）
                assert any(v in ["spk_0", "spk_1"] for v in values)

    @pytest.mark.anyio
    async def test_extract_speaker_sample_single_segment(
        self, iflytek_provider, sample_transcript
    ):
        """测试提取单个片段"""
        with patch.object(
            iflytek_provider, "extract_audio_sample", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = b"audio_sample"

            # 创建一个 3-6 秒的片段
            transcript = TranscriptionResult(
                segments=[
                    Segment(text="测试内容", start_time=0.0, end_time=4.0, speaker="spk_0"),
                ],
                full_text="测试内容",
                duration=4.0,
                language="zh-CN",
                provider="volcano",
            )

            result = await iflytek_provider._extract_speaker_sample(
                transcript, "http://example.com/audio.wav", "spk_0"
            )

            assert result == b"audio_sample"
            mock_extract.assert_called_once_with("http://example.com/audio.wav", 0.0, 4.0)

    @pytest.mark.anyio
    async def test_extract_speaker_sample_no_segments(self, iflytek_provider, sample_transcript):
        """测试没有找到说话人片段"""
        with pytest.raises(VoiceprintQualityError, match="No segments found"):
            await iflytek_provider._extract_speaker_sample(
                sample_transcript, "http://example.com/audio.wav", "spk_999"
            )

    @pytest.mark.anyio
    async def test_extract_speaker_sample_insufficient_audio(self, iflytek_provider):
        """测试音频时长不足"""
        # 创建一个时长很短的片段
        transcript = TranscriptionResult(
            segments=[
                Segment(text="嗯", start_time=0.0, end_time=0.3, speaker="spk_0"),
            ],
            full_text="嗯",
            duration=0.3,
            language="zh-CN",
            provider="volcano",
        )

        with pytest.raises(VoiceprintQualityError, match="Insufficient audio"):
            await iflytek_provider._extract_speaker_sample(
                transcript, "http://example.com/audio.wav", "spk_0"
            )

    @pytest.mark.anyio
    async def test_search_speaker_success(self, iflytek_provider, known_speakers):
        """测试 1:N 搜索成功"""
        # 构造 mock 响应
        search_result = {
            "scoreList": [
                {"score": 0.85, "featureId": "feat_001"},
                {"score": 0.45, "featureId": "feat_002"},
            ]
        }
        result_text = base64.b64encode(json.dumps(search_result).encode("utf-8")).decode("utf-8")

        mock_response = {
            "header": {"code": 0},
            "payload": {"searchFeaRes": {"text": result_text}},
        }

        with patch.object(
            iflytek_provider, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await iflytek_provider._search_speaker(b"audio_sample", known_speakers)

            assert result is not None
            assert result["name"] == "张三"
            assert result["score"] == 0.85
            assert result["speaker_id"] == "feat_001"

    @pytest.mark.anyio
    async def test_search_speaker_below_threshold(self, iflytek_provider, known_speakers):
        """测试分数低于阈值"""
        search_result = {
            "scoreList": [
                {"score": 0.45, "featureId": "feat_001"},
            ]
        }
        result_text = base64.b64encode(json.dumps(search_result).encode("utf-8")).decode("utf-8")

        mock_response = {
            "header": {"code": 0},
            "payload": {"searchFeaRes": {"text": result_text}},
        }

        with patch.object(
            iflytek_provider, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await iflytek_provider._search_speaker(b"audio_sample", known_speakers)

            assert result is None

    @pytest.mark.anyio
    async def test_search_speaker_score_diff_rescue(self, iflytek_provider, known_speakers):
        """测试分差挽救机制 - 分差太小应该被拒绝"""
        # 第一名和第二名分差太小，且分数低于高置信度阈值
        search_result = {
            "scoreList": [
                {"score": 0.50, "featureId": "feat_001"},  # 低于 0.58
                {"score": 0.45, "featureId": "feat_002"},  # 分差只有 0.05 < 0.15
            ]
        }
        result_text = base64.b64encode(json.dumps(search_result).encode("utf-8")).decode("utf-8")

        mock_response = {
            "header": {"code": 0},
            "payload": {"searchFeaRes": {"text": result_text}},
        }

        with patch.object(
            iflytek_provider, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await iflytek_provider._search_speaker(b"audio_sample", known_speakers)

            # 分差太小，应该返回 None
            assert result is None

    @pytest.mark.anyio
    async def test_search_speaker_empty_result(self, iflytek_provider, known_speakers):
        """测试空结果"""
        search_result = {"scoreList": []}
        result_text = base64.b64encode(json.dumps(search_result).encode("utf-8")).decode("utf-8")

        mock_response = {
            "header": {"code": 0},
            "payload": {"searchFeaRes": {"text": result_text}},
        }

        with patch.object(
            iflytek_provider, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await iflytek_provider._search_speaker(b"audio_sample", known_speakers)

            assert result is None

    def test_get_speaker_name_found(self, iflytek_provider, known_speakers):
        """测试获取说话人姓名 - 找到"""
        name = iflytek_provider._get_speaker_name("feat_001", known_speakers)
        assert name == "张三"

    def test_get_speaker_name_not_found(self, iflytek_provider, known_speakers):
        """测试获取说话人姓名 - 未找到"""
        name = iflytek_provider._get_speaker_name("feat_999", known_speakers)
        assert name == "feat_999"

    def test_get_speaker_name_no_known_speakers(self, iflytek_provider):
        """测试获取说话人姓名 - 无已知说话人"""
        name = iflytek_provider._get_speaker_name("feat_001", None)
        assert name == "feat_001"

    @pytest.mark.anyio
    async def test_make_request_success(self, iflytek_provider):
        """测试 HTTP 请求成功"""
        request_body = {"test": "data"}
        mock_response_data = {"header": {"code": 0}, "payload": {}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await iflytek_provider._make_request(request_body)

            assert result == mock_response_data

    @pytest.mark.anyio
    async def test_make_request_auth_error(self, iflytek_provider):
        """测试认证错误"""
        request_body = {"test": "data"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(AuthenticationError, match="authentication failed"):
                await iflytek_provider._make_request(request_body)

    @pytest.mark.anyio
    async def test_make_request_rate_limit(self, iflytek_provider):
        """测试速率限制"""
        request_body = {"test": "data"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(RateLimitError, match="rate limit exceeded"):
                await iflytek_provider._make_request(request_body)

    @pytest.mark.anyio
    async def test_make_request_business_error(self, iflytek_provider):
        """测试业务错误码"""
        request_body = {"test": "data"}
        mock_response_data = {
            "header": {"code": 10001, "message": "Invalid parameter"},
            "payload": {},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(VoiceprintError, match="API error 10001"):
                await iflytek_provider._make_request(request_body)

    @pytest.mark.anyio
    async def test_make_request_http_error(self, iflytek_provider):
        """测试 HTTP 错误"""
        request_body = {"test": "data"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

            with pytest.raises(VoiceprintError, match="HTTP error"):
                await iflytek_provider._make_request(request_body)
