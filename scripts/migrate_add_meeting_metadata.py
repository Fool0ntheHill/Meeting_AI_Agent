#!/usr/bin/env python3
"""添加会议元数据字段的数据库迁移脚本"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def migrate():
    """执行迁移"""
    conn = sqlite3.connect("meeting_agent.db")
    cursor = conn.cursor()
    
    print("=" * 80)
    print("数据库迁移：添加会议元数据字段")
    print("=" * 80)
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 添加 original_filenames 字段（JSON 数组）
        if "original_filenames" not in columns:
            print("\n添加 original_filenames 字段...")
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN original_filenames TEXT
            """)
            print("✅ original_filenames 字段添加成功")
        else:
            print("\n⚠️  original_filenames 字段已存在，跳过")
        
        # 添加 meeting_date 字段（可选的会议日期）
        if "meeting_date" not in columns:
            print("\n添加 meeting_date 字段...")
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN meeting_date TEXT
            """)
            print("✅ meeting_date 字段添加成功")
        else:
            print("\n⚠️  meeting_date 字段已存在，跳过")
        
        # 添加 meeting_time 字段（可选的会议时间）
        if "meeting_time" not in columns:
            print("\n添加 meeting_time 字段...")
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN meeting_time TEXT
            """)
            print("✅ meeting_time 字段添加成功")
        else:
            print("\n⚠️  meeting_time 字段已存在，跳过")
        
        conn.commit()
        
        print("\n" + "=" * 80)
        print("迁移完成！")
        print("=" * 80)
        
        # 显示新的表结构
        print("\n新的 tasks 表结构:")
        cursor.execute("PRAGMA table_info(tasks)")
        for col in cursor.fetchall():
            print(f"  - {col[1]}: {col[2]}")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
