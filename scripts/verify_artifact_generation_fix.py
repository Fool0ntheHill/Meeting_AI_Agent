"""验证 artifact 生成修复"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import TaskRepository, ArtifactRepository

def check_recent_tasks():
    """检查最近的任务状态"""
    with session_scope() as session:
        task_repo = TaskRepository(session)
        artifact_repo = ArtifactRepository(session)
        
        # 检查最近失败的任务
        print("=== 检查最近的任务 ===\n")
        
        # 查询最近的任务（按创建时间倒序）
        from src.database.models import Task
        recent_tasks = session.query(Task).order_by(Task.created_at.desc()).limit(5).all()
        
        for task in recent_tasks:
            print(f"Task ID: {task.task_id}")
            print(f"  State: {task.state}")
            print(f"  Progress: {task.progress}%")
            print(f"  Created: {task.created_at}")
            
            if task.error_details:
                print(f"  Error: {task.error_details[:200]}")
            
            # 检查 artifacts
            artifacts = artifact_repo.get_by_task_id(task.task_id)
            if artifacts:
                print(f"  Artifacts: {len(artifacts)}")
                for artifact in artifacts:
                    print(f"    - {artifact.artifact_id}: {artifact.artifact_type} v{artifact.version} ({artifact.state})")
                    if artifact.display_name:
                        print(f"      Display Name: {artifact.display_name}")
            else:
                print(f"  Artifacts: None")
            
            print()

if __name__ == "__main__":
    check_recent_tasks()
