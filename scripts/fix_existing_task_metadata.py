"""修复已存在任务的会议元数据"""

import sys
import sqlite3
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.meeting_metadata import extract_meeting_metadata

def fix_task_metadata(task_id: str):
    """修复任务的会议元数据"""
    db_path = project_root / "meeting_agent.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 查询任务信息
    cursor.execute("""
        SELECT 
            task_id,
            name,
            original_filenames,
            meeting_date,
            meeting_time
        FROM tasks
        WHERE task_id = ?
    """, (task_id,))
    
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ 任务不存在: {task_id}")
        conn.close()
        return
    
    task_id, name, original_filenames_json, meeting_date, meeting_time = row
    
    print(f"\n{'='*60}")
    print(f"修复任务元数据: {task_id}")
    print(f"{'='*60}")
    print(f"任务名称: {name or '(未命名)'}")
    print(f"\n当前元数据:")
    print(f"  原始文件名: {original_filenames_json or '(未保存)'}")
    print(f"  会议日期: {meeting_date or '(未设置)'}")
    print(f"  会议时间: {meeting_time or '(未设置)'}")
    
    # 解析文件名
    original_filenames = None
    if original_filenames_json:
        try:
            original_filenames = json.loads(original_filenames_json)
        except Exception as e:
            print(f"❌ 解析文件名失败: {e}")
            conn.close()
            return
    
    # 提取元数据
    extracted_date, extracted_time = extract_meeting_metadata(
        original_filenames=original_filenames,
        meeting_date=meeting_date,
        meeting_time=meeting_time,
    )
    
    print(f"\n提取的元数据:")
    print(f"  会议日期: {extracted_date or '(无法提取)'}")
    print(f"  会议时间: {extracted_time or '(无法提取)'}")
    
    # 更新数据库
    if extracted_date != meeting_date or extracted_time != meeting_time:
        cursor.execute("""
            UPDATE tasks
            SET meeting_date = ?, meeting_time = ?
            WHERE task_id = ?
        """, (extracted_date, extracted_time, task_id))
        
        conn.commit()
        print(f"\n✓ 元数据已更新到数据库")
    else:
        print(f"\n✓ 元数据无需更新")
    
    conn.close()
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = input("请输入任务 ID: ").strip()
    
    if task_id:
        fix_task_metadata(task_id)
    else:
        print("❌ 请提供任务 ID")
