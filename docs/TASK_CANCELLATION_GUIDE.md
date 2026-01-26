# 任务取消功能集成指南

## 概述

本文档说明如何在前端实现真正的任务取消功能，而不仅仅是停止轮询。

## 后端 API

### 取消任务

**端点**: `POST /api/v1/tasks/{task_id}/cancel`

**认证**: 需要 JWT Token

**权限**: 只能取消自己的任务

**可取消的状态**:
- `queued`: 队列中等待
- `running`: 正在执行
- `transcribing`: 转写中
- `identifying`: 识别中
- `correcting`: 校正中
- `summarizing`: 总结中

**不可取消的状态**:
- `success`: 已完成
- `failed`: 已失败
- `cancelled`: 已取消
- `confirmed`: 已确认
- `archived`: 已归档

### 请求示例

```typescript
const cancelTask = async (taskId: string) => {
  const response = await fetch(`/api/v1/tasks/${taskId}/cancel`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
};
```

### 响应示例

**成功 (200)**:
```json
{
  "success": true,
  "message": "Task cancelled successfully",
  "task_id": "task_abc123",
  "previous_state": "transcribing"
}
```

**失败 (400)** - 任务状态不允许取消:
```json
{
  "detail": "Task in state 'success' cannot be cancelled"
}
```

**失败 (403)** - 无权限:
```json
{
  "detail": "You don't have permission to access this task"
}
```

**失败 (404)** - 任务不存在:
```json
{
  "detail": "Task not found"
}
```

## 前端实现

### 1. 更新任务状态类型

```typescript
// types.ts
export type TaskState = 
  | 'pending'
  | 'queued'
  | 'running'
  | 'transcribing'
  | 'identifying'
  | 'correcting'
  | 'summarizing'
  | 'success'
  | 'failed'
  | 'partial_success'
  | 'confirmed'
  | 'archived'
  | 'cancelled';  // 新增

export interface TaskStatus {
  task_id: string;
  state: TaskState;
  progress: number;
  estimated_time: number | null;
  error_code: string | null;
  error_message: string | null;
  retryable: boolean;
  audio_duration: number | null;
  asr_language: string | null;
}
```

### 2. 实现取消逻辑

```typescript
// taskService.ts
export class TaskService {
  private baseUrl = '/api/v1';
  
  /**
   * 取消任务
   */
  async cancelTask(taskId: string): Promise<{
    success: boolean;
    message: string;
    task_id: string;
    previous_state: string;
  }> {
    const response = await fetch(`${this.baseUrl}/tasks/${taskId}/cancel`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.getToken()}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to cancel task');
    }
    
    return await response.json();
  }
  
  /**
   * 检查任务是否可以取消
   */
  canCancelTask(state: TaskState): boolean {
    const cancellableStates: TaskState[] = [
      'queued',
      'running',
      'transcribing',
      'identifying',
      'correcting',
      'summarizing'
    ];
    
    return cancellableStates.includes(state);
  }
  
  private getToken(): string {
    // 从 localStorage 或其他地方获取 token
    return localStorage.getItem('auth_token') || '';
  }
}
```

### 3. React 组件示例

```typescript
// TaskDetailPage.tsx
import React, { useState } from 'react';
import { TaskService } from './taskService';

interface Props {
  taskId: string;
  taskState: TaskState;
  onTaskCancelled: () => void;
}

export const TaskDetailPage: React.FC<Props> = ({ 
  taskId, 
  taskState, 
  onTaskCancelled 
}) => {
  const [isCancelling, setIsCancelling] = useState(false);
  const taskService = new TaskService();
  
  const handleCancel = async () => {
    if (!confirm('确定要取消这个任务吗？')) {
      return;
    }
    
    setIsCancelling(true);
    
    try {
      const result = await taskService.cancelTask(taskId);
      
      // 显示成功消息
      alert(result.message);
      
      // 停止轮询
      onTaskCancelled();
      
      // 更新 UI 状态
      // 可以触发重新获取任务状态，或直接更新本地状态
      
    } catch (error) {
      console.error('Failed to cancel task:', error);
      alert(`取消失败: ${error.message}`);
    } finally {
      setIsCancelling(false);
    }
  };
  
  // 判断是否显示取消按钮
  const showCancelButton = taskService.canCancelTask(taskState);
  
  return (
    <div>
      {/* 其他内容 */}
      
      {showCancelButton && (
        <button
          onClick={handleCancel}
          disabled={isCancelling}
          className="btn-cancel"
        >
          {isCancelling ? '取消中...' : '取消任务'}
        </button>
      )}
      
      {taskState === 'cancelled' && (
        <div className="alert alert-warning">
          此任务已被取消
        </div>
      )}
    </div>
  );
};
```

### 4. Vue 组件示例

```vue
<!-- TaskDetailPage.vue -->
<template>
  <div>
    <!-- 其他内容 -->
    
    <button
      v-if="canCancel"
      @click="handleCancel"
      :disabled="isCancelling"
      class="btn-cancel"
    >
      {{ isCancelling ? '取消中...' : '取消任务' }}
    </button>
    
    <div v-if="taskState === 'cancelled'" class="alert alert-warning">
      此任务已被取消
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { TaskService } from './taskService';

interface Props {
  taskId: string;
  taskState: TaskState;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'task-cancelled'): void;
}>();

const taskService = new TaskService();
const isCancelling = ref(false);

const canCancel = computed(() => {
  return taskService.canCancelTask(props.taskState);
});

const handleCancel = async () => {
  if (!confirm('确定要取消这个任务吗？')) {
    return;
  }
  
  isCancelling.value = true;
  
  try {
    const result = await taskService.cancelTask(props.taskId);
    
    // 显示成功消息
    alert(result.message);
    
    // 停止轮询
    emit('task-cancelled');
    
  } catch (error) {
    console.error('Failed to cancel task:', error);
    alert(`取消失败: ${error.message}`);
  } finally {
    isCancelling.value = false;
  }
};
</script>
```

## 工作流程

1. **用户点击取消按钮**
   - 前端显示确认对话框
   - 用户确认后，调用 `POST /api/v1/tasks/{task_id}/cancel`

2. **后端处理**
   - 验证任务所有权
   - 检查任务状态是否可取消
   - 在 Redis 中标记任务为取消状态
   - 更新数据库状态为 `cancelled`
   - 清除缓存

3. **Worker 检测取消**
   - Worker 在执行过程中定期检查 Redis
   - 如果发现任务被取消，立即停止执行
   - 更新任务状态为 `cancelled`

4. **前端更新**
   - 停止轮询任务状态
   - 更新 UI 显示任务已取消
   - 禁用相关操作按钮

## 注意事项

1. **取消时机**
   - 取消操作是异步的，Worker 需要时间检测到取消信号
   - 在某些情况下（如正在调用外部 API），可能需要等待当前步骤完成

2. **状态一致性**
   - 取消后，任务状态会变为 `cancelled`
   - 前端应该停止轮询，避免不必要的 API 调用

3. **错误处理**
   - 如果任务已经完成，取消会失败（400 错误）
   - 前端应该优雅地处理这种情况

4. **用户体验**
   - 显示确认对话框，避免误操作
   - 取消过程中显示加载状态
   - 取消成功后给予明确反馈

## 测试

使用提供的测试脚本验证功能：

```bash
python scripts/test_cancel_task.py
```

测试覆盖：
- ✅ 取消正在执行的任务
- ✅ 验证任务状态变为 `cancelled`
- ✅ 尝试取消已完成的任务（应该失败）
- ✅ 验证权限检查

## 相关文件

- `src/api/routes/tasks.py` - 取消任务 API 端点
- `src/queue/worker.py` - Worker 取消检查逻辑
- `src/services/pipeline.py` - Pipeline 取消检查点
- `src/core/models.py` - 添加 `CANCELLED` 状态
- `scripts/test_cancel_task.py` - 测试脚本
