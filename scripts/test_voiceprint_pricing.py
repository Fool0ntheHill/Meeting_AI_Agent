#!/usr/bin/env python3
"""测试声纹识别价格计算"""

import asyncio
from src.utils.cost import CostTracker
from src.config.loader import get_config

async def main():
    config = get_config()
    tracker = CostTracker(config.pricing)
    
    print("=" * 60)
    print("声纹识别价格测试")
    print("=" * 60)
    
    # 显示配置
    print(f"\n配置价格: {config.pricing.iflytek_voiceprint_per_call} 元/次")
    print(f"说明: 10万次200元，即每次0.002元\n")
    
    # 测试不同说话人数量
    test_cases = [
        (1, "单人会议"),
        (2, "双人对话"),
        (3, "三人会议（默认估算）"),
        (5, "五人会议"),
        (10, "大型会议"),
    ]
    
    print("按说话人数量计算成本:")
    print("-" * 60)
    for speaker_count, description in test_cases:
        cost = tracker.calculate_voiceprint_cost(speaker_count)
        print(f"{description:20s} | {speaker_count:2d} 人 | ¥{cost:.4f}")
    
    # 测试完整任务成本估算
    print("\n" + "=" * 60)
    print("完整任务成本估算（包含声纹识别）")
    print("=" * 60)
    
    test_durations = [
        (60, "1分钟音频"),
        (300, "5分钟音频"),
        (600, "10分钟音频"),
        (1800, "30分钟音频"),
        (3600, "1小时音频"),
    ]
    
    for duration, description in test_durations:
        cost_breakdown = await tracker.estimate_task_cost(
            audio_duration=duration,
            enable_speaker_recognition=True,
            asr_provider="volcano",
            llm_model="gemini-flash"
        )
        
        print(f"\n{description}:")
        print(f"  ASR 成本:        ¥{cost_breakdown['asr']:.4f}")
        print(f"  声纹识别成本:    ¥{cost_breakdown['voiceprint']:.4f} (3人 × ¥0.002)")
        print(f"  LLM 成本:        ¥{cost_breakdown['llm']:.4f}")
        print(f"  总成本:          ¥{cost_breakdown['total']:.4f}")
    
    # 对比：启用 vs 不启用声纹识别
    print("\n" + "=" * 60)
    print("声纹识别成本对比（10分钟音频）")
    print("=" * 60)
    
    with_voiceprint = await tracker.estimate_task_cost(
        audio_duration=600,
        enable_speaker_recognition=True
    )
    
    without_voiceprint = await tracker.estimate_task_cost(
        audio_duration=600,
        enable_speaker_recognition=False
    )
    
    print(f"\n启用声纹识别:   ¥{with_voiceprint['total']:.4f}")
    print(f"不启用声纹识别: ¥{without_voiceprint['total']:.4f}")
    print(f"差额:           ¥{(with_voiceprint['total'] - without_voiceprint['total']):.4f}")
    
    print("\n" + "=" * 60)
    print("✓ 测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
