# 数据库锁定问题

## 问题描述

前端无法获取 artifact，API 返回 500 错误：

```
database is locked
[SQL: UPDATE users SET updated_at=?, last_login_at=? WHERE users.user_id = ?]
```

## 根本原因

**SQLite 并发限制**：

1. Worker 进程持有数据库连接（长时间运行）
2. Backend API 尝试访问数据库（处理前端请求）
3. SQLite 不支持多进程并发写入
4. 导致 `database is locked` 错误

## 验证

任务已成功完成，artifact 已保存到数据库：

```bash
$ python scripts/check_new_task_artifact.py

任务: task_6b3e4935fcba4507
状态: success
Artifact ID: art_task_6b3e4935fcba4507_meeting_minutes_v1
✓ 包含真实姓名: 林煜东
✓ 包含真实姓名: 蓝为一
```

但前端 API 无法访问：

```bash
$ python scripts/test_frontend_artifact_api.py

GET /api/v1/tasks/task_6b3e4935fcba4507
Status: 500
Error: database is locked
```

## 解决方案

### 方案 1：重启 Backend API（推荐）

重启 Backend 会释放所有数据库连接：

```bash
# 停止 Backend (Ctrl+C)
# 重新启动
python -m uvicorn src.api.app:app --reload --port 8000
```

### 方案 2：暂时停止 Worker

如果只是测试前端 API：

```bash
# 停止 Worker (Ctrl+C)
# 测试前端 API
# 测试完成后重新启动 Worker
python worker.py
```

### 方案 3：配置 SQLite WAL 模式（临时缓解）

在 `src/database/session.py` 中配置 WAL 模式：

```python
from sqlalchemy import create_engine, event

engine = create_engine(
    database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 增加超时时间
    }
)

# 启用 WAL 模式
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 秒超时
    cursor.close()
```

**WAL 模式优点**：
- 允许一个写入者和多个读取者并发访问
- 减少锁定冲突

**WAL 模式限制**：
- 仍然只支持一个写入者
- 不适合高并发场景

### 方案 4：迁移到 PostgreSQL（长期方案）

**为什么需要迁移**：

1. **并发支持**：PostgreSQL 支持真正的多进程并发
2. **性能**：更好的查询优化和索引支持
3. **可靠性**：更强的事务支持和数据完整性
4. **扩展性**：支持水平扩展和复制

**迁移步骤**：

1. 安装 PostgreSQL
2. 创建数据库
3. 更新配置文件（`config/development.yaml`）：
   ```yaml
   database:
     url: "postgresql://user:password@localhost:5432/meeting_agent"
   ```
4. 安装 PostgreSQL 驱动：
   ```bash
   pip install psycopg2-binary
   ```
5. 运行迁移脚本（如果有）

## 当前状态

- ✅ 任务处理正常（Worker 工作正常）
- ✅ Artifact 已保存到数据库
- ✅ 说话人名称映射正确（林煜东、蓝为一）
- ❌ 前端 API 被数据库锁阻塞

## 建议

**开发环境**：
- 短期：重启 Backend API 或配置 WAL 模式
- 测试时：暂时停止 Worker

**生产环境**：
- **必须**迁移到 PostgreSQL 或 MySQL
- SQLite 不适合生产环境的多进程应用

## 相关文件

- `src/database/session.py` - 数据库连接配置
- `config/development.yaml` - 数据库 URL 配置
- `docs/production_deployment_guide.md` - 生产部署指南
