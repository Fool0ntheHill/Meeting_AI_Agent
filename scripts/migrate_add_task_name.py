#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""添加任务名称字段的数据库迁移脚本"""

import sys
import sqlite3
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def migrate():
    """执行迁移"""
    print("="*60)
    print("数据库迁移：添加任务名称字段")
    print("="*60)
    
    # 连接数据库
    db_path = project_root / "meeting_agent.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        print("\n1. 检查字段是否已存在...")
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'name' in columns:
            print("   ⚠️  字段 'name' 已存在，跳过迁移")
            return
        
        # 添加 name 字段
        print("\n2. 添加 name 字段...")
        cursor.execute("""
            ALTER TABLE tasks 
            ADD COLUMN name VARCHAR(255)
        """)
        conn.commit()
        print("   ✅ 字段已添加")
        
        # 验证
        print("\n3. 验证迁移...")
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'name' in columns:
            print("   ✅ 迁移成功")
        else:
            print("   ❌ 迁移失败")
            sys.exit(1)
    
    finally:
        conn.close()
    
    print("\n" + "="*60)
    print("✅ 迁移完成！")
    print("="*60)


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
