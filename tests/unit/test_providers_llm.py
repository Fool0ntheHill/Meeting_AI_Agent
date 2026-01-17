"""Unit tests for LLM providers."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config.models import GeminiConfig
from src.core.exceptions import (
    LLMError,
    LLMResponseParseError,
    LLMTokenLimitError,
    RateLimitError,
)
from src.core.models import (
    GeneratedArtifact,
    MeetingMinutes,
    OutputLanguage,
    PromptInstance,
    PromptTemplate,
    Segment,
    TranscriptionResult,
)
from src.providers.gemini_llm import GeminiLLM


@pytest.fixture
def gemini_config():
    """Gemini 配置 fixture"""
    return GeminiConfig(
        api_keys=["test_key_1", "test_key_2"],
        model="gemini-2.0-flash-exp",
        max_tokens=8192,
        temperature=0.7,
        max_retries=3,
        timeout=120,
    )


@pytest.fixture
def prompt_template():
    """提示词模板 fixture"""
    return PromptTemplate(
        template_id="tpl_001",
        title="标准会议纪要",
        description="生成标准会议纪要",
        prompt_body="你是一个专业的会议纪要助手。\n\n会议信息:\n{meeting_description}\n\n请生成会议纪要。",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN", "en-US"],
        parameter_schema={
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
            }
        },
        is_system=True,
        scope="global",
    )


@pytest.fixture
def prompt_instance():
    """提示词实例 fixture"""
    return PromptInstance(
        template_id="tpl_001",
        language="zh-CN",
        parameters={"meeting_description": "会议标题: 产品规划会议"},
    )


@pytest.fixture
def transcript():
    """转写结果 fixture"""
    return TranscriptionResult(
        segments=[
            Segment(
                text="大家好,今天我们讨论产品规划。",
                start_time=0.0,
                end_time=3.5,
                speaker="张三",
                confidence=0.95,
            ),
            Segment(
                text="我认为我们应该优先考虑用户反馈。",
                start_time=3.5,
                end_time=7.0,
                speaker="李四",
                confidence=0.92,
            ),
        ],
        full_text="大家好,今天我们讨论产品规划。我认为我们应该优先考虑用户反馈。",
        duration=7.0,
        language="zh-CN",
        provider="volcano",
    )


class TestGeminiLLM:
    """GeminiLLM 测试类"""

    def test_init(self, gemini_config):
        """测试初始化"""
        llm = GeminiLLM(gemini_config)
        assert llm.config == gemini_config
        assert llm.current_key_index == 0
        assert llm.get_provider_name() == "gemini"

    def test_init_no_keys(self):
        """测试无密钥初始化"""
        # Pydantic 会在配置创建时验证,所以这里应该捕获 ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="至少需要一个 API 密钥"):
            config = GeminiConfig(
                api_keys=[],
                model="gemini-2.0-flash-exp",
            )

    def test_format_transcript(self, gemini_config, transcript):
        """测试转写文本格式化"""
        llm = GeminiLLM(gemini_config)
        formatted = llm.format_transcript(transcript)

        assert "[张三]" in formatted
        assert "[李四]" in formatted
        assert "大家好,今天我们讨论产品规划。" in formatted
        assert "我认为我们应该优先考虑用户反馈。" in formatted
        assert "00:00:00 - 00:00:03" in formatted
        assert "00:00:03 - 00:00:07" in formatted

    def test_format_transcript_empty(self, gemini_config):
        """测试空转写文本格式化"""
        llm = GeminiLLM(gemini_config)
        transcript = TranscriptionResult(
            segments=[],
            full_text="",
            duration=0.0,
            language="zh-CN",
            provider="volcano",
        )
        formatted = llm.format_transcript(transcript)
        assert formatted == ""

    def test_format_time(self, gemini_config):
        """测试时间格式化"""
        llm = GeminiLLM(gemini_config)
        assert llm._format_time(0) == "00:00:00"
        assert llm._format_time(65) == "00:01:05"
        assert llm._format_time(3665) == "01:01:05"
        assert llm._format_time(3723.5) == "01:02:03"

    def test_build_prompt(self, gemini_config, prompt_template, prompt_instance, transcript):
        """���试提示词构建"""
        llm = GeminiLLM(gemini_config)
        formatted_transcript = llm.format_transcript(transcript)

        prompt = llm._build_prompt(
            template=prompt_template,
            prompt_instance=prompt_instance,
            formatted_transcript=formatted_transcript,
            output_language=OutputLanguage.ZH_CN,
        )

        assert "会议标题: 产品规划会议" in prompt
        assert "[张三]" in prompt
        assert "[李四]" in prompt
        assert "请使用中文生成会议纪要" in prompt

    def test_get_language_instruction(self, gemini_config):
        """测试语言指令获取"""
        llm = GeminiLLM(gemini_config)

        assert "中文" in llm._get_language_instruction(OutputLanguage.ZH_CN)
        assert "English" in llm._get_language_instruction(OutputLanguage.EN_US)
        assert "日本語" in llm._get_language_instruction(OutputLanguage.JA_JP)
        assert "한국어" in llm._get_language_instruction(OutputLanguage.KO_KR)

    def test_parse_response_valid_json(self, gemini_config):
        """测试解析有效 JSON 响应"""
        llm = GeminiLLM(gemini_config)

        response = json.dumps(
            {
                "title": "产品规划会议",
                "participants": ["张三", "李四"],
                "summary": "讨论了产品规划",
                "key_points": ["优先考虑用户反馈"],
                "action_items": [],
            },
            ensure_ascii=False,
        )

        result = llm._parse_response(response, "meeting_minutes")
        assert result["title"] == "产品规划会议"
        assert len(result["participants"]) == 2
        assert "张三" in result["participants"]

    def test_parse_response_markdown_json(self, gemini_config):
        """测试解析 Markdown 格式的 JSON 响应"""
        llm = GeminiLLM(gemini_config)

        response = """```json
{
    "title": "产品规划会议",
    "participants": ["张三", "李四"],
    "summary": "讨论了产品规划",
    "key_points": ["优先考虑用户反馈"],
    "action_items": []
}
```"""

        result = llm._parse_response(response, "meeting_minutes")
        assert result["title"] == "产品规划会议"

    def test_parse_response_missing_field(self, gemini_config):
        """测试解析缺少部分字段的响应（应该成功，因为不强制要求所有字段）"""
        llm = GeminiLLM(gemini_config)

        response = json.dumps(
            {
                "title": "产品规划会议",
                "participants": ["张三", "李四"],
                # 缺少 summary, key_points, action_items - 这是允许的
            },
            ensure_ascii=False,
        )

        # 应该成功解析，不抛出异常
        result = llm._parse_response(response, "meeting_minutes")
        assert result["title"] == "产品规划会议"
        assert result["participants"] == ["张三", "李四"]

    def test_parse_response_invalid_json(self, gemini_config):
        """测试解析无效 JSON 响应（会尝试 Markdown 解析作为后备，返回 raw_content）"""
        llm = GeminiLLM(gemini_config)

        response = "This is not a valid JSON"

        # 会尝试 Markdown 解析，返回包含 raw_content 的字典
        result = llm._parse_response(response, "meeting_minutes")
        assert "raw_content" in result
        assert result["raw_content"] == response
        assert result["format"] == "markdown"

    @pytest.mark.asyncio
    async def test_call_gemini_api_success(self, gemini_config):
        """测试成功调用 Gemini API"""
        llm = GeminiLLM(gemini_config)

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "title": "测试会议",
                "participants": ["张三"],
                "summary": "测试摘要",
                "key_points": [],
                "action_items": [],
            },
            ensure_ascii=False,  # 确保中文不被转义
        )
        # Mock usage_metadata
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.usage_metadata.total_token_count = 150

        with patch.object(llm.client.models, "generate_content", return_value=mock_response):
            result_text, usage_metadata = await llm._call_gemini_api("test prompt")
            assert "测试会议" in result_text
            assert usage_metadata["total_token_count"] == 150

    @pytest.mark.asyncio
    async def test_call_gemini_api_token_limit(self, gemini_config):
        """测试 Token 超限"""
        llm = GeminiLLM(gemini_config)

        with patch.object(
            llm.client.models,
            "generate_content",
            side_effect=Exception("Token limit exceeded")
        ):
            with pytest.raises(LLMTokenLimitError):
                await llm._call_gemini_api("test prompt")

    @pytest.mark.asyncio
    async def test_call_gemini_api_rate_limit_with_rotation(self, gemini_config):
        """测试速率限制并轮换密钥"""
        llm = GeminiLLM(gemini_config)

        mock_response = MagicMock()
        mock_response.text = "success"
        # Mock usage_metadata
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.usage_metadata.total_token_count = 150

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Rate limit exceeded (429)")
            return mock_response

        # Mock 第一个客户端
        with patch.object(llm.client.models, "generate_content", side_effect=side_effect):
            # Mock Client 构造函数，以便轮换密钥时返回一个新的 mock 客户端
            with patch("google.genai.Client") as mock_client_class:
                # 创建一个新的 mock 客户端用于轮换后
                new_mock_client = MagicMock()
                new_mock_client.models.generate_content.return_value = mock_response
                mock_client_class.return_value = new_mock_client
                
                result_text, usage_metadata = await llm._call_gemini_api("test prompt")
                assert result_text == "success"
                assert usage_metadata["total_token_count"] == 150
                assert llm.current_key_index == 1  # 已轮换到第二个密钥

    @pytest.mark.asyncio
    async def test_call_gemini_api_rate_limit_no_more_keys(self):
        """测试速率限制且无更多密钥"""
        config = GeminiConfig(
            api_keys=["test_key_1"],  # 只有一个密钥
            model="gemini-2.0-flash-exp",
        )
        llm = GeminiLLM(config)

        with patch.object(
            llm.client.models,
            "generate_content",
            side_effect=Exception("Rate limit exceeded (429)")
        ):
            with pytest.raises(RateLimitError):
                await llm._call_gemini_api("test prompt")

    @pytest.mark.asyncio
    async def test_generate_artifact_success(
        self, gemini_config, prompt_template, prompt_instance, transcript
    ):
        """测试成功生成衍生内容"""
        llm = GeminiLLM(gemini_config)

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "title": "产品规划会议",
                "participants": ["张三", "李四"],
                "summary": "讨论了产品规划",
                "key_points": ["优先考虑用户反馈"],
                "action_items": [],
            },
            ensure_ascii=False,
        )

        with patch.object(llm.client.models, "generate_content", return_value=mock_response):
            artifact = await llm.generate_artifact(
                transcript=transcript,
                prompt_instance=prompt_instance,
                output_language=OutputLanguage.ZH_CN,
                template=prompt_template,
                task_id="task_123",
                artifact_id="art_001",
                version=1,
                created_by="user_456",
            )

            assert artifact.artifact_type == "meeting_minutes"
            assert artifact.task_id == "task_123"
            assert artifact.version == 1
            assert artifact.created_by == "user_456"

            # 验证 content 可以解析
            content_dict = artifact.get_content_dict()
            assert content_dict["title"] == "产品规划会议"
            assert len(content_dict["participants"]) == 2

    @pytest.mark.asyncio
    async def test_generate_artifact_no_template(self, gemini_config, prompt_instance, transcript):
        """测试无模板生成衍生内容"""
        llm = GeminiLLM(gemini_config)

        with pytest.raises(LLMError, match="Template not provided"):
            await llm.generate_artifact(
                transcript=transcript,
                prompt_instance=prompt_instance,
                output_language=OutputLanguage.ZH_CN,
                task_id="task_123",
            )

    @pytest.mark.asyncio
    async def test_get_prompt_template(self, gemini_config):
        """测试获取提示词模板"""
        llm = GeminiLLM(gemini_config)
        template = await llm.get_prompt_template("tpl_001")
        assert "会议纪要助手" in template
        assert "JSON" in template
