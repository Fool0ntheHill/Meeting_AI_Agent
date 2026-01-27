# -*- coding: utf-8 -*-
"""
查看数据库中的 artifact 示例

运行方式:
    python scripts/show_artifact_example.py
"""

import sys
from pathlib import Path
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.models import GeneratedArtifactRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)


def show_artifact_example():
    """显示数据库中的 artifact 示例"""
    
    db = get_session()
    try:
        # 查询最新的一条 artifact
        artifact = db.query(GeneratedArtifactRecord).order_by(
            GeneratedArtifactRecord.created_at.desc()
        ).first()
        
        if not artifact:
            print("❌ 数据库中没有 artifact 记录")
            return
        
        print("=" * 80)
        print("📄 Artifact 示例（最新一条记录）")
        print("=" * 80)
        print()
        
        # 显示所有字段
        print(f"artifact_id:        {artifact.artifact_id}")
        print(f"task_id:            {artifact.task_id}")
        print(f"artifact_type:      {artifact.artifact_type}")
        print(f"version:            {artifact.version}")
        print(f"display_name:       {artifact.display_name}")
        print(f"created_by:         {artifact.created_by}")
        print(f"created_at:         {artifact.created_at}")
        print()
        
        # 显示 JSON 字段（格式化）
        print("prompt_instance:")
        if artifact.prompt_instance:
            prompt_data = json.loads(artifact.prompt_instance)
            print(json.dumps(prompt_data, indent=2, ensure_ascii=False))
        else:
            print("  None")
        print()
        
        print("content (前 500 字符):")
        if artifact.content:
            content_data = json.loads(artifact.content)
            content_str = json.dumps(content_data, indent=2, ensure_ascii=False)
            if len(content_str) > 500:
                print(content_str[:500] + "...")
            else:
                print(content_str)
        else:
            print("  None")
        print()
        
        print("artifact_metadata:")
        if artifact.artifact_metadata:
            metadata = json.loads(artifact.artifact_metadata)
            print(json.dumps(metadata, indent=2, ensure_ascii=False))
        else:
            print("  None")
        print()
        
        print("=" * 80)
        print("📊 数据库统计")
        print("=" * 80)
        
        # 统计信息
        total_count = db.query(GeneratedArtifactRecord).count()
        print(f"总 artifact 数量: {total_count}")
        
        # 按类型统计
        from sqlalchemy import func
        type_counts = db.query(
            GeneratedArtifactRecord.artifact_type,
            func.count(GeneratedArtifactRecord.artifact_id)
        ).group_by(GeneratedArtifactRecord.artifact_type).all()
        
        print("\n按类型统计:")
        for artifact_type, count in type_counts:
            print(f"  {artifact_type}: {count}")
        
        # 有 display_name 的数量
        with_name = db.query(GeneratedArtifactRecord).filter(
            GeneratedArtifactRecord.display_name != None,
            GeneratedArtifactRecord.display_name != ""
        ).count()
        
        without_name = total_count - with_name
        
        print(f"\n有 display_name: {with_name}")
        print(f"无 display_name: {without_name}")
        
        if without_name > 0:
            print(f"\n⚠️  有 {without_name} 条记录没有 display_name")
            print("   建议运行迁移脚本: python scripts/migrate_add_default_display_names.py")
        
    except Exception as e:
        logger.error(f"Failed to show artifact: {e}", exc_info=True)
        print(f"\n❌ 查询失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    show_artifact_example()
