# 时区问题修复完成

## 问题

数据库时间显示错误，比实际时间少 8 小时（UTC 时间）。

## 修复内容

### 1. 数据库模型

将所有 `datetime.utcnow` 改为 `datetime.now`：

- `src/database/models.py`：所有模型的时间戳字段
- `src/database/models_folders.py`：Folder 模型的时间戳字段

### 2. 数据库操作

将所有手动设置时间的地方改为使用本地时间：

- `src/database/repositories.py`：所有 `datetime.utcnow()` → `datetime.now()`
- `src/api/routes/auth.py`：JWT token 的时间戳
- `src/api/routes/artifacts.py`：artifact 更新时间
- `src/api/routes/corrections.py`：内容修改时间、确认时间
- `src/api/routes/trash.py`：删除时间

### 3. 保留 UTC 时间的地方

- `src/providers/volcano_hotword.py`：API 签名必须使用 UTC 时间，保持不变

## 修复过程中的问题

在批量替换时，不小心破坏了几个文件（内容被清空）：
- `src/api/routes/auth.py`
- `src/api/routes/corrections.py`
- `src/api/routes/trash.py`
- `src/api/routes/artifacts.py`
- `src/database/models_folders.py`

已通过 `git checkout` 恢复，然后使用 `strReplace` 逐个修复。

## 验证

Backend 可以正常启动：
```bash
python -c "from src.api.app import create_app; app = create_app(); print('✓ Backend app created successfully')"
# ✓ Backend app created successfully
```

## 下一步

1. **修复数据库中的已有数据**：
   ```bash
   python scripts/fix_timezone_in_db.py
   ```

2. **重启所有服务**：
   ```bash
   python main.py
   python worker.py
   ```

3. **测试**：创建新任务，验证时间显示正确

## 相关文档

- `docs/TIMEZONE_QUICK_FIX.md`：快速修复指南
- `docs/summaries/TIMEZONE_FIX.md`：详细说明
- `scripts/fix_timezone_in_db.py`：数据库时区修复脚本
