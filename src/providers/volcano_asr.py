"""Volcano Engine ASR Provider Implementation."""

import asyncio
import json
from typing import Optional

import httpx

from src.config.models import VolcanoConfig
from src.core.exceptions import (
    ASRError,
    AudioFormatError,
    AuthenticationError,
    RateLimitError,
    SensitiveContentError,
)
from src.core.models import ASRLanguage, HotwordSet, Segment, TranscriptionResult
from src.core.providers import ASRProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VolcanoASR(ASRProvider):
    """火山引擎 ASR 提供商实现"""

    def __init__(self, config: VolcanoConfig):
        """
        初始化火山引擎 ASR 提供商

        Args:
            config: 火山引擎配置
        """
        self.config = config
        # V3 API 端点
        self.submit_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/submit"
        self.query_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/query"
        self.resource_id = "volc.bigasr.auc"

    async def transcribe(
        self,
        audio_url: str,
        asr_language: ASRLanguage = ASRLanguage.ZH_EN,
        hotword_set: Optional[HotwordSet] = None,
        **kwargs,
    ) -> TranscriptionResult:
        """
        转写音频

        Args:
            audio_url: 音频文件 URL
            asr_language: ASR 识别语言
            hotword_set: 热词集
            **kwargs: 其他提供商特定参数

        Returns:
            TranscriptionResult: 转写结果

        Raises:
            ASRError: ASR 相关错误
            SensitiveContentError: 敏感内容被屏蔽
            AudioFormatError: 音频格式错误
        """
        try:
            # 提交转写任务 (V3 API 返回 task_id 和 x_tt_logid)
            task_id, x_tt_logid = await self._submit_task(audio_url, asr_language, hotword_set, **kwargs)
            logger.info(f"Volcano ASR task submitted: {task_id}")

            # 轮询结果(指数退避)
            result = await self._poll_result(task_id, x_tt_logid)
            logger.info(f"Volcano ASR task completed: {task_id}")

            # 解析结果为 TranscriptionResult
            return self._parse_result(result, audio_url)

        except (ASRError, SensitiveContentError, AudioFormatError):
            raise
        except Exception as e:
            logger.error(f"Volcano ASR transcription failed: {e}")
            raise ASRError(f"Volcano ASR transcription failed: {e}")

    async def _submit_task(
        self,
        audio_url: str,
        asr_language: ASRLanguage,
        hotword_set: Optional[HotwordSet],
        **kwargs,
    ) -> tuple[str, str]:
        """
        提交转写任务 (V3 API)

        Args:
            audio_url: 音频文件 URL
            asr_language: ASR 识别语言
            hotword_set: 热词集
            **kwargs: 其他参数

        Returns:
            tuple[str, str]: (task_id, x_tt_logid)

        Raises:
            ASRError: 提交失败
            AuthenticationError: 认证失败
            RateLimitError: 超频
        """
        # 生成任务 ID
        import uuid
        task_id = str(uuid.uuid4())

        # 构建 V3 API 请求头
        headers = {
            "X-Api-App-Key": self.config.app_id,
            "X-Api-Access-Key": self.config.access_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1",
        }

        # 构建 V3 API 请求体
        request_body = {
            "user": {"uid": kwargs.get("user_id", "python_client")},
            "audio": {"url": audio_url},
            "request": {
                "model_name": "bigmodel",
                "enable_channel_split": False,
                "enable_ddc": True,  # 语言顺滑
                "enable_speaker_info": True,  # 说话人分离
                "enable_punc": True,  # 标点
                "enable_itn": True,  # 数字归一化
                "language": self._map_language(asr_language),
                "corpus": {"correct_table_name": "", "context": ""},
            },
        }

        # 添加音频格式
        audio_format = kwargs.get("audio_format")
        if audio_format:
            request_body["audio"]["format"] = audio_format

        # 添加热词
        # 优先级：用户热词 > 全局热词
        if hotword_set and hotword_set.provider == "volcano":
            # 用户自定义热词
            request_body["request"]["corpus"]["correct_table_name"] = (
                hotword_set.provider_resource_id
            )
        elif self.config.boosting_table_id:
            # 全局热词（从配置读取）
            request_body["request"]["corpus"]["correct_table_name"] = (
                self.config.boosting_table_id
            )

        # 发送请求
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.post(
                    self.submit_url, json=request_body, headers=headers
                )

                # V3 API 使用 header 返回状态
                status_code = response.headers.get("X-Api-Status-Code", "")
                message = response.headers.get("X-Api-Message", "")
                x_tt_logid = response.headers.get("X-Tt-Logid", "")

                if status_code == "20000000":
                    logger.info(f"Volcano ASR V3 task submitted: {task_id}")
                    return task_id, x_tt_logid
                elif status_code.startswith("40"):
                    # 40xxxxxx: 认证相关错误
                    raise AuthenticationError(f"Volcano ASR authentication failed: {message}")
                elif status_code.startswith("4") or status_code.startswith("5"):
                    # 其他 4x/5x 错误
                    raise ASRError(f"Volcano ASR task submission failed: [{status_code}] {message}")
                else:
                    raise ASRError(f"Volcano ASR task submission failed: [{status_code}] {message}")

            except httpx.HTTPError as e:
                logger.error(f"Volcano ASR HTTP error: {e}")
                raise ASRError(f"Volcano ASR HTTP error: {e}")

    async def _poll_result(self, task_id: str, x_tt_logid: str, max_wait: int = 300) -> dict:
        """
        轮询转写结果 (V3 API, 指数退避)

        Args:
            task_id: 任务 ID
            x_tt_logid: 日志 ID
            max_wait: 最大等待时间(秒)

        Returns:
            dict: 转写结果

        Raises:
            ASRError: 轮询失败或超时
        """
        # 构建 V3 API 请求头
        headers = {
            "X-Api-App-Key": self.config.app_id,
            "X-Api-Access-Key": self.config.access_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Tt-Logid": x_tt_logid,
        }

        start_time = asyncio.get_event_loop().time()
        retry_delay = 2  # 初始延迟 2 秒
        max_retry_delay = 30  # 最大延迟 30 秒

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            while True:
                # 检查超时
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait:
                    raise ASRError(f"Volcano ASR polling timeout after {max_wait}s")

                try:
                    response = await client.post(
                        self.query_url, json={}, headers=headers
                    )

                    # V3 API 使用 header 返回状态
                    status_code = response.headers.get("X-Api-Status-Code", "")
                    message = response.headers.get("X-Api-Message", "")

                    if status_code == "20000000":
                        # 转写成功
                        result_data = response.json() if response.text else {}
                        return result_data.get("result", {})
                    elif status_code in ["20000001", "20000002"]:
                        # 处理中或排队中,继续轮询
                        status_text = "处理中" if status_code == "20000001" else "排队中"
                        logger.debug(f"Volcano ASR task {task_id} {status_text}: {message}")
                        await asyncio.sleep(retry_delay)
                        # 指数退避,最大 30 秒
                        retry_delay = min(retry_delay * 1.5, max_retry_delay)
                    else:
                        # 任务失败
                        raise ASRError(f"Volcano ASR task failed: [{status_code}] {message}")

                except httpx.HTTPError as e:
                    logger.error(f"Volcano ASR polling HTTP error: {e}")
                    raise ASRError(f"Volcano ASR polling HTTP error: {e}")

    def _parse_result(self, result: dict, audio_url: str) -> TranscriptionResult:
        """
        解析 V3 API 响应为 TranscriptionResult

        Args:
            result: V3 API 响应 (result 字段内容)
            audio_url: 音频文件 URL

        Returns:
            TranscriptionResult: 转写结果

        Raises:
            SensitiveContentError: 检测到敏感内容
        """
        # 获取完整文本
        text = result.get("text", "")
        
        # 检查敏感词屏蔽
        if "*" in text or "***" in text:
            logger.warning(f"Sensitive content detected in Volcano ASR result")
            raise SensitiveContentError("Sensitive content detected and masked by Volcano ASR")

        # 解析 utterances
        utterances = result.get("utterances", [])
        segments = []

        if utterances:
            # 有分段信息
            for utterance in utterances:
                # V3 API: 说话人信息在 additions.speaker 字段
                speaker_id = utterance.get("additions", {}).get("speaker", "1")
                speaker_label = f"Speaker {speaker_id}"
                
                segment = Segment(
                    text=utterance.get("text", ""),
                    start_time=utterance.get("start_time", 0) / 1000.0,  # 毫秒转秒
                    end_time=utterance.get("end_time", 0) / 1000.0,
                    speaker=speaker_label,
                    confidence=None,  # Volcano API 不返回置信度
                )
                segments.append(segment)
        elif text:
            # 没有分段信息,创建单个 segment
            logger.warning("No utterances in Volcano ASR result, creating single segment")
            duration = result.get("audio_info", {}).get("duration", 0) / 1000.0
            segment = Segment(
                text=text,
                start_time=0.0,
                end_time=duration,
                speaker="Speaker 1",
                confidence=None,
            )
            segments.append(segment)

        # 计算音频时长
        duration = max((seg.end_time for seg in segments), default=0.0)

        return TranscriptionResult(
            segments=segments,
            full_text=text,
            duration=duration,
            language=result.get("language", "zh-CN"),
            provider="volcano",
        )

    async def get_task_status(self, task_id: str, x_tt_logid: str) -> dict:
        """
        查询转写任务状态 (V3 API)

        Args:
            task_id: 任务 ID
            x_tt_logid: 日志 ID

        Returns:
            dict: 任务状态信息
        """
        headers = {
            "X-Api-App-Key": self.config.app_id,
            "X-Api-Access-Key": self.config.access_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Tt-Logid": x_tt_logid,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.post(
                    self.query_url, json={}, headers=headers
                )

                status_code = response.headers.get("X-Api-Status-Code", "")
                message = response.headers.get("X-Api-Message", "")

                return {
                    "status_code": status_code,
                    "message": message,
                    "data": response.json() if response.text else {},
                }

            except httpx.HTTPError as e:
                logger.error(f"Volcano ASR status query HTTP error: {e}")
                raise ASRError(f"Volcano ASR status query HTTP error: {e}")

    def get_provider_name(self) -> str:
        """
        获取提供商名称

        Returns:
            str: 提供商名称 (volcano)
        """
        return "volcano"

    def _map_language(self, asr_language: ASRLanguage) -> str:
        """
        映射 ASRLanguage 到火山引擎语言代码

        中英混合使用空字符串(火山引擎特殊处理)

        Args:
            asr_language: ASR 语言枚举

        Returns:
            str: 火山引擎语言代码
        """
        mapping = {
            ASRLanguage.ZH_CN: "zh-CN",
            ASRLanguage.EN_US: "en-US",
            ASRLanguage.ZH_EN: "",  # 中英混合使用空字符串
            ASRLanguage.JA_JP: "ja-JP",
            ASRLanguage.KO_KR: "ko-KR",
        }
        return mapping.get(asr_language, "")
