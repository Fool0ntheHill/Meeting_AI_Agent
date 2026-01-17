"""
任务 Worker

从队列拉取任务并执行处理。
"""

import signal
import sys
import time
import logging
from typing import Optional
from datetime import datetime

from src.queue.manager import QueueManager
from src.services.pipeline import PipelineService
from src.database.session import session_scope
from src.database.repositories import TaskRepository
from src.core.models import TaskState

logger = logging.getLogger(__name__)


class TaskWorker:
    """
    任务 Worker
    
    从队列拉取任务并执行会议处理管线。
    实现优雅停机机制。
    """
    
    def __init__(
        self,
        queue_manager: QueueManager,
        pipeline_service: PipelineService,
        max_shutdown_wait: int = 300,
    ):
        """
        初始化 Worker
        
        Args:
            queue_manager: 队列管理器
            pipeline_service: 管线服务
            max_shutdown_wait: 最大停机等待时间(秒)
        """
        self.queue_manager = queue_manager
        self.pipeline_service = pipeline_service
        self.max_shutdown_wait = max_shutdown_wait
        
        self.running = False
        self.current_task_id: Optional[str] = None
        self.shutdown_requested = False
        
        # 注册信号处理
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """
        处理停机信号
        
        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        logger.info(f"Received shutdown signal: {signum}")
        self.shutdown_requested = True
        self.running = False
        
        if self.current_task_id:
            logger.info(f"Waiting for current task to complete: {self.current_task_id}")
        else:
            logger.info("No task in progress, shutting down immediately")
            sys.exit(0)
    
    def start(self):
        """
        启动 Worker 主循环
        """
        logger.info("Starting TaskWorker...")
        self.running = True
        
        while self.running:
            try:
                # 拉取任务
                message = self.queue_manager.pull(timeout=1)
                
                if message:
                    task_id = message["task_id"]
                    task_data = message["data"]
                    
                    self.current_task_id = task_id
                    logger.info(f"Processing task: {task_id}")
                    
                    try:
                        self._process_task(task_id, task_data)
                    except Exception as e:
                        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                        self._mark_task_failed(task_id, str(e))
                    finally:
                        self.current_task_id = None
                
                # 检查是否需要停机
                if self.shutdown_requested:
                    logger.info("Shutdown completed")
                    sys.exit(0)
            
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(1)  # 避免错误循环
        
        logger.info("TaskWorker stopped")
    
    def _process_task(self, task_id: str, task_data: dict):
        """
        处理单个任务
        
        Args:
            task_id: 任务 ID
            task_data: 任务数据
        """
        start_time = time.time()
        
        # 更新任务状态为 RUNNING
        self._update_task_state(task_id, TaskState.RUNNING)
        
        try:
            # 执行管线
            result = self.pipeline_service.process_meeting(
                task_id=task_id,
                audio_files=task_data["audio_files"],
                file_order=task_data.get("file_order"),
                meeting_type=task_data.get("meeting_type", "common"),
                enable_speaker_recognition=task_data.get("enable_speaker_recognition", True),
                enable_correction=task_data.get("enable_correction", True),
                prompt_instance=task_data.get("prompt_instance"),
                hotword_sets=task_data.get("hotword_sets"),
                asr_language=task_data.get("asr_language", "zh-CN+en-US"),
                output_language=task_data.get("output_language", "zh-CN"),
            )
            
            # 更新任务状态为 SUCCESS
            self._update_task_state(task_id, TaskState.SUCCESS)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Task {task_id} completed successfully in {elapsed_time:.2f}s")
        
        except Exception as e:
            # 更新任务状态为 FAILED
            self._update_task_state(task_id, TaskState.FAILED, error_message=str(e))
            raise
    
    def _update_task_state(
        self,
        task_id: str,
        state: TaskState,
        error_message: Optional[str] = None,
    ):
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            state: 新状态
            error_message: 错误信息(可选)
        """
        try:
            with session_scope() as session:
                task_repo = TaskRepository(session)
                task_repo.update_state(
                    task_id=task_id,
                    state=state,
                    error_message=error_message,
                )
            logger.info(f"Updated task {task_id} state to {state.value}")
        except Exception as e:
            logger.error(f"Failed to update task {task_id} state: {e}")
    
    def _mark_task_failed(self, task_id: str, error_message: str):
        """
        标记任务为失败
        
        Args:
            task_id: 任务 ID
            error_message: 错误信息
        """
        self._update_task_state(task_id, TaskState.FAILED, error_message)
    
    def stop(self):
        """
        停止 Worker
        """
        logger.info("Stopping TaskWorker...")
        self.running = False
