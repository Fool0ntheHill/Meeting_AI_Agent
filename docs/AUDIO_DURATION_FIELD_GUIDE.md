# 音频时长字段说明

## 后端返回的字段信息

### 任务列表接口 (`GET /api/v1/tasks`)

**字段名**: `duration`  
**类型**: `float | null`  
**单位**: **秒** (不是毫秒)  
**说明**: 从转写记录中获取的音频总时长

### 示例响应

```json
{
  "task_id": "task_3f750baa05e2486d",
  "name": "会议录音",
  "state": "success",
  "duration": 479.09,  // ← 479.09 秒 = 7.98 分钟
  "created_at": "2026-01-20T05:31:51.897488",
  ...
}
```

## 前端处理建议

### 1. 字段名

使用 `duration` 字段（**不是** `audio_duration`）

```typescript
// ✅ 正确
const duration = task.duration;

// ❌ 错误
const duration = task.audio_duration;  // 后端不返回这个字段
```

### 2. 单位转换

**不需要除以 1000**，后端返回的单位已经是秒

```typescript
// ✅ 正确 - 直接使用秒
const durationInSeconds = task.duration;
const durationInMinutes = task.duration / 60;

// ❌ 错误 - 不要除以 1000
const durationInSeconds = task.duration / 1000;  // 这会导致时长错误
```

### 3. 空值处理

`duration` 可能为 `null`，需要处理这种情况

```typescript
// ✅ 正确 - 处理 null 值
const duration = task.duration ?? 0;
const displayText = task.duration 
  ? formatDuration(task.duration) 
  : '处理中...';

// 或者使用可选链
const durationText = task.duration 
  ? `${(task.duration / 60).toFixed(1)} 分钟` 
  : '未知';
```

### 4. 完整示例

```typescript
interface Task {
  task_id: string;
  name: string | null;
  state: string;
  duration: number | null;  // 秒，可能为 null
  created_at: string;
  // ... 其他字段
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) {
    return '--:--';
  }
  
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// 使用示例
const TaskList = ({ tasks }: { tasks: Task[] }) => {
  return (
    <div>
      {tasks.map(task => (
        <div key={task.task_id}>
          <span>{task.name ?? '未命名'}</span>
          <span>{formatDuration(task.duration)}</span>
        </div>
      ))}
    </div>
  );
};
```

## 为什么 duration 可能为 null？

`duration` 字段从转写记录中获取，在以下情况下会是 `null`：

1. **任务还未完成转写** - 状态为 `pending`、`running`、`transcribing` 等
2. **任务失败** - 状态为 `failed`，转写未完成
3. **旧任务** - 在修复之前创建的任务，没有保存转写记录

## 后端修复说明

**问题**: 之前 pipeline 没有保存转写记录到数据库，导致所有任务的 `duration` 都是 `null`

**修复**: 
- 在 `PipelineService` 中添加了 `transcript_repo` 参数
- 转写完成后自动保存转写记录到数据库
- 包含 `duration`、`segment_count`、`provider` 等信息

**生效时间**: 修复后创建的新任务会正确返回 `duration`

## 测试验证

可以使用以下脚本测试：

```bash
# 检查任务列表中的 duration 字段
python scripts/check_task_duration.py

# 检查数据库中的转写记录
python scripts/check_transcript_in_db.py
```

## 总结

| 项目 | 值 |
|------|-----|
| 字段名 | `duration` |
| 类型 | `float \| null` |
| 单位 | **秒** |
| 转换 | **不需要** 除以 1000 |
| 空值 | 需要处理 `null` 情况 |
| 格式化 | `formatDuration(seconds)` |

**重要**: 后端返回的是**秒**，不是毫秒！
