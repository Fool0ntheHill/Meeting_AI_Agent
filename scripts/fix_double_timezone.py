"""修复被时区脚本运行两次影响的任务"""

import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_double_timezone():
    """修复 task_e6ed6c336c4e4cae 的 updated_at"""
    db_path = project_root / "meeting_agent.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    task_id = "task_e6ed6c336c4e4cae"
    
    # 查询当前值
    cursor.execute("SELECT updated_at FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ 任务不存在: {task_id}")
        conn.close()
        return
    
    print(f"当前 updated_at: {row[0]}")
    
    # 减去 8 小时
    cursor.execute("""
        UPDATE tasks
        SET updated_at = datetime(updated_at, '-8 hours')
        WHERE task_id = ?
    """, (task_id,))
    
    conn.commit()
    
    # 验证
    cursor.execute("SELECT updated_at FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    
    print(f"修复后 updated_at: {row[0]}")
    print(f"✓ 修复完成")
    
    conn.close()


if __name__ == "__main__":
    fix_double_timezone()
