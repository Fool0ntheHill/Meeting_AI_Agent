# 实时进度和预估时间功能实现

## 问题描述

前端需要显示任务的实时进度和预估剩余时间，但后端存在以下问题：
1. `progress` 字段一直是 0% 或只在完成时跳到 100%
2. `audio_duration` 未返回，导致前端无法估算时间
3. `estimated_time` 未计算和返回

## 解决方案

### 1. 数据库模型（已有）

`Task` 模型已包含所需字段：
- `state`: 任务状态（queued/running/transcribing/identifying/correcting/summarizing/success/failed）
- `progress`: 进度百分比（0-100）
- `estimated_time`: 预估剩余时间（秒）
- `updated_at`: 状态更新时间

### 2. Pipeline 进度更新

在 `src/services/pipeline.py` 中，为每个处理阶段设置明确的进度百分比：

**进度分配：**
- 转写阶段：0% → 40%
- 说话人识别：40% → 60%（如果启用）
- 修正阶段：60% → 70%（如果有说话人映射）
- 生成衍生内容：70% → 100%

**关键更新点：**
```python
# 1. 转写开始 (0%)
await self._update_task_status(
    task_id, 
    TaskState.TRANSCRIBING, 
    progress=0.0,
    audio_duration=None,
)

# 2. 转写完成 (40%)
audio_duration = transcript.duration
await self._update_task_status(
    task_id,
    TaskState.TRANSCRIBING,
    progress=40.0,
    audio_duration=audio_duration,
)

# 3. 说话人识别开始 (40%)
await self._update_task_status(
    task_id, 
    TaskState.IDENTIFYING, 
    progress=40.0,
    audio_duration=audio_duration,
)

# 4. 说话人识别完成 (60%)
await self._update_task_status(
    task_id,
    TaskState.IDENTIFYING,
    progress=60.0,
    audio_duration=audio_duration,
)

# 5. 修正开始 (60%)
await self._update_task_status(
    task_id, 
    TaskState.CORRECTING, 
    progress=60.0,
    audio_duration=audio_duration,
)

# 6. 修正完成 (70%)
await self._update_task_status(
    task_id,
    TaskState.CORRECTING,
    progress=70.0,
    audio_duration=audio_duration,
)

# 7. 生成衍生内容开始 (70%)
await self._update_task_status(
    task_id, 
    TaskState.SUMMARIZING, 
    progress=70.0,
    audio_duration=audio_duration,
)

# 8. 完成 (100%)
await self._update_task_status(
    task_id, 
    TaskState.SUCCESS, 
    progress=100.0,
    audio_duration=audio_duration,
)
```

### 3. 预估时间计算

在 `_update_task_status` 方法中自动计算预估剩余时间：

```python
async def _update_task_status(
    self,
    task_id: str,
    state: TaskState,
    progress: float = 0.0,
    audio_duration: Optional[float] = None,
    error_details: Optional[str] = None,
) -> None:
    # 计算预估剩余时间
    estimated_time = None
    if audio_duration and progress < 100.0:
        # 使用 25% 规则：总耗时 = 音频时长 * 0.25
        total_estimated_time = audio_duration * 0.25
        # 剩余时间 = 总耗时 * (1 - 进度百分比)
        estimated_time = int(total_estimated_time * (1 - progress / 100.0))
    
    await self.tasks.update_status(
        task_id=task_id,
        state=state,
        progress=progress,
        estimated_time=estimated_time,
        error_details=error_details,
        updated_at=datetime.now(),
    )
```

**计算逻辑：**
- 总耗时 = 音频时长 × 0.25（经验值）
- 剩余时间 = 总耗时 × (1 - 进度百分比 / 100)
- 例如：600秒音频，进度40%
  - 总耗时 = 600 × 0.25 = 150秒
  - 剩余时间 = 150 × (1 - 0.4) = 90秒

### 4. Repository 更新

在 `src/database/repositories.py` 中：

**更新 `update_state` 方法：**
```python
def update_state(
    self,
    task_id: str,
    state: str,
    progress: Optional[float] = None,
    estimated_time: Optional[int] = None,  # 新增
    error_details: Optional[str] = None,
) -> None:
    task = self.get_by_id(task_id)
    if task:
        task.state = state
        if progress is not None:
            task.progress = progress
        if estimated_time is not None:
            task.estimated_time = estimated_time  # 新增
        if error_details is not None:
            task.error_details = error_details
        task.updated_at = datetime.now()
        
        if state in ["success", "failed", "partial_success"]:
            task.completed_at = datetime.now()
        
        self.session.flush()
```

**添加 `update_status` 方法：**
```python
def update_status(
    self,
    task_id: str,
    state,  # TaskState enum
    progress: Optional[float] = None,
    estimated_time: Optional[int] = None,
    error_details: Optional[str] = None,
    updated_at: Optional[datetime] = None,
) -> None:
    """更新任务状态（支持 TaskState enum）"""
    state_str = state.value if hasattr(state, 'value') else str(state)
    self.update_state(
        task_id=task_id,
        state=state_str,
        progress=progress,
        estimated_time=estimated_time,
        error_details=error_details,
    )
```

### 5. API 响应（已有）

`TaskStatusResponse` 和 `TaskDetailResponse` 已包含所需字段：

```python
class TaskStatusResponse(BaseModel):
    task_id: str
    state: TaskState
    progress: float = Field(..., ge=0, le=100, description="进度百分比")
    estimated_time: Optional[int] = Field(None, description="预计剩余时间(秒)")
    error_details: Optional[str] = None
    updated_at: datetime

class TaskDetailResponse(BaseModel):
    # ... 其他字段
    state: TaskState
    progress: float
    duration: Optional[float] = Field(None, description="音频总时长(秒)")
    # ...
```

## 前端集成

### 1. 轮询任务状态

```typescript
// 每 2 秒轮询一次
const pollInterval = setInterval(async () => {
  const response = await fetch(`/api/tasks/${taskId}/status`);
  const data = await response.json();
  
  // 更新进度条
  setProgress(data.progress);
  
  // 显示预估时间
  if (data.estimated_time) {
    setEstimatedTime(formatTime(data.estimated_time));
  }
  
  // 检查是否完成
  if (data.state === 'success' || data.state === 'failed') {
    clearInterval(pollInterval);
  }
}, 2000);
```

### 2. 显示进度

```typescript
// 进度条
<ProgressBar value={progress} max={100} />

// 预估时间
{estimatedTime && (
  <div>预计剩余时间: {estimatedTime}</div>
)}

// 当前阶段
<div>当前阶段: {getStageLabel(state)}</div>
```

### 3. 阶段标签映射

```typescript
function getStageLabel(state: string): string {
  const labels = {
    'queued': '排队中',
    'running': '处理中',
    'transcribing': '转写中',
    'identifying': '识别说话人',
    'correcting': '修正中',
    'summarizing': '生成纪要',
    'success': '完成',
    'failed': '失败',
  };
  return labels[state] || state;
}
```

## 测试验证

### 1. 创建测试脚本

```python
# scripts/test_progress_tracking.py
import asyncio
import time
from src.api.routes.tasks import get_task_status

async def test_progress():
    task_id = "task_xxx"
    
    for i in range(30):  # 轮询 30 次
        status = await get_task_status(task_id)
        print(f"Progress: {status.progress}%, "
              f"State: {status.state}, "
              f"Estimated: {status.estimated_time}s")
        
        if status.state in ['success', 'failed']:
            break
        
        await asyncio.sleep(2)

asyncio.run(test_progress())
```

### 2. 验证点

- ✓ 进度从 0% 开始
- ✓ 转写完成后进度达到 40%
- ✓ 说话人识别完成后进度达到 60%
- ✓ 修正完成后进度达到 70%
- ✓ 最终完成时进度达到 100%
- ✓ `estimated_time` 随进度递减
- ✓ `audio_duration` 在转写完成后可用

## 注意事项

1. **进度更新频率**：每个阶段至少更新 2 次（开始和结束）
2. **预估时间准确性**：25% 规则是经验值，实际可能有偏差
3. **缓存失效**：Redis 缓存 TTL 设为 60 秒，确保进度及时更新
4. **错误处理**：失败时 progress 保持当前值，不回退
5. **跳过阶段**：如果跳过说话人识别，进度直接从 40% 跳到 60%

## 相关文件

- `src/services/pipeline.py` - 进度更新逻辑
- `src/database/repositories.py` - 数据库更新
- `src/database/models.py` - 数据模型
- `src/api/routes/tasks.py` - API 端点
- `src/api/schemas.py` - 响应模型

## 时间

2026-01-22
