"""
企业微信通知工具

用于发送会议纪要生成通知
"""

import requests
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WeComNotificationService:
    """企业微信通知服务"""
    
    def __init__(self, api_url: str = "http://gsmsg.gs.com:24905", frontend_base_url: str = "http://localhost:5173"):
        """
        初始化企微通知服务
        
        Args:
            api_url: 企微消息 API 地址
            frontend_base_url: 前端基础 URL
        """
        self.api_url = api_url
        self.send_markdown_url = f"{api_url}/msg/send_wecom_markdown"
        self.frontend_base_url = frontend_base_url
    
    def send_artifact_success_notification(
        self,
        user_account: str,
        task_id: str,
        task_name: Optional[str],
        meeting_date: Optional[str],
        meeting_time: Optional[str],
        artifact_id: str,
        artifact_type: str,
        display_name: Optional[str]
    ) -> bool:
        """
        发送 artifact 生成成功通知
        
        Args:
            user_account: 用户英文账号（企微账号）
            task_id: 任务 ID
            task_name: 任务名称
            meeting_date: 会议日期
            meeting_time: 会议时间
            artifact_id: Artifact ID
            artifact_type: Artifact 类型
            display_name: 自定义显示名称
            
        Returns:
            bool: 是否发送成功
        """
        try:
            # 构建 workspace 链接（正确格式）
            workspace_url = f"{self.frontend_base_url}/workspace/{task_id}"
            
            # 构建会议时间显示
            meeting_datetime = self._format_meeting_datetime(meeting_date, meeting_time)
            
            # 获取 artifact 显示名称
            artifact_display = display_name or self._get_default_artifact_name(artifact_type)
            
            # 构建标准 Markdown 消息
            message = f"""✅ **会议纪要生成成功**

**会议名称**: {task_name or '未命名会议'}
**会议时间**: {meeting_datetime}
**生成内容**: {artifact_display}

---

📄 [点击查看会议纪要]({workspace_url})"""
            
            # 发送通知
            response = requests.post(
                self.send_markdown_url,
                json={
                    "to": [user_account],
                    "msg": message
                },
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent success notification to {user_account} for task {task_id}")
                return True
            else:
                logger.error(f"Failed to send notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WeChat notification: {e}", exc_info=True)
            return False
    
    def send_artifact_failure_notification(
        self,
        user_account: str,
        task_id: str,
        task_name: Optional[str],
        meeting_date: Optional[str],
        meeting_time: Optional[str],
        error_code: Optional[str],
        error_message: Optional[str]
    ) -> bool:
        """
        发送 artifact 生成失败通知
        
        Args:
            user_account: 用户英文账号（企微账号）
            task_id: 任务 ID
            task_name: 任务名称
            meeting_date: 会议日期
            meeting_time: 会议时间
            error_code: 错误码
            error_message: 错误消息
            
        Returns:
            bool: 是否发送成功
        """
        try:
            # 构建 workbench 链接
            workbench_url = f"{self.frontend_base_url}/tasks/{task_id}/workbench"
            
            # 构建会议时间显示
            meeting_datetime = self._format_meeting_datetime(meeting_date, meeting_time)
            
            # 构建标准 Markdown 消息
            message = f"""❌ **会议纪要生成失败**

**会议名称**: {task_name or '未命名会议'}
**会议时间**: {meeting_datetime}

**错误信息**: {error_message or '未知错误'}
**错误码**: {error_code or 'UNKNOWN'}

---

🔧 [前往工作台查看详情]({workbench_url})"""
            
            # 发送通知
            response = requests.post(
                self.send_markdown_url,
                json={
                    "to": [user_account],
                    "msg": message
                },
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent failure notification to {user_account} for task {task_id}")
                return True
            else:
                logger.error(f"Failed to send notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WeChat notification: {e}", exc_info=True)
            return False
    
    def _format_meeting_datetime(self, meeting_date: Optional[str], meeting_time: Optional[str]) -> str:
        """
        格式化会议时间
        
        Args:
            meeting_date: 会议日期 (YYYY-MM-DD)
            meeting_time: 会议时间 (HH:MM)
            
        Returns:
            str: 格式化后的时间字符串
        """
        if meeting_date and meeting_time:
            return f"{meeting_date} {meeting_time}"
        elif meeting_date:
            return meeting_date
        elif meeting_time:
            return meeting_time
        else:
            return "未指定"
    
    def _get_default_artifact_name(self, artifact_type: str) -> str:
        """
        获取默认的 artifact 名称
        
        Args:
            artifact_type: Artifact 类型
            
        Returns:
            str: 默认名称
        """
        type_names = {
            "meeting_minutes": "会议纪要",
            "action_items": "行动项",
            "summary_notes": "摘要笔记"
        }
        return type_names.get(artifact_type, artifact_type)


# 全局实例
_wecom_service = None


def get_wecom_service(api_url: str = None, frontend_base_url: str = None) -> WeComNotificationService:
    """
    获取企微通知服务实例
    
    Args:
        api_url: 企微消息 API 地址（可选，用于初始化）
        frontend_base_url: 前端基础 URL（可选，用于初始化）
    """
    global _wecom_service
    if _wecom_service is None:
        _wecom_service = WeComNotificationService(
            api_url=api_url or "http://gsmsg.gs.com:24905",
            frontend_base_url=frontend_base_url or "http://localhost:5173"
        )
    return _wecom_service
