import sqlite3
conn = sqlite3.connect('meeting_agent.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("数据库表:")
for row in cursor.fetchall():
    print(f"  - {row[0]}")
conn.close()
