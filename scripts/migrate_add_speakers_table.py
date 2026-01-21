#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加 speakers 表

用于存储声纹 ID 到真实姓名的映射
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database.session import get_engine

def migrate():
    """执行迁移"""
    # 获取数据库引擎
    engine = get_engine()
    
    # 创建 speakers 表
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS speakers (
        speaker_id VARCHAR(64) PRIMARY KEY,
        display_name VARCHAR(128) NOT NULL,
        tenant_id VARCHAR(64) NOT NULL,
        created_by VARCHAR(64) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_speaker_tenant ON speakers (tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_speaker_created_by ON speakers (created_by);",
    ]
    
    with engine.connect() as conn:
        print("Creating speakers table...")
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✓ speakers table created")
        
        print("\nCreating indexes...")
        for index_sql in create_indexes_sql:
            conn.execute(text(index_sql))
        conn.commit()
        print("✓ indexes created")
        
        # 插入测试数据
        print("\nInserting test speaker data...")
        test_speakers = [
            ("speaker_linyudong", "林煜东", "default", "user_test_user"),
            ("speaker_lanweiyi", "蓝为一", "default", "user_test_user"),
        ]
        
        for speaker_id, display_name, tenant_id, created_by in test_speakers:
            insert_sql = """
            INSERT OR REPLACE INTO speakers (speaker_id, display_name, tenant_id, created_by, updated_at)
            VALUES (:speaker_id, :display_name, :tenant_id, :created_by, CURRENT_TIMESTAMP)
            """
            conn.execute(
                text(insert_sql),
                {
                    "speaker_id": speaker_id,
                    "display_name": display_name,
                    "tenant_id": tenant_id,
                    "created_by": created_by,
                }
            )
            print(f"  ✓ {speaker_id} -> {display_name}")
        
        conn.commit()
        print("\n✓ Migration completed successfully")

if __name__ == "__main__":
    migrate()
