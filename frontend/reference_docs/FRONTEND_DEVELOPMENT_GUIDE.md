# 前端开发完整指南

**最后更新**: 2026-01-16  
**API 版本**: v1  
**后端地址**: http://localhost:8000

---

## 目录

1. [快速开始](#快速开始)
2. [认证流程](#认证流程)
3. [核心功能实现](#核心功能实现)
4. [API 端点详解](#api-端点详解)
5. [数据模型](#数据模型)
6. [前端页面需求](#前端页面需求)
7. [错误处理](#错误处理)
8. [最佳实践](#最佳实践)

---

## 快速开始

### 1. 启动后端服务

```bash
# 启动 API 服务器
python main.py

# 启动 Worker (另一个终端)
python worker.py

# 服务地址
# API: http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

### 2. 推荐开发工具

- **Swagger UI** (http://localhost:8000/docs) - 实时 API 文档和测试
- **Postman 集合** (`docs/api_references/postman_collection.json`)
- **API 使用指南** (`docs/api_references/API_USAGE_GUIDE.md`)

### 3. 基础 API 客户端封装

```typescript
// api/client.ts
class MeetingAgentAPI {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = null;

  async login(username: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/auth/dev/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    });
    const data = await response.json();
    this.token = data.access_token;
    localStorage.setItem('access_token', this.token);
  }

  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
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
}

export const api = new MeetingAgentAPI();
```

---

## 认证流程

### JWT Token 认证

系统使用 JWT Bearer Token 进行认证。

#### 开发环境登录

```typescript
// 1. 登录获取 Token
const loginResponse = await api.login('test_user');
// Token 自动保存到 localStorage

// 2. 后续请求自动带上 Token
const tasks = await api.listTasks();
```

#### Token 管理

```typescript
class TokenManager {
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

    if (!token || !expiry) return null;

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
}
```

---

## 核心功能实现

### 功能 1: 创建会议任务

```typescript
interface CreateTaskRequest {
  audio_files: Array<{
    file_path: string;
    speaker_id: string;
  }>;
  meeting_type: string;
  asr_language?: string;  // 默认 "zh-CN+en-US"
  output_language?: string;  // 默认 "zh-CN"
  prompt_instance?: {
    template_id: string;
    language?: string;
    parameters?: Record<string, any>;
  };
  skip_speaker_recognition?: boolean;
}

async function createTask(data: CreateTaskRequest) {
  const response = await api.request('/tasks', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return response.task_id;
}
```

### 功能 2: 轮询任务状态

```typescript
type TaskState = 
  | 'pending' 
  | 'queued' 
  | 'running' 
  | 'transcribing' 
  | 'identifying' 
  | 'correcting' 
  | 'summarizing' 
  | 'success' 
  | 'failed';

interface TaskStatus {
  task_id: string;
  state: TaskState;
  progress: number;  // 0-100
  estimated_time?: number;  // 秒
  error_details?: string;
  updated_at: string;
}

async function pollTaskStatus(
  taskId: string,
  onUpdate: (status: TaskStatus) => void,
  interval: number = 5000
): Promise<void> {
  const poll = async () => {
    const status = await api.getTaskStatus(taskId);
    onUpdate(status);

    if (status.state === 'success' || status.state === 'failed') {
      return;
    }

    setTimeout(poll, interval);
  };

  await poll();
}
```

### 功能 3: 获取生成内容

```typescript
interface ArtifactInfo {
  artifact_id: string;
  task_id: string;
  artifact_type: string;  // meeting_minutes, action_items, summary_notes
  version: number;
  prompt_instance: {
    template_id: string;
    language: string;
    parameters: Record<string, any>;
  };
  created_at: string;
  created_by: string;
}

interface ListArtifactsResponse {
  task_id: string;
  artifacts_by_type: Record<string, ArtifactInfo[]>;
  total_count: number;
}

async function getArtifacts(taskId: string): Promise<ListArtifactsResponse> {
  return await api.request(`/tasks/${taskId}/artifacts`);
}

async function getArtifactDetail(artifactId: string) {
  const response = await api.request(`/artifacts/${artifactId}`);
  // response.artifact.content 是 JSON 字符串，需要解析
  const content = JSON.parse(response.artifact.content);
  return content;
}
```

### 功能 4: 修正转写文本

```typescript
async function correctTranscript(
  taskId: string,
  correctedText: string,
  regenerate: boolean = true
) {
  return await api.request(`/tasks/${taskId}/transcript`, {
    method: 'PUT',
    body: JSON.stringify({
      corrected_text: correctedText,
      regenerate_artifacts: regenerate,
    }),
  });
}
```

### 功能 5: 重新生成内容

```typescript
async function regenerateArtifact(
  taskId: string,
  artifactType: string,
  promptInstance: {
    template_id: string;
    language?: string;
    parameters?: Record<string, any>;
  }
) {
  return await api.request(`/tasks/${taskId}/artifacts/${artifactType}/generate`, {
    method: 'POST',
    body: JSON.stringify({ prompt_instance: promptInstance }),
  });
}
```

### 功能 6: 确认任务

```typescript
async function confirmTask(
  taskId: string,
  confirmationItems: Record<string, boolean>,
  responsiblePerson: { id: string; name: string }
) {
  return await api.request(`/tasks/${taskId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({
      confirmation_items: confirmationItems,
      responsible_person: responsiblePerson,
    }),
  });
}
```

---

## API 端点详解

### 认证相关

#### POST /api/v1/auth/dev/login
开发环境登录

**请求**:
```json
{
  "username": "test_user"
}
```

**响应**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": "user_123",
  "tenant_id": "tenant_456",
  "expires_in": 86400
}
```

### 任务管理

#### POST /api/v1/tasks
创建任务

**请求**:
```json
{
  "audio_files": [
    {
      "file_path": "test_data/meeting.wav",
      "speaker_id": "speaker_001"
    }
  ],
  "meeting_type": "weekly_sync",
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN",
  "prompt_instance": {
    "template_id": "global_meeting_minutes_v1",
    "language": "zh-CN",
    "parameters": {
      "meeting_description": "会议标题: 产品规划会议"
    }
  }
}
```

**响应**:
```json
{
  "success": true,
  "task_id": "task_abc123",
  "message": "任务已创建"
}
```

#### GET /api/v1/tasks/{task_id}/status
查询任务状态

**响应**:
```json
{
  "task_id": "task_abc123",
  "state": "transcribing",
  "progress": 35.5,
  "estimated_time": 120,
  "updated_at": "2026-01-16T10:30:00Z"
}
```

#### GET /api/v1/tasks
列出任务

**查询参数**:
- `limit`: 每页数量 (默认 10)
- `offset`: 偏移量 (默认 0)

**响应**:
```json
[
  {
    "task_id": "task_abc123",
    "meeting_type": "weekly_sync",
    "state": "success",
    "progress": 100,
    "created_at": "2026-01-16T10:00:00Z",
    "completed_at": "2026-01-16T10:15:00Z"
  }
]
```

#### GET /api/v1/tasks/{task_id}
获取任务详情

**响应**:
```json
{
  "task_id": "task_abc123",
  "user_id": "user_123",
  "tenant_id": "tenant_456",
  "meeting_type": "weekly_sync",
  "audio_files": ["test_data/meeting.wav"],
  "file_order": [0],
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN",
  "state": "success",
  "progress": 100,
  "created_at": "2026-01-16T10:00:00Z",
  "updated_at": "2026-01-16T10:15:00Z",
  "completed_at": "2026-01-16T10:15:00Z"
}
```

### 衍生内容管理

#### GET /api/v1/tasks/{task_id}/artifacts
列出任务的所有衍生内容

**响应**:
```json
{
  "task_id": "task_abc123",
  "artifacts_by_type": {
    "meeting_minutes": [
      {
        "artifact_id": "art_001",
        "version": 2,
        "prompt_instance": {
          "template_id": "tpl_001",
          "language": "zh-CN",
          "parameters": {}
        },
        "created_at": "2026-01-16T10:20:00Z",
        "created_by": "user_123"
      }
    ]
  },
  "total_count": 1
}
```

#### GET /api/v1/artifacts/{artifact_id}
获取衍生内容详情

**响应**:
```json
{
  "artifact": {
    "artifact_id": "art_001",
    "task_id": "task_abc123",
    "artifact_type": "meeting_minutes",
    "version": 1,
    "content": "{\"title\":\"产品规划会议\",\"participants\":[\"张三\",\"李四\"],\"summary\":\"讨论了Q2产品路线图\",\"key_points\":[],\"action_items\":[]}",
    "created_at": "2026-01-16T10:15:00Z",
    "created_by": "user_123"
  }
}
```

#### POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate
生成新版本的衍生内容

**请求**:
```json
{
  "prompt_instance": {
    "template_id": "tpl_002",
    "language": "zh-CN",
    "parameters": {
      "meeting_description": "重点关注技术决策"
    }
  }
}
```

**响应**:
```json
{
  "success": true,
  "artifact_id": "art_002",
  "version": 2,
  "content": {...},
  "message": "内容已生成"
}
```

### 修正相关

#### PUT /api/v1/tasks/{task_id}/transcript
修正转写文本

**请求**:
```json
{
  "corrected_text": "修正后的完整转写文本...",
  "regenerate_artifacts": true
}
```

**响应**:
```json
{
  "success": true,
  "message": "转写文本已修正",
  "regenerated_artifacts": ["art_003"]
}
```

#### PATCH /api/v1/tasks/{task_id}/speakers
修正说话人映射

**请求**:
```json
{
  "speaker_mapping": {
    "Speaker 0": "张三",
    "Speaker 1": "李四"
  },
  "regenerate_artifacts": true
}
```

### 提示词模板

#### GET /api/v1/prompt-templates
列出所有可用模板

**响应**:
```json
{
  "templates": [
    {
      "template_id": "global_meeting_minutes_v1",
      "title": "标准会议纪要",
      "description": "生成包含摘要、关键要点和行动项的标准会议纪要",
      "artifact_type": "meeting_minutes",
      "supported_languages": ["zh-CN", "en-US"],
      "is_system": true,
      "scope": "global"
    }
  ]
}
```

#### GET /api/v1/prompt-templates/{template_id}
获取模板详情

### 热词管理

#### POST /api/v1/hotwords
创建热词集

**请求** (multipart/form-data):
- `name`: 热词集名称
- `scope`: 作用域 (global/tenant/user)
- `scope_id`: 作用域 ID
- `asr_language`: ASR 语言
- `description`: 描述
- `hotwords_file`: 热词文件 (.txt)

#### GET /api/v1/hotwords
列出热词集

**查询参数**:
- `scope`: 过滤作用域
- `asr_language`: 过滤语言

---

## 数据模型

### 会议纪要结构

```typescript
interface MeetingMinutes {
  title: string;
  participants: string[];
  summary: string;
  key_points: string[];
  action_items: string[];
  created_at: string;
  responsible_person?: string;
}
```

### 任务状态流转

```
pending → queued → running → transcribing → identifying → correcting → summarizing → success
                                                                                    ↓
                                                                                  failed
```

### 语言配置

**ASR 语言** (转写识别):
- `zh-CN`: 纯中文
- `en-US`: 纯英文
- `zh-CN+en-US`: 中英文混合 (默认)
- `ja-JP`: 日文
- `ko-KR`: 韩文

**输出语言** (纪要生成):
- `zh-CN`: 中文 (默认)
- `en-US`: 英文
- `ja-JP`: 日文
- `ko-KR`: 韩文

---

## 前端页面需求

### 1. 登录页面
- 输入用户名
- 调用登录 API
- 保存 Token
- 跳转到任务列表

### 2. 任务列表页面
- 显示所有任务
- 任务状态标签 (进行中/已完成/失败)
- 创建新任务按钮
- 点击任务查看详情

### 3. 创建任务页面
- 上传音频文件 (支持多文件)
- 选择会议类型
- 选择提示词模板
- 填写会议描述参数
- 高级选项:
  - ASR 语言选择
  - 输出语言选择
  - 是否跳过说话人识别
- 提交创建

### 4. 任务详情页面
- 任务基本信息
- 实时状态显示
- 进度条
- 预计剩余时间
- 错误信息 (如果失败)

### 5. 结果查看页面
- 转写文本展示
- 说话人标签
- 时间戳
- 编辑转写按钮
- 修正说话人按钮

### 6. 会议纪要页面
- 显示生成的纪要
- 版本历史
- 重新生成按钮
- 选择不同模板
- 导出功能 (PDF/Word)
- 确认按钮

### 7. 确认页面
- 确认项清单:
  - ☑ 关键结论已确认
  - ☑ 负责人无误
  - ☑ 行动项已明确
- 责任人信息输入
- 提交确认

### 8. 模板管理页面
- 系统模板列表
- 我的模板列表
- 创建新模板
- 编辑模板
- 删除模板

### 9. 热词管理页面
- 热词集列表
- 创建热词集
- 上传热词文件
- 删除热词集

---

## 错误处理

### 常见错误码

| HTTP 状态码 | 错误类型 | 处理方式 |
|------------|---------|---------|
| 401 | Token 无效或过期 | 重新登录 |
| 403 | 未提供 Token | 跳转登录页 |
| 404 | 资源不存在 | 提示用户 |
| 422 | 请求参数错误 | 显示验证错误 |
| 429 | 请求过多 | 降低请求频率 |
| 500 | 服务器错误 | 联系管理员 |

### 错误处理示例

```typescript
async function handleAPIError(error: any) {
  if (error.status === 401) {
    TokenManager.clearToken();
    window.location.href = '/login';
  } else if (error.status === 422) {
    // 显示表单验证错误
    showValidationErrors(error.detail);
  } else {
    // 显示通用错误提示
    showErrorToast(error.message);
  }
}
```

---

## 最佳实践

### 1. Token 自动刷新

```typescript
// 在 Token 过期前 5 分钟自动刷新
setInterval(() => {
  const expiry = localStorage.getItem('token_expiry');
  if (expiry && Date.now() > parseInt(expiry) - 300000) {
    api.login('test_user');  // 重新登录
  }
}, 60000);  // 每分钟检查一次
```

### 2. 请求重试

```typescript
async function retryRequest<T>(
  fn: () => Promise<T>,
  maxRetries = 3
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
  throw new Error('Max retries exceeded');
}
```

### 3. 轮询优化

```typescript
// 使用指数退避减少服务器压力
async function smartPoll(taskId: string) {
  let interval = 2000;  // 初始 2 秒
  const maxInterval = 10000;  // 最大 10 秒

  while (true) {
    const status = await api.getTaskStatus(taskId);
    
    if (status.state === 'success' || status.state === 'failed') {
      break;
    }

    await new Promise(r => setTimeout(r, interval));
    interval = Math.min(interval * 1.5, maxInterval);
  }
}
```

### 4. 内容解析

```typescript
// 安全解析 artifact.content
function parseArtifactContent(artifact: any): MeetingMinutes | null {
  try {
    return JSON.parse(artifact.content);
  } catch (error) {
    console.error('Failed to parse artifact content:', error);
    return null;
  }
}
```

### 5. 文件上传

```typescript
async function uploadAudio(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/api/v1/upload', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TokenManager.getToken()}`,
    },
    body: formData,
  });

  const data = await response.json();
  return data.file_path;
}
```

---

## 开发调试

### 使用 Swagger UI

1. 访问 http://localhost:8000/docs
2. 点击右上角 "Authorize" 按钮
3. 输入 `Bearer <your_token>`
4. 测试所有 API 端点

### 使用浏览器开发者工具

```javascript
// 在控制台快速测试
const token = localStorage.getItem('access_token');
fetch('http://localhost:8000/api/v1/tasks', {
  headers: { Authorization: `Bearer ${token}` }
})
  .then(r => r.json())
  .then(console.log);
```

---

## 相关资源

- **Swagger UI**: http://localhost:8000/docs
- **API 使用指南**: `docs/api_references/API_USAGE_GUIDE.md`
- **前端集成指南**: `docs/api_references/FRONTEND_INTEGRATION_GUIDE.md`
- **需求文档**: `.kiro/specs/meeting-minutes-agent/requirements.md`
- **设计文档**: `.kiro/specs/meeting-minutes-agent/design.md`

---

## 常见问题

### Q: 如何处理大文件上传？
A: 建议使用分片上传或直接上传到 TOS，然后传递文件路径给 API。

### Q: 轮询频率建议？
A: 初始 2-5 秒，使用指数退避最大到 10 秒。

### Q: 如何导出会议纪要？
A: 前端自行实现，可以使用 jsPDF 或 docx 库生成 PDF/Word。

### Q: 生产环境认证会变吗？
A: 会，生产环境将使用企业微信等第三方认证，但 Token 使用方式相同。

---

**维护者**: 后端开发团队  
**联系方式**: 查看项目 README
