# Audio Duration and Language Field Guide

## 概述

本文档说明后端如何在任务状态接口中提供 `audio_duration` 和 `asr_language` 字段，以便前端：
1. 从 progress=0 开始就能准确计算 ETA
2. 正确显示识别语言标签（如"中文 / 英文"），避免显示 `--`

## 改动内容

### 1. 数据库改动

**新增字段：`tasks.audio_duration`**
- 类型：`REAL` (Float)
- 可空：`True`
- 说明：音频总时长（秒），在任务创建时从上传接口获取

**迁移脚本：**
```bash
python scripts/migrate_add_audio_duration.py
```

### 2. API 改动

#### 2.1 创建任务接口

**接口：`POST /api/v1/tasks`**

**请求新增字段：**
```json
{
  "audio_files": ["https://tos.example.com/meeting.wav"],
  "audio_duration": 479.1,  // 新增：从上传接口获取的音频时长
  "asr_language": "zh-CN+en-US",
  "meeting_type": "weekly_sync",
  ...
}
```

#### 2.2 任务状态接口

**接口：`GET /api/v1/tasks/{task_id}/status`**

**响应新增字段：**
```json
{
  "task_id": "task_abc123",
  "state": "pending",
  "progress": 0.0,
  "audio_duration": 479.1,      // 新增：音频总时长（秒）
  "asr_language": "zh-CN+en-US", // 新增：ASR识别语言
  "estimated_time": 119.775,
  "error_details": null,
  "updated_at": "2026-01-22T14:30:00Z"
}
```

**字段说明：**

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `audio_duration` | `float?` | 音频总时长（秒），从任务创建时保存 | `479.1` |
| `asr_language` | `string?` | ASR识别语言，格式：单语言或多语言组合 | `"zh-CN+en-US"` |

**语言格式：**
- 单语言：`"zh-CN"`, `"en-US"`, `"ja-JP"`
- 多语言：`"zh-CN+en-US"`, `"zh-CN+en-US+ja-JP"`

#### 2.3 任务详情接口

**接口：`GET /api/v1/tasks/{task_id}`**

任务详情接口已有 `asr_language` 字段，保持不变。

## 前端使用指南

### 1. 创建任务流程

```typescript
// Step 1: 上传音频文件
const uploadResponse = await uploadAudio(file);
const { file_path, duration } = uploadResponse;

// Step 2: 创建任务，传入 audio_duration
const createResponse = await createTask({
  audio_files: [file_path],
  audio_duration: duration,  // 从上传响应获取
  asr_language: "zh-CN+en-US",
  meeting_type: "weekly_sync",
  ...
});
```

### 2. 轮询任务状态

```typescript
// 轮询任务状态
const status = await getTaskStatus(taskId);

// 从 progress=0 开始就能获取 audio_duration
if (status.audio_duration) {
  // 计算 ETA
  const totalTime = status.audio_duration * 0.25;
  const eta = totalTime * (1 - status.progress / 100);
  console.log(`预计剩余时间: ${eta.toFixed(0)} 秒`);
}

// 显示识别语言
if (status.asr_language) {
  const languages = parseLanguages(status.asr_language);
  console.log(`识别语言: ${languages.join(' / ')}`);
  // 输出: "识别语言: 中文 / 英文"
}
```

### 3. 语言解析函数

```typescript
function parseLanguages(asrLanguage: string): string[] {
  const languageMap: Record<string, string> = {
    'zh-CN': '中文',
    'en-US': '英文',
    'ja-JP': '日文',
    'ko-KR': '韩文',
    'es-ES': '西班牙文',
    'fr-FR': '法文',
    'de-DE': '德文',
  };
  
  return asrLanguage
    .split('+')
    .map(lang => languageMap[lang] || lang);
}

// 示例
parseLanguages('zh-CN+en-US');  // ['中文', '英文']
parseLanguages('zh-CN');         // ['中文']
```

## ETA 计算公式

```
estimated_time = audio_duration × 0.25 × (1 - progress / 100)
```

**说明：**
- `audio_duration`：音频总时长（秒）
- `0.25`：处理系数（音频时长的 25%）
- `progress`：当前进度（0-100）

**示例：**
- 音频时长：479.1 秒
- 进度：0%
- ETA = 479.1 × 0.25 × (1 - 0/100) = 119.775 秒

- 进度：40%
- ETA = 479.1 × 0.25 × (1 - 40/100) = 71.865 秒

- 进度：100%
- ETA = 479.1 × 0.25 × (1 - 100/100) = 0 秒

## 数据来源优先级

### audio_duration
1. **优先**：`Task.audio_duration`（任务创建时保存）
2. **降级**：`TranscriptRecord.duration`（转写完成后可用）

### asr_language
- **来源**：`Task.asr_language`（任务创建时保存）

## 缓存策略

任务状态接口使用 Redis 缓存：
- **进行中任务**：TTL = 5 秒（确保能及时看到状态更新）
- **已完成任务**：TTL = 60 秒

缓存数据包含 `audio_duration` 和 `asr_language` 字段。

## 测试

运行测试脚本验证功能：

```bash
# 测试 audio_duration 和 asr_language 字段
python scripts/test_audio_duration_flow.py
```

**预期输出：**
```
✓ Task created with audio_duration and asr_language
✓ audio_duration available at progress=0
✓ asr_language available at progress=0
✓ Frontend can calculate ETA from the start
✓ Frontend can display language labels (中文 / 英文)
```

## 向后兼容性

- `audio_duration` 和 `asr_language` 字段为可选（`Optional`）
- 旧任务可能没有 `audio_duration`，前端应处理 `null` 情况
- 所有任务都有 `asr_language`（默认值：`"zh-CN+en-US"`）

## 相关文档

- [Audio Duration Field Guide](./AUDIO_DURATION_FIELD_GUIDE.md)
- [Frontend Development Guide](./FRONTEND_DEVELOPMENT_GUIDE.md)
- [API Quick Reference](./API_QUICK_REFERENCE.md)
