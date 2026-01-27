"""测试企微通知的 Markdown 格式"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.wecom_notification import get_wecom_service

def test_success_notification():
    """测试成功通知"""
    print("=" * 60)
    print("测试成功通知（标准 Markdown 格式）")
    print("=" * 60)
    print()
    
    wecom_service = get_wecom_service(
        api_url="http://gsmsg.gs.com:24905",
        frontend_base_url="http://localhost:3000"
    )
    
    success = wecom_service.send_artifact_success_notification(
        user_account="lorenzolin",
        task_id="test_task_markdown_123",
        task_name="测试会议 - Markdown 格式",
        meeting_date="2026-01-27",
        meeting_time="22:30",
        artifact_id="test_artifact_md_123",
        artifact_type="meeting_minutes",
        display_name="测试纪要"
    )
    
    if success:
        print("✅ 成功通知发送成功")
        print("\n预期格式：")
        print("---")
        print("✅ **会议纪要生成成功**")
        print()
        print("**会议名称**: 测试会议 - Markdown 格式")
        print("**会议时间**: 2026-01-27 22:30")
        print("**生成内容**: 测试纪要")
        print()
        print("---")
        print()
        print("📄 [点击查看会议纪要](http://localhost:3000/tasks/test_task_markdown_123/workspace?artifactId=test_artifact_md_123)")
        print("---")
    else:
        print("❌ 成功通知发送失败")
    
    print()

def test_failure_notification():
    """测试失败通知"""
    print("=" * 60)
    print("测试失败通知（标准 Markdown 格式）")
    print("=" * 60)
    print()
    
    wecom_service = get_wecom_service()
    
    success = wecom_service.send_artifact_failure_notification(
        user_account="lorenzolin",
        task_id="test_task_fail_md_123",
        task_name="测试会议 - 失败场景",
        meeting_date="2026-01-27",
        meeting_time="22:30",
        error_code="LLM_TIMEOUT",
        error_message="LLM 生成超时，请稍后重试"
    )
    
    if success:
        print("✅ 失败通知发送成功")
        print("\n预期格式：")
        print("---")
        print("❌ **会议纪要生成失败**")
        print()
        print("**会议名称**: 测试会议 - 失败场景")
        print("**会议时间**: 2026-01-27 22:30")
        print()
        print("**错误信息**: LLM 生成超时，请稍后重试")
        print("**错误码**: LLM_TIMEOUT")
        print()
        print("---")
        print()
        print("🔧 [前往工作台查看详情](http://localhost:3000/tasks/test_task_fail_md_123/workbench)")
        print("---")
    else:
        print("❌ 失败通知发送失败")
    
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("企微通知 Markdown 格式测试")
    print("=" * 60)
    print()
    
    # 测试成功通知
    test_success_notification()
    
    # 测试失败通知
    test_failure_notification()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n说明：")
    print("1. 新格式使用标准 Markdown 语法")
    print("2. 使用 **粗体** 代替 <b> 标签")
    print("3. 使用换行代替 <br> 标签")
    print("4. 使用 --- 分隔线代替 ━━━━")
    print("5. 使用 [文本](链接) 代替 <a href> 标签")
    print("\n请检查企微消息，确认格式是否正确显示")
