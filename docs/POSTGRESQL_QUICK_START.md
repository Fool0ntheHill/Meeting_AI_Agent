# PostgreSQL 快速开始指南

## 5 分钟快速迁移

### 步骤 1: 安装 PostgreSQL (使用 Docker)

```powershell
# Windows PowerShell
docker run --name meeting-postgres `
  -e POSTGRES_PASSWORD=meeting_password `
  -e POSTGRES_DB=meeting_agent `
  -p 5432:5432 `
  -d postgres:15
```

### 步骤 2: 创建用户和授权

```powershell
# 连接到 PostgreSQL
docker exec -it meeting-postgres psql -U postgres -d meeting_agent

# 在 psql 中执行
CREATE USER meeting_user WITH PASSWORD 'meeting_password';
GRANT ALL PRIVILEGES ON DATABASE meeting_agent TO meeting_user;
GRANT ALL ON SCHEMA public TO meeting_user;
\q
```

### 步骤 3: 安装 Python 驱动

```bash
pip install psycopg2-binary
```

### 步骤 4: 测试连接

```bash
# 设置环境变量
$env:DB_PASSWORD="meeting_password"

# 运行测试
python scripts/test_postgresql_connection.py
```

### 步骤 5: 迁移数据 (可选)

```bash
# 如果有现有 SQLite 数据需要迁移
python scripts/migrate_sqlite_to_postgresql.py
```

### 步骤 6: 更新配置

编辑 `config/development.yaml`:

```yaml
# 注释掉 SQLite 配置
# database:
#   type: sqlite
#   database: test_meeting_agent.db

# 启用 PostgreSQL 配置
database:
  url: "postgresql://meeting_user:meeting_password@localhost:5432/meeting_agent"
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 3600
  echo: false
```

### 步骤 7: 重启服务

```powershell
# 停止现有服务
.\scripts\stop_all.ps1

# 启动服务
.\scripts\start_all.ps1
```

## 验证迁移

```bash
# 检查数据库状态
python scripts/check_db_status.py

# 创建测试任务
python scripts/create_test_task.py
```

## 常用命令

### Docker 管理

```powershell
# 启动 PostgreSQL
docker start meeting-postgres

# 停止 PostgreSQL
docker stop meeting-postgres

# 查看日志
docker logs meeting-postgres

# 进入 PostgreSQL 命令行
docker exec -it meeting-postgres psql -U meeting_user -d meeting_agent
```

### 数据库操作

```sql
-- 查看所有表
\dt

-- 查看任务数量
SELECT COUNT(*) FROM tasks;

-- 查看最近的任务
SELECT task_id, task_name, state, created_at 
FROM tasks 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看连接数
SELECT count(*) FROM pg_stat_activity;
```

## 回滚到 SQLite

如果需要回滚到 SQLite:

1. 编辑 `config/development.yaml`:
   ```yaml
   database:
     type: sqlite
     database: meeting_agent.db
   ```

2. 重启服务:
   ```powershell
   .\scripts\stop_all.ps1
   .\scripts\start_all.ps1
   ```

## 故障排除

### 连接失败

```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 检查端口是否被占用
netstat -an | findstr 5432

# 查看 PostgreSQL 日志
docker logs meeting-postgres
```

### 权限问题

```sql
-- 重新授权
GRANT ALL PRIVILEGES ON DATABASE meeting_agent TO meeting_user;
GRANT ALL ON SCHEMA public TO meeting_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO meeting_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO meeting_user;
```

### 性能问题

```sql
-- 查看慢查询
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- 查看表大小
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 下一步

- 启动多个 Worker 测试并发: `python worker.py &`
- 配置生产环境: 参考 `config/production.yaml.example`
- 设置备份: 使用 `pg_dump` 定期备份
- 监控性能: 使用 `pg_stat_statements` 扩展

## 更多信息

- 完整迁移指南: [docs/POSTGRESQL_MIGRATION_GUIDE.md](POSTGRESQL_MIGRATION_GUIDE.md)
- 数据库设计: [docs/database_migration_guide.md](database_migration_guide.md)
- 配置说明: [config/development.yaml.example](../config/development.yaml.example)
