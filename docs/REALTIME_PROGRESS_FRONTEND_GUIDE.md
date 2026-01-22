# 实时进度和预估时间 - 前端集成指南

## 概述

后端现在提供完整的实时进度跟踪和预估时间功能。本文档说明前端如何集成这些功能。

## API 响应字段

### GET /api/tasks/{task_id}/status

**响应示例：**
```json
{
  "task_id": "task_abc123",
  "state": "transcribing",
  "progress": 25.0,
  "estimated_time": 90,
  "error_details": null,
  "updated_at": "2026-01-22T10:30:45"
}
```

**字段说明：**

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `task_id` | string | 任务 ID | "task_abc123" |
| `state` | string | 当前阶段 | "transcribing" |
| `progress` | float | 进度百分比 (0-100) | 25.0 |
| `estimated_time` | int \| null | 预估剩余时间（秒） | 90 |
| `error_details` | string \| null | 错误信息 | null |
| `updated_at` | datetime | 最后更新时间 | "2026-01-22T10:30:45" |

### GET /api/tasks/{task_id}

**响应示例：**
```json
{
  "task_id": "task_abc123",
  "state": "transcribing",
  "progress": 25.0,
  "duration": 600.0,
  "estimated_time": 90,
  // ... 其他字段
}
```

**新增字段：**
- `duration`: 音频总时长（秒），转写完成后可用

## 任务状态（state）

| 状态值 | 中文名称 | 进度范围 | 说明 |
|--------|----------|----------|------|
| `pending` | 待处理 | 0% | 任务已创建，等待处理 |
| `queued` | 排队中 | 0% | 任务在队列中等待 |
| `running` | 运行中 | 0% | 任务开始处理 |
| `transcribing` | 转写中 | 0-40% | 音频转文字 |
| `identifying` | 识别说话人 | 40-60% | 识别不同说话人（可选） |
| `correcting` | 修正中 | 60-70% | 修正说话人标签 |
| `summarizing` | 生成纪要 | 70-100% | 生成会议纪要 |
| `success` | 完成 | 100% | 任务成功完成 |
| `failed` | 失败 | - | 任务失败 |

## 进度阶段详解

### 1. 转写阶段 (0% → 40%)

```
0%  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 40%
    转写开始                          转写完成
```

- 开始时：`progress = 0%`, `estimated_time = audio_duration * 0.25`
- 完成时：`progress = 40%`, `estimated_time = audio_duration * 0.15`
- 此阶段完成后，`duration` 字段可用

### 2. 说话人识别阶段 (40% → 60%)

```
40% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 60%
    识别开始                          识别完成
```

- 开始时：`progress = 40%`
- 完成时：`progress = 60%`
- 如果跳过此阶段，进度直接从 40% 跳到 60%

### 3. 修正阶段 (60% → 70%)

```
60% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 70%
    修正开始                          修正完成
```

- 仅在有说话人映射时执行
- 如果没有说话人映射，跳过此阶段

### 4. 生成纪要阶段 (70% → 100%)

```
70% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
    生成开始                          生成完成
```

- 开始时：`progress = 70%`
- 完成时：`progress = 100%`, `state = "success"`

## 前端实现示例

### 1. React 组件示例

```typescript
import { useState, useEffect } from 'react';

interface TaskStatus {
  task_id: string;
  state: string;
  progress: number;
  estimated_time: number | null;
  error_details: string | null;
  updated_at: string;
}

function TaskProgressTracker({ taskId }: { taskId: string }) {
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    if (!isPolling) return;

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/tasks/${taskId}/status`, {
          headers: {
            'Authorization': `Bearer ${getToken()}`,
          },
        });
        
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data: TaskStatus = await response.json();
        setStatus(data);

        // 停止轮询条件
        if (data.state === 'success' || data.state === 'failed') {
          setIsPolling(false);
        }
      } catch (error) {
        console.error('Error polling task status:', error);
      }
    };

    // 立即执行一次
    pollStatus();

    // 每 2 秒轮询一次
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [taskId, isPolling]);

  if (!status) {
    return <div>加载中...</div>;
  }

  return (
    <div className="task-progress">
      {/* 进度条 */}
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${status.progress}%` }}
        />
      </div>
      
      {/* 进度百分比 */}
      <div className="progress-text">
        {status.progress.toFixed(1)}%
      </div>
      
      {/* 当前阶段 */}
      <div className="stage-text">
        {getStageLabel(status.state)}
      </div>
      
      {/* 预估时间 */}
      {status.estimated_time && (
        <div className="estimated-time">
          预计剩余时间: {formatTime(status.estimated_time)}
        </div>
      )}
      
      {/* 错误信息 */}
      {status.error_details && (
        <div className="error-message">
          错误: {status.error_details}
        </div>
      )}
    </div>
  );
}

// 阶段标签映射
function getStageLabel(state: string): string {
  const labels: Record<string, string> = {
    'pending': '待处理',
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

// 时间格式化
function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}分${remainingSeconds}秒`;
}
```

### 2. Vue 组件示例

```vue
<template>
  <div class="task-progress" v-if="status">
    <!-- 进度条 -->
    <div class="progress-bar">
      <div 
        class="progress-fill" 
        :style="{ width: `${status.progress}%` }"
      />
    </div>
    
    <!-- 进度百分比 -->
    <div class="progress-text">
      {{ status.progress.toFixed(1) }}%
    </div>
    
    <!-- 当前阶段 -->
    <div class="stage-text">
      {{ getStageLabel(status.state) }}
    </div>
    
    <!-- 预估时间 -->
    <div v-if="status.estimated_time" class="estimated-time">
      预计剩余时间: {{ formatTime(status.estimated_time) }}
    </div>
    
    <!-- 错误信息 -->
    <div v-if="status.error_details" class="error-message">
      错误: {{ status.error_details }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

interface TaskStatus {
  task_id: string;
  state: string;
  progress: number;
  estimated_time: number | null;
  error_details: string | null;
  updated_at: string;
}

const props = defineProps<{
  taskId: string;
}>();

const status = ref<TaskStatus | null>(null);
let pollInterval: number | null = null;

const pollStatus = async () => {
  try {
    const response = await fetch(`/api/tasks/${props.taskId}/status`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
    });
    
    if (!response.ok) throw new Error('Failed to fetch status');
    
    const data: TaskStatus = await response.json();
    status.value = data;

    // 停止轮询
    if (data.state === 'success' || data.state === 'failed') {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    }
  } catch (error) {
    console.error('Error polling task status:', error);
  }
};

onMounted(() => {
  pollStatus();
  pollInterval = setInterval(pollStatus, 2000);
});

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval);
  }
});

function getStageLabel(state: string): string {
  const labels: Record<string, string> = {
    'pending': '待处理',
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

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}分${remainingSeconds}秒`;
}
</script>
```

### 3. 样式示例

```css
.task-progress {
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fff;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 24px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.stage-text {
  font-size: 16px;
  color: #666;
  margin-bottom: 8px;
}

.estimated-time {
  font-size: 14px;
  color: #999;
}

.error-message {
  color: #f44336;
  font-size: 14px;
  margin-top: 12px;
  padding: 8px;
  background: #ffebee;
  border-radius: 4px;
}
```

## 最佳实践

### 1. 轮询间隔

- **推荐间隔**：2 秒
- **原因**：平衡实时性和服务器负载
- **优化**：可根据任务状态动态调整
  - 转写中：2 秒
  - 生成纪要：3 秒
  - 完成/失败：停止轮询

### 2. 错误处理

```typescript
const pollStatus = async () => {
  try {
    const response = await fetch(`/api/tasks/${taskId}/status`);
    
    if (response.status === 404) {
      // 任务不存在
      setError('任务不存在');
      setIsPolling(false);
      return;
    }
    
    if (response.status === 403) {
      // 无权访问
      setError('无权访问此任务');
      setIsPolling(false);
      return;
    }
    
    if (!response.ok) {
      throw new Error('Failed to fetch status');
    }
    
    const data = await response.json();
    setStatus(data);
    
  } catch (error) {
    console.error('Error polling task status:', error);
    // 继续轮询，不中断
  }
};
```

### 3. 性能优化

```typescript
// 使用 React Query 或 SWR 进行数据缓存和自动重试
import { useQuery } from '@tanstack/react-query';

function useTaskStatus(taskId: string) {
  return useQuery({
    queryKey: ['taskStatus', taskId],
    queryFn: () => fetchTaskStatus(taskId),
    refetchInterval: (data) => {
      // 根据状态动态调整轮询间隔
      if (!data) return 2000;
      if (data.state === 'success' || data.state === 'failed') {
        return false; // 停止轮询
      }
      return 2000;
    },
  });
}
```

### 4. 用户体验优化

```typescript
// 显示更友好的进度信息
function getProgressMessage(state: string, progress: number): string {
  if (progress === 0) return '准备开始...';
  if (progress < 40) return '正在转写音频...';
  if (progress < 60) return '正在识别说话人...';
  if (progress < 70) return '正在修正内容...';
  if (progress < 100) return '正在生成会议纪要...';
  return '处理完成！';
}

// 显示进度动画
<div className="progress-message">
  {getProgressMessage(status.state, status.progress)}
  {status.progress < 100 && <LoadingSpinner />}
</div>
```

## 常见问题

### Q1: 为什么 estimated_time 是 null？

**A:** 在转写完成之前，后端还不知道音频时长，无法计算预估时间。转写完成后（progress >= 40%）会开始提供预估时间。

### Q2: 进度会倒退吗？

**A:** 不会。进度只会递增，即使某个阶段失败，进度也会保持在当前值。

### Q3: 如何处理跳过的阶段？

**A:** 如果跳过说话人识别，进度会直接从 40% 跳到 60%。前端应该平滑过渡，不要显示跳跃。

### Q4: 预估时间准确吗？

**A:** 预估时间基于 25% 规则（总耗时 = 音频时长 × 0.25），是经验值，实际可能有 ±20% 的偏差。

### Q5: 如何优化轮询性能？

**A:** 
1. 使用 HTTP 缓存头（后端已设置 60 秒 TTL）
2. 根据任务状态动态调整轮询间隔
3. 使用 WebSocket 替代轮询（未来优化）

## 相关文档

- [API 快速参考](./API_QUICK_REFERENCE.md)
- [前端开发指南](./FRONTEND_DEVELOPMENT_GUIDE.md)
- [实时进度实现详解](./summaries/REALTIME_PROGRESS_IMPLEMENTATION.md)

## 更新日志

- 2026-01-22: 初始版本，实现实时进度和预估时间功能
