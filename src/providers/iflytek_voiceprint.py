# -*- coding: utf-8 -*-
"""iFLYTEK Voiceprint Recognition Provider Implementation."""

import base64
import hashlib
import hmac
import json
from datetime import datetime
from email.utils import formatdate
from typing import Dict, List, Optional
from urllib.parse import urlencode

import httpx

from src.config.models import IFlyTekConfig
from src.core.exceptions import (
    AuthenticationError,
    RateLimitError,
    VoiceprintError,
    VoiceprintNotFoundError,
    VoiceprintQualityError,
)
from src.core.models import SpeakerIdentity, TranscriptionResult
from src.core.providers import VoiceprintProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IFlyTekVoiceprint(VoiceprintProvider):
    """科大讯飞声纹识别提供商实现"""

    def __init__(self, config: IFlyTekConfig):
        """
        初始化科大讯飞声纹提供商

        Args:
            config: 科大讯飞配置
        """
        self.config = config
        self.api_url = config.api_endpoint
        self.host = "api.xf-yun.com"
        
        # 识别阈值配置
        self.score_threshold = 0.58  # 高置信度阈值（调整为 0.58）
        self.min_accept_score = 0.40  # 最低容忍分数（防止完全是噪音）
        self.gap_threshold = 0.15  # 分差挽救阈值（需显著高于第二名）

    async def identify_speakers(
        self,
        transcript: TranscriptionResult,
        audio_url: str,
        known_speakers: Optional[List[SpeakerIdentity]] = None,
        **kwargs,
    ) -> Dict[str, str]:
        """
        识别说话人

        Args:
            transcript: 转写结果
            audio_url: 本地音频文件路径 (参数名保留为 audio_url 以兼容接口)
            known_speakers: 已知说话人列表(用于 1:N 搜索)
            **kwargs: 其他提供商特定参数

        Returns:
            dict: 说话人映射 {speaker_label: speaker_name}

        Raises:
            VoiceprintError: 声纹识别相关错误
        """
        speaker_mapping = {}
        
        # 获取唯一说话人标签
        speaker_labels = transcript.speakers
        logger.info(f"Identifying {len(speaker_labels)} speakers")

        for speaker_label in speaker_labels:
            try:
                # 提取该说话人的音频样本(3-6秒)
                audio_sample = await self._extract_speaker_sample(
                    transcript, audio_url, speaker_label
                )

                # 进行 1:N 搜索
                result = await self._search_speaker(audio_sample, known_speakers)

                if result:
                    speaker_mapping[speaker_label] = result["name"]
                    logger.info(
                        f"Speaker {speaker_label} identified as {result['name']} "
                        f"(score: {result['score']:.3f})"
                    )
                else:
                    # 识别失败,保留原标签
                    speaker_mapping[speaker_label] = speaker_label
                    logger.warning(f"Speaker {speaker_label} not identified, keeping original label")

            except Exception as e:
                # 识别失败,保留原标签
                speaker_mapping[speaker_label] = speaker_label
                logger.error(f"Failed to identify speaker {speaker_label}: {e}")

        return speaker_mapping

    async def _extract_speaker_sample(
        self, transcript: TranscriptionResult, audio_path: str, speaker_label: str
    ) -> bytes:
        """
        提取说话人音频样本(3-6秒)

        Args:
            transcript: 转写结果
            audio_path: 本地音频文件路径
            speaker_label: 说话人标签

        Returns:
            bytes: 音频样本数据

        Raises:
            VoiceprintQualityError: 音频质量不足
        """
        # 找到该说话人的所有片段
        speaker_segments = [seg for seg in transcript.segments if seg.speaker == speaker_label]

        if not speaker_segments:
            raise VoiceprintQualityError(f"No segments found for speaker {speaker_label}")

        # 选择最长的片段(或合并多个片段达到 3-6 秒)
        total_duration = 0.0
        selected_segments = []

        for seg in sorted(speaker_segments, key=lambda x: x.end_time - x.start_time, reverse=True):
            duration = seg.end_time - seg.start_time
            if duration >= 3.0 and duration <= 6.0:
                # 找到合适的单个片段
                selected_segments = [seg]
                total_duration = duration
                break
            elif total_duration < 6.0:
                selected_segments.append(seg)
                total_duration += duration
                if total_duration >= 3.0:
                    break

        if total_duration < 0.5:
            raise VoiceprintQualityError(
                f"Insufficient audio for speaker {speaker_label}: {total_duration:.2f}s"
            )

        # 提取音频片段
        if len(selected_segments) == 1:
            seg = selected_segments[0]
            return await self.extract_audio_sample(audio_path, seg.start_time, seg.end_time)
        else:
            # 合并多个片段(简化实现:只取第一个片段)
            seg = selected_segments[0]
            return await self.extract_audio_sample(audio_path, seg.start_time, seg.end_time)

    async def _search_speaker(
        self, audio_sample: bytes, known_speakers: Optional[List[SpeakerIdentity]]
    ) -> Optional[Dict[str, any]]:
        """
        在声纹库中搜索说话人(1:N)

        Args:
            audio_sample: 音频样本
            known_speakers: 已知说话人列表

        Returns:
            dict: {"name": str, "score": float, "speaker_id": str} 或 None

        Raises:
            VoiceprintError: 声纹识别错误
        """
        # 构建请求
        request_body = {
            "header": {
                "app_id": self.config.app_id,
                "status": 3,
            },
            "parameter": {
                "s1aa729d0": {
                    "func": "searchFea",
                    "groupId": self.config.group_id,
                    "topK": 5,  # 返回前5个结果用于分差挽救
                    "searchFeaRes": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json",
                    },
                },
            },
            "payload": {
                "resource": {
                    "encoding": "raw",
                    "sample_rate": 16000,
                    "channels": 1,
                    "bit_depth": 16,
                    "status": 3,
                    "audio": base64.b64encode(audio_sample).decode("utf-8"),
                },
            },
        }

        # 发送请求
        response = await self._make_request(request_body)

        # 解析响应
        if "payload" not in response or "searchFeaRes" not in response["payload"]:
            raise VoiceprintError("Invalid response format from iFLYTEK")

        # 解码 Base64 结果
        result_text = response["payload"]["searchFeaRes"]["text"]
        result_data = json.loads(base64.b64decode(result_text).decode("utf-8"))

        score_list = result_data.get("scoreList", [])
        if not score_list:
            return None

        # 获取 Top-1 和 Top-2
        top_result = score_list[0]
        top_score = top_result["score"]

        # 情况 A: 高置信度，直接采纳
        if top_score >= self.score_threshold:
            logger.info(
                f"Speaker identified with high confidence: {top_score:.3f} >= {self.score_threshold}"
            )
            feature_id = top_result["featureId"]
            speaker_name = self._get_speaker_name(feature_id, known_speakers)
            return {
                "name": speaker_name,
                "score": top_score,
                "speaker_id": feature_id,
            }

        # 情况 B: 分差挽救机制
        if len(score_list) > 1:
            second_score = score_list[1]["score"]
            score_gap = top_score - second_score

            # 分差挽救条件：
            # 1. 分数不能太低（>= min_accept_score，防止完全是噪音）
            # 2. 分差要足够大（>= gap_threshold，显著高于第二名）
            if top_score >= self.min_accept_score and score_gap >= self.gap_threshold:
                logger.info(
                    f"Speaker identified via gap rescue: score={top_score:.3f}, "
                    f"gap={score_gap:.3f} >= {self.gap_threshold}"
                )
                logger.info(
                    f"Explanation: Although score < {self.score_threshold}, "
                    f"it's significantly higher than 2nd place in closed set"
                )
                feature_id = top_result["featureId"]
                speaker_name = self._get_speaker_name(feature_id, known_speakers)
                return {
                    "name": speaker_name,
                    "score": top_score,
                    "speaker_id": feature_id,
                    "rescue_mode": "gap",
                    "score_gap": score_gap,
                }

        # 情况 C: 完全拒绝
        logger.debug(f"Top score {top_score:.3f} below threshold {self.score_threshold}")
        if top_score < self.min_accept_score:
            logger.debug(f"Score too low: {top_score:.3f} < {self.min_accept_score}")
        elif len(score_list) > 1:
            score_gap = top_score - second_score
            logger.warning(
                f"Score gap too small: {score_gap:.3f} < {self.gap_threshold}"
            )
        return None

    def _get_speaker_name(
        self, feature_id: str, known_speakers: Optional[List[SpeakerIdentity]]
    ) -> str:
        """
        根据 feature_id 获取说话人姓名

        Args:
            feature_id: 特征 ID
            known_speakers: 已知说话人列表

        Returns:
            str: 说话人姓名
        """
        if known_speakers:
            for speaker in known_speakers:
                if speaker.speaker_id == feature_id:
                    return speaker.name

        # 如果没有找到,返回 feature_id
        return feature_id

    async def extract_audio_sample(
        self, audio_path: str, start_time: float, end_time: float
    ) -> bytes:
        """
        提取音频样本

        Args:
            audio_path: 本地音频文件路径
            start_time: 开始时间(秒)
            end_time: 结束时间(秒)

        Returns:
            bytes: 音频样本数据

        Raises:
            VoiceprintError: 提取失败
        """
        # 这里需要使用 AudioProcessor 来提取音频片段
        # 为了避免循环依赖,我们在这里导入
        from src.utils.audio import AudioProcessor

        processor = AudioProcessor()

        try:
            # 直接使用本地文件路径提取片段
            audio_sample = await processor.extract_segment(audio_path, start_time, end_time)
            return audio_sample

        except Exception as e:
            logger.error(f"Failed to extract audio sample: {e}")
            raise VoiceprintError(f"Failed to extract audio sample: {e}")

    async def _make_request(self, request_body: dict) -> dict:
        """
        发送 HTTP 请求到科大讯飞 API

        Args:
            request_body: 请求体

        Returns:
            dict: 响应数据

        Raises:
            VoiceprintError: 请求失败
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
        """
        # 生成鉴权参数
        auth_params = self._generate_auth_params()

        # 构建完整 URL
        url = f"{self.api_url}?{urlencode(auth_params)}"

        # 发送请求
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=request_body,
                    headers={"Content-Type": "application/json"},
                )

                # 检查 HTTP 状态码
                if response.status_code == 401:
                    raise AuthenticationError(f"iFLYTEK authentication failed: {response.text}")
                elif response.status_code == 403:
                    raise AuthenticationError(f"iFLYTEK authorization failed: {response.text}")
                elif response.status_code == 429:
                    raise RateLimitError("iFLYTEK rate limit exceeded")

                response.raise_for_status()

                # 解析响应
                result = response.json()

                # 检查业务错误码
                if "header" in result and result["header"].get("code") != 0:
                    error_code = result["header"].get("code")
                    error_msg = result["header"].get("message", "Unknown error")
                    raise VoiceprintError(f"iFLYTEK API error {error_code}: {error_msg}")

                return result

            except httpx.HTTPError as e:
                logger.error(f"iFLYTEK HTTP error: {e}")
                raise VoiceprintError(f"iFLYTEK HTTP error: {e}")

    def _generate_auth_params(self) -> dict:
        """
        生成 HMAC-SHA256 鉴权参数

        Returns:
            dict: 鉴权参数 {host, date, authorization}
        """
        # 生成 RFC1123 格式的时间戳
        date = formatdate(timeval=None, localtime=False, usegmt=True)

        # 构造签名原始串
        request_line = "POST /v1/private/s1aa729d0 HTTP/1.1"
        signature_origin = f"host: {self.host}\ndate: {date}\n{request_line}"

        # 计算 HMAC-SHA256
        signature_sha = hmac.new(
            self.config.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        # Base64 编码签名
        signature = base64.b64encode(signature_sha).decode("utf-8")

        # 构造 Authorization 原始串
        authorization_origin = (
            f'api_key="{self.config.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )

        # Base64 编码 Authorization
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        return {
            "host": self.host,
            "date": date,
            "authorization": authorization,
        }

    def get_provider_name(self) -> str:
        """
        获取提供商名称

        Returns:
            str: 提供商名称 (iflytek)
        """
        return "iflytek"
