# 会议元数据问题快速修复指南

## 问题

文件名包含日期（如 `20251229会议.ogg`），但生成的纪要显示今天的日期而不是文件名中的日期。

## 原因

代码从文件名提取了日期，但没有保存到数据库，导致 LLM 生成纪要时使用了默认的当前日期。

## 已修复

✅ 已在 `src/services/pipeline.py` 中添加代码，将提取的元数据保存到数据库

## 使用方法

### 1. 重启 Worker

```bash
# 停止当前 worker（Ctrl+C）
# 重新启动
python worker.py
```

### 2. 测试新任务

上传一个文件名包含日期的音频文件，例如：
- `20251229会议.ogg` → 应提取日期 `2025-12-29`
- `meeting_20260115.mp3` → 应提取日期 `2026-01-15`
- `2026-01-20_讨论.wav` → 应提取日期 `2026-01-20`

### 3. 修复已存在的任务（可选）

如果需要修复已经创建的任务：

```bash
python scripts/fix_existing_task_metadata.py <task_id>
```

**注意**：这只会更新数据库中的日期，不会重新生成已有的会议纪要。如果需要正确的日期，请重新创建任务。

## 支持的文件名格式

### 日期格式

- `YYYYMMDD`：`20251229会议.ogg` → `2025-12-29`
- `YYYY-MM-DD`：`2025-12-29_会议.mp3` → `2025-12-29`
- `YYYY_MM_DD`：`2025_12_29_会议.wav` → `2025-12-29`

### 时间格式（仅用户明确提供时使用）

目前不从文件名提取时间，只使用用户在创建任务时明确提供的时间。

## 验证

### 检查数据库

```bash
python scripts/check_task_metadata.py <task_id>
```

应该看到：
```
会议日期: 2025-12-29  ✓
```

### 检查生成的纪要

在纪要的"会议基本信息"部分应该看到正确的日期：
```
- **会议时间和日期**: 2025年12月29日
```

## 测试脚本

### 测试元数据提取功能

```bash
python scripts/test_metadata_extraction.py
```

### 修复特定任务

```bash
python scripts/fix_existing_task_metadata.py task_df5e6f8fb3854bf4
```

## 相关文档

- `docs/summaries/MEETING_METADATA_BUG_FIX.md`：详细的 Bug 分析和修复说明
- `docs/MEETING_METADATA_FRONTEND_GUIDE.md`：前端集成指南
- `docs/summaries/MEETING_METADATA_FEATURE.md`：功能实现总结
