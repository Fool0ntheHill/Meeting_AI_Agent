# 会议元数据 Bug 修复

## 问题描述

用户报告即使文件名包含日期（如 `20251229ONE产品和业务规则中心的设计讨论会议.ogg`），生成的会议纪要中仍然显示当前日期（2026-01-21）而不是文件名中的日期（2025-12-29）。

## 根本原因

经过调查发现，问题出在 `src/services/pipeline.py` 中：

1. **元数据提取正常**：`extract_meeting_metadata()` 函数能够正确从文件名中提取日期
2. **数据未保存**：提取的 `meeting_date` 和 `meeting_time` 只在内存中更新，但从未保存回数据库
3. **LLM 使用旧数据**：由于数据库中的 `meeting_date` 仍然是 `None`，LLM 生成纪要时使用了默认的当前日期

## 修复方案

### 1. 添加数据库更新逻辑

在 `src/services/pipeline.py` 的元数据提取后，添加代码将提取的元数据保存回数据库：

```python
# 提取会议元数据（在转写完成后）
if not meeting_date:
    from src.utils.meeting_metadata import extract_meeting_metadata
    extracted_date, extracted_time = extract_meeting_metadata(
        original_filenames=original_filenames,
        meeting_date=meeting_date,
        meeting_time=meeting_time,
    )
    meeting_date = extracted_date or meeting_date
    # 只有用户明确提供时才使用时间
    if not meeting_time and extracted_time:
        meeting_time = extracted_time
    
    logger.info(f"Task {task_id}: Meeting metadata - date={meeting_date}, time={meeting_time}")
    
    # 保存提取的元数据到数据库
    try:
        from src.database.repositories import TaskRepository
        from src.database.session import get_db_session
        
        with get_db_session() as db:
            task_repo = TaskRepository(db)
            task = task_repo.get_by_id(task_id)
            if task:
                task.meeting_date = meeting_date
                task.meeting_time = meeting_time
                db.commit()
                logger.info(f"Task {task_id}: Meeting metadata saved to database")
    except Exception as e:
        logger.warning(f"Task {task_id}: Failed to save meeting metadata: {e}")
```

### 2. 添加调试日志

在读取任务元数据时添加日志，方便追踪数据流：

```python
logger.info(
    f"Task {task_id}: Loaded metadata from DB - "
    f"date={meeting_date}, time={meeting_time}, "
    f"filenames={original_filenames}"
)
```

## 验证测试

### 测试脚本

创建了以下测试脚本：

1. **`scripts/test_metadata_extraction.py`**：测试元数据提取函数
   - 验证日期提取功能
   - 测试各种文件名格式
   - 确认提取逻辑正确

2. **`scripts/fix_existing_task_metadata.py`**：修复已存在任务的元数据
   - 读取任务的 `original_filenames`
   - 提取会议日期
   - 更新数据库

### 测试结果

```bash
# 测试元数据提取
$ python scripts/test_metadata_extraction.py

文件名: 20251229ONE产品和业务规则中心的设计讨论会议.ogg
提取日期: 2025-12-29  ✓

# 修复已存在的任务
$ python scripts/fix_existing_task_metadata.py task_df5e6f8fb3854bf4

当前元数据:
  原始文件名: ["20251229ONE产品和业务规则中心的设计讨论会议.ogg"]
  会议日期: (未设置)
  会议时间: (未设置)

提取的元数据:
  会议日期: 2025-12-29  ✓
  会议时间: (无法提取)

✓ 元数据已更新到数据库
```

## 影响范围

### 已修复的文件

- `src/services/pipeline.py`：添加元数据保存逻辑和调试日志

### 新增的文件

- `scripts/test_metadata_extraction.py`：元数据提取测试脚本
- `scripts/fix_existing_task_metadata.py`：修复已存在任务的脚本

### 需要用户操作

1. **重启 Worker**：使用更新后的代码
   ```bash
   # 停止当前 worker
   # 重新启动
   python worker.py
   ```

2. **修复已存在的任务**（可选）：
   ```bash
   python scripts/fix_existing_task_metadata.py <task_id>
   ```
   注意：这只会更新数据库中的 `meeting_date`，不会重新生成已有的 artifact。

3. **创建新任务测试**：上传新文件验证日期提取功能

## 数据流程

### 修复前

```
上传文件 → 创建任务 → 保存 original_filenames
                    ↓
                 转写音频
                    ↓
            提取元数据（内存中）← 从 original_filenames 提取
                    ↓
            ❌ 未保存到数据库
                    ↓
            LLM 生成纪要 ← 使用 None（默认当前日期）
```

### 修复后

```
上传文件 → 创建任务 → 保存 original_filenames
                    ↓
                 转写音频
                    ↓
            提取元数据（内存中）← 从 original_filenames 提取
                    ↓
            ✓ 保存到数据库（meeting_date, meeting_time）
                    ↓
            LLM 生成纪要 ← 使用正确的日期
```

## 设计原则（保持不变）

- **日期优先级**：用户提供 > 文件名提取 > 当前日期
- **时间策略**：只使用用户明确提供的时间（不推算、不从文件名提取）
- **不使用 created_at**：避免使用任务创建时间推算会议时间（不准确）

## 后续建议

1. **添加集成测试**：测试完整的任务创建 → 元数据提取 → LLM 生成流程
2. **前端显示**：在任务详情页显示会议日期和时间
3. **用户输入**：前端提供日期/时间输入框，让用户可以手动指定

## 相关文档

- `docs/MEETING_METADATA_FRONTEND_GUIDE.md`：前端集成指南
- `docs/summaries/MEETING_METADATA_FEATURE.md`：功能实现总结
- `docs/SYSTEM_INSTRUCTION_QUICK_REF.md`：System Instruction 参考
