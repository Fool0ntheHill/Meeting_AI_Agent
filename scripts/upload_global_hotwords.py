#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传全局热词到火山引擎

此脚本将 docs/external_api_docs/volcano_hotword_api.txt 中的热词
上传到火山引擎，并返回 BoostingTableID，用于后续 ASR 调用。

使用方法:
    python scripts/upload_global_hotwords.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.loader import get_config
from src.providers.volcano_hotword import VolcanoHotwordClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    # 加载配置
    config = get_config()
    
    # 初始化火山热词客户端
    client = VolcanoHotwordClient(
        app_id=config.volcano.app_id,
        access_key=config.volcano.access_key,
        secret_key=config.volcano.secret_key,
    )
    
    # 读取热词文件
    hotwords_file = project_root / "docs" / "external_api_docs" / "volcano_hotword_api.txt"
    
    if not hotwords_file.exists():
        logger.error(f"热词文件不存在: {hotwords_file}")
        return 1
    
    logger.info(f"读取热词文件: {hotwords_file}")
    hotwords_content = hotwords_file.read_text(encoding="utf-8")
    
    # 统计热词数量
    hotword_lines = [line.strip() for line in hotwords_content.strip().split("\n") if line.strip()]
    logger.info(f"热词数量: {len(hotword_lines)}")
    
    # 检查是否已存在全局热词库
    logger.info("检查现有热词库...")
    try:
        tables = client.list_boosting_tables(page_size=100)
        existing_table = None
        
        for table in tables.get("BoostingTables", []):
            if table["BoostingTableName"] == "global_hotwords":
                existing_table = table
                logger.info(f"找到现有热词库: {table['BoostingTableID']}")
                break
        
        if existing_table:
            # 更新现有热词库
            logger.info(f"更新现有热词库: {existing_table['BoostingTableID']}")
            result = client.update_boosting_table(
                boosting_table_id=existing_table["BoostingTableID"],
                hotwords_content=hotwords_content,
            )
        else:
            # 创建新热词库
            logger.info("创建新热词库...")
            result = client.create_boosting_table(
                name="global_hotwords",
                hotwords_content=hotwords_content,
            )
        
        # 打印结果
        logger.info("=" * 60)
        logger.info("热词库上传成功！")
        logger.info("=" * 60)
        logger.info(f"BoostingTableID: {result['BoostingTableID']}")
        logger.info(f"BoostingTableName: {result['BoostingTableName']}")
        logger.info(f"WordCount: {result['WordCount']}")
        logger.info(f"WordSize: {result['WordSize']}")
        logger.info(f"CreateTime: {result['CreateTime']}")
        logger.info(f"UpdateTime: {result['UpdateTime']}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("请将以下配置添加到您的配置文件中:")
        logger.info("")
        logger.info("volcano:")
        logger.info(f"  boosting_table_id: \"{result['BoostingTableID']}\"")
        logger.info("")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"上传热词库失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
