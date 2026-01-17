"""Abstract provider interfaces for ASR, Voiceprint, and LLM services."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.models import (
    ASRLanguage,
    GeneratedArtifact,
    HotwordSet,
    OutputLanguage,
    PromptInstance,
    SpeakerIdentity,
    TranscriptionResult,
)


class ASRProvider(ABC):
    """ASR 提供商抽象基类"""

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_task_status(self, task_id: str) -> dict:
        """
        查询转写任务状态

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务状态信息
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取提供商名称

        Returns:
            str: 提供商名称 (volcano/azure)
        """
        pass


class VoiceprintProvider(ABC):
    """声纹识别提供商抽象基类"""

    @abstractmethod
    async def identify_speakers(
        self,
        transcript: TranscriptionResult,
        audio_url: str,
        known_speakers: Optional[List[SpeakerIdentity]] = None,
        **kwargs,
    ) -> dict:
        """
        识别说话人

        Args:
            transcript: 转写结果
            audio_url: 音频文件 URL
            known_speakers: 已知说话人列表(用于 1:N 搜索)
            **kwargs: 其他提供商特定参数

        Returns:
            dict: 说话人映射 {speaker_label: speaker_name}

        Raises:
            VoiceprintError: 声纹识别相关错误
            VoiceprintNotFoundError: 声纹未找到
            VoiceprintQualityError: 声纹质量不足
        """
        pass

    @abstractmethod
    async def extract_audio_sample(
        self, audio_url: str, start_time: float, end_time: float
    ) -> bytes:
        """
        提取音频样本

        Args:
            audio_url: 音频文件 URL
            start_time: 开始时间(秒)
            end_time: 结束时间(秒)

        Returns:
            bytes: 音频样本数据
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取提供商名称

        Returns:
            str: 提供商名称 (iflytek)
        """
        pass


class LLMProvider(ABC):
    """LLM 提供商抽象基类"""

    @abstractmethod
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
            **kwargs: 其他提供商特定参数

        Returns:
            GeneratedArtifact: 生成的衍生内容

        Raises:
            LLMError: LLM 相关错误
            LLMResponseParseError: 响应解析错误
            LLMTokenLimitError: Token 超限
        """
        pass

    @abstractmethod
    async def get_prompt_template(self, template_id: str) -> str:
        """
        获取提示词模板

        Args:
            template_id: 模板 ID

        Returns:
            str: 提示词模板
        """
        pass

    @abstractmethod
    def format_transcript(self, transcript: TranscriptionResult) -> str:
        """
        格式化转写文本

        Args:
            transcript: 转写结果

        Returns:
            str: 格式化后的文本
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取提供商名称

        Returns:
            str: 提供商名称 (gemini)
        """
        pass
