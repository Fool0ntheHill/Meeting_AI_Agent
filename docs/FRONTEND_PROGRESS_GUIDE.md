# 前端进度显示集成指南

## 进度更新机制

**后端进度是跳跃式的，不是连续的**

```
时间轴：
0s    → 0%   (转写开始)
30s   → 40%  (转写完成) ← 跳跃
40s   → 60%  (识别完成) ← 跳跃  
50s   → 70%  (修正完成) ← 跳跃
120s  → 100% (全部完成) ← 跳跃
```

**每个阶段内部不会更新进度**，只在阶段切换时跳跃。

## API 端点

```
GET /api/workspaces/{workspace_id}/tasks/{task_id}/status
```

**响应示例：**
```json
{
  "task_id": "task_xxx",
  "state": "transcribing",
  "progress": 40.0,
  "estimated_time": 72,
  "error_details": null,
  "updated_at": "2026-01-22T16:30:00"
}
```

## 前端实现（React 示例）

```typescript
import { useState, useEffect } from 'react';

function TaskProgress({ taskId }: { taskId: string }) {
  const [progress, setProgress] = useState(0);
  const [estimatedTime, setEstimatedTime] = useState<number | null>(null);
  const [state, setState] = useState('pending');

  useEffect(() => {
    // 轮询间隔：2 秒
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `/api/workspaces/default/tasks/${taskId}/status`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Cache-Control': 'no-cache', // 重要！禁用缓存
            },
          }
        );
        
        const data = await response.json();
        
        setProgress(data.progress);
        setEstimatedTime(data.estimated_time);
        setState(data.state);
        
        // 完成或失败时停止轮询
        if (data.state === 'success' || data.state === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    }, 2000); // 每 2 秒轮询一次
    
    return () => clearInterval(interval);
  }, [taskId]);

  return (
    <div>
      <div className="progress-bar">
        <div style={{ width: `${progress}%` }} />
      </div>
      <div>{progress.toFixed(1)}%</div>
      {estimatedTime && (
        <div>预计剩余: {Math.floor(estimatedTime / 60)}分{estimatedTime % 60}秒</div>
      )}
      <div>状态: {state}</div>
    </div>
  );
}
```

## 关键点

### 1. 轮询间隔：2 秒

```typescript
setInterval(pollStatus, 2000); // 推荐
```

- ✅ 2 秒：能捕捉到大部分进度变化
- ⚠️ 5 秒：可能错过快速阶段
- ❌ 10 秒：会错过很多中间状态

### 2. 禁用缓存

```typescript
headers: {
  'Cache-Control': 'no-cache',
  'Pragma': 'no-cache',
}
```

**必须禁用缓存**，否则浏览器会返回旧数据。

### 3. 平滑过渡（可选）

虽然后端是跳跃的，但前端可以做平滑动画：

```typescript
// 使用 CSS transition
.progress-fill {
  transition: width 0.5s ease-out;
}
```

这样从 40% 跳到 60% 时会有平滑动画。

### 4. 停止轮询

```typescript
if (data.state === 'success' || data.state === 'failed') {
  clearInterval(interval);
}
```

任务完成后必须停止轮询，避免浪费资源。

## 状态映射

```typescript
const stateLabels = {
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
```

## 预估时间显示

```typescript
function formatTime(seconds: number): string {
  if (!seconds) return '计算中...';
  
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  
  if (minutes > 0) {
    return `${minutes}分${secs}秒`;
  }
  return `${secs}秒`;
}
```

## 完整示例（Vue）

```vue
<template>
  <div class="task-progress">
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: `${progress}%` }" />
    </div>
    <div class="progress-text">{{ progress.toFixed(1) }}%</div>
    <div class="state-text">{{ stateLabel }}</div>
    <div v-if="estimatedTime" class="time-text">
      预计剩余: {{ formatTime(estimatedTime) }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';

const props = defineProps(['taskId']);

const progress = ref(0);
const estimatedTime = ref(null);
const state = ref('pending');

let pollInterval = null;

const stateLabel = computed(() => {
  const labels = {
    'transcribing': '转写中',
    'identifying': '识别说话人',
    'summarizing': '生成纪要',
    'success': '完成',
  };
  return labels[state.value] || state.value;
});

const formatTime = (seconds) => {
  if (!seconds) return '计算中...';
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return min > 0 ? `${min}分${sec}秒` : `${sec}秒`;
};

const pollStatus = async () => {
  try {
    const response = await fetch(
      `/api/workspaces/default/tasks/${props.taskId}/status`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Cache-Control': 'no-cache',
        },
      }
    );
    
    const data = await response.json();
    progress.value = data.progress;
    estimatedTime.value = data.estimated_time;
    state.value = data.state;
    
    if (data.state === 'success' || data.state === 'failed') {
      clearInterval(pollInterval);
    }
  } catch (error) {
    console.error('Poll failed:', error);
  }
};

onMounted(() => {
  pollStatus(); // 立即执行一次
  pollInterval = setInterval(pollStatus, 2000);
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<style>
.progress-bar {
  width: 100%;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.5s ease-out; /* 平滑过渡 */
}
</style>
```

## 常见问题

### Q: 为什么进度一直不变？

A: 检查：
1. 是否每 2 秒轮询？
2. 是否禁用了缓存？
3. 任务是否真的在处理中？（检查 state）

### Q: 为什么看不到中间进度？

A: 因为后端是跳跃式的。如果任务处理很快（< 10 秒），可能只看到 0% 和 100%。

### Q: 如何让进度看起来更平滑？

A: 使用 CSS transition：
```css
.progress-fill {
  transition: width 0.5s ease-out;
}
```

### Q: estimated_time 为什么是 null？

A: 转写完成前（progress < 40%），后端还不知道音频时长，无法计算预估时间。

## 调试技巧

### 1. 在浏览器控制台查看

```javascript
// 手动轮询测试
setInterval(async () => {
  const res = await fetch('/api/workspaces/default/tasks/task_xxx/status', {
    headers: { 'Authorization': 'Bearer xxx' }
  });
  const data = await res.json();
  console.log(`Progress: ${data.progress}%, State: ${data.state}`);
}, 2000);
```

### 2. 检查网络请求

打开浏览器开发者工具 → Network 标签，确认：
- 请求每 2 秒发送一次
- 响应状态码是 200
- 响应数据中 progress 有变化

### 3. 检查缓存

如果 progress 不变，检查响应头是否有：
```
Cache-Control: no-cache
```

## 总结

✅ **每 2 秒轮询一次**
✅ **禁用缓存**
✅ **完成后停止轮询**
✅ **使用 CSS transition 平滑过渡**
✅ **处理 estimated_time 为 null 的情况**

进度是跳跃式的，这是正常的！前端通过 CSS 动画可以让它看起来平滑。
