"""Cost tracking and estimation utilities."""

from datetime import datetime
from typing import Dict, Optional

from src.config.models import PricingConfig


class CostTracker:
    """成本跟踪器"""

    def __init__(self, pricing_config: Optional[PricingConfig] = None):
        """
        初始化成本跟踪器
        
        Args:
            pricing_config: 价格配置，如果为 None 则使用默认价格
        """
        self.pricing = pricing_config or PricingConfig()

    async def estimate_task_cost(
        self,
        audio_duration: float,
        enable_speaker_recognition: bool = True,
        asr_provider: str = "volcano",
        llm_model: str = "gemini-flash",
    ) -> Dict[str, float]:
        """
        预估任务成本

        Args:
            audio_duration: 音频时长(秒)
            enable_speaker_recognition: 是否启用说话人识别
            asr_provider: ASR 提供商 (volcano/azure)
            llm_model: LLM 模型 (gemini-flash/gemini-pro)

        Returns:
            Dict[str, float]: 成本拆分 {
                "asr": ASR 成本,
                "voiceprint": 声纹识别成本,
                "llm": LLM 成本,
                "total": 总成本
            }
        """
        # ASR 成本
        if asr_provider == "volcano":
            asr_cost = audio_duration * self.pricing.volcano_asr_per_second
        elif asr_provider == "azure":
            asr_cost = audio_duration * self.pricing.azure_asr_per_second
        else:
            asr_cost = audio_duration * self.pricing.volcano_asr_per_second

        # 声纹识别成本（按次计费）
        voiceprint_cost = 0.0
        if enable_speaker_recognition:
            # 每个说话人识别一次
            voiceprint_cost = (
                self.pricing.estimated_speakers_count * 
                self.pricing.iflytek_voiceprint_per_call
            )

        # LLM 成本(基于预估 Token 数)
        estimated_tokens = audio_duration * self.pricing.estimated_tokens_per_second
        if llm_model == "gemini-pro":
            llm_cost = estimated_tokens * self.pricing.gemini_pro_per_token
        else:  # gemini-flash
            llm_cost = estimated_tokens * self.pricing.gemini_flash_per_token

        total_cost = asr_cost + voiceprint_cost + llm_cost

        return {
            "asr": round(asr_cost, 4),
            "voiceprint": round(voiceprint_cost, 4),
            "llm": round(llm_cost, 4),
            "total": round(total_cost, 4),
        }

    async def track_api_call(
        self,
        task_id: str,
        provider: str,
        api_type: str,
        cost: float,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        记录 API 调用成本

        Args:
            task_id: 任务 ID
            provider: 提供商
            api_type: API 类型
            cost: 成本
            metadata: 额外元数据
        """
        # TODO: 实际实现需要写入数据库
        # await db.cost_records.insert(
        #     task_id=task_id,
        #     provider=provider,
        #     api_type=api_type,
        #     cost=cost,
        #     metadata=metadata,
        #     timestamp=datetime.now()
        # )

        # 记录日志(如果 logger 可用)
        try:
            from src.utils.logger import get_logger
            logger = get_logger(__name__)
            logger.info(
                "api_cost_tracked",
                task_id=task_id,
                provider=provider,
                api_type=api_type,
                cost=cost,
                metadata=metadata,
            )
        except ImportError:
            pass

    def calculate_asr_cost(self, duration: float, provider: str = "volcano") -> float:
        """
        计算 ASR 成本

        Args:
            duration: 音频时长(秒)
            provider: 提供商 (volcano/azure)

        Returns:
            float: 成本(元)
        """
        if provider == "volcano":
            price = self.pricing.volcano_asr_per_second
        elif provider == "azure":
            price = self.pricing.azure_asr_per_second
        else:
            price = self.pricing.volcano_asr_per_second
        return round(duration * price, 4)

    def calculate_voiceprint_cost(self, speaker_count: int) -> float:
        """
        计算声纹识别成本（按次计费）

        Args:
            speaker_count: 说话人数量（识别次数）

        Returns:
            float: 成本(元)
        """
        return round(speaker_count * self.pricing.iflytek_voiceprint_per_call, 4)

    def calculate_llm_cost(self, token_count: int, model: str = "gemini-flash") -> float:
        """
        计算 LLM 成本

        Args:
            token_count: Token 数量
            model: 模型名称 (gemini-flash/gemini-pro)

        Returns:
            float: 成本(元)
        """
        if model == "gemini-pro":
            price = self.pricing.gemini_pro_per_token
        else:  # gemini-flash
            price = self.pricing.gemini_flash_per_token
        return round(token_count * price, 4)

    def estimate_tokens_from_duration(self, duration: float) -> int:
        """
        根据音频时长估算 Token 数

        Args:
            duration: 音频时长(秒)

        Returns:
            int: 估算的 Token 数
        """
        return int(duration * self.pricing.estimated_tokens_per_second)
