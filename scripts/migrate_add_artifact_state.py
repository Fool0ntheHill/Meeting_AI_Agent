"""
数据库迁移脚本：为 generated_artifacts 表添加 state 字段

用于支持异步生成 artifact 的状态追踪
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import get_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


def migrate():
    """执行迁移"""
    engine = get_engine()
    
    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("PRAGMA table_info(generated_artifacts)"))
        columns = [row[1] for row in result.fetchall()]
        
        if "state" in columns:
            logger.info("Field 'state' already exists, skipping migration")
            return
        
        logger.info("Adding 'state' field to generated_artifacts table...")
        
        # 添加 state 字段（默认值为 'success' 以兼容现有数据）
        conn.execute(text("""
            ALTER TABLE generated_artifacts 
            ADD COLUMN state VARCHAR(32) DEFAULT 'success'
        """))
        
        conn.commit()
        logger.info("✅ Migration completed successfully")


if __name__ == "__main__":
    migrate()
