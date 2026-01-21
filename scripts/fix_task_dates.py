"""修复任务的会议日期"""

import sys
import sqlite3
import json
from pathlib import Path

project_root = Path(__file__).parent.parent

def fix_task_date(task_id: str):
    """修复任务的会议日期"""
    db_path = project_root / "meeting_agent.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 查询任务信息
    cursor.execute("""
        SELECT original_filenames, meeting_date
        FROM tasks
        WHERE task_id = ?
    """, (task_id,))
    
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ 任务不存在: {task_id}")
        conn.close()
        return
    
    original_filenames, current_date = row
    
    if not original_filenames:
        print(f"❌ 任务没有原始文件名: {task_id}")
        conn.close()
        return
    
    # 解析文件名
    filenames = json.loads(original_filenames)
    if not filenames:
        print(f"❌ 文件名列表为空: {task_id}")
        conn.close()
        return
    
    # 从文件名提取日期
    sys.path.insert(0, str(project_root))
    from src.utils.meeting_metadata import extract_date_from_filename
    
    extracted_date = extract_date_from_filename(filenames[0])
    
    if not extracted_date:
        print(f"❌ 无法从文件名提取日期: {filenames[0]}")
        conn.close()
        return
    
    print(f"\n任务 ID: {task_id}")
    print(f"文件名: {filenames[0]}")
    print(f"当前日期: {current_date}")
    print(f"提取的日期: {extracted_date}")
    
    if current_date == extracted_date:
        print(f"✓ 日期已经正确，无需更新")
        conn.close()
        return
    
    # 更新数据库
    cursor.execute("""
        UPDATE tasks
        SET meeting_date = ?
        WHERE task_id = ?
    """, (extracted_date, task_id))
    
    conn.commit()
    print(f"✓ 已更新任务日期: {extracted_date}")
    
    # 提示需要重新生成 artifact
    print(f"\n⚠️  注意：需要重新生成会议纪要才能在内容中看到正确的日期")
    print(f"   可以通过 API 调用重新生成：")
    print(f"   POST /api/v1/tasks/{task_id}/artifacts/meeting_minutes/regenerate")
    
    conn.close()


if __name__ == "__main__":
    task_ids = [
        "task_c65873f13d524eb4",
        "task_df5e6f8fb3854bf4",
    ]
    
    for task_id in task_ids:
        fix_task_date(task_id)
        print()
