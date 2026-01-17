# 集成测试

本目录包含会议纪要 Agent 的集成测试。

## 测试文件

### test_pipeline_integration.py
测试完整的管线处理流程:
- 完整的会议处理流程 (转写 → 识别 → 修正 → 生成)
- 跳过说话人识别的流程
- ASR 降级机制
- 错误处理和部分失败场景

### test_api_integration.py
测试 API 端到端流程:
- 任务创建到完成
- 修正和重新生成
- 热词管理
- 提示词模板管理
- 衍生内容管理
- 任务确认流程

### test_queue_worker_integration.py
测试队列和 Worker 集成:
- 任务推送和拉取
- Worker 处理流程
- 优先级队列
- 错误重试
- 优雅停机

## 运行测试

### 运行所有集成测试
```bash
pytest tests/integration/ -v
```

### 运行特定测试文件
```bash
pytest tests/integration/test_pipeline_integration.py -v
```

### 运行特定测试
```bash
pytest tests/integration/test_pipeline_integration.py::test_complete_pipeline_flow -v
```

### 跳过需要外部服务的测试
```bash
SKIP_INTEGRATION_TESTS=true pytest tests/integration/ -v
```

## 测试依赖

### 必需服务
某些集成测试需要以下服务运行:

1. **Redis** (用于队列测试)
   ```bash
   docker run -d -p 6379:6379 redis:latest
   ```

2. **PostgreSQL** (可选，用于数据库测试)
   ```bash
   docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:latest
   ```

### 环境变量
集成测试使用以下环境变量 (可选):

```bash
# 跳过集成测试
export SKIP_INTEGRATION_TESTS=false

# API 密钥 (用于真实 API 调用测试)
export VOLCANO_APP_ID=your_app_id
export VOLCANO_ACCESS_KEY=your_access_key
export VOLCANO_SECRET_KEY=your_secret_key
export AZURE_SUBSCRIPTION_KEY=your_key
export GEMINI_API_KEY=your_key
export IFLYTEK_APP_ID=your_app_id
export IFLYTEK_API_KEY=your_key
export IFLYTEK_API_SECRET=your_secret

# JWT 密钥
export JWT_SECRET_KEY=your_secret_key
```

## 测试策略

### Mock vs 真实服务
- **单元测试**: 使用 mock 对象，不依赖外部服务
- **集成测试**: 
  - 优先使用 mock 对象测试业务逻辑
  - 可选使用真实服务测试完整流程 (需要配置环境变量)

### 测试数据
- 使用 `conftest.py` 中的 fixtures 创建测试数据
- 测试音频文件使用 `test_audio_file` fixture 生成
- 数据库使用 SQLite 内存数据库或测试数据库

### 测试隔离
- 每个测试使用独立的数据库会话
- 队列测试使用独立的 Redis 数据库 (db=15)
- 测试后自动清理临时文件

## 测试覆盖率

查看集成测试覆盖率:
```bash
pytest tests/integration/ --cov=src --cov-report=html
```

## 注意事项

1. **性能**: 集成测试比单元测试慢，因为涉及更多组件
2. **依赖**: 某些测试需要外部服务 (Redis, PostgreSQL)
3. **隔离**: 确保测试之间相互独立，不共享状态
4. **清理**: 测试后自动清理资源 (数据库记录、临时文件等)

## 故障排查

### Redis 连接失败
```
ConnectionError: Error connecting to Redis
```
**解决方案**: 确保 Redis 服务运行在 `localhost:6379`

### 数据库锁定
```
sqlite3.OperationalError: database is locked
```
**解决方案**: 使用独立的测试数据库或内存数据库

### 测试超时
```
TimeoutError: Test exceeded timeout
```
**解决方案**: 增加测试超时时间或优化测试逻辑

## 持续集成

在 CI/CD 环境中运行集成测试:

```yaml
# .github/workflows/test.yml
- name: Start Redis
  run: docker run -d -p 6379:6379 redis:latest

- name: Run Integration Tests
  run: pytest tests/integration/ -v --cov=src
```

## 扩展测试

添加新的集成测试:

1. 在 `tests/integration/` 创建新的测试文件
2. 使用 `conftest.py` 中的共享 fixtures
3. 遵循现有测试的命名和结构约定
4. 添加必要的文档说明

## 相关文档

- [单元测试](../unit/README.md)
- [测试说明](../../docs/测试说明.md)
- [测试配置指南](../../docs/测试配置指南.md)
