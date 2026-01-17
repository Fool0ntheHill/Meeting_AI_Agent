"""
集成测试: 队列和 Worker

测试消息队列和 Worker 的集成:
1. 任务推送和拉取
2. Worker 处理流程
3. 优先级队列
4. 错误重试
5. 优雅停机
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from src.queue.manager import QueueManager, QueueBackend
from src.queue.worker import TaskWorker
from src.core.models import TaskState


@pytest.fixture
def redis_queue():
    """创建 Redis 队列管理器 (需要 Redis 服务运行)"""
    try:
        queue = QueueManager(
            backend=QueueBackend.REDIS,
            redis_url="redis://localhost:6379/15",  # 使用测试数据库
            queue_name="test_queue_integration",
        )
        queue.clear_queue()
        yield queue
        queue.clear_queue()
        queue.close()
    except Exception as e:
        pytest.skip(f"Redis 不可用: {e}")


@pytest.fixture
def pipeline_service():
    """创建 mock 管线服务"""
    from unittest.mock import Mock
    service = Mock()
    service.process_meeting = Mock(return_value={"status": "success"})
    return service


def test_queue_push_and_pull(redis_queue):
    """测试队列推送和拉取"""
    # 推送任务
    task_id = "test_task_001"
    task_data = {
        "audio_files": ["test_audio.wav"],
        "meeting_type": "test",
    }
    
    success = redis_queue.push(task_id, task_data, priority=5)
    assert success is True
    
    # 验证队列长度
    length = redis_queue.get_queue_length()
    assert length == 1
    
    # 拉取任务
    message = redis_queue.pull(timeout=1)
    assert message is not None
    assert message["task_id"] == task_id
    assert message["data"] == task_data
    assert message["priority"] == 5
    
    # 验证队列为空
    length = redis_queue.get_queue_length()
    assert length == 0


def test_priority_queue_ordering(redis_queue):
    """测试优先级队列排序"""
    # 推送不同优先级的任务
    tasks = [
        ("task_low", {"type": "low"}, 0),
        ("task_high", {"type": "high"}, 10),
        ("task_medium", {"type": "medium"}, 5),
    ]
    
    for task_id, task_data, priority in tasks:
        redis_queue.push(task_id, task_data, priority)
    
    # 拉取任务应该按优先级顺序 (高到低)
    expected_order = ["task_high", "task_medium", "task_low"]
    actual_order = []
    
    for _ in range(3):
        message = redis_queue.pull(timeout=1)
        if message:
            actual_order.append(message["task_id"])
    
    assert actual_order == expected_order


def test_queue_timeout(redis_queue):
    """测试队列拉取超时"""
    # 空队列拉取应该超时返回 None
    start_time = time.time()
    message = redis_queue.pull(timeout=1)
    elapsed = time.time() - start_time
    
    assert message is None
    assert elapsed >= 1.0
    assert elapsed < 2.0  # 不应该等待太久


@pytest.mark.integration
def test_worker_task_processing(redis_queue, pipeline_service):
    """测试 Worker 任务处理"""
    # 创建 Worker
    worker = TaskWorker(
        queue_manager=redis_queue,
        pipeline_service=pipeline_service,
    )
    
    # 准备测试任务
    task_id = "task_worker_test_001"
    task_data = {
        "audio_files": ["test_audio.wav"],
        "meeting_type": "common",
        "enable_speaker_recognition": False,
        "enable_correction": False,
    }
    
    # 推送任务到队列
    redis_queue.push(task_id, task_data)
    
    # Mock pipeline service 处理
    with patch.object(
        pipeline_service,
        "process_meeting",
        return_value={"status": "success"},
    ) as mock_process:
        # 手动拉取并处理一个任务
        message = redis_queue.pull(timeout=1)
        assert message is not None
        assert message["task_id"] == task_id
        
        # 处理任务
        worker._process_task(message["task_id"], message["data"])
        
        # 验证 pipeline 被调用
        mock_process.assert_called_once()


@pytest.mark.integration
def test_worker_error_handling(redis_queue, pipeline_service):
    """测试 Worker 错误处理"""
    # 创建 Worker
    worker = TaskWorker(
        queue_manager=redis_queue,
        pipeline_service=pipeline_service,
    )
    
    # 准备测试任务
    task_id = "task_worker_test_002"
    task_data = {
        "audio_files": ["test_audio.wav"],
        "meeting_type": "common",
        "enable_speaker_recognition": False,
        "enable_correction": False,
    }
    
    # 推送任务到队列
    redis_queue.push(task_id, task_data)
    
    # Mock pipeline service 抛出异常
    with patch.object(
        pipeline_service,
        "process_meeting",
        side_effect=Exception("处理失败"),
    ) as mock_process:
        # 手动拉取并处理任务
        message = redis_queue.pull(timeout=1)
        assert message is not None
        
        # 处理任务应该捕获异常
        try:
            worker._process_task(message["task_id"], message["data"])
        except Exception:
            pass  # 异常被捕获是预期的
        
        # 验证 pipeline 被调用
        mock_process.assert_called_once()


@pytest.mark.integration
def test_worker_graceful_shutdown(redis_queue, pipeline_service):
    """测试 Worker 优雅停机"""
    # 创建 Worker
    worker = TaskWorker(
        queue_manager=redis_queue,
        pipeline_service=pipeline_service,
    )
    
    # 验证 Worker 可以启动和停止
    assert worker.running is False
    
    # 模拟启动
    worker.running = True
    assert worker.running is True
    
    # 停止 Worker
    worker.stop()
    assert worker.running is False


def test_queue_clear(redis_queue):
    """测试队列清空"""
    # 推送多个任务
    for i in range(5):
        redis_queue.push(f"task_{i}", {"index": i}, priority=i)
    
    # 验证队列长度
    assert redis_queue.get_queue_length() == 5
    
    # 清空队列
    redis_queue.clear_queue()
    
    # 验证队列为空
    assert redis_queue.get_queue_length() == 0


def test_queue_connection_error():
    """测试队列连接错误"""
    # 尝试连接到不存在的 Redis 服务
    with pytest.raises(Exception):
        queue = QueueManager(
            backend=QueueBackend.REDIS,
            redis_url="redis://invalid-host:6379/0",
            queue_name="test_queue",
        )
        queue.push("task_001", {}, priority=0)


@pytest.mark.asyncio
async def test_worker_concurrent_processing():
    """测试 Worker 并发处理 (如果支持)"""
    # 注意: 当前 Worker 实现是单线程的
    # 如果未来支持并发处理，可以添加此测试
    pass


def test_queue_message_persistence(redis_queue):
    """测试队列消息持久化"""
    # 推送任务
    task_id = "test_task_persistent"
    task_data = {"important": "data"}
    
    redis_queue.push(task_id, task_data, priority=5)
    
    # 关闭连接
    redis_queue.close()
    
    # 重新连接
    new_queue = QueueManager(
        backend=QueueBackend.REDIS,
        redis_url="redis://localhost:6379/15",
        queue_name="test_queue_integration",
    )
    
    # 验证任务仍然存在
    message = new_queue.pull(timeout=1)
    assert message is not None
    assert message["task_id"] == task_id
    assert message["data"] == task_data
    
    new_queue.close()
