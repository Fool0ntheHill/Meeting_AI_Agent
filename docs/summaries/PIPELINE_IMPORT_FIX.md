# Pipeline Import Error Fix

## 问题描述

Worker 日志显示两个问题：
1. 导入错误：`cannot import name 'get_db_session' from 'src.database.session'`
2. Gemini API Key 泄露警告：`Your API key was reported as leaked. Please use another API key.`

## 修复内容

### 1. 修复导入错误

在 `src/services/pipeline.py` 中有两处使用了不存在的 `get_db_session` 函数：

**第一处（第 90 行）**：读取任务元数据
```python
# 修复前
from src.database.session import get_db_session
with get_db_session() as db:
    # ...

# 修复后
from src.database.session import session_scope
with session_scope() as db:
    # ...
```

**第二处（第 149 行）**：保存会议元数据
```python
# 修复前
from src.database.session import get_db_session
with get_db_session() as db:
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    if task:
        task.meeting_date = meeting_date
        task.meeting_time = meeting_time
        db.commit()  # 手动提交

# 修复后
from src.database.session import session_scope
with session_scope() as db:
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    if task:
        task.meeting_date = meeting_date
        task.meeting_time = meeting_time
    # session_scope 会自动提交
```

### 2. 关于 Gemini API Key 泄露

**问题原因**：
- Gemini API 检测到当前使用的 API key 已经泄露（可能在 git 历史或公开渠道中暴露）
- 当前 key：`AIzaSyBVdYD5kXLV2aOC3LNJ9Oj_CP6v7S9XqI4`

**解决方案**：
用户需要：
1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey) 创建新的 API key
2. 撤销已泄露的旧 key
3. 更新配置文件 `config/development.yaml` 中的 `gemini.api_keys`
4. 重启 worker

## 验证步骤

1. 确认导入错误已修复：
```bash
python -c "from src.services.pipeline import PipelineService; print('Import OK')"
```

2. 更新 API key 后重启 worker：
```bash
python worker.py
```

3. 检查 worker 日志，确认没有导入错误和 API key 警告

## 相关文件

- `src/services/pipeline.py` - 修复导入错误
- `src/database/session.py` - 正确的数据库会话管理
- `config/development.yaml` - 需要更新 Gemini API key

## 注意事项

- `session_scope()` 是上下文管理器，会自动处理提交和回滚，不需要手动调用 `db.commit()`
- `get_db_session()` 函数不存在，正确的函数是 `get_session()` 或使用 `session_scope()` 上下文管理器
- API key 泄露后必须立即更换，旧 key 将无法继续使用

## 时间

2026-01-22
