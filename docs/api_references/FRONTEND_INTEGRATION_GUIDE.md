# 前端联调指南

**最后更新**: 2026-01-15  
**API 版本**: 1.0.0

---

## 概述

本指南帮助前端开发者快速接入会议纪要 Agent API，包括认证、API 调用、错误处理等完整流程。

---

## 推荐文档

### 主要文档（按优先级）

1. **Swagger UI** (推荐) ⭐
   - **地址**: http://localhost:8000/docs
   - **优势**: 
     - 实时同步代码变更
     - 可直接测试 API
     - 自动生成请求示例
     - 包含完整的请求/响应模型
   - **使用场景**: 开发调试、API 探索、快速测试

2. **API 使用指南** (推荐) ⭐
   - **文件**: `docs/api_references/API_USAGE_GUIDE.md`
   - **优势**:
     - 完整的使用流程说明
     - 丰富的代码示例
     - 常见场景演示
     - 最佳实践建议
   - **使用场景**: 学习 API 使用、理解业务流程

3. **Postman 集合**
   - **文件**: `docs/api_references/postman_collection.json`
   - **优势**:
     - 预配置的请求集合
     - 自动 Token 管理
     - 环境变量支持
   - **使用场景**: API 测试、团队协作

4. **OpenAPI 规范**
   - **地址**: http://localhost:8000/openapi.json
   - **优势**:
     - 机器可读的 API 定义
     - 可生成客户端代码
   - **使用场景**: 自动化工具、代码生成

---

## 快速开始

### 1. 启动服务

```bash
# 启动 API 服务器
python main.py

# 服务地址
# API: http://localhost:8000
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### 2. 访问 Swagger UI

打开浏览器访问: http://localhost:8000/docs

你会看到：
- 所有 API 端点列表
- 每个端点的详细说明
- 请求/响应模型
- "Try it out" 按钮可直接测试

### 3. 认证流程

#### 步骤 1: 登录获取 Token

在 Swagger UI 中：
1. 找到 `POST /api/v1/auth/dev/login`
2. 点击 "Try it out"
3. 输入请求体：
   ```json
   {
     "username": "test_user"
   }
   ```
4. 点击 "Execute"
5. 复制响应中的 `access_token`

#### 步骤 2: 配置认证

1. 点击页面右上角的 "Authorize" 按钮（🔒图标）
2. 在弹出框中输入: `Bearer <your_token>`
3. 点击 "Authorize"
4. 点击 "Close"

现在所有 API 请求都会自动带上认证 Token！

---

## 前端集成示例

### JavaScript/TypeScript

#### 1. 基础封装

```typescript
// api/client.ts
class MeetingAgentAPI {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = null;

  // 登录获取 Token
  async login(username: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/auth/dev/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username }),
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    this.token = data.access_token;
    
    // 可选：保存到 localStorage
    localStorage.setItem('access_token', this.token);
  }

  // 通用请求方法
  private async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<any> {
    // 从 localStorage 恢复 token
    if (!this.token) {
      this.token = localStorage.getItem('access_token');
    }

    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });

    // 处理 401 错误（Token 过期）
    if (response.status === 401) {
      this.token = null;
      localStorage.removeItem('access_token');
      throw new Error('Token expired, please login again');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  // API 方法
  async createTask(data: CreateTaskRequest): Promise<CreateTaskResponse> {
    return this.request('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    return this.request(`/tasks/${taskId}/status`);
  }

  async listTasks(limit = 10, offset = 0): Promise<TaskDetailResponse[]> {
    return this.request(`/tasks?limit=${limit}&offset=${offset}`);
  }

  async getArtifacts(taskId: string): Promise<ListArtifactsResponse> {
    return this.request(`/tasks/${taskId}/artifacts`);
  }
}

// 导出单例
export const api = new MeetingAgentAPI();
```

#### 2. React 示例

```tsx
// components/TaskCreator.tsx
import React, { useState } from 'react';
import { api } from '../api/client';

export const TaskCreator: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);

  const handleCreateTask = async () => {
    setLoading(true);
    try {
      // 1. 确保已登录
      if (!localStorage.getItem('access_token')) {
        await api.login('test_user');
      }

      // 2. 创建任务
      const response = await api.createTask({
        audio_files: [
          {
            file_path: 'test_data/meeting.wav',
            speaker_id: 'speaker_001',
          },
        ],
        meeting_type: 'weekly_sync',
        prompt_instance: {
          template_id: 'global_meeting_minutes_v1',
          parameters: {},
        },
      });

      setTaskId(response.task_id);
      
      // 3. 轮询任务状态
      pollTaskStatus(response.task_id);
    } catch (error) {
      console.error('Failed to create task:', error);
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await api.getTaskStatus(taskId);
        console.log('Task status:', status.state, status.progress);

        if (status.state === 'success' || status.state === 'failed') {
          clearInterval(interval);
          
          if (status.state === 'success') {
            // 获取结果
            const artifacts = await api.getArtifacts(taskId);
            console.log('Artifacts:', artifacts);
          }
        }
      } catch (error) {
        console.error('Failed to poll status:', error);
        clearInterval(interval);
      }
    }, 5000); // 每 5 秒轮询一次
  };

  return (
    <div>
      <button onClick={handleCreateTask} disabled={loading}>
        {loading ? '创建中...' : '创建任务'}
      </button>
      {taskId && <p>任务 ID: {taskId}</p>}
    </div>
  );
};
```

#### 3. Vue 示例

```vue
<!-- components/TaskCreator.vue -->
<template>
  <div>
    <button @click="createTask" :disabled="loading">
      {{ loading ? '创建中...' : '创建任务' }}
    </button>
    <p v-if="taskId">任务 ID: {{ taskId }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../api/client';

const loading = ref(false);
const taskId = ref<string | null>(null);

const createTask = async () => {
  loading.value = true;
  try {
    // 1. 确保已登录
    if (!localStorage.getItem('access_token')) {
      await api.login('test_user');
    }

    // 2. 创建任务
    const response = await api.createTask({
      audio_files: [
        {
          file_path: 'test_data/meeting.wav',
          speaker_id: 'speaker_001',
        },
      ],
      meeting_type: 'weekly_sync',
      prompt_instance: {
        template_id: 'global_meeting_minutes_v1',
        parameters: {},
      },
    });

    taskId.value = response.task_id;
    
    // 3. 轮询任务状态
    pollTaskStatus(response.task_id);
  } catch (error) {
    console.error('Failed to create task:', error);
    alert(error.message);
  } finally {
    loading.value = false;
  }
};

const pollTaskStatus = async (id: string) => {
  const interval = setInterval(async () => {
    try {
      const status = await api.getTaskStatus(id);
      console.log('Task status:', status.state, status.progress);

      if (status.state === 'success' || status.state === 'failed') {
        clearInterval(interval);
        
        if (status.state === 'success') {
          const artifacts = await api.getArtifacts(id);
          console.log('Artifacts:', artifacts);
        }
      }
    } catch (error) {
      console.error('Failed to poll status:', error);
      clearInterval(interval);
    }
  }, 5000);
};
</script>
```

---

## 类型定义

### TypeScript 类型

```typescript
// types/api.ts

// 认证相关
export interface LoginRequest {
  username: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  tenant_id: string;
  expires_in: number;
}

// 任务相关
export interface AudioFile {
  file_path: string;
  speaker_id: string;
}

export interface PromptInstance {
  template_id: string;
  language?: string;
  parameters?: Record<string, any>;
}

export interface CreateTaskRequest {
  audio_files: AudioFile[];
  meeting_type: string;
  asr_language?: string;
  output_language?: string;
  prompt_instance?: PromptInstance;
  skip_speaker_recognition?: boolean;
}

export interface CreateTaskResponse {
  success: boolean;
  task_id: string;
  message: string;
}

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
  | 'partial_success';

export interface TaskStatusResponse {
  task_id: string;
  state: TaskState;
  progress: number;
  estimated_time?: number;
  error_details?: string;
  updated_at: string;
}

export interface TaskDetailResponse {
  task_id: string;
  user_id: string;
  tenant_id: string;
  meeting_type: string;
  audio_files: AudioFile[];
  file_order: number[];
  asr_language: string;
  output_language: string;
  state: TaskState;
  progress: number;
  error_details?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

// 衍生内容相关
export interface ArtifactInfo {
  artifact_id: string;
  task_id: string;
  artifact_type: string;
  version: number;
  prompt_instance: PromptInstance;
  created_at: string;
  created_by: string;
}

export interface ListArtifactsResponse {
  task_id: string;
  artifacts_by_type: Record<string, ArtifactInfo[]>;
  total_count: number;
}

export interface GeneratedArtifact {
  artifact_id: string;
  task_id: string;
  artifact_type: string;
  version: number;
  prompt_instance: PromptInstance;
  content: string; // JSON string
  metadata?: Record<string, any>;
  created_at: string;
  created_by: string;
}
```

---

## 错误处理

### 常见错误码

| HTTP 状态码 | 错误类型 | 说明 | 处理方式 |
|------------|---------|------|---------|
| 401 | Unauthorized | Token 无效或过期 | 重新登录 |
| 403 | Forbidden | 未提供 Token | 提示用户登录 |
| 404 | Not Found | 资源不存在 | 检查 ID 是否正确 |
| 422 | Validation Error | 请求参数错误 | 检查请求体格式 |
| 429 | Too Many Requests | 请求过多 | 降低请求频率 |
| 500 | Internal Server Error | 服务器错误 | 联系后端团队 |

### 错误处理示例

```typescript
// utils/errorHandler.ts
export class APIError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public response?: any
  ) {
    super(detail);
    this.name = 'APIError';
  }
}

export async function handleAPIError(response: Response): Promise<never> {
  const data = await response.json().catch(() => ({}));
  
  switch (response.status) {
    case 401:
      // Token 过期，清除本地存储
      localStorage.removeItem('access_token');
      throw new APIError(401, 'Token 已过期，请重新登录', data);
    
    case 403:
      throw new APIError(403, '无权访问，请先登录', data);
    
    case 404:
      throw new APIError(404, '资源不存在', data);
    
    case 422:
      throw new APIError(422, '请求参数错误: ' + data.detail, data);
    
    case 429:
      throw new APIError(429, '请求过于频繁，请稍后再试', data);
    
    case 500:
      throw new APIError(500, '服务器错误，请联系管理员', data);
    
    default:
      throw new APIError(
        response.status,
        data.detail || '请求失败',
        data
      );
  }
}
```

---

## 最佳实践

### 1. Token 管理

```typescript
// utils/tokenManager.ts
export class TokenManager {
  private static TOKEN_KEY = 'access_token';
  private static EXPIRY_KEY = 'token_expiry';

  static saveToken(token: string, expiresIn: number): void {
    localStorage.setItem(this.TOKEN_KEY, token);
    const expiry = Date.now() + expiresIn * 1000;
    localStorage.setItem(this.EXPIRY_KEY, expiry.toString());
  }

  static getToken(): string | null {
    const token = localStorage.getItem(this.TOKEN_KEY);
    const expiry = localStorage.getItem(this.EXPIRY_KEY);

    if (!token || !expiry) {
      return null;
    }

    // 检查是否过期
    if (Date.now() > parseInt(expiry)) {
      this.clearToken();
      return null;
    }

    return token;
  }

  static clearToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.EXPIRY_KEY);
  }

  static isTokenValid(): boolean {
    return this.getToken() !== null;
  }
}
```

### 2. 请求重试

```typescript
// utils/retry.ts
export async function retryRequest<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  delay = 1000
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) {
        throw error;
      }
      
      // 指数退避
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
    }
  }
  
  throw new Error('Max retries exceeded');
}
```

### 3. 请求取消

```typescript
// utils/cancellable.ts
export class CancellableRequest {
  private controller: AbortController;

  constructor() {
    this.controller = new AbortController();
  }

  async fetch(url: string, options: RequestInit = {}): Promise<Response> {
    return fetch(url, {
      ...options,
      signal: this.controller.signal,
    });
  }

  cancel(): void {
    this.controller.abort();
  }
}

// 使用示例
const request = new CancellableRequest();

// 发起请求
request.fetch('/api/v1/tasks')
  .then(response => response.json())
  .catch(error => {
    if (error.name === 'AbortError') {
      console.log('Request cancelled');
    }
  });

// 取消请求
request.cancel();
```

---

## 常见问题

### Q1: Swagger UI 和文档不一致怎么办？

**答**: Swagger UI 是实时从代码生成的，始终是最新的。如果发现文档不一致，以 Swagger UI 为准。

### Q2: 如何处理 Token 过期？

**答**: 
1. 捕获 401 错误
2. 清除本地 Token
3. 重新调用登录接口
4. 重试原请求

### Q3: 如何调试 API 请求？

**答**:
1. 使用 Swagger UI 的 "Try it out" 功能
2. 使用浏览器开发者工具的 Network 面板
3. 使用 Postman 集合

### Q4: 生产环境认证方式会变吗？

**答**: 会。生产环境将使用企业微信等第三方认证，但 Token 使用方式相同（都是 Bearer Token）。

### Q5: 如何生成 TypeScript 类型？

**答**: 可以使用 OpenAPI Generator:
```bash
npx @openapitools/openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-fetch \
  -o ./src/api/generated
```

---

## 相关资源

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **API 使用指南**: `docs/api_references/API_USAGE_GUIDE.md`
- **Postman 集合**: `docs/api_references/postman_collection.json`

---

## 联系支持

如有问题，请：
1. 查看 Swagger UI 文档
2. 查看 API 使用指南
3. 联系后端开发团队

---

**最后更新**: 2026-01-15  
**维护者**: 后端开发团队
