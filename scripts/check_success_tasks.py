"""检查成功的任务"""

import sqlite3

conn = sqlite3.connect('meeting_agent.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        t.task_id,
        t.state,
        t.created_at,
        tr.transcript_id,
        tr.duration
    FROM tasks t
    LEFT JOIN transcripts tr ON t.task_id = tr.task_id
    WHERE t.state = 'success'
    ORDER BY t.created_at DESC
    LIMIT 10
""")

rows = cursor.fetchall()

print("成功的任务:")
for row in rows:
    task_id, state, created_at, transcript_id, duration = row
    print(f"\n任务: {task_id}")
    print(f"  创建时间: {created_at}")
    print(f"  转写记录: {transcript_id if transcript_id else '无'}")
    print(f"  时长: {duration if duration else '无'} 秒")

conn.close()
