"""检查 artifact 详细信息"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import get_session
from src.database.repositories import ArtifactRepository

def check_artifacts(task_id: str):
    """检查任务的所有 artifacts"""
    session = get_session()
    repo = ArtifactRepository(session)
    
    artifacts = repo.get_by_task_id(task_id)
    
    print(f"\n任务 {task_id} 的所有 Artifacts:")
    print("=" * 80)
    
    for artifact in artifacts:
        print(f"\nArtifact ID: {artifact.artifact_id}")
        print(f"  类型: {artifact.artifact_type}")
        print(f"  版本: {artifact.version}")
        print(f"  Display Name: {artifact.display_name}")
        print(f"  状态: {artifact.state}")
        print(f"  创建时间: {artifact.created_at}")
        print(f"  创建者: {artifact.created_by}")
        
        # 检查 prompt_instance
        if artifact.prompt_instance:
            if isinstance(artifact.prompt_instance, dict):
                template_id = artifact.prompt_instance.get("template_id", "N/A")
            else:
                template_id = "N/A (not dict)"
            print(f"  Template ID: {template_id}")
    
    session.close()

if __name__ == "__main__":
    task_id = "task_dadac03a8f3048ef"
    check_artifacts(task_id)
