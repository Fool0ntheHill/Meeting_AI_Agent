"""直接测试企微通知功能（不依赖 worker）"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.wecom_notification import get_wecom_service

def test_notification():
    """直接发送测试通知"""
    print("=" * 60)
    print("直接测试企微通知")
    print("=" * 60)
    print()
    
    # 获取企微服务
    wecom_service = get_wecom_service(
        api_url="http://gsmsg.gs.com:24905",
        frontend_base_url="http://localhost:3000"
    )
    
    print("发送测试通知...")
    print()
    
    # 发送成功通知
    success = wecom_service.send_artifact_success_notification(
        user_account="lorenzolin",
        task_id="task_20b2e0f35592446c",
        task_name="测试任务 - Worker 重启验证",
        meeting_date="2025-12-29",
        meeting_time=None,
        artifact_id="test_artifact_123",
        artifact_type="meeting_minutes",
        display_name="纪要"
    )
    
    if success:
        print("✅ 通知发送成功！")
        print()
        print("如果你收到了这条通知，说明：")
        print("  1. 企微通知服务正常工作")
        print("  2. 你的账号 'lorenzolin' 在企微系统中存在")
        print("  3. 网络连接正常")
        print()
        print("如果 worker 重启后仍然没有通知，请检查：")
        print("  1. Worker 日志中是否有错误")
        print("  2. Pipeline 代码是否正确执行到通知部分")
    else:
        print("❌ 通知发送失败！")
        print()
        print("可能的原因：")
        print("  1. 企微 API 服务不可用")
        print("  2. 网络连接问题")
        print("  3. 账号 'lorenzolin' 在企微系统中不存在")
        print()
        print("请检查企微 API 服务状态")

if __name__ == "__main__":
    test_notification()
