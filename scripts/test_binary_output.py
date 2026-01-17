#!/usr/bin/env python3
"""
测试脚本：检测二进制数据输出问题

这个脚本用于重现和诊断二进制数据被打印到日志的问题
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.audio import AudioProcessor
from src.utils.logger import get_logger

# 设置日志（使用长度限制）
logger = get_logger("binary_test")


async def test_audio_extraction():
    """测试音频提取是否会输出二进制数据"""
    
    audio_file = "test_data/20251229ONE产品和业务规则中心的设计讨论会议.ogg"
    
    if not Path(audio_file).exists():
        logger.error(f"测试音频文件不存在: {audio_file}")
        return
    
    logger.info(f"开始测试音频提取: {audio_file}")
    
    processor = AudioProcessor()
    
    try:
        # 1. 测试格式转换
        logger.info("测试 1: 音频格式转换")
        converted_path = await processor.convert_format(audio_file)
        logger.info(f"转换成功: {converted_path}")
        
        # 2. 测试片段提取
        logger.info("测试 2: 提取音频片段 (0-5秒)")
        audio_sample = await processor.extract_segment(converted_path, 0.0, 5.0)
        logger.info(f"提取成功: {len(audio_sample)} bytes")
        
        # 3. 测试是否会打印二进制数据
        logger.info("测试 3: 检查日志是否包含二进制数据")
        logger.info(f"音频样本类型: {type(audio_sample)}")
        logger.info(f"音频样本长度: {len(audio_sample)}")
        
        # 故意尝试打印二进制数据（应该被过滤器截断）
        logger.info(f"音频样本内容（前100字节）: {audio_sample[:100]}")
        
        # 清理
        import os
        if os.path.exists(converted_path):
            os.remove(converted_path)
            logger.info(f"清理临时文件: {converted_path}")
        
        logger.info("✓ 所有测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_audio_extraction())
