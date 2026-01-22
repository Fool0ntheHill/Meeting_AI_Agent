#!/usr/bin/env python3
"""
诊断进度更新问题

检查为什么进度一直是 0%
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import session_scope
from src.database.repositories import TaskRepository
from src.database.models import Task
from sqlalchemy import desc


def diagnose_progress_issue():
    """诊断进度更新问题"""
    
    print("\n" + "=" * 80)
    print("诊断进度更新问题")
    print("=" * 80)
    
    with session_scope() as db:
        # 1. 检查最近的任务
        tasks = (
            db.query(Task)
            .order_by(desc(Task.created_at))
            .limit(5)
            .all()
        )
        
        if not tasks:
            print("\n❌ 没有找到任务")
            return
        
        print(f"\n找到 {len(tasks)} 个最近的任务\n")
        
        for i, task in enumerate(tasks, 1):
            print(f"{i}. 任务 {task.task_id}")
            print(f"   状态: {task.state}")
            print(f"   进度: {task.progress}%")
            print(f"   预估时间: {task.estimated_time}秒" if task.estimated_time else "   预估时间: None")
            print(f"   创建时间: {task.created_at}")
            print(f"   更新时间: {task.updated_at}")
            
            # 检查是否有转写记录
            if task.transcripts:
                transcript = task.transcripts[0]
                print(f"   ✓ 有转写记录，时长: {transcript.duration}秒")
            else:
                print(f"   ✗ 没有转写记录")
            
            # 检查是否有 artifact
            if task.artifacts:
                print(f"   ✓ 有 {len(task.artifacts)} 个 artifact")
            else:
                print(f"   ✗ 没有 artifact")
            
            print()
        
        # 2. 检查是否有进度更新
        print("\n" + "=" * 80)
        print("进度更新分析")
        print("=" * 80)
        
        has_progress = any(task.progress > 0 for task in tasks)
        has_estimated_time = any(task.estimated_time is not None for task in tasks)
        
        if not has_progress:
            print("\n❌ 问题：所有任务的进度都是 0%")
            print("\n可能的原因：")
            print("1. Worker 没有重启，还在使用旧代码")
            print("2. Pipeline 的 task_repo 没有正确初始化")
            print("3. _update_task_status 方法没有被调用")
            print("\n解决方案：")
            print("1. 重启 worker: python worker.py")
            print("2. 检查 worker 日志，看是否有进度更新的日志")
            print("3. 运行: python scripts/check_task_progress.py <task_id>")
        else:
            print("\n✅ 有任务的进度 > 0%，进度更新正常")
        
        if not has_estimated_time:
            print("\n⚠️  所有任务的 estimated_time 都是 None")
            print("\n可能的原因：")
            print("1. 转写还没完成，还不知道音频时长")
            print("2. 计算逻辑有问题")
        else:
            print("\n✅ 有任务有 estimated_time，预估时间计算正常")
        
        # 3. 检查 worker 是否在运行
        print("\n" + "=" * 80)
        print("Worker 状态检查")
        print("=" * 80)
        
        running_tasks = [task for task in tasks if task.state in ["running", "transcribing", "identifying", "correcting", "summarizing"]]
        
        if running_tasks:
            print(f"\n✅ 有 {len(running_tasks)} 个任务正在处理中")
            for task in running_tasks:
                print(f"   - {task.task_id}: {task.state} ({task.progress}%)")
        else:
            print("\n⚠️  没有任务正在处理中")
            print("   可能 worker 没有运行或队列为空")
        
        # 4. 给出建议
        print("\n" + "=" * 80)
        print("建议")
        print("=" * 80)
        print("\n1. 如果进度一直是 0%，请重启 worker:")
        print("   python worker.py")
        print("\n2. 创建一个新任务测试:")
        print("   python scripts/create_test_task.py")
        print("\n3. 实时监控任务进度:")
        print("   python scripts/test_progress_tracking.py <task_id>")
        print("\n4. 检查 worker 日志，查找类似这样的日志:")
        print("   'Task xxx: Status updated - state=transcribing, progress=40.0%, estimated_time=90s'")
        print()


if __name__ == "__main__":
    diagnose_progress_issue()
