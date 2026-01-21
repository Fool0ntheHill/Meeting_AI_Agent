# 时区问题快速修复指南

## 问题

数据库时间显示错误，比实际时间少 8 小时。

## 原因

数据库使用 UTC 时间存储，但前端显示时没有转换为本地时间（北京时间 UTC+8）。

## 修复步骤

### 1. 备份数据库（重要！）

```bash
copy meeting_agent.db meeting_agent.db.backup
```

### 2. 停止所有服务

- 停止 backend（Ctrl+C）
- 停止 worker（Ctrl+C）

### 3. 修复数据库时间

```bash
python scripts/fix_timezone_in_db.py
```

输入 `yes` 确认。

### 4. 重启服务

```bash
# 启动 backend
python main.py

# 启动 worker（新终端）
python worker.py
```

### 5. 验证

创建一个新任务，检查时间是否正确。

## 已修改的代码

- ✅ `src/database/models.py`：所有时间戳改用本地时间
- ✅ `src/database/repositories.py`：所有时间设置改用本地时间
- ✅ `src/api/routes/*.py`：所有时间设置改用本地时间

## 注意事项

1. **只运行一次**：时区修复脚本只需运行一次，重复运行会导致时间再次偏移
2. **先停服务**：修复前必须停止所有服务，避免新旧数据混合
3. **前端无需修改**：前端直接显示后端返回的时间即可

## 验证方法

```bash
# 检查最新任务的时间
python -c "import sqlite3; conn = sqlite3.connect('meeting_agent.db'); cursor = conn.cursor(); cursor.execute('SELECT task_id, created_at FROM tasks ORDER BY created_at DESC LIMIT 1'); print(cursor.fetchone()); conn.close()"
```

时间应该是当前北京时间。

## 详细文档

参见：`docs/summaries/TIMEZONE_FIX.md`
