"""
检查数据库中的 folder_id 字段
"""

import sqlite3
import json

def check_db_folders():
    """检查数据库中的文件夹数据"""
    
    conn = sqlite3.connect("meeting_agent.db")
    cursor = conn.cursor()
    
    print("=" * 60)
    print("检查数据库中的 folder_id 字段")
    print("=" * 60)
    print()
    
    # 检查 tasks 表结构
    print("1. Tasks 表结构:")
    print("-" * 60)
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]:20s} {col[2]:15s} {'NOT NULL' if col[3] else 'NULL'}")
    print()
    
    # 检查是否有 folder_id 列
    has_folder_id = any(col[1] == 'folder_id' for col in columns)
    if not has_folder_id:
        print("❌ tasks 表中没有 folder_id 列！")
        print("   需要运行数据库迁移脚本添加 folder_id 列")
        print()
    else:
        print("✓ tasks 表中有 folder_id 列")
        print()
    
    # 检查任务的 folder_id 值
    print("2. 任务的 folder_id 统计:")
    print("-" * 60)
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(folder_id) as with_folder,
            COUNT(*) - COUNT(folder_id) as without_folder
        FROM tasks
    """)
    stats = cursor.fetchone()
    print(f"  总任务数: {stats[0]}")
    print(f"  有 folder_id: {stats[1]}")
    print(f"  无 folder_id (NULL): {stats[2]}")
    print()
    
    # 显示有 folder_id 的任务示例
    if stats[1] > 0:
        print("3. 有 folder_id 的任务示例:")
        print("-" * 60)
        cursor.execute("""
            SELECT task_id, name, folder_id
            FROM tasks
            WHERE folder_id IS NOT NULL
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  task_id: {row[0]}")
            print(f"  name: {row[1]}")
            print(f"  folder_id: {row[2]}")
            print()
    
    # 检查 folders 表
    print("4. Folders 表:")
    print("-" * 60)
    try:
        cursor.execute("SELECT COUNT(*) FROM folders")
        folder_count = cursor.fetchone()[0]
        print(f"  文件夹总数: {folder_count}")
        
        if folder_count > 0:
            cursor.execute("""
                SELECT folder_id, name, parent_id
                FROM folders
                LIMIT 10
            """)
            print("\n  文件夹列表:")
            for row in cursor.fetchall():
                print(f"    - {row[0]}: {row[1]} (parent: {row[2]})")
    except sqlite3.OperationalError as e:
        print(f"  ❌ folders 表不存在或查询失败: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_db_folders()
