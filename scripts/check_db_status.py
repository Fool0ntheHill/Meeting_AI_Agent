#!/usr/bin/env python3
"""Check database status and lock state."""

import sqlite3
import os

db_path = "meeting_agent.db"

if not os.path.exists(db_path):
    print(f"Database file not found: {db_path}")
    exit(1)

try:
    # Try to connect and query
    conn = sqlite3.connect(db_path, timeout=5.0)
    cursor = conn.cursor()
    
    # Check if we can read
    cursor.execute("SELECT COUNT(*) FROM tasks")
    task_count = cursor.fetchone()[0]
    print(f"✓ Database is accessible")
    print(f"✓ Total tasks: {task_count}")
    
    # Check recent tasks
    cursor.execute("""
        SELECT task_id, state, created_at 
        FROM tasks 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    print("\nRecent tasks:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} - {row[2]}")
    
    # Check for journal file (indicates active write)
    journal_path = f"{db_path}-journal"
    if os.path.exists(journal_path):
        journal_size = os.path.getsize(journal_path)
        print(f"\n⚠ Journal file exists: {journal_path} ({journal_size} bytes)")
        if journal_size > 0:
            print("  This may indicate an incomplete transaction")
    else:
        print("\n✓ No journal file (no active transactions)")
    
    # Try a write operation
    cursor.execute("BEGIN IMMEDIATE")
    print("✓ Can acquire write lock")
    conn.rollback()
    
    conn.close()
    print("\n✓ Database is NOT locked and fully operational")
    
except sqlite3.OperationalError as e:
    print(f"✗ Database error: {e}")
    if "locked" in str(e).lower():
        print("\n⚠ Database is LOCKED")
        print("Possible causes:")
        print("  - Another process has an open connection")
        print("  - Worker or backend server is running")
        print("  - Incomplete transaction from crashed process")
    exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    exit(1)
