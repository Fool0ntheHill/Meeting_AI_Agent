"""
测试 Pipeline 企微通知（使用文件名作为任务名称）

验证当 task.name 为 None 时，使用原始文件名作为会议名称
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import TaskRepository, UserRepository
from src.utils.wecom_notification import get_wecom_service


def test_notification_with_filename():
    """测试使用文件名的通知"""
    
    print("=" * 60)
    print("测试 Pipeline 企微通知（使用文件名）")
    print("=" * 60)
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        user_repo = UserRepository(db)
        
        # 查找最近的一个任务（task.name 为 None）
        # 使用 SQL 查询获取任务列表
        from sqlalchemy import desc
        from src.database.models import Task
        
        tasks = db.query(Task).filter(
            Task.user_id == "user_gsuc_1231"
        ).order_by(desc(Task.created_at)).limit(10).all()
        
        if not tasks:
            print("❌ 没有找到任务")
            return
        
        # 找一个 name 为 None 的任务
        test_task = None
        for task in tasks:
            if task.name is None:
                test_task = task
                break
        
        if not test_task:
            print("❌ 没有找到 name 为 None 的任务")
            print("使用第一个任务进行测试...")
            test_task = tasks[0]
        
        print(f"\n📋 测试任务信息:")
        print(f"  Task ID: {test_task.task_id}")
        print(f"  Task Name: {test_task.name}")
        print(f"  Original Filenames: {test_task.get_original_filenames_list()}")
        print(f"  Meeting Date: {test_task.meeting_date}")
        print(f"  Meeting Time: {test_task.meeting_time}")
        print(f"  State: {test_task.state}")
        
        # 获取用户信息
        user = user_repo.get_by_id(test_task.user_id)
        if not user:
            print(f"❌ 用户不存在: {test_task.user_id}")
            return
        
        print(f"\n👤 用户信息:")
        print(f"  User ID: {user.user_id}")
        print(f"  Username: {user.username}")
        
        # 模拟 Pipeline 中的逻辑
        task_name = test_task.name
        original_filenames = test_task.get_original_filenames_list()
        
        # 如果 task.name 为 None，使用原始文件名（去掉扩展名）
        if not task_name and original_filenames:
            import os
            task_name = os.path.splitext(original_filenames[0])[0]
        
        print(f"\n📝 最终使用的任务名称: {task_name}")
        
        # 发送测试通知
        print(f"\n📤 发送企微通知...")
        wecom_service = get_wecom_service()
        
        if test_task.state == "success":
            success = wecom_service.send_artifact_success_notification(
                user_account=user.username,
                task_id=test_task.task_id,
                task_name=task_name,
                meeting_date=test_task.meeting_date,
                meeting_time=test_task.meeting_time,
                artifact_id="artifact_test",
                artifact_type="meeting_minutes",
                display_name="纪要",
            )
        else:
            success = wecom_service.send_artifact_failure_notification(
                user_account=user.username,
                task_id=test_task.task_id,
                task_name=task_name,
                meeting_date=test_task.meeting_date,
                meeting_time=test_task.meeting_time,
                error_code=test_task.error_code or "TEST_ERROR",
                error_message=test_task.error_message or "测试错误消息",
            )
        
        if success:
            print(f"✅ 通知发送成功")
        else:
            print(f"❌ 通知发送失败")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    test_notification_with_filename()
