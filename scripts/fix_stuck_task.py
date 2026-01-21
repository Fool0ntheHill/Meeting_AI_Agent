#!/usr/bin/env python3
"""Fix the stuck task and clean up database."""

import sqlite3
import os

db_path = "meeting_agent.db"
stuck_task_id = "task_807af04f269d4601"

# Update the stuck task to failed state
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Updating stuck task {stuck_task_id} to failed state...")
cursor.execute("""
    UPDATE tasks 
    SET state = 'failed', 
        error_details = 'Worker interrupted - task stuck for 10+ hours',
        updated_at = datetime('now')
    WHERE task_id = ?
""", (stuck_task_id,))

affected = cursor.rowcount
conn.commit()
conn.close()

print(f"✓ Updated {affected} task(s)")

# Check if journal file still exists
journal_path = f"{db_path}-journal"
if os.path.exists(journal_path):
    print(f"\n⚠ Journal file still exists: {journal_path}")
    print("This is normal - SQLite will clean it up on next connection")
else:
    print("\n✓ No journal file")

print("\n✓ Database cleanup complete")
print(f"Task {stuck_task_id} is now marked as failed")
