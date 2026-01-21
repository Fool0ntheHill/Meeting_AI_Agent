"""
检查数据库中的 artifacts 记录

用于验证 artifacts 是否被正确保存到数据库
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import session_scope
from src.database.repositories import ArtifactRepository, TaskRepository


def check_artifacts():
    """检查数据库中的 artifacts"""
    with session_scope() as session:
        artifact_repo = ArtifactRepository(session)
        task_repo = TaskRepository(session)
        
        # 获取最近的任务
        tasks = task_repo.get_by_user(
            user_id="user_test_user",
            limit=5,
        )
        
        print(f"\n{'='*60}")
        print(f"检查最近 {len(tasks)} 个任务的 artifacts")
        print(f"{'='*60}\n")
        
        for task in tasks:
            print(f"任务: {task.task_id}")
            print(f"  状态: {task.state}")
            print(f"  创建时间: {task.created_at}")
            
            # 获取该任务的所有 artifacts
            artifacts = artifact_repo.get_by_task_id(task.task_id)
            
            if artifacts:
                print(f"  Artifacts: {len(artifacts)} 个")
                for artifact in artifacts:
                    print(f"    - {artifact.artifact_id}")
                    print(f"      类型: {artifact.artifact_type}")
                    print(f"      版本: {artifact.version}")
                    print(f"      创建时间: {artifact.created_at}")
                    print(f"      创建者: {artifact.created_by}")
                    
                    # 显示内容的前100个字符
                    content_dict = artifact.get_content_dict()
                    if isinstance(content_dict, dict):
                        content_str = str(content_dict)
                        print(f"      内容预览: {content_str[:100]}...")
                    else:
                        print(f"      内容: {content_dict}")
            else:
                print(f"  Artifacts: 无")
            
            print()


if __name__ == "__main__":
    check_artifacts()
