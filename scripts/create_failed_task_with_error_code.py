# -*- coding: utf-8 -*-
"""
创建一个带有错误码的失败任务

用于测试前端是否能正确接收和显示错误码
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uuid
from datetime import datetime
from src.database.session import session_scope
from src.database.repositories import TaskRepository
from src.core.error_codes import ErrorCode, create_error
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_failed_task_with_error_code():
    """创建一个带有错误码的失败任务"""
    
    with session_scope() as session:
        task_repo = TaskRepository(session)
        
        # 生成任务 ID
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        
        # 创建任务（使用与 task_c11b7c3f75e54b82 相同的 user_id）
        task = task_repo.create(
            task_id=task_id,
            user_id="user_test_user",
            tenant_id="tenant_test_user",
            meeting_type="weekly_sync",
            audio_files=["uploads/user_test_user/test_audio.ogg"],
            file_order=[0],
            original_filenames=["test_meeting.ogg"],
            audio_duration=479.1,
            asr_language="zh-CN+en-US",
            output_language="zh-CN",
        )
        
        logger.info(f"Task created: {task_id}")
        
        # 模拟 LLM SSL 错误（使用真实的错误消息）
        error = create_error(
            error_code=ErrorCode.NETWORK_TIMEOUT,
            error_message="网络连接异常（SSL），请稍后重试",
            error_details="Failed to call Gemini API after 3 attempts: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1000)",
        )
        
        # 更新任务为失败状态，并设置错误码
        task_repo.update_error(
            task_id=task_id,
            error_code=error.error_code.value,
            error_message=error.error_message,
            error_details=error.error_details,
            retryable=error.retryable,
        )
        
        # 更新任务状态为失败
        task_repo.update_state(
            task_id=task_id,
            state="failed",
            progress=70.0,
        )
        
        logger.info(f"Task marked as failed with error code: {error.error_code.value}")
        
        print("\n" + "=" * 80)
        print("测试任务已创建")
        print("=" * 80)
        print(f"\n任务 ID: {task_id}")
        print(f"状态: failed")
        print(f"进度: 70%")
        print(f"错误码: {error.error_code.value}")
        print(f"错误消息: {error.error_message}")
        print(f"可重试: {error.retryable}")
        print(f"错误详情: {error.error_details}")
        
        print("\n" + "=" * 80)
        print("前端测试步骤")
        print("=" * 80)
        print(f"\n1. 在前端查看任务状态：")
        print(f"   GET /api/v1/tasks/{task_id}/status")
        print(f"\n2. 预期响应：")
        print(f"""   {{
     "task_id": "{task_id}",
     "state": "failed",
     "progress": 70.0,
     "error_code": "NETWORK_TIMEOUT",
     "error_message": "网络连接异常（SSL），请稍后重试",
     "error_details": "LLM: SSL/TLS error: SSL: UNEXPECTED_EOF_WHILE_READING",
     "retryable": true,
     "updated_at": "..."
   }}""")
        
        print(f"\n3. 前端应该显示：")
        print(f"   - 错误类型: 网络/上游服务异常")
        print(f"   - 错误消息: 网络连接异常（SSL），请稍后重试")
        print(f"   - 重试按钮: 显示（因为 retryable=true）")
        
        print("\n" + "=" * 80)
        print("使用 curl 测试")
        print("=" * 80)
        print(f"\ncurl -X GET http://localhost:8000/api/v1/tasks/{task_id}/status \\")
        print(f'  -H "Authorization: Bearer YOUR_TOKEN"')
        
        return task_id


if __name__ == "__main__":
    task_id = create_failed_task_with_error_code()
    print(f"\n✓ 任务创建成功: {task_id}\n")
