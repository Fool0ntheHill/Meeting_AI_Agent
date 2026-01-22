#!/usr/bin/env python3
"""检查任务的详细历史记录（从日志中）"""

import sys
from datetime import datetime
from src.database.session import session_scope
from src.database.repositories import TaskRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


def check_task_history(task_id: str):
    """检查任务历史"""
    print(f"\n任务 ID: {task_id}")
    print("=" * 60)
    
    with session_scope() as session:
        task_repo = TaskRepository(session)
        task = task_repo.get_by_id(task_id)
        
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print(f"状态: {task.state}")
        print(f"进度: {task.progress}%")
        print(f"创建时间: {task.created_at}")
        print(f"更新时间: {task.updated_at}")
        print(f"完成时间: {task.completed_at}")
        
        # 检查转写记录
        if task.transcripts:
            transcript = task.transcripts[0]
            print(f"\n转写记录:")
            print(f"  时长: {transcript.duration}秒")
            print(f"  语言: {transcript.language}")
            print(f"  提供商: {transcript.provider}")
        
        # 检查 artifact
        if task.artifacts:
            print(f"\nArtifact 记录:")
            for artifact in task.artifacts:
                print(f"  ID: {artifact.artifact_id}")
                print(f"  类型: {artifact.artifact_type}")
                print(f"  版本: {artifact.version}")
                print(f"  创建时间: {artifact.created_at}")
        
        print(f"\n提示: 查看 worker 日志以了解详细的状态变化历史")
        print(f"建议: 在 worker 运行时使用 scripts/monitor_existing_task.py 实时监控")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/check_task_history_detailed.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    check_task_history(task_id)
