#!/usr/bin/env python3
"""
检查任务进度

快速查看任务的当前进度和预估时间
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import session_scope
from src.database.repositories import TaskRepository


def check_task_progress(task_id: str):
    """
    检查任务进度
    
    Args:
        task_id: 任务 ID
    """
    with session_scope() as db:
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print(f"\n任务 ID: {task.task_id}")
        print("=" * 60)
        print(f"状态: {task.state}")
        print(f"进度: {task.progress}%")
        
        if task.estimated_time:
            est_min = task.estimated_time // 60
            est_sec = task.estimated_time % 60
            print(f"预估剩余时间: {est_min}分{est_sec}秒")
        else:
            print(f"预估剩余时间: 未知")
        
        print(f"创建时间: {task.created_at}")
        print(f"更新时间: {task.updated_at}")
        
        if task.error_details:
            print(f"\n错误信息: {task.error_details}")
        
        # 检查转写记录
        if task.transcripts:
            transcript = task.transcripts[0]
            print(f"\n音频时长: {transcript.duration}秒 ({transcript.duration/60:.1f}分钟)")
        
        print()


def list_recent_tasks(limit: int = 5):
    """列出最近的任务"""
    with session_scope() as db:
        task_repo = TaskRepository(db)
        
        # 获取所有任务（简化版，实际应该按时间排序）
        from src.database.models import Task
        from sqlalchemy import desc
        
        tasks = (
            db.query(Task)
            .order_by(desc(Task.created_at))
            .limit(limit)
            .all()
        )
        
        if not tasks:
            print("没有找到任务")
            return
        
        print(f"\n最近的 {len(tasks)} 个任务:")
        print("=" * 80)
        
        for task in tasks:
            status_icon = {
                "pending": "⏳",
                "queued": "⏳",
                "running": "🔄",
                "transcribing": "🎤",
                "identifying": "👥",
                "correcting": "✏️",
                "summarizing": "📝",
                "success": "✅",
                "failed": "❌",
            }.get(task.state, "❓")
            
            print(f"{status_icon} {task.task_id}")
            print(f"   状态: {task.state} | 进度: {task.progress}% | 创建: {task.created_at}")
            
            if task.estimated_time:
                est_min = task.estimated_time // 60
                est_sec = task.estimated_time % 60
                print(f"   预估剩余: {est_min}分{est_sec}秒")
            
            print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        check_task_progress(task_id)
    else:
        list_recent_tasks()
        print("\n用法: python scripts/check_task_progress.py <task_id>")
