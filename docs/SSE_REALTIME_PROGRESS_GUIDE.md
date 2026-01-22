# SSE 实时进度推送指南

## 概述

使用 Server-Sent Events (SSE) 实现任务进度的实时推送，替代传统的轮询方式。

## 为什么使用 SSE？

### 轮询的问题
- **延迟高**: 2 秒轮询间隔可能错过快速变化的状态
- **资源浪费**: 即使没有更新也要发送请求
- **服务器压力**: 大量客户端同时轮询

### SSE 的优势
- **实时性**: 状态变化立即推送，延迟 < 1 秒
- **高效**: 只在状态变化时推送数据
- **简单**: 比 WebSocket 更简单，单向推送足够
- **自动重连**: 浏览器原生支持断线重连

## 后端实现

### API 端点

```
GET /api/v1/sse/tasks/{task_id}/progress
```

**认证**: Bearer Token (JWT)

**响应格式**: `text/event-stream`

### 事件类型

1. **progress** - 进度更新
```json
{
  "task_id": "task_abc123",
  "state": "transcribing",
  "progress": 40.0,
  "estimated_time": 71,
  "updated_at": "2026-01-22T11:08:09.588379"
}
```

2. **complete** - 任务完成
```json
{
  "state": "success"
}
```

3. **error** - 错误
```json
{
  "error": "Task not found"
}
```

4. **timeout** - 超时（10 分钟）
```json
{
  "message": "Stream timeout"
}
```

### 工作原理

1. 客户端连接 SSE 端点
2. 后端验证任务权限
3. 发送初始状态
4. 每秒检查数据库状态
5. 状态变化时立即推送
6. 任务完成后关闭连接

## 前端集成

### 基础用法

```javascript
// 创建 SSE 连接
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/sse/tasks/${taskId}/progress`,
  {
    // 注意：EventSource 不支持自定义 headers
    // 需要通过 URL 参数传递 token 或使用 polyfill
  }
);

// 监听进度更新
eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.state, data.progress);
  
  // 更新 UI
  updateProgressBar(data.progress);
  updateStatusText(data.state);
  updateEstimatedTime(data.estimated_time);
});

// 监听完成事件
eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('Task completed:', data.state);
  
  // 关闭连接
  eventSource.close();
  
  // 刷新任务详情
  fetchTaskDetails(taskId);
});

// 监听错误
eventSource.addEventListener('error', (event) => {
  console.error('SSE error:', event);
  eventSource.close();
});
```

### 带认证的 SSE（使用 fetch polyfill）

由于原生 EventSource 不支持自定义 headers，需要使用 polyfill：

```bash
npm install event-source-polyfill
```

```javascript
import { EventSourcePolyfill } from 'event-source-polyfill';

const eventSource = new EventSourcePolyfill(
  `http://localhost:8000/api/v1/sse/tasks/${taskId}/progress`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

// 其他代码同上
```

### React Hook 示例

```typescript
import { useEffect, useState } from 'react';
import { EventSourcePolyfill } from 'event-source-polyfill';

interface TaskProgress {
  task_id: string;
  state: string;
  progress: number;
  estimated_time: number | null;
  updated_at: string;
}

export function useTaskProgress(taskId: string, token: string) {
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId || !token) return;

    const eventSource = new EventSourcePolyfill(
      `http://localhost:8000/api/v1/sse/tasks/${taskId}/progress`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    eventSource.addEventListener('progress', (event: any) => {
      const data = JSON.parse(event.data);
      setProgress(data);
    });

    eventSource.addEventListener('complete', (event: any) => {
      const data = JSON.parse(event.data);
      setIsComplete(true);
      eventSource.close();
    });

    eventSource.addEventListener('error', (event: any) => {
      setError('Connection error');
      eventSource.close();
    });

    // 清理函数
    return () => {
      eventSource.close();
    };
  }, [taskId, token]);

  return { progress, isComplete, error };
}

// 使用示例
function TaskProgressView({ taskId }: { taskId: string }) {
  const token = getAuthToken();
  const { progress, isComplete, error } = useTaskProgress(taskId, token);

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!progress) {
    return <div>Connecting...</div>;
  }

  return (
    <div>
      <h3>Task Progress</h3>
      <p>State: {progress.state}</p>
      <p>Progress: {progress.progress}%</p>
      <p>Estimated Time: {progress.estimated_time}s</p>
      {isComplete && <p>✓ Task completed!</p>}
    </div>
  );
}
```

## 对比：轮询 vs SSE

| 特性 | 轮询 | SSE |
|------|------|-----|
| 实时性 | 2 秒延迟 | < 1 秒延迟 |
| 资源消耗 | 高（持续请求） | 低（单连接） |
| 服务器压力 | 高 | 低 |
| 实现复杂度 | 简单 | 中等 |
| 浏览器支持 | 100% | 95%+ |
| 断线重连 | 需手动实现 | 自动 |
| 错过状态 | 可能（快速变化） | 不会 |

## 测试

### 后端测试

```bash
# 创建一个新任务
python scripts/create_test_task.py

# 使用 SSE 监控进度
python scripts/test_sse.py task_abc123
```

### 前端测试

```bash
# 使用 curl 测试 SSE
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/sse/tasks/task_abc123/progress
```

## 生产环境注意事项

### Nginx 配置

SSE 需要禁用缓冲：

```nginx
location /api/v1/sse/ {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

### 负载均衡

SSE 是长连接，需要：
- 使用 sticky session（会话保持）
- 或使用 Redis Pub/Sub 在多个后端实例间同步状态

### 超时设置

- 后端超时：10 分钟（可配置）
- Nginx 超时：建议 15 分钟
- 客户端重连：浏览器自动处理

## 迁移指南

### 从轮询迁移到 SSE

1. **保留轮询作为降级方案**
```javascript
function useTaskProgress(taskId, token) {
  const [useSSE, setUseSSE] = useState(true);
  
  // 尝试 SSE
  if (useSSE) {
    try {
      return useSSEProgress(taskId, token);
    } catch (error) {
      console.warn('SSE failed, falling back to polling');
      setUseSSE(false);
    }
  }
  
  // 降级到轮询
  return usePollingProgress(taskId, token);
}
```

2. **渐进式部署**
- 先在开发环境测试
- 小范围灰度发布
- 监控错误率和性能
- 全量发布

3. **监控指标**
- SSE 连接数
- 平均连接时长
- 错误率
- 推送延迟

## 常见问题

### Q: SSE 连接断开怎么办？
A: 浏览器会自动重连，无需手动处理。

### Q: 如何处理多个任务？
A: 为每个任务创建独立的 SSE 连接。

### Q: SSE 支持双向通信吗？
A: 不支持，只能服务器推送。如需双向通信，使用 WebSocket。

### Q: 移动端支持吗？
A: iOS Safari 和 Android Chrome 都支持 SSE。

### Q: 如何调试 SSE？
A: Chrome DevTools → Network → EventStream 类型。

## 总结

SSE 提供了比轮询更好的实时性和效率，适合任务进度推送场景。建议：

- ✅ 使用 SSE 作为主要方案
- ✅ 保留轮询作为降级方案
- ✅ 监控 SSE 连接质量
- ✅ 配置合理的超时时间
