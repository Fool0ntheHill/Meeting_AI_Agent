# 消息队列模块

## 概述

消息队列模块提供异步任务处理能力,实现 Producer-Consumer 模式。

## 组件

### QueueManager (队列管理器)

负责任务的推送、拉取和队列管理。

**支持的后端**:
- Redis (推荐,简单高效)
- RabbitMQ (复杂场景,更多特性)

**核心功能**:
- 任务推送 (push)
- 任务拉取 (pull)
- 优先级队列
- 队列长度查询
- 队列清空

### TaskWorker (任务 Worker)

从队列拉取任务并执行处理。

**核心功能**:
- 任务拉取循环
- 管线执行
- 状态更新
- 优雅停机
- 错误处理

## 使用示例

### 创建队列管理器

```python
from src.queue.manager import QueueManager, QueueBackend

# Redis 后端
queue = QueueManager(
    backend=QueueBackend.REDIS,
    redis_url="redis://localhost:6379/0",
    queue_name="meeting_tasks",
)

# RabbitMQ 后端
queue = QueueManager(
    backend=QueueBackend.RABBITMQ,
    rabbitmq_url="amqp://guest:guest@localhost:5672/",
    queue_name="meeting_tasks",
)
```

### 推送任务

```python
task_id = "task_123"
task_data = {
    "audio_files": ["meeting.wav"],
    "meeting_type": "weekly_sync",
}
priority = 5  # 0-10, 数字越大优先级越高

success = queue.push(task_id, task_data, priority)
```

### 拉取任务

```python
# 阻塞式拉取(超时 1 秒)
message = queue.pull(timeout=1)

if message:
    task_id = message["task_id"]
    task_data = message["data"]
    priority = message["priority"]
    
    # 处理任务
    process_task(task_id, task_data)
```

### 创建 Worker

```python
from src.queue.worker import TaskWorker
from src.services.pipeline import PipelineService

# 创建 Worker
worker = TaskWorker(
    queue_manager=queue,
    pipeline_service=pipeline_service,
    max_shutdown_wait=300,  # 5 分钟
)

# 启动 Worker
worker.start()
```

### 优雅停机

Worker 会监听 SIGTERM 和 SIGINT 信号:

```bash
# 发送停机信号
kill -TERM <worker_pid>

# 或使用 Ctrl+C
```

停机流程:
1. 停止拉取新任务
2. 等待当前任务完成(最多 5 分钟)
3. 清理资源并退出

## 架构设计

### Producer-Consumer 模式

```
┌─────────┐      ┌──────────┐      ┌────────┐
│Producer │─────▶│  Queue   │◀─────│Consumer│
│(FastAPI)│      │ (Redis)  │      │(Worker)│
└─────────┘      └──────────┘      └────────┘
```

**Producer (FastAPI)**:
- 创建任务记录
- 推送到队列
- 立即返回任务 ID

**Consumer (Worker)**:
- 拉取任务
- 执行管线
- 更新状态

### 优先级队列

使用 Redis sorted set 实现:

```python
# 推送任务
ZADD meeting_tasks -5 '{"task_id": "task_123", ...}'

# 拉取任务 (最高优先级)
BZPOPMIN meeting_tasks 1
```

Score 使用负数,使得 BZPOPMIN 取出最高优先级任务。

## 配置

### Redis 配置

```yaml
# config/development.yaml
redis:
  url: redis://localhost:6379/0
```

### Worker 配置

```python
worker = TaskWorker(
    queue_manager=queue_manager,
    pipeline_service=pipeline_service,
    max_shutdown_wait=300,  # 最大停机等待时间(秒)
)
```

## 监控

### 队列长度

```python
length = queue.get_queue_length()
print(f"Queue length: {length}")
```

### Worker 日志

```bash
tail -f logs/worker.log
```

## 测试

### 运行测试

```bash
python scripts/test_queue.py
```

### 测试内容

- ✅ Redis 连接
- ✅ 任务推送
- ✅ 任务拉取
- ✅ 优先级队列
- ✅ 队列长度查询

## 部署

### 开发环境

```bash
# 启动 Redis
docker run -d -p 6379:6379 redis:latest

# 启动 Worker
python worker.py
```

### 生产环境

使用 Supervisor 管理 Worker:

```ini
# /etc/supervisor/conf.d/meeting-worker.conf
[program:meeting-worker]
command=/path/to/venv/bin/python /path/to/worker.py
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/meeting-worker.log
```

### Docker 部署

```yaml
# docker-compose.yml
services:
  worker:
    build: .
    command: python worker.py
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
    deploy:
      replicas: 3  # 3 个 Worker 实例
```

## 故障处理

### Worker 崩溃
- 任务保留在队列中
- 重启 Worker 后自动继续处理

### Redis 崩溃
- 启用 AOF 持久化
- 使用 Redis Sentinel 或 Cluster

### 任务超时
- Worker 等待当前任务完成
- 超过 max_shutdown_wait 后强制退出
- 任务状态标记为 FAILED

## 性能优化

### 增加 Worker 数量

```bash
# 启动多个 Worker
python worker.py &  # Worker 1
python worker.py &  # Worker 2
python worker.py &  # Worker 3
```

### 调整拉取超时

```python
# 减少空闲等待时间
message = queue.pull(timeout=0.5)
```

### 使用 Redis Pipeline

```python
# 批量推送任务
pipe = queue.client.pipeline()
for task in tasks:
    pipe.zadd(queue_name, {message: -priority})
pipe.execute()
```

## 最佳实践

1. **使用优先级**: 重要任务设置更高优先级
2. **监控队列长度**: 避免队列积压
3. **横向扩展**: 增加 Worker 数量而不是单个 Worker 性能
4. **优雅停机**: 使用信号而不是强制 kill
5. **错误处理**: 记录详细日志便于排查
6. **幂等性**: 确保任务可以安全重试

## 参考

- [Redis Documentation](https://redis.io/documentation)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Celery Documentation](https://docs.celeryproject.org/) (类似项目)

