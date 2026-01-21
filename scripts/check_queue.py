"""
Check Redis queue status and optionally clear it
"""

import redis
import json
import sys

def check_queue():
    """Check queue status"""
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # Check connection
    try:
        r.ping()
        print("✓ Connected to Redis")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")
        return
    
    # Check queue length
    queue_name = "meeting_agent:tasks"
    queue_length = r.llen(queue_name)
    print(f"\nQueue: {queue_name}")
    print(f"Tasks in queue: {queue_length}")
    
    if queue_length > 0:
        print("\nFirst 5 tasks:")
        for i in range(min(5, queue_length)):
            task_json = r.lindex(queue_name, i)
            if task_json:
                try:
                    task = json.loads(task_json)
                    print(f"\n  Task {i+1}:")
                    print(f"    task_id: {task.get('task_id', 'N/A')}")
                    print(f"    user_id: {task.get('data', {}).get('user_id', 'N/A')}")
                    print(f"    audio_files: {len(task.get('data', {}).get('audio_files', []))} files")
                except Exception as e:
                    print(f"    Error parsing task: {e}")
        
        # Ask if user wants to clear
        if len(sys.argv) > 1 and sys.argv[1] == "--clear":
            print(f"\nClearing {queue_length} tasks from queue...")
            r.delete(queue_name)
            print("✓ Queue cleared")
        else:
            print("\nTo clear the queue, run: python scripts/check_queue.py --clear")

if __name__ == "__main__":
    check_queue()
