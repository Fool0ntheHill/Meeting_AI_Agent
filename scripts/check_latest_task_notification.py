"""检查最新任务的企微通知情况"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import TaskRepository, UserRepository
from src.database.models import Task

def check_latest_task():
    """检查最新任务的详细信息"""
    print("=" * 60)
    print("检查最新任务的企微通知情况")
    print("=" * 60)
    print()
    
    with session_scope() as session:
        task_repo = TaskRepository(session)
        user_repo = UserRepository(session)
        
        # 获取最新的成功任务
        latest_task = session.query(Task).filter(
            Task.state == "success"
        ).order_by(Task.completed_at.desc()).first()
        
        if not latest_task:
            print("❌ 没有找到成功的任务")
            return
        
        print(f"Task ID: {latest_task.task_id}")
        print(f"  状态: {latest_task.state}")
        print(f"  任务名称 (name): {latest_task.name or '未命名'}")
        print(f"  会议日期: {latest_task.meeting_date or '未指定'}")
        print(f"  会议时间: {latest_task.meeting_time or '未指定'}")
        print(f"  完成时间: {latest_task.completed_at}")
        print(f"  用户 ID: {latest_task.user_id}")
        print()
        
        # 获取用户信息
        user = user_repo.get_by_id(latest_task.user_id)
        if user:
            print(f"用户信息:")
            print(f"  用户名 (username): {user.username}")
            print(f"  租户 ID: {user.tenant_id}")
            print()
            
            print("企微通知检查:")
            print(f"  ✅ 用户账号存在: {user.username}")
            print(f"  ✅ 任务已完成")
            print()
            
            # 检查是否应该发送通知
            print("应该发送的通知内容:")
            print(f"  收件人: {user.username}")
            print(f"  任务 ID: {latest_task.task_id}")
            print(f"  任务名称: {latest_task.name or '未命名会议'}")
            print(f"  会议时间: {latest_task.meeting_date or '未指定'} {latest_task.meeting_time or ''}")
            print()
            
            print("⚠️ 如果没有收到通知，可能的原因：")
            print("  1. Worker 没有重启，还在使用旧代码")
            print("  2. 企微 API 调用失败（检查网络连接）")
            print("  3. 用户账号在企微系统中不存在")
            print("  4. 代码中的 try-except 捕获了错误但没有抛出")
            print()
            print("解决方案：")
            print("  1. 重启 worker: 停止当前 worker，然后运行 python worker.py")
            print("  2. 检查 worker 日志中是否有 'WeCom notification sent' 消息")
            print("  3. 检查是否有错误日志 'Failed to send WeCom notification'")
            
        else:
            print(f"❌ 用户不存在: {latest_task.user_id}")
            print("   这是通知无法发送的原因")

if __name__ == "__main__":
    check_latest_task()
