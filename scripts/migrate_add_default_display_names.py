# -*- coding: utf-8 -*-
"""
数据迁移脚本：为没有 display_name 的 artifact 添加默认名称

运行方式:
    python scripts/migrate_add_default_display_names.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.models import GeneratedArtifactRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)


def migrate_display_names():
    """为没有 display_name 的 artifact 添加默认名称"""
    
    # 类型到默认名称的映射
    type_to_name = {
        "meeting_minutes": "会议纪要",
        "action_items": "行动项",
        "summary_notes": "摘要笔记",
    }
    
    db = get_session()
    try:
        # 查询所有没有 display_name 的 artifact
        artifacts = db.query(GeneratedArtifactRecord).filter(
            (GeneratedArtifactRecord.display_name == None) | 
            (GeneratedArtifactRecord.display_name == "")
        ).all()
        
        logger.info(f"Found {len(artifacts)} artifacts without display_name")
        
        updated_count = 0
        for artifact in artifacts:
            # 根据 artifact_type 设置默认名称
            default_name = type_to_name.get(artifact.artifact_type, artifact.artifact_type)
            artifact.display_name = default_name
            updated_count += 1
            logger.info(f"Set display_name='{default_name}' for artifact {artifact.artifact_id}")
        
        db.commit()
        logger.info(f"Migration completed: updated {updated_count} artifacts")
        
        # 显示统计信息
        print(f"\n✅ Migration completed successfully!")
        print(f"   Updated {updated_count} artifacts with default display_name")
        
        # 显示每种类型的统计
        for artifact_type, default_name in type_to_name.items():
            count = db.query(GeneratedArtifactRecord).filter(
                GeneratedArtifactRecord.artifact_type == artifact_type,
                GeneratedArtifactRecord.display_name == default_name
            ).count()
            if count > 0:
                print(f"   - {artifact_type}: {count} artifacts → '{default_name}'")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting display_name migration...")
    print("This will add default display_name to all artifacts that don't have one.\n")
    
    migrate_display_names()
