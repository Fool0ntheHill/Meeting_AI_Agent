# 数据库时区问题修复

## 问题描述

数据库中的时间戳使用 `datetime.utcnow()` 存储 UTC 时间，但前端显示时没有转换为本地时间，导致时间显示错误。

### 示例

- **系统时间**：2026-01-21 23:29（北京时间 UTC+8）
- **数据库存储**：2026-01-21 15:29（UTC 时间）
- **前端显示**：2026-01-21 15:29（错误，应该显示 23:29）

时间差：8 小时

## 修复方案

### 方案选择

有两种修复方案：

1. **方案 A（已采用）**：改用本地时间
   - 数据库存储本地时间（`datetime.now()`）
   - 前端直接显示，无需转换
   - 简单直接，适合单时区应用

2. **方案 B（未采用）**：保持 UTC，前端转换
   - 数据库存储 UTC 时间
   - API 返回 ISO 8601 格式（带时区信息）
   - 前端转换为本地时间显示
   - 适合多时区应用，但需要前后端配合

考虑到当前是单时区应用（中国），选择方案 A。

## 修复步骤

### 1. 修改代码

将所有 `datetime.utcnow` 改为 `datetime.now`：

- `src/database/models.py`：所有模型的时间戳字段
- `src/database/repositories.py`：所有手动设置时间的地方

### 2. 修复已有数据

运行脚本将数据库中的 UTC 时间转换为本地时间（+8 小时）：

```bash
python scripts/fix_timezone_in_db.py
```

**警告**：此操作会修改数据库，建议先备份！

### 3. 重启服务

```bash
# 重启 backend
python main.py

# 重启 worker
python worker.py
```

### 4. 验证

```bash
# 验证时区修复结果
python scripts/fix_timezone_in_db.py --verify
```

## 修改的文件

### 代码文件

- `src/database/models.py`：所有模型的 `default=datetime.utcnow` → `default=datetime.now`
- `src/database/repositories.py`：所有 `datetime.utcnow()` → `datetime.now()`

### 新增文件

- `scripts/fix_timezone_in_db.py`：时区修复脚本
- `docs/summaries/TIMEZONE_FIX.md`：本文档

## 影响范围

### 受影响的表

- `tasks`：created_at, updated_at, completed_at, confirmed_at, deleted_at, last_content_modified_at
- `folders`：created_at, updated_at
- `speakers`：created_at, updated_at
- `users`：created_at, updated_at, last_login_at
- `transcript_records`：created_at
- `speaker_mappings`：created_at, corrected_at
- `prompt_templates`：created_at, updated_at
- `generated_artifacts`：created_at
- `hotword_sets`：created_at, updated_at
- `audit_logs`：created_at

### 前端影响

- **无需修改**：前端直接显示后端返回的时间即可
- 如果前端之前有时区转换逻辑，需要移除

## 注意事项

### 1. 数据备份

修复前务必备份数据库：

```bash
copy meeting_agent.db meeting_agent.db.backup
```

### 2. 一次性操作

时区修复脚本只需运行一次，重复运行会导致时间再次偏移 8 小时。

### 3. 新旧数据混合

如果在修复代码后、修复数据前创建了新任务，这些任务的时间已经是本地时间，不需要再加 8 小时。

建议：
- 先停止所有服务
- 修复代码
- 修复数据
- 重启服务

### 4. 多时区支持

如果将来需要支持多时区：
- 改回使用 UTC 时间存储
- API 返回 ISO 8601 格式（如 `2026-01-21T15:29:25+08:00`）
- 前端使用 `new Date()` 解析并转换为本地时间

## 验证方法

### 检查数据库

```bash
python -c "import sqlite3; conn = sqlite3.connect('meeting_agent.db'); cursor = conn.cursor(); cursor.execute('SELECT task_id, created_at FROM tasks ORDER BY created_at DESC LIMIT 1'); print(cursor.fetchone()); conn.close()"
```

应该显示本地时间（北京时间）。

### 检查新创建的任务

创建一个新任务，检查数据库中的 `created_at` 是否是当前本地时间。

### 前端验证

在前端查看任务列表，时间应该与系统时间一致。

## 相关问题

### Q: 为什么不使用 timezone-aware datetime？

A: SQLite 不原生支持时区，使用 timezone-aware datetime 会增加复杂度。对于单时区应用，使用本地时间更简单。

### Q: 如果服务器在不同时区怎么办？

A: 确保服务器系统时区设置为 Asia/Shanghai（UTC+8）。

### Q: 会影响已有的 API 吗？

A: 不会。API 返回的时间格式不变，只是时间值从 UTC 改为本地时间。

## 总结

- ✅ 代码已修改：使用 `datetime.now()` 代替 `datetime.utcnow()`
- ⚠️ 数据需修复：运行 `scripts/fix_timezone_in_db.py`
- ✅ 前端无需修改：直接显示后端返回的时间
- ⚠️ 记得备份数据库
