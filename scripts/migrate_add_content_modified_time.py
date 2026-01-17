#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移：添加内容最后修改时间字段

为 Task 表添加 last_content_modified_at 字段，用于追踪内容修改时间
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database.session import get_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


def migrate():
    """执行数据库迁移"""
    engine = get_engine()
    
    print("开始数据库迁移：添加内容最后修改时间字段...\n")
    
    with engine.connect() as conn:
        # 1. 为 tasks 表添加 last_content_modified_at 字段
        print("1. 为 tasks 表添加 last_content_modified_at 字段...")
        try:
            conn.execute(text("""
                ALTER TABLE tasks 
                ADD COLUMN last_content_modified_at DATETIME
            """))
            conn.commit()
            print("   ✅ 添加 last_content_modified_at 字段")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("   ⚠️  字段已存在，跳过")
            else:
                raise
        
        # 2. 为现有任务设置初始值（使用 completed_at 或 updated_at）
        print("\n2. 为现有任务设置初始值...")
        try:
            conn.execute(text("""
                UPDATE tasks 
                SET last_content_modified_at = COALESCE(completed_at, updated_at)
                WHERE last_content_modified_at IS NULL
            """))
            conn.commit()
            print("   ✅ 已为现有任务设置初始值")
        except Exception as e:
            print(f"   ⚠️  设置初始值失败: {e}")
        
        # 3. 创建索引
        print("\n3. 创建索引...")
        try:
            conn.execute(text("""
                CREATE INDEX idx_task_content_modified 
                ON tasks(last_content_modified_at)
            """))
            conn.commit()
            print("   ✅ 创建 idx_task_content_modified 索引")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("   ⚠️  索引已存在，跳过")
            else:
                raise
    
    print("\n✅ 迁移完成！")
    print("\n新增功能:")
    print("  - tasks.last_content_modified_at：内容最后修改时间")
    print("  - 追踪转写修正、说话人修正、生成内容等操作")
    print()


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\n❌ 迁移失败: {e}")
        sys.exit(1)
