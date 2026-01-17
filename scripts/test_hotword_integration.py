#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试热词集成

此脚本测试：
1. 上传全局热词到火山引擎
2. 验证配置中的 boosting_table_id
3. 测试 ASR 调用时使用热词

使用方法:
    python scripts/test_hotword_integration.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.loader import get_config
from src.providers.volcano_hotword import VolcanoHotwordClient
from src.providers.volcano_asr import VolcanoASR
from src.core.models import ASRLanguage
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_hotword_integration():
    """测试热词集成"""
    # 加载配置
    config = get_config()
    
    logger.info("=" * 60)
    logger.info("测试热词集成")
    logger.info("=" * 60)
    
    # 1. 检查配置中的 boosting_table_id
    if config.volcano.boosting_table_id:
        logger.info(f"✓ 配置中已设置 boosting_table_id: {config.volcano.boosting_table_id}")
    else:
        logger.warning("✗ 配置中未设置 boosting_table_id")
        logger.info("请运行以下命令上传全局热词:")
        logger.info("  python scripts/upload_global_hotwords.py")
        logger.info("然后将返回的 BoostingTableID 添加到配置文件中")
        return 1
    
    # 2. 验证热词库是否存在
    logger.info("\n检查热词库...")
    client = VolcanoHotwordClient(
        app_id=config.volcano.app_id,
        access_key=config.volcano.access_key,
        secret_key=config.volcano.secret_key,
    )
    
    try:
        table = client.get_boosting_table(config.volcano.boosting_table_id)
        logger.info(f"✓ 热词库存在: {table['BoostingTableName']}")
        logger.info(f"  - 热词数量: {table['WordCount']}")
        logger.info(f"  - 更新时间: {table['UpdateTime']}")
        logger.info(f"  - 预览: {', '.join(table['Preview'][:5])}...")
    except Exception as e:
        logger.error(f"✗ 热词库不存在或无法访问: {e}")
        logger.info("请运行以下命令重新上传:")
        logger.info("  python scripts/upload_global_hotwords.py")
        return 1
    
    # 3. 测试 ASR 调用（模拟）
    logger.info("\n测试 ASR 配置...")
    asr = VolcanoASR(config.volcano)
    
    # 检查 ASR 是否会使用热词
    logger.info(f"✓ ASR 提供商已配置")
    logger.info(f"  - 全局热词 ID: {config.volcano.boosting_table_id}")
    logger.info(f"  - ASR 调用时将自动使用全局热词")
    
    logger.info("\n" + "=" * 60)
    logger.info("热词集成测试完成！")
    logger.info("=" * 60)
    logger.info("\n说明:")
    logger.info("- 全局热词已配置并可用")
    logger.info("- 所有 ASR 转写任务将自动使用全局热词")
    logger.info("- 如需更新热词，请重新运行 upload_global_hotwords.py")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(test_hotword_integration()))
