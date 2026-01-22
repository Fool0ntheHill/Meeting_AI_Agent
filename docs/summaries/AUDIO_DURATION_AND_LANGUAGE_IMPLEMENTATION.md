# Audio Duration and Language Field Implementation Summary

## 实现概述

为了解决前端在任务状态接口中无法获取音频时长和识别语言的问题，我们进行了以下改动：

1. **添加 `audio_duration` 字段到 Task 模型**：在任务创建时保存音频时长
2. **在状态接口返回 `asr_language` 字段**：让前端能正确显示识别语言标签

## 问题背景

### 问题 1：ETA 计算不准确
- **现象**：前端在 progress < 40% 时无法获取 `audio_duration`，导致 ETA 计算错误
- **原因**：`audio_duration` 只在转写完成后（progress=40%）才从 `TranscriptRecord` 中获取
- **影响**：前端在转写前阶段显示错误的 ETA

### 问题 2：识别语言显示为 `--`
- **现象**：前端无法从状态接口获取识别语言，显示 `--`
- **原因**：状态接口未返回 `asr_language` 字段
- **影响**：用户无法看到任务使用的识别语言（如"中文 / 英文"）

## 解决方案

### 1. 数据库改动

**新增字段：`tasks.audio_duration`**

```sql
ALTER TABLE tasks ADD COLUMN audio_duration REAL;
```

**迁移脚本：**
```bash
python scripts/migrate_add_audio_duration.py
```

**迁移内容：**
- 添加 `audio_duration` 列
- 从现有的 `TranscriptRecord` 回填数据（37 个任务）

### 2. 模型改动

**文件：`src/database/models.py`**

```python
class Task(Base):
    # ...
    audio_duration = Column(Float, nullable=True)  # 音频总时长（秒）
```

### 3. Repository 改动

**文件：`src/database/repositories.py`**

```python
def create(
    self,
    task_id: str,
    # ...
    audio_duration: Optional[float] = None,  # 新增参数
    # ...
) -> Task:
    task = Task(
        # ...
        audio_duration=audio_duration,
        # ...
    )
```

### 4. API Schema 改动

**文件：`src/api/schemas.py`**

```python
class CreateTaskRequest(BaseModel):
    audio_files: List[str]
    audio_duration: Optional[float] = Field(None, description="音频总时长(秒)，从上传接口获取")
    # ...

class TaskStatusResponse(BaseModel):
    task_id: str
    state: TaskState
    progress: float
    audio_duration: Optional[float] = Field(None, description="音频总时长(秒)")
    asr_language: Optional[str] = Field(None, description="ASR识别语言 (如 zh-CN+en-US)")
    # ...
```

### 5. API 路由改动

**文件：`src/api/routes/tasks.py`**

**创建任务：**
```python
task = task_repo.create(
    # ...
    audio_duration=request.audio_duration,  # 保存音频时长
    # ...
)
```

**获取状态：**
```python
# 优先从 Task 模型获取，降级到 TranscriptRecord
audio_duration = task.audio_duration
if audio_duration is None and task.transcripts:
    audio_duration = task.transcripts[0].duration

# 获取 ASR 识别语言
asr_language = task.asr_language

return TaskStatusResponse(
    # ...
    audio_duration=audio_duration,
    asr_language=asr_language,
    # ...
)
```

**缓存更新：**
```python
cache_data = {
    # ...
    "audio_duration": audio_duration,
    "asr_language": asr_language,
    # ...
}
```

## 前端使用指南

### 1. 创建任务流程

```typescript
// Step 1: 上传音频
const uploadResponse = await uploadAudio(file);
const { file_path, duration } = uploadResponse;

// Step 2: 创建任务，传入 audio_duration
const createResponse = await createTask({
  audio_files: [file_path],
  audio_duration: duration,  // 从上传响应获取
  asr_language: "zh-CN+en-US",
  meeting_type: "weekly_sync",
});
```

### 2. 轮询状态并计算 ETA

```typescript
const status = await getTaskStatus(taskId);

// 从 progress=0 开始就能获取 audio_duration
if (status.audio_duration) {
  const totalTime = status.audio_duration * 0.25;
  const eta = totalTime * (1 - status.progress / 100);
  console.log(`预计剩余: ${eta.toFixed(0)} 秒`);
}
```

### 3. 显示识别语言

```typescript
function parseLanguages(asrLanguage: string): string[] {
  const languageMap: Record<string, string> = {
    'zh-CN': '中文',
    'en-US': '英文',
    'ja-JP': '日文',
    'ko-KR': '韩文',
  };
  
  return asrLanguage
    .split('+')
    .map(lang => languageMap[lang] || lang);
}

// 使用
if (status.asr_language) {
  const languages = parseLanguages(status.asr_language);
  console.log(`识别语言: ${languages.join(' / ')}`);
  // 输出: "识别语言: 中文 / 英文"
}
```

## 测试验证

### 测试脚本

```bash
python scripts/test_audio_duration_flow.py
```

### 预期输出

```
✓ Task created with audio_duration and asr_language
✓ audio_duration available at progress=0
✓ asr_language available at progress=0
✓ Frontend can calculate ETA from the start
✓ Frontend can display language labels (中文 / 英文)
```

## API 响应示例

### GET /api/v1/tasks/{task_id}/status

**progress=0 时：**
```json
{
  "task_id": "task_abc123",
  "state": "pending",
  "progress": 0.0,
  "audio_duration": 479.1,
  "asr_language": "zh-CN+en-US",
  "estimated_time": 119.775,
  "error_details": null,
  "updated_at": "2026-01-22T14:30:00Z"
}
```

**progress=40 时：**
```json
{
  "task_id": "task_abc123",
  "state": "running",
  "progress": 40.0,
  "audio_duration": 479.1,
  "asr_language": "zh-CN+en-US",
  "estimated_time": 71.865,
  "error_details": null,
  "updated_at": "2026-01-22T14:32:00Z"
}
```

## 数据来源优先级

### audio_duration
1. **优先**：`Task.audio_duration`（任务创建时保存）
2. **降级**：`TranscriptRecord.duration`（转写完成后可用）

### asr_language
- **来源**：`Task.asr_language`（任务创建时保存）

## 向后兼容性

- 字段为可选（`Optional`），旧任务可能为 `null`
- 前端应处理 `null` 情况，提供降级方案
- 所有新任务都会包含这两个字段

## 相关文件

### 修改的文件
- `src/database/models.py` - 添加 `audio_duration` 字段
- `src/database/repositories.py` - 更新 `create()` 方法
- `src/api/schemas.py` - 更新请求/响应 schema
- `src/api/routes/tasks.py` - 更新创建和状态接口
- `docs/frontend-types.ts` - 更新前端类型定义

### 新增的文件
- `scripts/migrate_add_audio_duration.py` - 数据库迁移脚本
- `scripts/test_audio_duration_flow.py` - 测试脚本
- `docs/AUDIO_DURATION_AND_LANGUAGE_GUIDE.md` - 使用指南
- `docs/summaries/AUDIO_DURATION_AND_LANGUAGE_IMPLEMENTATION.md` - 本文档

## 总结

通过这次改动，我们解决了两个关键问题：

1. ✅ **ETA 计算准确**：前端从 progress=0 开始就能获取 `audio_duration`，准确计算 ETA
2. ✅ **语言显示正确**：前端能从状态接口获取 `asr_language`，正确显示"中文 / 英文"等标签

这些改动提升了用户体验，让前端能够：
- 在任务开始前就显示准确的预计时间
- 清晰地展示任务使用的识别语言
- 避免显示 `--` 等占位符

## 下一步

建议前端团队：
1. 更新 API 调用代码，在创建任务时传入 `audio_duration`
2. 更新状态轮询代码，使用新的 `audio_duration` 和 `asr_language` 字段
3. 实现语言解析函数，将 `zh-CN+en-US` 转换为"中文 / 英文"
4. 测试 ETA 计算和语言显示功能
