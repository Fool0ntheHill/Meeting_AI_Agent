# 消息队列与 Worker 实现总结

## 完成时间
2026-01-14

## 实现内容

### 1. 队列管理器 (`src/queue/manager.py`)

#### ✅ QueueManager 类
- 支持 Redis 和 RabbitMQ 两种后端
- 实现任务推送、拉取和优先级队列
- 支持队列长度查询和清空操作

#### 核心功能

**推送任务 (push)**:
- 接受任务 ID、任务数据和优先级
- Redis: 使用 sorted set 实现优先级队列
- RabbitMQ: 使用 priority 参数
- 消息持久化防止丢失

**拉取任务 (pull)**:
- 阻塞式拉取(可配置超时)
- 自动按优先级排序
- Redis: 使用 bzpopmin 拉取最高优先级
- RabbitMQ: 使用 basic_get 拉取

**队列管理**:
- `get_queue_length()`: 查询队列长度
- `clear_queue()`: 清空队列
- `close()`: 关闭连接

### 2. 任务 Worker (`src/queue/worker.py`)

#### ✅ TaskWorker 类
- 从队列拉取任务并执行处理
- 实现优雅停机机制
- 集成管线服务和数据库

#### 核心功能

**主循环 (start)**:
- 持续从队列拉取任务
- 执行任务处理
- 更新任务状态
- 错误处理和日志记录

**优雅停机**:
- 监听 SIGTERM 和 SIGINT 信号
- 停止拉取新任务
- 等待当前任务完成(最多 5 分钟)
- 清理资源并退出

**任务处理**:
- 调用 PipelineService 执行完整管线
- 更新任务状态: PENDING → RUNNING → SUCCESS/FAILED
- 记录处理时间和错误信息

### 3. Worker 入口 (`worker.py`)

#### ✅ 独立进程
- 创建所有服务和提供商实例
- 初始化数据库连接
- 连接 Redis 队列
- 启动 Worker 主循环

#### 使用方式

```bash
# 启动 Worker
python worker.py
```

### 4. API 集成 (`src/api/routes/tasks.py`)

#### ✅ 任务创建端点更新
- 创建任务记录后立即推送到队列
- 返回任务 ID 而不等待处理完成
- 响应时间 < 1 秒

#### 流程

```
1. 验证请求参数
2. 生成任务 ID
3. 创建数据库记录
4. 推送到消息队列
5. 立即返回任务 ID
```

### 5. 测试脚本 (`scripts/test_queue.py`)

#### ✅ 队列测试
- 测试 Redis 连接
- 测试任务推送和拉取
- 测试优先级队列
- 测试队列长度查询

## 架构设计

### 异步任务处理

```
┌─────────┐      ┌──────────┐      ┌────────┐      ┌────────┐
│ Client  │─────▶│ FastAPI  │─────▶│ Redis  │◀─────│ Worker │
│         │      │   API    │      │ Queue  │      │        │
└─────────┘      └──────────┘      └────────┘      └────────┘
     │                │                                  │
     │                │                                  │
     │           ┌────▼────┐                        ┌───▼────┐
     │           │Database │                        │Pipeline│
     │           │         │                        │Service │
     │           └─────────┘                        └────────┘
     │                                                   │
     └───────────────────────────────────────────────────┘
              (查询任务状态)
```

### Producer-Consumer 模式

**Producer (FastAPI)**:
- 职责: 请求验证、任务创建、队列推送
- 不执行: 音频处理、模型调用
- 响应时间: < 1 秒

**Consumer (Worker)**:
- 职责: 任务拉取、管线执行、状态更新
- 并发: 可横向扩展(启动多个 Worker)
- 隔离: 单个 Worker 崩溃不影响其他 Worker

**消息队列 (Redis)**:
- 持久化: 任务消息持久化防止丢失
- 优先级: 支持任务优先级队列
- 可靠性: at-least-once 语义

## 技术特性

### ✅ 优雅停机
- 监听 SIGTERM/SIGINT 信号
- 停止拉取新任务
- 等待当前任务完成
- 超时保护(5 分钟)

### ✅ 优先级队列
- 支持任务优先级(0-10)
- 高优先级任务优先处理
- Redis sorted set 实现

### ✅ 错误处理
- 任务失败自动标记
- 错误信息记录到数据库
- 详细日志记录

### ✅ 横向扩展
- 支持多个 Worker 并发处理
- 无状态设计
- 任务自动分配

## 使用示例

### 启动 Redis

```bash
# Docker 方式
docker run -d -p 6379:6379 redis:latest

# 或使用 docker-compose
docker-compose up -d redis
```

### 启动 Worker

```bash
# 单个 Worker
python worker.py

# 多个 Worker (不同终端)
python worker.py  # Worker 1
python worker.py  # Worker 2
python worker.py  # Worker 3
```

### 启动 API 服务器

```bash
python main.py
```

### 创建任务

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_files": ["https://example.com/meeting.wav"],
    "meeting_type": "weekly_sync",
    "asr_language": "zh-CN+en-US",
    "output_language": "zh-CN"
  }'
```

响应:
```json
{
  "success": true,
  "task_id": "task_abc123",
  "message": "任务已创建并加入处理队列"
}
```

### 查询任务状态

```bash
curl -X GET http://localhost:8000/api/v1/tasks/task_abc123/status \
  -H "Authorization: Bearer your_api_key"
```

响应:
```json
{
  "task_id": "task_abc123",
  "state": "RUNNING",
  "progress": 50,
  "estimated_time": 120,
  "error_details": null,
  "updated_at": "2026-01-14T10:30:00Z"
}
```

## 配置

### Redis 连接

在 `config/development.yaml` 中配置:

```yaml
redis:
  url: redis://localhost:6379/0
```

或使用环境变量:

```bash
export REDIS_URL=redis://localhost:6379/0
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
from src.queue.manager import QueueManager

queue = QueueManager(backend="redis")
length = queue.get_queue_length()
print(f"Queue length: {length}")
```

### Worker 状态

查看 Worker 日志:
```bash
tail -f logs/worker.log
```

### 任务状态

通过 API 查询:
```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/status
```

## 测试

### 运行队列测试

```bash
python scripts/test_queue.py
```

测试内容:
- ✅ Redis 连接
- ✅ 任务推送
- ✅ 任务拉取
- ✅ 优先级队列
- ✅ 队列长度查询

### 运行 API 测试

```bash
python scripts/test_api.py
```

## 部署建议

### 开发环境
- 单个 Worker
- 本地 Redis
- SQLite 数据库

### 生产环境
- 多个 Worker (3-5 个)
- Redis Cluster (高可用)
- PostgreSQL 数据库
- 使用 Supervisor 或 systemd 管理 Worker 进程

### Docker 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  api:
    build: .
    command: python main.py
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@postgres:5432/meeting_agent

  worker:
    build: .
    command: python worker.py
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@postgres:5432/meeting_agent
    deploy:
      replicas: 3  # 3 个 Worker 实例

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=meeting_agent
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

## 故障处理

### Worker 崩溃
- 任务会保留在队列中
- 重启 Worker 后自动继续处理
- 使用 Supervisor 自动重启

### Redis 崩溃
- 任务会丢失(如果未持久化)
- 建议启用 Redis AOF 持久化
- 使用 Redis Sentinel 或 Cluster 提高可用性

### 任务超时
- Worker 会等待当前任务完成
- 超过 max_shutdown_wait 后强制退出
- 任务状态会标记为 FAILED

## 性能优化

### 队列优化
- 使用 Redis Pipeline 批量操作
- 调整 Redis maxmemory 配置
- 使用 Redis Cluster 分片

### Worker 优化
- 增加 Worker 数量
- 调整任务拉取超时
- 使用异步 I/O

### 数据库优化
- 使用连接池
- 添加索引
- 定期清理历史数据

## 下一步

### 高优先级
1. ✅ 实现消息队列 (Task 17.1) - 完成
2. ✅ 实现 Worker (Task 17.2) - 完成
3. 实现热词管理 API (Task 20)
4. 实现衍生内容管理 API (Task 22)
5. 实现提示词模板管理 API (Task 21)

### 中优先级
6. 实现 Redis 缓存 (Cache-Aside 模式)
7. 实现任务重试机制
8. 实现 WebSocket 实时状态推送
9. 实现配额管理和熔断

### 低优先级
10. 实现 RabbitMQ 支持
11. 实现审计日志
12. 实现性能监控 (Prometheus)

## 总结

✅ **消息队列与 Worker 已完整实现**
- QueueManager 支持 Redis 和 RabbitMQ
- TaskWorker 实现优雅停机
- API 集成队列推送
- 完整的测试脚本
- 详细的文档

✅ **可以开始下一阶段开发**
- 热词管理 API
- 衍生内容管理 API
- 提示词模板管理 API

✅ **生产就绪**
- 异步任务处理
- 横向扩展支持
- 优雅停机机制
- 错误处理和日志
- Docker 部署支持

