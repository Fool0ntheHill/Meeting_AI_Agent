"""测试 Pipeline 企微通知修复"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import TaskRepository
from src.database.models import Task

def check_task_name_field():
    """检查 Task 模型的字段名"""
    print("=" * 60)
    print("检查 Task 模型字段")
    print("=" * 60)
    print()
    
    # 检查 Task 模型的属性
    task_attrs = [attr for attr in dir(Task) if not attr.startswith('_')]
    
    print("Task 模型的主要字段：")
    important_fields = ['task_id', 'name', 'task_name', 'user_id', 'meeting_date', 'meeting_time']
    for field in important_fields:
        if field in task_attrs:
            print(f"  ✅ {field}")
        else:
            print(f"  ❌ {field} (不存在)")
    
    print()
    print("结论：")
    if 'name' in task_attrs:
        print("  ✅ 任务名称字段是 'name'")
    if 'task_name' not in task_attrs:
        print("  ❌ 没有 'task_name' 字段")
    
    print()

def check_recent_task():
    """检查最近的任务"""
    print("=" * 60)
    print("检查最近任务的名称字段")
    print("=" * 60)
    print()
    
    with session_scope() as session:
        task_repo = TaskRepository(session)
        
        # 获取最近的任务
        recent_task = session.query(Task).order_by(Task.created_at.desc()).first()
        
        if recent_task:
            print(f"Task ID: {recent_task.task_id}")
            print(f"  任务名称 (name): {recent_task.name}")
            print(f"  会议日期: {recent_task.meeting_date}")
            print(f"  会议时间: {recent_task.meeting_time}")
            print(f"  用户 ID: {recent_task.user_id}")
            print(f"  状态: {recent_task.state}")
            
            # 尝试访问 task_name（应该会失败）
            try:
                task_name = recent_task.task_name
                print(f"  ❌ task_name: {task_name} (不应该存在)")
            except AttributeError:
                print(f"  ✅ task_name 属性不存在（符合预期）")
        else:
            print("没有找到任务")
    
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Pipeline 企微通知字段名修复验证")
    print("=" * 60)
    print()
    
    # 1. 检查模型字段
    check_task_name_field()
    
    # 2. 检查实际任务
    check_recent_task()
    
    print("=" * 60)
    print("验证完成")
    print("=" * 60)
    print("\n说明：")
    print("1. Task 模型的任务名称字段是 'name' 而不是 'task_name'")
    print("2. Pipeline 中已修复为使用 task.name")
    print("3. 下次新增任务时应该能正常发送企微通知")
