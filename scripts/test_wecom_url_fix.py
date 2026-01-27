"""测试企微通知 URL 格式修复"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.wecom_notification import get_wecom_service

def test_url_formats():
    """测试 URL 格式"""
    print("=" * 60)
    print("测试企微通知 URL 格式")
    print("=" * 60)
    print()
    
    # 获取企微服务
    wecom_service = get_wecom_service(
        api_url="http://gsmsg.gs.com:24905",
        frontend_base_url="http://localhost:5173"
    )
    
    task_id = "task_test_123"
    artifact_id = "artifact_test_456"
    
    print("预期 URL 格式：")
    print()
    print("1. 成功通知 - Workspace URL:")
    print(f"   ✅ 正确: http://localhost:5173/workspace/{task_id}")
    print(f"   ❌ 错误: http://localhost:5173/tasks/{task_id}/workspace?artifactId={artifact_id}")
    print()
    print("2. 失败通知 - Workbench URL:")
    print(f"   ✅ 正确: http://localhost:5173/tasks/{task_id}/workbench")
    print()
    
    print("=" * 60)
    print("发送测试通知验证 URL...")
    print("=" * 60)
    print()
    
    # 测试成功通知
    print("1. 测试成功通知...")
    success = wecom_service.send_artifact_success_notification(
        user_account="lorenzolin",
        task_id=task_id,
        task_name="URL 格式测试",
        meeting_date="2026-01-27",
        meeting_time="23:00",
        artifact_id=artifact_id,
        artifact_type="meeting_minutes",
        display_name="测试纪要"
    )
    
    if success:
        print("   ✅ 成功通知发送成功")
        print(f"   请检查企微消息中的链接是否为: http://localhost:5173/workspace/{task_id}")
    else:
        print("   ❌ 成功通知发送失败（可能是企微 API 问题）")
    
    print()
    
    # 测试失败通知
    print("2. 测试失败通知...")
    success = wecom_service.send_artifact_failure_notification(
        user_account="lorenzolin",
        task_id=task_id,
        task_name="URL 格式测试",
        meeting_date="2026-01-27",
        meeting_time="23:00",
        error_code="TEST_ERROR",
        error_message="这是一个测试错误"
    )
    
    if success:
        print("   ✅ 失败通知发送成功")
        print(f"   请检查企微消息中的链接是否为: http://localhost:5173/tasks/{task_id}/workbench")
    else:
        print("   ❌ 失败通知发送失败（可能是企微 API 问题）")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print()
    print("说明：")
    print("1. Workspace URL 格式已修正为 /workspace/{task_id}")
    print("2. Workbench URL 格式保持为 /tasks/{task_id}/workbench")
    print("3. 请在企微消息中点击链接验证是否能正确跳转")

if __name__ == "__main__":
    test_url_formats()
