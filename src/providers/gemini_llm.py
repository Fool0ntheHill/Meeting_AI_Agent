"""Gemini LLM provider implementation."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

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
from src.core.providers import LLMProvider

logger = logging.getLogger(__name__)


class GeminiLLM(LLMProvider):
    """Gemini LLM 提供商实现"""

    def __init__(self, config: GeminiConfig):
        """
        初始化 Gemini LLM 提供商

        Args:
            config: Gemini 配置
        """
        self.config = config
        self.current_key_index = 0
        self._configure_api()

    def _configure_api(self) -> None:
        """配置 Gemini API"""
        if not self.config.api_keys:
            raise ValueError("Gemini API keys not configured")

        # 使用当前密钥创建客户端
        self.client = genai.Client(api_key=self.config.api_keys[self.current_key_index])

    def _rotate_api_key(self) -> bool:
        """
        轮换到下一个 API 密钥

        Returns:
            bool: 是否成功轮换(False 表示已用完所有密钥)
        """
        self.current_key_index += 1
        if self.current_key_index >= len(self.config.api_keys):
            return False

        # 重新创建客户端
        self.client = genai.Client(api_key=self.config.api_keys[self.current_key_index])
        logger.info(f"Rotated to API key index {self.current_key_index}")
        return True

    async def generate_artifact(
        self,
        transcript: TranscriptionResult,
        prompt_instance: PromptInstance,
        output_language: OutputLanguage = OutputLanguage.ZH_CN,
        **kwargs,
    ) -> GeneratedArtifact:
        """
        生成衍生内容

        Args:
            transcript: 转写结果
            prompt_instance: 提示词实例
            output_language: 输出语言
            **kwargs: 其他参数(task_id, created_by, version)

        Returns:
            GeneratedArtifact: 生成的衍生内容

        Raises:
            LLMError: LLM 相关错误
            LLMResponseParseError: 响应解析错误
            LLMTokenLimitError: Token 超限
        """
        try:
            # 1. 获取提示词模板
            template = kwargs.get("template")
            if not template:
                raise LLMError("Template not provided", provider="gemini")

            # 2. 格式化转写文本
            formatted_transcript = self.format_transcript(transcript)

            # 3. 构建完整提示词
            prompt = self._build_prompt(
                template=template,
                prompt_instance=prompt_instance,
                formatted_transcript=formatted_transcript,
                output_language=output_language,
            )

            # 4. 调用 Gemini API
            response_text, usage_metadata = await self._call_gemini_api(prompt)

            # 5. 解析响应
            content_dict = self._parse_response(response_text, template.artifact_type)

            # 6. 构建 metadata (包含 token 使用信息)
            metadata = kwargs.get("metadata", {}) or {}
            metadata.update({
                "llm_model": self.config.model,
                "token_count": usage_metadata.get("total_token_count", 0),
                "prompt_token_count": usage_metadata.get("prompt_token_count", 0),
                "candidates_token_count": usage_metadata.get("candidates_token_count", 0),
            })

            # 7. 构建 GeneratedArtifact
            artifact = GeneratedArtifact(
                artifact_id=kwargs.get("artifact_id", f"art_{datetime.now().timestamp()}"),
                task_id=kwargs.get("task_id", ""),
                artifact_type=template.artifact_type,
                version=kwargs.get("version", 1),
                prompt_instance=prompt_instance,
                content=json.dumps(content_dict, ensure_ascii=False),
                metadata=metadata,
                created_by=kwargs.get("created_by", "system"),
            )

            logger.info(
                f"Generated artifact: type={artifact.artifact_type}, "
                f"task_id={artifact.task_id}, version={artifact.version}"
            )

            return artifact

        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate artifact: {e}")
            raise LLMError(f"Failed to generate artifact: {e}", provider="gemini")

    def _build_prompt(
        self,
        template: PromptTemplate,
        prompt_instance: PromptInstance,
        formatted_transcript: str,
        output_language: OutputLanguage,
    ) -> str:
        """
        构建完整提示词

        Args:
            template: 提示词模板
            prompt_instance: 提示词实例
            formatted_transcript: 格式化后的转写文本
            output_language: 输出语言

        Returns:
            str: 完整提示词
        """
        # 1. 从模板获取 prompt_body
        prompt_body = template.prompt_body

        # 2. 替换参数占位符
        for param_name, param_value in prompt_instance.parameters.items():
            placeholder = f"{{{param_name}}}"
            if placeholder in prompt_body:
                prompt_body = prompt_body.replace(placeholder, str(param_value))

        # 3. 替换转写文本占位符
        if "{transcript}" in prompt_body:
            prompt_body = prompt_body.replace("{transcript}", formatted_transcript)
        else:
            # 如果模板中没有 {transcript} 占位符，则追加到末尾
            prompt_body += f"\n\n会议转写:\n{formatted_transcript}"

        # 4. 添加输出语言指令
        language_instruction = self._get_language_instruction(output_language)
        prompt_body += f"\n\n{language_instruction}"

        return prompt_body

    def _get_language_instruction(self, output_language: OutputLanguage) -> str:
        """
        获取输出语言指令

        Args:
            output_language: 输出语言

        Returns:
            str: 语言指令
        """
        language_map = {
            OutputLanguage.ZH_CN: "请使用中文生成会议纪要。",
            OutputLanguage.EN_US: "Please generate the meeting minutes in English.",
            OutputLanguage.JA_JP: "日本語で議事録を作成してください。",
            OutputLanguage.KO_KR: "한국어로 회의록을 작성해 주세요.",
        }
        return language_map.get(output_language, "请使用中文生成会议纪要。")

    async def _call_gemini_api(self, prompt: str) -> tuple[str, dict]:
        """
        调用 Gemini API(带指数退避重试)，使用结构化 JSON 输出

        Args:
            prompt: 提示词

        Returns:
            tuple[str, dict]: (响应文本（JSON 格式）, 使用统计信息)

        Raises:
            LLMError: API 调用失败
            LLMTokenLimitError: Token 超限
            RateLimitError: 速率限制
        """
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                # 配置生成参数 - 使用结构化 JSON 输出
                config = types.GenerateContentConfig(
                    max_output_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    response_mime_type="application/json",  # 强制 JSON 输出
                )

                # 调用 API
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.config.model,
                    contents=prompt,
                    config=config,
                )

                # 检查响应
                if not response.text:
                    raise LLMError("Empty response from Gemini", provider="gemini")

                # 提取使用统计信息
                usage_metadata = {}
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage_metadata = {
                        "prompt_token_count": getattr(response.usage_metadata, 'prompt_token_count', 0),
                        "candidates_token_count": getattr(response.usage_metadata, 'candidates_token_count', 0),
                        "total_token_count": getattr(response.usage_metadata, 'total_token_count', 0),
                    }
                    logger.info(f"Gemini API usage: {usage_metadata}")

                return response.text, usage_metadata

            except Exception as e:
                error_msg = str(e).lower()
                last_error = e

                # Token 超限
                if "token" in error_msg and "limit" in error_msg:
                    raise LLMTokenLimitError(
                        f"Token limit exceeded: {e}",
                        provider="gemini",
                        details={"error": str(e)},
                    )

                # 速率限制
                if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                    # 尝试轮换密钥
                    if self._rotate_api_key():
                        logger.warning(f"Rate limit hit, rotated to next API key")
                        continue
                    else:
                        raise RateLimitError(
                            f"Rate limit exceeded and no more API keys available: {e}",
                            provider="gemini",
                            details={"error": str(e)},
                        )

                # 其他错误,指数退避重试
                if attempt < self.config.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Gemini API call failed (attempt {attempt + 1}/{self.config.max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Gemini API call failed after {self.config.max_retries} attempts: {e}")

        raise LLMError(
            f"Failed to call Gemini API after {self.config.max_retries} attempts: {last_error}",
            provider="gemini",
        )

    def _parse_response(self, response_text: str, artifact_type: str) -> Dict[str, Any]:
        """
        解析 Gemini 响应（原生 JSON 格式）

        Args:
            response_text: 响应文本（应该是 JSON 格式）
            artifact_type: 内容类型

        Returns:
            Dict[str, Any]: 解析后的内容字典

        Raises:
            LLMResponseParseError: 响应解析错误
        """
        try:
            # 预处理：如果响应包含 Markdown 代码块，提取其中的 JSON
            json_text = response_text.strip()
            
            if "```json" in json_text:
                start = json_text.find("```json") + 7
                end = json_text.find("```", start)
                if end != -1:
                    json_text = json_text[start:end].strip()
            elif "```" in json_text:
                start = json_text.find("```") + 3
                end = json_text.find("```", start)
                if end != -1:
                    json_text = json_text[start:end].strip()
            
            # 解析 JSON
            content_dict = json.loads(json_text)
            return content_dict

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse as JSON: {e}, attempting Markdown parsing as fallback")
            
            # 如果 JSON 解析失败，尝试解析 Markdown 格式（后备方案）
            try:
                content_dict = self._parse_markdown_response(response_text, artifact_type)
                logger.info("Successfully parsed Markdown response")
                return content_dict
            except Exception as markdown_error:
                logger.error(f"Failed to parse Gemini response as JSON or Markdown: {e}\nResponse: {response_text}")
                raise LLMResponseParseError(
                    f"Invalid JSON response: {e}",
                    provider="gemini",
                    details={"response": response_text, "json_error": str(e), "markdown_error": str(markdown_error)},
                )
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise LLMResponseParseError(
                f"Failed to parse response: {e}",
                provider="gemini",
                details={"response": response_text},
            )
    
    def _parse_markdown_response(self, response_text: str, artifact_type: str) -> Dict[str, Any]:
        """
        解析 Markdown 格式的响应（后备方案）
        
        Args:
            response_text: Markdown 格式的响应文本
            artifact_type: 内容类型
            
        Returns:
            Dict[str, Any]: 解析后的内容字典
        """
        import re
        
        content_dict = {
            "raw_content": response_text,
            "format": "markdown",
        }
        
        # 提取标题（会议主题）
        title_match = re.search(r'\*\*1\.\s*会议主题\*\*\s*\n(.+?)(?:\n|$)', response_text)
        if title_match:
            content_dict["title"] = title_match.group(1).strip()
        
        # 提取参与人员
        participants_match = re.search(r'\*\*2\.\s*参与人员\*\*\s*\n(.+?)(?:\n\n|\*\*)', response_text, re.DOTALL)
        if participants_match:
            participants_text = participants_match.group(1).strip()
            # 分割参与人员（可能是逗号分隔或顿号分隔）
            participants = [p.strip() for p in re.split(r'[,、]', participants_text) if p.strip()]
            content_dict["participants"] = participants
        
        # 提取讨论要点
        key_points_match = re.search(r'\*\*3\.\s*讨论要点\*\*\s*\n(.+?)(?:\n\n\*\*|$)', response_text, re.DOTALL)
        if key_points_match:
            key_points_text = key_points_match.group(1).strip()
            # 提取列表项
            key_points = re.findall(r'\*\s+(.+?)(?:\n|$)', key_points_text)
            content_dict["key_points"] = [kp.strip() for kp in key_points if kp.strip()]
        
        # 提取决策事项
        decisions_match = re.search(r'\*\*4\.\s*决策事项\*\*\s*\n(.+?)(?:\n\n\*\*|$)', response_text, re.DOTALL)
        if decisions_match:
            decisions_text = decisions_match.group(1).strip()
            decisions = re.findall(r'\*\s+(.+?)(?:\n|$)', decisions_text)
            content_dict["decisions"] = [d.strip() for d in decisions if d.strip()]
        
        # 提取行动项
        action_items_match = re.search(r'\*\*5\.\s*行动项\*\*\s*\n(.+?)(?:\n\n\*\*|$)', response_text, re.DOTALL)
        if action_items_match:
            action_items_text = action_items_match.group(1).strip()
            action_items = []
            # 提取行动项（格式：* **[负责人]**: 任务描述）
            for match in re.finditer(r'\*\s+\*\*\[(.+?)\]\*\*[：:]\s*(.+?)(?:\n|$)', action_items_text):
                action_items.append({
                    "assignee": match.group(1).strip(),
                    "task": match.group(2).strip(),
                })
            content_dict["action_items"] = action_items
        
        logger.info(f"Parsed Markdown response: {len(content_dict)} fields extracted")
        return content_dict

    async def get_prompt_template(self, template_id: str) -> str:
        """
        获取提示词模板

        注意: 此方法在当前实现中不直接使用,模板由数据库层管理
        这里提供一个占位实现

        Args:
            template_id: 模板 ID

        Returns:
            str: 提示词模板
        """
        # 在实际使用中,模板由 PromptTemplateRepository 管理
        # 这里返回一个默认模板作为后备
        return """你是一个专业的会议纪要助手。

请根据以下会议转写生成结构化的会议纪要,包含:
1. 会议标题
2. 参与者列表
3. 会议摘要
4. 关键要点
5. 行动项

请以 JSON 格式返回结果。"""

    def format_transcript(self, transcript: TranscriptionResult) -> str:
        """
        格式化转写文本

        Args:
            transcript: 转写结果

        Returns:
            str: 格式化后的文本
        """
        if not transcript.segments:
            return ""

        lines = []
        for segment in transcript.segments:
            # 格式: [说话人] 文本 (开始时间 - 结束时间)
            speaker = segment.speaker or "未知说话人"
            start_time = self._format_time(segment.start_time)
            end_time = self._format_time(segment.end_time)
            lines.append(f"[{speaker}] {segment.text} ({start_time} - {end_time})")

        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """
        格式化时间(秒 -> HH:MM:SS)

        Args:
            seconds: 秒数

        Returns:
            str: 格式化后的时间
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_provider_name(self) -> str:
        """
        获取提供商名称

        Returns:
            str: 提供商名称
        """
        return "gemini"
