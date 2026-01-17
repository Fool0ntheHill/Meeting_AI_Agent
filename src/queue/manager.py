"""
队列管理器

支持 Redis 和 RabbitMQ 作为消息队列后端。
"""

import json
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class QueueBackend(str, Enum):
    """队列后端类型"""
    REDIS = "redis"
    RABBITMQ = "rabbitmq"


class QueueManager:
    """
    队列管理器
    
    支持任务推送、拉取和优先级队列。
    """
    
    def __init__(
        self,
        backend: QueueBackend = QueueBackend.REDIS,
        redis_url: Optional[str] = None,
        rabbitmq_url: Optional[str] = None,
        queue_name: str = "meeting_tasks",
    ):
        """
        初始化队列管理器
        
        Args:
            backend: 队列后端类型
            redis_url: Redis 连接 URL (格式: redis://host:port/db)
            rabbitmq_url: RabbitMQ 连接 URL (格式: amqp://user:pass@host:port/)
            queue_name: 队列名称
        """
        self.backend = backend
        self.queue_name = queue_name
        self.client = None
        
        if backend == QueueBackend.REDIS:
            self._init_redis(redis_url or "redis://localhost:6379/0")
        elif backend == QueueBackend.RABBITMQ:
            self._init_rabbitmq(rabbitmq_url or "amqp://guest:guest@localhost:5672/")
        else:
            raise ValueError(f"Unsupported queue backend: {backend}")
    
    def _init_redis(self, redis_url: str):
        """初始化 Redis 客户端"""
        try:
            import redis
            self.client = redis.from_url(redis_url, decode_responses=True)
            # 测试连接
            self.client.ping()
            logger.info(f"Connected to Redis: {redis_url}")
        except ImportError:
            raise ImportError("Redis backend requires 'redis' package. Install with: pip install redis")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    def _init_rabbitmq(self, rabbitmq_url: str):
        """初始化 RabbitMQ 客户端"""
        try:
            import pika
            self.connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            self.client = self.connection.channel()
            # 声明队列(持久化)
            self.client.queue_declare(queue=self.queue_name, durable=True)
            logger.info(f"Connected to RabbitMQ: {rabbitmq_url}")
        except ImportError:
            raise ImportError("RabbitMQ backend requires 'pika' package. Install with: pip install pika")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to RabbitMQ: {e}")
    
    def push(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        priority: int = 0,
    ) -> bool:
        """
        推送任务到队列
        
        Args:
            task_id: 任务 ID
            task_data: 任务数据
            priority: 优先级 (数字越大优先级越高)
        
        Returns:
            是否推送成功
        """
        message = {
            "task_id": task_id,
            "data": task_data,
            "priority": priority,
        }
        message_json = json.dumps(message)
        
        try:
            if self.backend == QueueBackend.REDIS:
                # Redis: 使用 sorted set 实现优先级队列
                # score 越大优先级越高,使用负数使得 zpopmin 取出最高优先级
                self.client.zadd(self.queue_name, {message_json: -priority})
                logger.info(f"Pushed task {task_id} to Redis queue (priority={priority})")
                return True
            
            elif self.backend == QueueBackend.RABBITMQ:
                # RabbitMQ: 使用 priority 参数
                import pika
                self.client.basic_publish(
                    exchange="",
                    routing_key=self.queue_name,
                    body=message_json,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 持久化消息
                        priority=priority,
                    ),
                )
                logger.info(f"Pushed task {task_id} to RabbitMQ queue (priority={priority})")
                return True
        
        except Exception as e:
            logger.error(f"Failed to push task {task_id}: {e}")
            return False
    
    def pull(self, timeout: int = 1) -> Optional[Dict[str, Any]]:
        """
        从队列拉取任务
        
        Args:
            timeout: 超时时间(秒)
        
        Returns:
            任务数据,如果队列为空则返回 None
        """
        try:
            if self.backend == QueueBackend.REDIS:
                # Redis: 使用 bzpopmin 阻塞式拉取最高优先级任务
                result = self.client.bzpopmin(self.queue_name, timeout=timeout)
                if result:
                    _, message_json, _ = result
                    message = json.loads(message_json)
                    logger.info(f"Pulled task {message['task_id']} from Redis queue")
                    return message
                return None
            
            elif self.backend == QueueBackend.RABBITMQ:
                # RabbitMQ: 使用 basic_get 非阻塞拉取
                method_frame, header_frame, body = self.client.basic_get(
                    queue=self.queue_name,
                    auto_ack=True,
                )
                if method_frame:
                    message = json.loads(body.decode())
                    logger.info(f"Pulled task {message['task_id']} from RabbitMQ queue")
                    return message
                return None
        
        except Exception as e:
            logger.error(f"Failed to pull task: {e}")
            return None
    
    def get_queue_length(self) -> int:
        """
        获取队列长度
        
        Returns:
            队列中的任务数量
        """
        try:
            if self.backend == QueueBackend.REDIS:
                return self.client.zcard(self.queue_name)
            elif self.backend == QueueBackend.RABBITMQ:
                queue_info = self.client.queue_declare(
                    queue=self.queue_name,
                    durable=True,
                    passive=True,
                )
                return queue_info.method.message_count
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    def clear_queue(self) -> bool:
        """
        清空队列
        
        Returns:
            是否清空成功
        """
        try:
            if self.backend == QueueBackend.REDIS:
                self.client.delete(self.queue_name)
                logger.info(f"Cleared Redis queue: {self.queue_name}")
                return True
            elif self.backend == QueueBackend.RABBITMQ:
                self.client.queue_purge(queue=self.queue_name)
                logger.info(f"Cleared RabbitMQ queue: {self.queue_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return False
    
    def close(self):
        """关闭队列连接"""
        try:
            if self.backend == QueueBackend.REDIS and self.client:
                self.client.close()
                logger.info("Closed Redis connection")
            elif self.backend == QueueBackend.RABBITMQ and self.client:
                self.connection.close()
                logger.info("Closed RabbitMQ connection")
        except Exception as e:
            logger.error(f"Failed to close queue connection: {e}")
