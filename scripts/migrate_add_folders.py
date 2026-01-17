# -*- coding: utf-8 -*-
"""添加文件夹和回收站功能的数据库迁移

使用方法:
    python scripts/migrate_add_folders.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import get_engine


def migrate():
    """执行迁移"""
    engine = get_engine()
    
    print("开始数据库迁移：添加文件夹和回收站功能...")
    print()
    
    with engine.connect() as conn:
        # 1. 创建 folders 表
        print("1. 创建 folders 表...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS folders (
                folder_id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(256) NOT NULL,
                parent_id VARCHAR(64),
                owner_user_id VARCHAR(64) NOT NULL,
                owner_tenant_id VARCHAR(64) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES folders(folder_id) ON DELETE CASCADE
            )
        """))
        print("   ✅ folders 表创建成功")
        
        # 2. 为 tasks 表添加新字段
        print("2. 为 tasks 表添加新字段...")
        
        try:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN folder_id VARCHAR(64)"))
            print("   ✅ 添加 folder_id 字段")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   ⚠️  folder_id 字段已存在，跳过")
            else:
                raise
        
        try:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0"))
            print("   ✅ 添加 is_deleted 字段")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   ⚠️  is_deleted 字段已存在，跳过")
            else:
                raise
        
        try:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP"))
            print("   ✅ 添加 deleted_at 字段")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   ⚠️  deleted_at 字段已存在，跳过")
            else:
                raise
        
        # 3. 创建索引
        print("3. 创建索引...")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_folder_owner_user ON folders(owner_user_id)"))
            print("   ✅ 创建 idx_folder_owner_user 索引")
        except:
            print("   ⚠️  idx_folder_owner_user 索引已存在，跳过")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_folder_owner_tenant ON folders(owner_tenant_id)"))
            print("   ✅ 创建 idx_folder_owner_tenant 索引")
        except:
            print("   ⚠️  idx_folder_owner_tenant 索引已存在，跳过")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_folder_parent ON folders(parent_id)"))
            print("   ✅ 创建 idx_folder_parent 索引")
        except:
            print("   ⚠️  idx_folder_parent 索引已存在，跳过")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_folder ON tasks(folder_id)"))
            print("   ✅ 创建 idx_task_folder 索引")
        except:
            print("   ⚠️  idx_task_folder 索引已存在，跳过")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_deleted ON tasks(is_deleted, deleted_at)"))
            print("   ✅ 创建 idx_task_deleted 索引")
        except:
            print("   ⚠️  idx_task_deleted 索引已存在，跳过")
        
        conn.commit()
    
    print()
    print("✅ 迁移完成！")
    print()
    print("新增功能:")
    print("  - folders 表：用于存储文件夹结构")
    print("  - tasks.folder_id：任务所属文件夹")
    print("  - tasks.is_deleted：软删除标记")
    print("  - tasks.deleted_at：删除时间")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
