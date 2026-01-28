"""
任务 Worker

从队列拉取任务并执行处理。
"""

import signal
import sys
import time
import logging
import asyncio
import os
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
        
        # Redis 客户端（用于检查取消状态）
        self.redis_client = None
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
            )
            self.redis_client.ping()
            logger.info("Redis client initialized for cancellation checks")
        except Exception as e:
            logger.warning(f"Redis client not available: {e}")
        
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
                        # Run async _process_task in event loop
                        asyncio.run(self._process_task(task_id, task_data))
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
    
    async def _process_task(self, task_id: str, task_data: dict):
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
            # 为这个任务创建 transcript 和 artifact repositories
            from src.database.session import session_scope
            from src.database.repositories import (
                TaskRepository,
                TranscriptRepository, 
                ArtifactRepository, 
                SpeakerMappingRepository, 
                SpeakerRepository,
                PromptTemplateRepository
            )
            
            with session_scope() as session:
                task_repo = TaskRepository(session)
                transcript_repo = TranscriptRepository(session)
                artifact_repo = ArtifactRepository(session)
                speaker_mapping_repo = SpeakerMappingRepository(session)
                speaker_repo = SpeakerRepository(session)
                template_repo = PromptTemplateRepository(session)
                
                # 临时设置到 pipeline
                self.pipeline_service.tasks = task_repo  # 添加这一行
                self.pipeline_service.transcripts = transcript_repo
                self.pipeline_service.artifact_generation.artifacts = artifact_repo
                self.pipeline_service.artifact_generation.templates = template_repo
                self.pipeline_service.speaker_mappings = speaker_mapping_repo
                self.pipeline_service.speakers = speaker_repo
                
                # 执行管线
                result = await self.pipeline_service.process_meeting(
                    task_id=task_id,
                    user_id=task_data["user_id"],
                    audio_files=task_data["audio_files"],
                    file_order=task_data.get("file_order", []),
                    prompt_instance=task_data.get("prompt_instance"),  # This is required by pipeline
                    tenant_id=task_data.get("tenant_id", "default"),
                    asr_language=task_data.get("asr_language", "zh-CN+en-US"),
                    output_language=task_data.get("output_language", "zh-CN"),
                    skip_speaker_recognition=not task_data.get("enable_speaker_recognition", True),
                    hotword_set_id=task_data.get("hotword_set_id"),
                    cancellation_check=self._is_task_cancelled,  # 传递取消检查回调
                )
                # 显式提交 session 以确保转写记录和 artifact 被保存
                session.commit()
                logger.info(f"Task {task_id}: Session committed, transcript and artifact saved")
            
            # Pipeline 已经更新了任务状态为 SUCCESS，不需要再次更新
            
            elapsed_time = time.time() - start_time
            logger.info(f"Task {task_id} completed successfully in {elapsed_time:.2f}s")
        
        except Exception as e:
            # Pipeline 失败时才需要更新状态
            # 因为 pipeline 内部可能已经更新了状态
            logger.error(f"Task {task_id} failed: {e}")
            # 不需要再次更新，pipeline 已经处理了
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
                    state=state.value,  # Convert enum to string
                    error_details=error_message,  # Use error_details instead of error_message
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
    
    def _is_task_cancelled(self, task_id: str) -> bool:
        """
        检查任务是否被取消
        
        Args:
            task_id: 任务 ID
            
        Returns:
            bool: 任务是否被取消
        """
        if not self.redis_client:
            return False
        
        try:
            # 检查 Redis Set 中是否包含该任务 ID
            is_cancelled = self.redis_client.sismember("cancelled_tasks", task_id)
            if is_cancelled:
                logger.info(f"Task {task_id} has been cancelled")
                # 从集合中移除（避免重复检查）
                self.redis_client.srem("cancelled_tasks", task_id)
            return bool(is_cancelled)
        except Exception as e:
            logger.error(f"Failed to check cancellation status: {e}")
            return False
    
    def stop(self):
        """
        停止 Worker
        """
        logger.info("Stopping TaskWorker...")
        self.running = False
