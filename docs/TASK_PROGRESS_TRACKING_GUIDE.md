# 任务进度追踪完整指南

> **重要更新**: 现在支持 SSE 实时推送！详见 [SSE 实时进度推送指南](./SSE_REALTIME_PROGRESS_GUIDE.md)

## 两种方案对比

| 特性 | 轮询 | SSE 实时推送 |
|------|------|-------------|
| 实时性 | 2 秒延迟 | < 1 秒延迟 |
| 资源消耗 | 高 | 低 |
| 实现复杂度 | 简单 | 中等 |
| 错过状态 | 可能 | 不会 |
| 推荐场景 | 简单应用 | 生产环境 |

**推荐**: 生产环境使用 SSE，开发环境可用轮询。

---

# 任务进度追踪完整指南（轮询方式）

## 概述

本文档详细说明后端如何实现任务进度追踪，以及前端如何正确集成和显示实时进度。

---

## 后端实现

### 1. 数据库字段

任务表 (`tasks`) 包含以下进度相关字段：

```python
class Task(Base):
    task_id: str              # 任务 ID
    state: str                # 任务状态
    progress: float           # 进度百分比 (0.0-100.0)
    estimated_time: int       # 预估剩余时间（秒）
    audio_duration: float     # 音频总时长（秒）
    updated_at: datetime      # 最后更新时间
    error_details: str        # 错误详情（如果失败）
```

### 2. 任务状态枚举

```python
class TaskState(str, Enum):
    PENDING = "pending"           # 待处理（在队列中）
    RUNNING = "running"           # 运行中（Worker 已接收）
    TRANSCRIBING = "transcribing" # 转写中
    IDENTIFYING = "identifying"   # 说话人识别中
    CORRECTING = "correcting"     # 修正中
    SUMMARIZING = "summarizing"   # 生成摘要中
    SUCCESS = "success"           # 成功
    FAILED = "failed"             # 失败
    PARTIAL_SUCCESS = "partial_success"  # 部分成功
```

### 3. 进度更新机制

#### 3.1 更新时机（跳跃式）

Pipeline 在关键节点更新进度，**不是连续的**：

| 阶段 | State | Progress | 说明 |
|------|-------|----------|------|
| 转写开始 | `transcribing` | 0% | 刚开始处理 |
| 转写完成 | `transcribing` | 40% | ASR 完成 |
| 识别开始 | `identifying` | 40% | 开始声纹识别 |
| 识别完成 | `identifying` | 60% | 声纹识别完成 |
| 修正开始 | `correcting` | 60% | 开始修正转写 |
| 修正完成 | `correcting` | 70% | 修正完成 |
| 生成开始 | `summarizing` | 70% | 开始 LLM 生成 |
| 任务完成 | `success` | 100% | 全部完成 |
| 任务失败 | `failed` | 0% | 处理失败 |

**注意**：如果跳过说话人识别，进度会从 40% 直接跳到 60%。

#### 3.2 预估时间计算

使用 **25% 规则**：

```python
# 总耗时 = 音频时长 × 0.25
total_time = audio_duration * 0.25

# 剩余时间 = 总耗时 × (1 - 进度百分比)
estimated_time = int(total_time * (1 - progress / 100.0))

# 特殊情况
if progress >= 100.0:
    estimated_time = 0  # 任务完成，剩余时间为 0
```

**示例**：
- 音频时长：480 秒（8 分钟）
- 预计总耗时：480 × 0.25 = 120 秒（2 分钟）
- 进度 40% 时：剩余 72 秒
- 进度 60% 时：剩余 48 秒
- 进度 70% 时：剩余 36 秒
- 进度 100% 时：剩余 0 秒

#### 3.3 更新代码位置

在 `src/services/pipeline.py` 的 `process_meeting` 方法中：

```python
def _update_task_status(
    self,
    task_id: str,
    state: TaskState,
    progress: float = 0.0,
    audio_duration: Optional[float] = None,
    error_details: Optional[str] = None,
) -> None:
    """更新任务状态到数据库"""
    if self.tasks is None:
        return
    
    # 计算预估剩余时间
    estimated_time = None
    if audio_duration:
        if progress >= 100.0:
            estimated_time = 0
        else:
            total_estimated_time = audio_duration * 0.25
            estimated_time = int(total_estimated_time * (1 - progress / 100.0))
    
    # 更新数据库
    self.tasks.update_status(
        task_id=task_id,
        state=state,
        progress=progress,
        estimated_time=estimated_time,
        error_details=error_details,
        updated_at=datetime.now(),
    )
```

### 4. API 端点

#### 4.1 查询任务状态

```
GET /api/v1/tasks/{task_id}/status
```

**请求头**：
```
Authorization: Bearer <JWT_TOKEN>
```

**响应**：
```json
{
  "task_id": "task_abc123",
  "state": "transcribing",
  "progress": 40.0,
  "estimated_time": 72,
  "error_details": null,
  "updated_at": "2026-01-22T10:30:45.123456"
}
```

**字段说明**：
- `state`: 当前状态（见状态枚举）
- `progress`: 进度百分比（0.0-100.0）
- `estimated_time`: 预估剩余时间（秒），`null` 表示未知，`0` 表示已完成
- `error_details`: 错误信息（仅在 `failed` 状态时有值）
- `updated_at`: 最后更新时间（ISO 8601 格式）

#### 4.2 缓存机制

API 使用 **Cache-Aside 模式**优化性能：

1. **读取流程**：
   - 先查 Redis 缓存（key: `task_status:{task_id}`）
   - 缓存命中：直接返回
   - 缓存未命中：查数据库 → 回填缓存（TTL 60秒）

2. **写入流程**：
   - Pipeline 更新数据库
   - 不主动更新缓存（让缓存自然过期）

3. **缓存失效**：
   - TTL 60 秒自动过期
   - 确保最多 60 秒延迟

---

## 前端集成

### 1. 轮询策略

#### 1.1 推荐方案：定时轮询

```typescript
interface TaskStatus {
  task_id: string;
  state: string;
  progress: number;
  estimated_time: number | null;
  error_details: string | null;
  updated_at: string;
}

class TaskProgressTracker {
  private taskId: string;
  private intervalId: number | null = null;
  private onUpdate: (status: TaskStatus) => void;
  
  constructor(taskId: string, onUpdate: (status: TaskStatus) => void) {
    this.taskId = taskId;
    this.onUpdate = onUpdate;
  }
  
  start() {
    // 立即查询一次
    this.fetchStatus();
    
    // 每 2 秒轮询一次
    this.intervalId = setInterval(() => {
      this.fetchStatus();
    }, 2000);
  }
  
  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
  
  private async fetchStatus() {
    try {
      const response = await fetch(
        `/api/v1/tasks/${this.taskId}/status`,
        {
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Cache-Control': 'no-cache',  // 禁用浏览器缓存
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const status: TaskStatus = await response.json();
      this.onUpdate(status);
      
      // 如果任务完成或失败，停止轮询
      if (status.state === 'success' || status.state === 'failed') {
        this.stop();
      }
    } catch (error) {
      console.error('Failed to fetch task status:', error);
    }
  }
}

// 使用示例
const tracker = new TaskProgressTracker('task_abc123', (status) => {
  console.log('Progress:', status.progress);
  console.log('Estimated time:', status.estimated_time);
  updateUI(status);
});

tracker.start();

// 组件卸载时停止
onUnmount(() => {
  tracker.stop();
});
```

#### 1.2 轮询频率建议

| 场景 | 频率 | 说明 |
|------|------|------|
| 正常轮询 | 2 秒 | 平衡实时性和服务器负载 |
| 快速更新 | 1 秒 | 用户主动查看进度时 |
| 后台轮询 | 5 秒 | 标签页不可见时 |

### 2. UI 显示

#### 2.1 进度条

由于后端进度是跳跃式的，前端需要平滑过渡：

```typescript
interface ProgressState {
  current: number;    // 当前显示的进度
  target: number;     // 目标进度（后端返回）
  animating: boolean; // 是否正在动画
}

class SmoothProgressBar {
  private state: ProgressState = {
    current: 0,
    target: 0,
    animating: false,
  };
  
  updateTarget(newTarget: number) {
    this.state.target = newTarget;
    
    if (!this.state.animating) {
      this.animate();
    }
  }
  
  private animate() {
    this.state.animating = true;
    
    const step = () => {
      const diff = this.state.target - this.state.current;
      
      if (Math.abs(diff) < 0.1) {
        // 到达目标
        this.state.current = this.state.target;
        this.state.animating = false;
        this.render();
        return;
      }
      
      // 平滑移动（每帧移动 10% 的差距）
      this.state.current += diff * 0.1;
      this.render();
      
      requestAnimationFrame(step);
    };
    
    requestAnimationFrame(step);
  }
  
  private render() {
    // 更新 UI
    const progressBar = document.getElementById('progress-bar');
    if (progressBar) {
      progressBar.style.width = `${this.state.current}%`;
    }
  }
}
```

**CSS 方案（更简单）**：

```css
.progress-bar {
  width: 0%;
  height: 4px;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.5s ease-out;  /* 平滑过渡 */
}
```

```typescript
// 直接更新，CSS 自动平滑过渡
function updateProgress(progress: number) {
  const bar = document.querySelector('.progress-bar') as HTMLElement;
  bar.style.width = `${progress}%`;
}
```

#### 2.2 预估时间显示

```typescript
function formatEstimatedTime(seconds: number | null): string {
  if (seconds === null) {
    return '--:--';  // 未知
  }
  
  if (seconds === 0) {
    return '完成';
  }
  
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  
  if (minutes > 0) {
    return `${minutes}分${secs}秒`;
  } else {
    return `${secs}秒`;
  }
}

// 使用
console.log(formatEstimatedTime(125));  // "2分5秒"
console.log(formatEstimatedTime(45));   // "45秒"
console.log(formatEstimatedTime(0));    // "完成"
console.log(formatEstimatedTime(null)); // "--:--"
```

#### 2.3 状态文本映射

```typescript
const STATE_TEXT: Record<string, string> = {
  'pending': '等待处理',
  'running': '准备中',
  'transcribing': '转写中',
  'identifying': '识别说话人',
  'correcting': '修正中',
  'summarizing': '生成摘要',
  'success': '完成',
  'failed': '失败',
  'partial_success': '部分完成',
};

function getStateText(state: string): string {
  return STATE_TEXT[state] || '未知状态';
}
```

### 3. 完整示例（React）

```typescript
import { useEffect, useState } from 'react';

interface TaskStatus {
  task_id: string;
  state: string;
  progress: number;
  estimated_time: number | null;
  error_details: string | null;
  updated_at: string;
}

export function TaskProgressView({ taskId }: { taskId: string }) {
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    let intervalId: number;
    
    const fetchStatus = async () => {
      try {
        const response = await fetch(`/api/v1/tasks/${taskId}/status`, {
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Cache-Control': 'no-cache',
          },
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data: TaskStatus = await response.json();
        setStatus(data);
        setError(null);
        
        // 任务完成或失败，停止轮询
        if (data.state === 'success' || data.state === 'failed') {
          clearInterval(intervalId);
        }
      } catch (err) {
        setError(err.message);
      }
    };
    
    // 立即查询
    fetchStatus();
    
    // 每 2 秒轮询
    intervalId = setInterval(fetchStatus, 2000);
    
    // 清理
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [taskId]);
  
  if (error) {
    return <div className="error">加载失败: {error}</div>;
  }
  
  if (!status) {
    return <div className="loading">加载中...</div>;
  }
  
  return (
    <div className="task-progress">
      <div className="status-text">
        {getStateText(status.state)}
      </div>
      
      <div className="progress-container">
        <div 
          className="progress-bar" 
          style={{ width: `${status.progress}%` }}
        />
      </div>
      
      <div className="progress-info">
        <span>{status.progress.toFixed(1)}%</span>
        <span>
          {status.estimated_time !== null && status.estimated_time > 0
            ? `剩余 ${formatEstimatedTime(status.estimated_time)}`
            : status.state === 'success'
            ? '已完成'
            : ''}
        </span>
      </div>
      
      {status.error_details && (
        <div className="error-details">
          错误: {status.error_details}
        </div>
      )}
    </div>
  );
}
```

### 4. 性能优化建议

#### 4.1 避免重复请求

```typescript
class RequestThrottler {
  private pending: Map<string, Promise<any>> = new Map();
  
  async fetch<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
    // 如果已有相同请求在进行中，复用
    if (this.pending.has(key)) {
      return this.pending.get(key)!;
    }
    
    const promise = fetcher().finally(() => {
      this.pending.delete(key);
    });
    
    this.pending.set(key, promise);
    return promise;
  }
}

const throttler = new RequestThrottler();

// 使用
const status = await throttler.fetch(
  `task_status:${taskId}`,
  () => fetchTaskStatus(taskId)
);
```

#### 4.2 标签页可见性检测

```typescript
function useVisibilityAwarePolling(
  callback: () => void,
  visibleInterval: number = 2000,
  hiddenInterval: number = 5000
) {
  useEffect(() => {
    let intervalId: number;
    
    const startPolling = () => {
      const interval = document.hidden ? hiddenInterval : visibleInterval;
      
      if (intervalId) {
        clearInterval(intervalId);
      }
      
      callback();
      intervalId = setInterval(callback, interval);
    };
    
    startPolling();
    
    // 监听可见性变化
    document.addEventListener('visibilitychange', startPolling);
    
    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', startPolling);
    };
  }, [callback, visibleInterval, hiddenInterval]);
}
```

---

## 常见问题

### Q1: 为什么进度不是连续的？

**A**: 后端采用跳跃式更新，只在关键节点更新进度（0% → 40% → 60% → 70% → 100%）。这样设计的原因：
- 减少数据库写入次数
- 避免频繁更新缓存
- 降低系统负载

前端应使用 CSS transition 或 JavaScript 动画实现平滑过渡。

### Q2: 为什么 estimated_time 有时是 null？

**A**: 在转写完成前（progress < 40%），后端还不知道音频时长，无法计算预估时间。此时 `estimated_time` 为 `null`。

### Q3: 任务完成后 estimated_time 应该是多少？

**A**: 应该是 `0`（不是 `null`）。如果看到其他值，说明后端有 bug。

### Q4: 轮询会不会造成服务器压力？

**A**: 不会。后端使用了 Redis 缓存（TTL 60秒），大部分请求直接从缓存返回，不会查询数据库。

### Q5: 可以用 WebSocket 代替轮询吗？

**A**: 可以，但当前版本使用轮询更简单。未来可以考虑：
- Server-Sent Events (SSE)
- WebSocket
- Long Polling

---

## 测试工具

### 后端测试

```bash
# 检查任务进度
python scripts/check_task_progress.py

# 实时监控任务
python scripts/test_progress_tracking.py <task_id>

# 创建任务并监控
python scripts/create_and_monitor_task.py
```

### 前端测试

```bash
# 使用 curl 测试 API
curl -H "Authorization: Bearer <token>" \
     -H "Cache-Control: no-cache" \
     http://localhost:8000/api/v1/tasks/<task_id>/status
```

---

## 相关文件

- `src/services/pipeline.py` - 进度更新逻辑
- `src/api/routes/tasks.py` - API 端点实现
- `src/database/models.py` - 数据库模型
- `src/database/repositories.py` - 数据访问层
- `docs/FRONTEND_PROGRESS_GUIDE.md` - 前端集成指南（旧版）
- `docs/REALTIME_PROGRESS_FRONTEND_GUIDE.md` - 实时进度指南（旧版）
