"""检查数据库中的转写记录"""

import sqlite3

def check_transcripts():
    """检查转写记录表"""
    
    conn = sqlite3.connect('meeting_agent.db')
    cursor = conn.cursor()
    
    # 检查最近的任务
    print("=" * 60)
    print("检查最近的任务和转写记录")
    print("=" * 60)
    
    cursor.execute("""
        SELECT 
            t.task_id,
            t.state,
            t.created_at,
            tr.transcript_id,
            tr.duration
        FROM tasks t
        LEFT JOIN transcripts tr ON t.task_id = tr.task_id
        ORDER BY t.created_at DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    for row in rows:
        task_id, state, created_at, transcript_id, duration = row
        print(f"\n任务: {task_id}")
        print(f"  状态: {state}")
        print(f"  创建时间: {created_at}")
        print(f"  转写记录ID: {transcript_id if transcript_id else '无'}")
        print(f"  时长: {duration if duration else '无'} 秒")
    
    # 统计
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)
    
    cursor.execute("SELECT COUNT(*) FROM tasks")
    task_count = cursor.fetchone()[0]
    print(f"总任务数: {task_count}")
    
    cursor.execute("SELECT COUNT(*) FROM transcripts")
    transcript_count = cursor.fetchone()[0]
    print(f"总转写记录数: {transcript_count}")
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM tasks t
        LEFT JOIN transcripts tr ON t.task_id = tr.task_id
        WHERE t.state = 'success' AND tr.transcript_id IS NULL
    """)
    success_no_transcript = cursor.fetchone()[0]
    print(f"成功但无转写记录的任务数: {success_no_transcript}")
    
    conn.close()

if __name__ == "__main__":
    check_transcripts()
