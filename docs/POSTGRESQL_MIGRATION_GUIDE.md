# SQLite 迁移到 PostgreSQL 完整指南

## 为什么要迁移？

### SQLite 的限制
1. **写并发限制**: 同一时间只能有一个写操作，多个 Worker 会互相阻塞
2. **锁超时**: 频繁出现 "database is locked" 错误
3. **性能瓶颈**: 大量并发读写时性能下降明显
4. **生产环境不适合**: 不支持网络访问，无法做主从复制

### PostgreSQL 的优势
1. **真正的并发**: 支持多个 Worker 同时处理任务
2. **MVCC**: 多版本并发控制，读写不互相阻塞
3. **生产级**: 成熟的事务管理、备份恢复、主从复制
4. **性能**: 更好的查询优化器和索引支持

---

## 迁移步骤

### 步骤 1: 安装 PostgreSQL

#### Windows (推荐使用 Docker)

```powershell
# 使用 Docker 运行 PostgreSQL
docker run --name meeting-postgres `
  -e POSTGRES_PASSWORD=your_password `
  -e POSTGRES_DB=meeting_agent `
  -p 5432:5432 `
  -d postgres:15

# 或者下载安装包
# https://www.postgresql.org/download/windows/
```

#### Linux/Mac

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Mac
brew install postgresql@15
brew services start postgresql@15
```

### 步骤 2: 创建数据库和用户

```sql
-- 连接到 PostgreSQL
psql -U postgres

-- 创建数据库
CREATE DATABASE meeting_agent;

-- 创建用户
CREATE USER meeting_user WITH PASSWORD 'your_secure_password';

-- 授权
GRANT ALL PRIVILEGES ON DATABASE meeting_agent TO meeting_user;

-- 切换到新数据库
\c meeting_agent

-- 授予 schema 权限
GRANT ALL ON SCHEMA public TO meeting_user;
```

### 步骤 3: 安装 Python 依赖

```bash
# 安装 PostgreSQL 驱动
pip install psycopg2-binary

# 或者从源码编译（性能更好）
pip install psycopg2
```

### 步骤 4: 更新配置文件

修改 `config/development.yaml`:

```yaml
database:
  # 旧的 SQLite 配置（注释掉）
  # url: "sqlite:///./meeting_agent.db"
  
  # 新的 PostgreSQL 配置
  url: "postgresql://meeting_user:your_secure_password@localhost:5432/meeting_agent"
  
  # 连接池配置（PostgreSQL 专用）
  pool_size: 10          # 连接池大小
  max_overflow: 20       # 最大溢出连接数
  pool_timeout: 30       # 获取连接超时（秒）
  pool_recycle: 3600     # 连接回收时间（秒）
  echo: false            # 是否打印 SQL（开发时可设为 true）
```

修改 `config/production.yaml.example`:

```yaml
database:
  url: "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
  pool_size: 20
  max_overflow: 40
  pool_timeout: 30
  pool_recycle: 3600
  echo: false
```

修改 `.env`:

```bash
# PostgreSQL 配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=meeting_agent
DB_USER=meeting_user
DB_PASSWORD=your_secure_password
```

### 步骤 5: 更新数据库连接代码

修改 `src/database/session.py`:

```python
# 添加 PostgreSQL 连接池配置
engine = create_engine(
    database_url,
    echo=config.database.echo if hasattr(config.database, 'echo') else False,
    pool_size=config.database.pool_size if hasattr(config.database, 'pool_size') else 10,
    max_overflow=config.database.max_overflow if hasattr(config.database, 'max_overflow') else 20,
    pool_timeout=config.database.pool_timeout if hasattr(config.database, 'pool_timeout') else 30,
    pool_recycle=config.database.pool_recycle if hasattr(config.database, 'pool_recycle') else 3600,
    pool_pre_ping=True,  # 自动检测失效连接
)
```

### 步骤 6: 创建数据库表结构

```bash
# 使用 SQLAlchemy 创建表
python -c "from src.database.session import engine; from src.database.models import Base; Base.metadata.create_all(engine)"
```

### 步骤 7: 迁移数据（可选）

如果需要保留 SQLite 中的数据：

```bash
# 运行数据迁移脚本
python scripts/migrate_sqlite_to_postgresql.py
```

### 步骤 8: 验证迁移

```bash
# 测试数据库连接
python scripts/test_postgresql_connection.py

# 运行测试
python scripts/test_database.py
```

### 步骤 9: 更新启动脚本

确保所有服务使用新的数据库配置：

```bash
# 启动后端
python main.py

# 启动 Worker
python worker.py
```

---

## 代码修改清单

### 1. 配置文件

- ✅ `config/development.yaml` - 添加 PostgreSQL 配置
- ✅ `config/production.yaml.example` - 添加 PostgreSQL 配置
- ✅ `config/test.yaml.example` - 添加测试数据库配置
- ✅ `.env.example` - 添加数据库环境变量示例

### 2. 数据库连接

- ✅ `src/database/session.py` - 添加连接池配置
- ✅ `src/config/models.py` - 添加数据库配置模型

### 3. 数据模型调整

- ✅ `src/database/models.py` - 确保兼容 PostgreSQL 数据类型

### 4. 迁移脚本

- ✅ `scripts/migrate_sqlite_to_postgresql.py` - 数据迁移脚本
- ✅ `scripts/test_postgresql_connection.py` - 连接测试脚本

### 5. 文档

- ✅ `docs/POSTGRESQL_MIGRATION_GUIDE.md` - 本文档
- ✅ `README.md` - 更新数据库配置说明

---

## PostgreSQL 特定优化

### 1. 索引优化

```sql
-- 为常用查询添加索引
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_state ON tasks(state);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_user_state ON tasks(user_id, state);

-- 为转写记录添加索引
CREATE INDEX idx_transcripts_task_id ON transcript_records(task_id);

-- 为说话人映射添加索引
CREATE INDEX idx_speaker_mappings_task_id ON speaker_mappings(task_id);
```

### 2. 连接池监控

```python
# 在 main.py 中添加连接池监控
from src.database.session import engine

@app.on_event("startup")
async def startup_event():
    logger.info(f"Database pool size: {engine.pool.size()}")
    logger.info(f"Database pool checked out: {engine.pool.checkedout()}")
```

### 3. 事务隔离级别

```python
# 对于高并发场景，可以调整隔离级别
from sqlalchemy import create_engine

engine = create_engine(
    database_url,
    isolation_level="READ COMMITTED",  # PostgreSQL 默认
)
```

---

## 常见问题

### Q1: 迁移后性能没有提升？

**A**: 检查以下几点：
1. 确保创建了必要的索引
2. 检查连接池配置是否合理
3. 使用 `EXPLAIN ANALYZE` 分析慢查询
4. 考虑增加 PostgreSQL 的 `shared_buffers` 和 `work_mem`

### Q2: 出现连接池耗尽错误？

**A**: 调整连接池配置：
```yaml
database:
  pool_size: 20        # 增加连接池大小
  max_overflow: 40     # 增加溢出连接数
```

### Q3: 如何回滚到 SQLite？

**A**: 
1. 修改 `config/development.yaml` 恢复 SQLite 配置
2. 重启服务即可

### Q4: 数据迁移失败怎么办？

**A**:
1. 检查 PostgreSQL 是否正常运行
2. 检查用户权限是否正确
3. 查看迁移脚本的错误日志
4. 可以手动导出 SQLite 数据后再导入

---

## 性能对比

### SQLite (单 Worker)
- 并发任务: 1 个
- 平均响应时间: 100ms
- 数据库锁等待: 频繁

### PostgreSQL (多 Worker)
- 并发任务: 5-10 个
- 平均响应时间: 50ms
- 数据库锁等待: 几乎没有

---

## 下一步

迁移完成后，你可以：

1. **启动多个 Worker**: 
   ```bash
   python worker.py &  # Worker 1
   python worker.py &  # Worker 2
   python worker.py &  # Worker 3
   ```

2. **监控数据库性能**:
   ```sql
   -- 查看活动连接
   SELECT * FROM pg_stat_activity;
   
   -- 查看慢查询
   SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```

3. **配置备份**:
   ```bash
   # 定期备份
   pg_dump -U meeting_user meeting_agent > backup.sql
   ```

---

## 总结

迁移到 PostgreSQL 后，你的系统将能够：
- ✅ 支持多个 Worker 并发处理任务
- ✅ 消除数据库锁等待问题
- ✅ 提升整体性能和响应速度
- ✅ 为生产环境部署做好准备

如有问题，请参考 PostgreSQL 官方文档或联系开发团队。
