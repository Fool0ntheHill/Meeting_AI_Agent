#!/usr/bin/env python3
"""Check the running task status."""

import sqlite3
from datetime import datetime

conn = sqlite3.connect("meeting_agent.db", timeout=1.0)
cursor = conn.cursor()

# Find running tasks
cursor.execute("""
    SELECT task_id, state, created_at, updated_at, user_id, tenant_id
    FROM tasks 
    WHERE state = 'running'
    ORDER BY created_at DESC
""")

running_tasks = cursor.fetchall()
print(f"Found {len(running_tasks)} running task(s):\n")

for task in running_tasks:
    task_id, state, created_at, updated_at, user_id, tenant_id = task
    print(f"Task ID: {task_id}")
    print(f"State: {state}")
    print(f"User: {user_id}")
    print(f"Tenant: {tenant_id}")
    print(f"Created: {created_at}")
    print(f"Updated: {updated_at}")
    
    # Calculate how long it's been running
    created = datetime.fromisoformat(created_at)
    now = datetime.now()
    duration = now - created
    print(f"Running for: {duration}")
    
    # Check if there's a transcript
    cursor.execute("SELECT COUNT(*) FROM transcripts WHERE task_id = ?", (task_id,))
    transcript_count = cursor.fetchone()[0]
    print(f"Transcripts: {transcript_count}")
    
    # Check if there's an artifact
    cursor.execute("SELECT COUNT(*) FROM artifacts WHERE task_id = ?", (task_id,))
    artifact_count = cursor.fetchone()[0]
    print(f"Artifacts: {artifact_count}")
    print()

conn.close()
