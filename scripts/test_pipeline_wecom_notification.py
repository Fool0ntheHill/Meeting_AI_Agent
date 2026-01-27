"""测试 Pipeline 企微通知功能"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from src.database.session import session_scope
from src.database.repositories import TaskRepository, UserRepository

def check_recent_tasks():
    """检查最近的任务，看看是否有企微通知相关的日志"""
    print("=== 检查最近任务的企微通知 ===\n")
    
    with session_scope() as session:
        task_repo = TaskRepository(session)
        user_repo = UserRepository(session)
        
        # 查询最近的任务
        from src.database.models import Task
        recent_tasks = session.query(Task).order_by(Task.created_at.desc()).limit(5).all()
        
        for task in recent_tasks:
            print(f"Task ID: {task.task_id}")
            print(f"  State: {task.state}")
            print(f"  User ID: {task.user_id}")
            
            # 获取用户账号
            user = user_repo.get_by_id(task.user_id)
            if user:
                print(f"  User Account: {user.username}")
            else:
                print(f"  User Account: NOT FOUND")
            
            print(f"  Created: {task.created_at}")
            
            if task.state == "success":
                print(f"  ✅ 任务成功 - 应该发送成功通知")
            elif task.state == "failed":
                print(f"  ❌ 任务失败 - 应该发送失败通知")
                if task.error_code:
                    print(f"  Error Code: {task.error_code}")
                if task.error_message:
                    print(f"  Error Message: {task.error_message}")
            
            print()

def test_notification_service():
    """测试企微通知服务是否可用"""
    print("=== 测试企微通知服务 ===\n")
    
    try:
        from src.utils.wecom_notification import get_wecom_service
        
        wecom_service = get_wecom_service()
        print(f"✅ 企微通知服务初始化成功")
        print(f"  API URL: {wecom_service.api_url}")
        print(f"  Frontend URL: {wecom_service.frontend_base_url}")
        print()
        
        # 测试发送通知（使用测试账号）
        print("测试发送通知...")
        success = wecom_service.send_artifact_success_notification(
            user_account="lorenzolin",  # 使用你的账号
            task_id="test_task_123",
            artifact_id="test_artifact_123",
            artifact_type="meeting_minutes",
            display_name="测试纪要",
        )
        
        if success:
            print("✅ 测试通知发送成功")
        else:
            print("❌ 测试通知发送失败")
        
    except Exception as e:
        print(f"❌ 企微通知服务初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("Pipeline 企微通知功能测试")
    print("=" * 60)
    print()
    
    # 1. 检查最近任务
    check_recent_tasks()
    
    # 2. 测试通知服务
    test_notification_service()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n提示：")
    print("1. 如果看到 '用户账号 NOT FOUND'，说明用户表中没有该用户记录")
    print("2. 新增任务时，Pipeline 会在任务成功/失败时自动发送企微通知")
    print("3. 检查 worker 日志中是否有 'WeCom notification sent' 的消息")
