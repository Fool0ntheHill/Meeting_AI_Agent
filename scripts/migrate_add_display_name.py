"""
添加 display_name 字段到 generated_artifacts 表

用于存储用户自定义的 artifact 显示名称
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import get_session
from src.utils.logger import get_logger

logger = get_logger(__name__)


def migrate():
    """添加 display_name 字段"""
    session = get_session()
    
    try:
        # 检查字段是否已存在
        result = session.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('generated_artifacts')
            WHERE name = 'display_name'
        """))
        
        count = result.fetchone()[0]
        
        if count > 0:
            logger.info("✅ display_name 字段已存在，无需迁移")
            return
        
        # 添加字段
        logger.info("📝 添加 display_name 字段到 generated_artifacts 表...")
        session.execute(text("""
            ALTER TABLE generated_artifacts
            ADD COLUMN display_name VARCHAR(256)
        """))
        
        session.commit()
        logger.info("✅ display_name 字段添加成功")
        
        # 验证
        result = session.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('generated_artifacts')
            WHERE name = 'display_name'
        """))
        
        count = result.fetchone()[0]
        if count == 1:
            logger.info("✅ 验证成功：display_name 字段已添加")
        else:
            logger.error("❌ 验证失败：display_name 字段未添加")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("开始迁移：添加 display_name 字段")
    logger.info("=" * 80)
    
    migrate()
    
    logger.info("=" * 80)
    logger.info("迁移完成")
    logger.info("=" * 80)
