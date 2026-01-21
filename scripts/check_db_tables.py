#!/usr/bin/env python3
"""检查数据库表结构"""

import sqlite3

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

# 获取所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("数据库中的表:")
print("=" * 60)
for table in tables:
    table_name = table[0]
    print(f"\n表名: {table_name}")
    
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print("  列:")
    for col in columns:
        col_id, name, col_type, not_null, default, pk = col
        print(f"    - {name} ({col_type})")

conn.close()
