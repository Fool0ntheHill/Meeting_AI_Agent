# PostgreSQL 迁移速查表

## 一键命令

### Docker 启动 PostgreSQL
```powershell
docker run --name meeting-postgres -e POSTGRES_PASSWORD=meeting_password -e POSTGRES_DB=meeting_agent -p 5432:5432 -d postgres:15
```

### 创建用户
```sql
CREATE USER meeting_user WITH PASSWORD 'meeting_password';
GRANT ALL PRIVILEGES ON DATABASE meeting_agent TO meeting_user;
GRANT ALL ON SCHEMA public TO meeting_user;
```

### 测试连接
```bash
$env:DB_PASSWORD="meeting_password"
python scripts/test_postgresql_connection.py
```

### 迁移数据
```bash
python scripts/migrate_sqlite_to_postgresql.py
```

## 配置示例

### development.yaml
```yaml
database:
  url: "postgresql://meeting_user:meeting_password@localhost:5432/meeting_agent"
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 3600
  echo: false
```

### 环境变量
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=meeting_agent
DB_USER=meeting_user
DB_PASSWORD=meeting_password
```

## 常用 SQL

### 查看表
```sql
\dt
```

### 查看任务
```sql
SELECT task_id, task_name, state FROM tasks ORDER BY created_at DESC LIMIT 10;
```

### 查看连接
```sql
SELECT count(*) FROM pg_stat_activity;
```

### 查看表大小
```sql
SELECT pg_size_pretty(pg_total_relation_size('tasks'));
```

## Docker 管理

```powershell
docker start meeting-postgres    # 启动
docker stop meeting-postgres     # 停止
docker logs meeting-postgres     # 查看日志
docker exec -it meeting-postgres psql -U meeting_user -d meeting_agent  # 进入命令行
```

## 故障排除

### 连接失败
```bash
docker ps | grep postgres        # 检查是否运行
netstat -an | findstr 5432       # 检查端口
docker logs meeting-postgres     # 查看日志
```

### 权限问题
```sql
GRANT ALL ON ALL TABLES IN SCHEMA public TO meeting_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO meeting_user;
```

## 性能对比

| 指标 | SQLite | PostgreSQL |
|------|--------|------------|
| 并发任务 | 1 个 | 5-10 个 |
| 写操作 | 串行 | 并行 |
| Worker 数量 | 1 个 | 多个 |
| 响应时间 | 基准 | 提升 50%+ |

## 文档链接

- 📖 [完整迁移指南](POSTGRESQL_MIGRATION_GUIDE.md)
- ⚡ [5分钟快速开始](POSTGRESQL_QUICK_START.md)
- 📋 [实施总结](summaries/POSTGRESQL_MIGRATION_IMPLEMENTATION.md)
