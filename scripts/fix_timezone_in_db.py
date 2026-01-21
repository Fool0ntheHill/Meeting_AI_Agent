"""修复数据库中的时区问题 - 将 UTC 时间转换为本地时间（UTC+8）"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 时区偏移（中国是 UTC+8）
TIMEZONE_OFFSET = timedelta(hours=8)

def fix_timezone():
    """修复数据库中的时区"""
    db_path = project_root / "meeting_agent.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("修复数据库时区（UTC → UTC+8）")
    print("="*60)
    
    # 需要修复的表和字段
    tables_to_fix = [
        ("tasks", ["created_at", "updated_at", "completed_at", "confirmed_at", "deleted_at", "last_content_modified_at"]),
        ("folders", ["created_at", "updated_at"]),
        ("speakers", ["created_at", "updated_at"]),
        ("users", ["created_at", "updated_at", "last_login_at"]),
        ("transcript_records", ["created_at"]),
        ("speaker_mappings", ["created_at", "corrected_at"]),
        ("prompt_templates", ["created_at", "updated_at"]),
        ("generated_artifacts", ["created_at"]),
        ("hotword_sets", ["created_at", "updated_at"]),
        ("audit_logs", ["created_at"]),
    ]
    
    total_updated = 0
    
    for table_name, time_fields in tables_to_fix:
        # 检查表是否存在
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"⚠ 表不存在，跳过: {table_name}")
            continue
        
        print(f"\n处理表: {table_name}")
        
        for field in time_fields:
            # 检查字段是否存在
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            if field not in columns:
                print(f"  ⚠ 字段不存在，跳过: {field}")
                continue
            
            # 更新时间字段（加 8 小时）
            try:
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET {field} = datetime({field}, '+8 hours')
                    WHERE {field} IS NOT NULL
                """)
                
                updated = cursor.rowcount
                total_updated += updated
                
                if updated > 0:
                    print(f"  ✓ {field}: 更新了 {updated} 条记录")
                else:
                    print(f"  - {field}: 无需更新")
            except Exception as e:
                print(f"  ✗ {field}: 更新失败 - {e}")
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✓ 完成！共更新 {total_updated} 条记录")
    print(f"{'='*60}\n")


def verify_timezone():
    """验证时区修复结果"""
    db_path = project_root / "meeting_agent.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("验证时区修复结果")
    print("="*60)
    
    # 查询最近的任务
    cursor.execute("""
        SELECT task_id, created_at, updated_at
        FROM tasks
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        print("\n最近的任务:")
        for task_id, created_at, updated_at in rows:
            print(f"  {task_id}")
            print(f"    created_at: {created_at}")
            print(f"    updated_at: {updated_at}")
    else:
        print("\n没有任务记录")
    
    conn.close()
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_timezone()
    else:
        print("\n⚠ 警告：此操作将修改数据库中的所有时间戳")
        print("建议先备份数据库文件: meeting_agent.db")
        
        confirm = input("\n确认继续？(yes/no): ").strip().lower()
        
        if confirm == "yes":
            fix_timezone()
            verify_timezone()
        else:
            print("\n已取消操作")
