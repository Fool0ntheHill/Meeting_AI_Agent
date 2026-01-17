# 前端开发完整指南

**最后更新**: 2026-01-16  
**API 版本**: v1  
**后端地址**: http://localhost:8000

---

## 🚀 API 快速参考（直接复制使用）

### 1️⃣ 文件夹 CRUD

```typescript
// 列出文件夹
GET /api/v1/folders
// 响应：{ items: [{ folder_id, name, parent_id, ... }], total }

// 创建文件夹（扁平结构，无 parent_id）
POST /api/v1/folders
Body: { "name": "2024年会议" }
// 成功：{ success: true, folder_id: "folder_xxx", message }
// 重名：409 { detail: "文件夹名称已存在: 2024年会议" }

// 重命名文件夹
PATCH /api/v1/folders/{folder_id}
Body: { "name": "新名称" }
// 成功：{ success: true, message }
// 重名：409 { detail: "文件夹名称已存在: 新名称" }

// 删除文件夹（会话自动移到根目录）
DELETE /api/v1/folders/{folder_id}
// 响应：{ success: true, message }
```

### 2️⃣ 任务操作

```typescript
// 重命名任务
PATCH /api/v1/tasks/{task_id}/rename
Body: { "name": "2024年Q1产品规划会议" }
// 响应：{ success: true, message }

// 移动任务到文件夹
PATCH /api/v1/sessions/{task_id}/move
Body: { "folder_id": "folder_xxx" }  // null = 移到根目录
// 响应：{ success: true, message }
```

### 3️⃣ 回收站操作

```typescript
// 软删除任务（移入回收站）⭐ 前端应该用这个
PATCH /api/v1/sessions/{task_id}/delete
// 响应：{ success: true, message: "会话已移至回收站" }

// 还原任务（从回收站恢复）
PATCH /api/v1/sessions/{task_id}/restore
// 响应：{ success: true, message }

// 彻底删除任务（从回收站永久删除）
DELETE /api/v1/sessions/{task_id}
// 响应：{ success: true, message }

// 列出回收站
GET /api/v1/trash/sessions
// 响应：{ items: [{ task_id, folder_id, deleted_at, ... }], total }
```

**⚠️ 注意**：还有一个 `DELETE /api/v1/tasks/{task_id}` 接口是硬删除（直接删除，不经过回收站），前端一般不应该使用。
```

### 4️⃣ 批量操作

```typescript
// 批量移动
POST /api/v1/sessions/batch-move
Body: { "task_ids": ["task_1", "task_2"], "folder_id": "folder_xxx" }
// 响应：{ success: true, moved_count: 2, message }

// 批量删除
POST /api/v1/sessions/batch-delete
Body: { "task_ids": ["task_1", "task_2"] }
// 响应：{ success: true, deleted_count: 2, message }

// 批量还原
POST /api/v1/sessions/batch-restore
Body: { "task_ids": ["task_1", "task_2"] }
// 响应：{ success: true, restored_count: 2, message }
```

### 5️⃣ 任务列表（包含文件夹信息）

```typescript
// 获取任务列表
GET /api/v1/tasks?folder_id=folder_xxx&include_deleted=false
// 响应示例：
[{
  "task_id": "task_abc123",
  "name": "产品规划会议",           // ✨ 任务名称
  "folder_id": "folder_xxx",        // ✨ 所属文件夹 ID（null = 根目录）
  "meeting_type": "weekly_sync",
  "state": "success",
  "duration": 300.5,                // ✨ 音频时长（秒）
  "created_at": "2026-01-16T10:00:00Z",
  "last_content_modified_at": "2026-01-16T14:30:00Z"  // ✨ 内容修改时间
}]

// 查询参数：
// - folder_id: 文件夹筛选（"" = 根目录，不传 = 所有）
// - include_deleted: 是否包含已删除（默认 false）
// - state: 状态筛选（pending/running/success/failed）
// - limit: 每页数量（默认 100）
// - offset: 偏移量（默认 0）
```

### 📋 关键字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `folder_id` | string \| null | 文件夹 ID，null 表示根目录 |
| `name` | string \| null | 任务名称，null 时前端显示默认名称 |
| `duration` | number \| null | 音频时长（秒），未完成转写时为 null |
| `last_content_modified_at` | string \| null | 内容最后修改时间（转写/说话人/生成内容） |
| `updated_at` | string | 任务任何字段更新时间（包括移动文件夹等） |

**注意**：
- 文件夹为**扁平结构**（单层），不支持嵌套
- 任务移动使用 `/sessions/{id}/move`，不是 `/tasks/{id}/move`
- 回收站路径是 `/trash/sessions`，不是 `/tasks/trash`

---

## ⚠️ 重要：占位接口替换指南

如果你的前端正在使用占位接口，请参考以下映射表替换为真实接口：

| 功能 | 占位路径 | 真实路径 | 状态 |
|------|---------|---------|------|
| **会话重命名** | `PATCH /tasks/{id}/rename` | `PATCH /tasks/{id}/rename` | ✅ 已实现 |
| **会话移动** | `PATCH /tasks/{id}/move` | `PATCH /sessions/{id}/move` | ✅ 已实现 |
| **回收站列表** | `GET /tasks/trash` | `GET /trash/sessions` | ✅ 已实现 |
| 列出文件夹 | - | `GET /folders` | ✅ 已实现 |
| 创建文件夹 | - | `POST /folders` | ✅ 已实现 |
| 重命名文件夹 | - | `PATCH /folders/{id}` | ✅ 已实现 |
| 删除文件夹 | - | `DELETE /folders/{id}` | ✅ 已实现 |
| 软删除会话 | - | `PATCH /sessions/{id}/delete` | ✅ 已实现 |
| 还原会话 | - | `PATCH /sessions/{id}/restore` | ✅ 已实现 |
| 彻底删除 | - | `DELETE /sessions/{id}` | ✅ 已实现 |
| 批量移动 | - | `POST /sessions/batch-move` | ✅ 已实现 |
| 批量删除 | - | `POST /sessions/batch-delete` | ✅ 已实现 |
| 批量还原 | - | `POST /sessions/batch-restore` | ✅ 已实现 |

**关键修改**:
1. 移除文件夹和回收站的本地 fallback 逻辑
2. 更新接口路径：`/tasks/{id}/move` → `/sessions/{id}/move`
3. 更新接口路径：`/tasks/trash` → `/trash/sessions`
4. 会话重命名接口路径：`PATCH /tasks/{id}/rename` ✅ 已实现

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

### 功能 0: 音频文件上传 ✅

**最新更新**: 音频上传接口已实现！

#### 上传音频文件

```typescript
async function uploadAudio(file: File): Promise<{
  file_path: string;
  file_size: number;
  duration: number;
}> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/api/v1/upload', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TokenManager.getToken()}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '上传失败');
  }

  return await response.json();
}
```

#### 删除已上传文件

```typescript
async function deleteUpload(filePath: string): Promise<void> {
  const encodedPath = encodeURIComponent(filePath);
  await api.request(`/upload/${encodedPath}`, {
    method: 'DELETE',
  });
}
```

#### 支持的格式和限制

- **支持格式**: .wav, .opus, .mp3, .m4a, .ogg
- **最大文件大小**: 500MB
- **自动功能**: 
  - 获取音频时长
  - 用户隔离 (uploads/{user_id}/)
  - 文件名去重

#### 完整上传流程

```typescript
async function handleFileUpload(files: FileList) {
  const uploadedFiles = [];

  for (const file of files) {
    // 1. 验证文件格式
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['wav', 'opus', 'mp3', 'm4a', 'ogg'].includes(ext || '')) {
      throw new Error(`不支持的文件格式: ${ext}`);
    }

    // 2. 验证文件大小
    if (file.size > 500 * 1024 * 1024) {
      throw new Error('文件大小超过 500MB');
    }

    // 3. 上传文件
    try {
      const result = await uploadAudio(file);
      uploadedFiles.push({
        file_path: result.file_path,
        speaker_id: `speaker_${uploadedFiles.length}`,
        duration: result.duration,
      });
    } catch (error) {
      console.error(`上传失败: ${file.name}`, error);
      throw error;
    }
  }

  return uploadedFiles;
}
```

#### 开发环境方案 (已过时)

~~方案 1: 使用测试数据目录的文件~~
~~方案 2: 手动复制文件到服务器~~

**现在直接使用上传接口即可！**

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

// 获取特定类型的所有版本
async function getArtifactVersions(taskId: string, artifactType: string) {
  return await api.request(`/tasks/${taskId}/artifacts/${artifactType}/versions`);
}
```

### 功能 3.1: 版本管理

```typescript
// 列出所有版本
async function listVersions(taskId: string, artifactType: string) {
  const response = await api.request(
    `/tasks/${taskId}/artifacts/${artifactType}/versions`
  );
  
  // response.versions 按版本号降序排列（最新版本在前）
  return response.versions;
}

// 获取特定版本
async function getVersion(artifactId: string) {
  const response = await api.request(`/artifacts/${artifactId}`);
  return JSON.parse(response.artifact.content);
}

// 版本对比（前端实现）
import { diff_match_patch } from 'diff-match-patch';

async function compareVersions(
  taskId: string,
  artifactType: string,
  version1: number,
  version2: number
) {
  // 1. 获取版本列表
  const versions = await listVersions(taskId, artifactType);
  const v1 = versions.find(v => v.version === version1);
  const v2 = versions.find(v => v.version === version2);
  
  if (!v1 || !v2) {
    throw new Error('版本不存在');
  }
  
  // 2. 获取详细内容
  const content1 = await getVersion(v1.artifact_id);
  const content2 = await getVersion(v2.artifact_id);
  
  // 3. 使用 diff 库对比
  const dmp = new diff_match_patch();
  const text1 = JSON.stringify(content1, null, 2);
  const text2 = JSON.stringify(content2, null, 2);
  const diffs = dmp.diff_main(text1, text2);
  
  return {
    version1: { ...v1, content: content1 },
    version2: { ...v2, content: content2 },
    diff: {
      added: diffs.filter(d => d[0] === 1).map(d => d[1]),
      removed: diffs.filter(d => d[0] === -1).map(d => d[1]),
      unchanged: diffs.filter(d => d[0] === 0).map(d => d[1]),
    },
  };
}

// 版本切换（前端实现）
function switchVersion(versions: ArtifactInfo[], targetVersion: number) {
  const version = versions.find(v => v.version === targetVersion);
  if (!version) {
    throw new Error(`版本 ${targetVersion} 不存在`);
  }
  return version.artifact_id;
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

### 文件上传 ✨ 新增

#### POST /api/v1/upload
上传音频文件

**请求** (multipart/form-data):
- `file`: 音频文件 (.wav, .opus, .mp3, .m4a)

**响应**:
```json
{
  "success": true,
  "file_path": "uploads/user_123/meeting_20260116_143022.wav",
  "file_size": 1024000,
  "duration": 300.5
}
```

**错误响应**:
```json
{
  "detail": "不支持的文件格式，仅支持: .wav, .opus, .mp3, .m4a, .ogg"
}
```

**使用示例**:
```typescript
const formData = new FormData();
formData.append('file', audioFile);

const response = await fetch('/api/v1/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const { file_path, duration } = await response.json();
```

#### DELETE /api/v1/upload/{file_path}
删除已上传的文件

**路径参数**:
- `file_path`: URL 编码的文件路径

**响应**:
```json
{
  "success": true,
  "message": "文件已删除"
}
```

**使用示例**:
```typescript
const encodedPath = encodeURIComponent('uploads/user_123/meeting.wav');
await api.request(`/upload/${encodedPath}`, { method: 'DELETE' });
```

#### 上传限制和规范

**支持的格式**:
- `.wav` - 无损音频（推荐）
- `.opus` - 高压缩比（推荐）
- `.ogg` - Ogg Vorbis 格式
- `.mp3` - 常用格式
- `.m4a` - Apple 格式

**文件大小限制**:
- 最大: 500MB
- 建议: 使用 .opus 格式可大幅减小文件大小

**file_path 规范**:
- 格式: `uploads/{user_id}/{filename}`
- 示例: `uploads/user_123/meeting_20260116_143022.wav`
- 自动添加时间戳避免重名
- 用户隔离（不同用户的文件在不同目录）

**直接使用**:
```typescript
// 上传后返回的 file_path 可以直接用于创建任务
const uploadResult = await api.uploadAudio(file);

await api.createTask({
  audio_files: [
    {
      file_path: uploadResult.file_path,  // ✅ 直接使用
      speaker_id: "speaker_001"
    }
  ],
  meeting_type: 'general',
  // ...
});
```

**多文件顺序与合并**:
```typescript
// 1. 上传多个文件
const files = [file1, file2, file3];
const uploadedFiles = [];

for (const file of files) {
  const result = await api.uploadAudio(file);
  uploadedFiles.push({
    file_path: result.file_path,
    speaker_id: `speaker_${uploadedFiles.length}`
  });
}

// 2. 指定顺序
await api.createTask({
  audio_files: uploadedFiles,
  file_order: [0, 1, 2],  // 按上传顺序
  // ...
});

// 3. 自定义顺序（拖拽排序后）
await api.createTask({
  audio_files: uploadedFiles,
  file_order: [2, 0, 1],  // 用户调整后的顺序
  // ...
});
```

**后端处理**:
- 按 `file_order` 指定的顺序拼接音频
- 使用 ffmpeg 或 pydub 合并
- 生成单一音频文件用于处理

**上传进度显示**:
```typescript
async function uploadWithProgress(
  file: File,
  onProgress: (progress: number) => void
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // 监听上传进度
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const progress = (e.loaded / e.total) * 100;
        onProgress(progress);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'));
    });

    xhr.open('POST', '/api/v1/upload');
    xhr.setRequestHeader('Authorization', `Bearer ${getToken()}`);
    xhr.send(formData);
  });
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
- `limit`: 每页数量 (默认 100)
- `offset`: 偏移量 (默认 0)
- `state`: 状态筛选 (pending/running/success/failed) **✨ 新增**

**响应**:
```json
[
  {
    "task_id": "task_abc123",
    "user_id": "user_123",
    "tenant_id": "tenant_456",
    "meeting_type": "weekly_sync",
    "audio_files": ["uploads/user_123/meeting.wav"],
    "file_order": [0],
    "asr_language": "zh-CN+en-US",
    "output_language": "zh-CN",
    "state": "success",
    "progress": 100,
    "error_details": null,
    "duration": 300.5,
    "created_at": "2026-01-16T10:00:00Z",
    "updated_at": "2026-01-16T10:15:00Z",
    "completed_at": "2026-01-16T10:15:00Z",
    "last_content_modified_at": "2026-01-16T14:30:00Z"
  }
]
```

**字段说明**:
- `updated_at`: 任务任何字段更新时间（包括状态变化、移动文件夹等）
- `last_content_modified_at`: 内容最后修改时间（仅追踪转写修正、说话人修正、生成内容等内容相关操作）
- 前端建议：任务列表中显示 `last_content_modified_at`，因为用户更关心"内容什么时候被编辑过"

**使用示例**:
```typescript
// 获取所有任务
const allTasks = await api.listTasks();

// 只获取进行中的任务
const runningTasks = await api.listTasks({ state: 'running' });

// 只获取已完成的任务
const completedTasks = await api.listTasks({ state: 'success', limit: 20 });

// 只获取失败的任务
const failedTasks = await api.listTasks({ state: 'failed' });
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
  "audio_files": ["uploads/user_123/meeting.wav"],
  "file_order": [0],
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN",
  "state": "success",
  "progress": 100,
  "duration": 300.5,
  "created_at": "2026-01-16T10:00:00Z",
  "updated_at": "2026-01-16T10:15:00Z",
  "completed_at": "2026-01-16T10:15:00Z",
  "last_content_modified_at": "2026-01-16T14:30:00Z"
}
```

**字段说明**:
- `duration`: 音频总时长（秒），从转写记录获取，未完成转写时为 null
- `last_content_modified_at`: 内容最后修改时间，追踪转写修正、说话人修正、生成内容等操作

#### GET /api/v1/tasks/{task_id}/transcript ✨ 新增
获取任务的转写文本

**响应**:
```json
{
  "task_id": "task_abc123",
  "segments": [
    {
      "text": "大家好",
      "start_time": 0.0,
      "end_time": 1.5,
      "speaker": "张三",
      "confidence": 0.95
    },
    {
      "text": "今天我们讨论产品规划",
      "start_time": 1.5,
      "end_time": 4.2,
      "speaker": "李四",
      "confidence": 0.92
    }
  ],
  "full_text": "大家好，今天我们讨论产品规划...",
  "duration": 300.5,
  "language": "zh-CN",
  "provider": "volcano"
}
```

**使用示例**:
```typescript
// 获取转写文本
const transcript = await api.getTranscript(taskId);

// 显示逐字稿
transcript.segments.forEach(seg => {
  console.log(`[${formatTime(seg.start_time)}] ${seg.speaker}: ${seg.text}`);
});

// 音频时间戳跳转
function jumpToTime(startTime: number) {
  audioPlayer.currentTime = startTime;
  audioPlayer.play();
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

#### GET /api/v1/tasks/{task_id}/artifacts/{artifact_type}/versions
列出特定类型的所有版本

**路径参数**:
- `artifact_type`: 衍生内容类型 (meeting_minutes, action_items, summary_notes)

**响应**:
```json
{
  "task_id": "task_abc123",
  "artifact_type": "meeting_minutes",
  "versions": [
    {
      "artifact_id": "art_002",
      "version": 2,
      "prompt_instance": {
        "template_id": "global_brainstorming_v1",
        "language": "zh-CN",
        "parameters": {}
      },
      "created_at": "2026-01-16T10:15:00Z",
      "created_by": "user_123"
    },
    {
      "artifact_id": "art_001",
      "version": 1,
      "prompt_instance": {
        "template_id": "global_general_meeting_v1",
        "language": "zh-CN",
        "parameters": {}
      },
      "created_at": "2026-01-16T10:00:00Z",
      "created_by": "user_123"
    }
  ],
  "total_count": 2
}
```

**说明**:
- 版本按降序排列（最新版本在前）
- 每个版本有独立的 artifact_id
- version 字段在同一 artifact_type 内递增

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

**查询参数**:
- `scope`: 作用域过滤 (global/private)
- `artifact_type`: 内容类型过滤
- `user_id`: 用户 ID (用于查询私有模板)

**响应**:
```json
{
  "templates": [
    {
      "template_id": "global_meeting_minutes_v1",
      "title": "标准会议纪要",
      "description": "生成包含摘要、关键要点和行动项的标准会议纪要",
      "prompt_body": "你是一个专业的会议纪要助手...",
      "artifact_type": "meeting_minutes",
      "supported_languages": ["zh-CN", "en-US"],
      "parameter_schema": {
        "meeting_description": {
          "type": "string",
          "required": false,
          "default": "",
          "description": "会议描述信息"
        }
      },
      "is_system": true,
      "scope": "global",
      "scope_id": null,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

#### GET /api/v1/prompt-templates/{template_id}
获取模板详情

**查询参数**:
- `user_id`: 用户 ID (用于验证私有模板权限)

**响应**:
```json
{
  "template": {
    "template_id": "global_meeting_minutes_v1",
    "title": "标准会议纪要",
    "description": "生成包含摘要、关键要点和行动项的标准会议纪要",
    "prompt_body": "你是一个专业的会议纪要助手...",
    "artifact_type": "meeting_minutes",
    "supported_languages": ["zh-CN", "en-US"],
    "parameter_schema": {...},
    "is_system": true,
    "scope": "global"
  }
}
```

#### POST /api/v1/prompt-templates
创建私有模板

**查询参数**:
- `user_id`: 用户 ID (创建者)

**请求**:
```json
{
  "title": "我的自定义会议纪要模板",
  "description": "适用于技术团队的会议纪要",
  "prompt_body": "你是一个专业的会议纪要助手。\n\n会议信息:\n{meeting_description}\n\n请生成技术导向的会议纪要...",
  "artifact_type": "meeting_minutes",
  "supported_languages": ["zh-CN", "en-US"],
  "parameter_schema": {
    "meeting_description": {
      "type": "string",
      "required": false,
      "default": "",
      "description": "会议描述信息"
    }
  }
}
```

**响应**:
```json
{
  "success": true,
  "template_id": "tpl_abc123def456",
  "message": "提示词模板已创建"
}
```

**错误响应**:
```json
{
  "detail": "参数验证失败"  // 400
}
{
  "detail": "未登录"  // 401
}
{
  "detail": "模板内容格式错误"  // 422
}
```

#### PUT /api/v1/prompt-templates/{template_id}
更新私有模板

**查询参数**:
- `user_id`: 用户 ID (用于验证权限)

**请求** (所有字段可选):
```json
{
  "title": "更新后的标题",
  "description": "更新后的描述",
  "prompt_body": "更新后的提示词正文...",
  "supported_languages": ["zh-CN"],
  "parameter_schema": {...}
}
```

**响应**:
```json
{
  "success": true,
  "message": "提示词模板已更新"
}
```

**错误响应**:
```json
{
  "detail": "无权修改此模板"  // 403 - 不是创建者或尝试修改系统模板
}
{
  "detail": "提示词模板不存在"  // 404
}
```

**权限说明**:
- 只能更新自己创建的私有模板
- 不能更新系统模板 (scope=global)
- 不能更新其他用户的私有模板

#### DELETE /api/v1/prompt-templates/{template_id}
删除私有模板

**查询参数**:
- `user_id`: 用户 ID (用于验证权限)

**响应**:
```json
{
  "success": true,
  "message": "提示词模板已删除"
}
```

**错误响应**:
```json
{
  "detail": "无权删除此模板"  // 403
}
{
  "detail": "提示词模板不存在"  // 404
}
{
  "detail": "模板正在被使用中"  // 409 (可选检查)
}
```

**权限说明**:
- 只能删除自己创建的私有模板
- 不能删除系统模板
- 不能删除其他用户的私有模板

#### 模板权限范围总结

| 模板类型 | scope | 可读 | 可修改 | 可删除 |
|---------|-------|------|--------|--------|
| 系统模板 | global | ✅ 所有用户 | ❌ 不可修改 | ❌ 不可删除 |
| 私有模板 | private | ✅ 仅创建者 | ✅ 仅创建者 | ✅ 仅创建者 |

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

### 文件夹管理 ✨ 新增

**重要说明**: 
- 文件夹为**扁平结构**（单层），不支持嵌套。类似标签系统，但仍称为"文件夹"
- ✅ 文件夹会持久化到数据库，刷新后不会消失
- ✅ 移除所有本地 fallback 逻辑，直接调用后端接口

#### GET /api/v1/folders
列出用户的所有文件夹

**响应**:
```json
{
  "items": [
    {
      "folder_id": "folder_abc123",
      "name": "2024年会议",
      "parent_id": null,
      "owner_user_id": "user_123",
      "owner_tenant_id": "tenant_456",
      "created_at": "2026-01-16T10:00:00Z",
      "updated_at": "2026-01-16T10:00:00Z"
    },
    {
      "folder_id": "folder_def456",
      "name": "产品规划",
      "parent_id": null,
      "owner_user_id": "user_123",
      "owner_tenant_id": "tenant_456",
      "created_at": "2026-01-16T10:05:00Z",
      "updated_at": "2026-01-16T10:05:00Z"
    }
  ],
  "total": 2
}
```

**说明**:
- 返回扁平的文件夹列表（所有 `parent_id` 均为 `null`）
- 按创建时间倒序排列
- 每个会话只能属于一个文件夹

**使用示例**:
```typescript
// 获取所有文件夹
const { items: folders } = await api.listFolders();

// 直接显示为列表，无需构建树形结构
folders.forEach(folder => {
  console.log(`${folder.name} (${folder.folder_id})`);
});
```

#### POST /api/v1/folders
创建文件夹

**请求**:
```json
{
  "name": "2024年会议"
}
```

**响应**:
```json
{
  "success": true,
  "folder_id": "folder_abc123",
  "message": "文件夹已创建"
}
```

**说明**:
- 不支持 `parent_id` 参数（扁平结构）
- 所有文件夹都在根级别
- ✅ 创建后会持久化到数据库，刷新后仍存在

**使用示例**:
```typescript
// ❌ 不要使用本地占位逻辑
// const localFolders = ref([]);
// localFolders.value.push({ id: Date.now(), name: '新文件夹' });

// ✅ 直接调用后端接口
const result = await api.post('/folders', { name: '2024年会议' });
console.log('文件夹已创建:', result.folder_id);

// 刷新文件夹列表
const folders = await api.get('/folders');
```

#### PATCH /api/v1/folders/{folder_id}
重命名文件夹

**请求**:
```json
{
  "name": "2024年重要会议"
}
```

**响应**:
```json
{
  "success": true,
  "message": "文件夹已更新"
}
```

**错误响应**:
```json
{
  "detail": "文件夹不存在"  // 404
}
{
  "detail": "无权访问此文件夹"  // 403
}
```

#### DELETE /api/v1/folders/{folder_id}
删除文件夹

**响应**:
```json
{
  "success": true,
  "message": "文件夹已删除，3 个会话已移至根目录"
}
```

**错误响应**:
```json
{
  "detail": "文件夹不存在"  // 404
}
{
  "detail": "无权访问此文件夹"  // 403
}
```

**删除行为**:
- 删除文件夹时，该文件夹下的所有会话自动移到根目录（`folder_id=null`）
- 不需要 `force` 参数（扁平结构无子文件夹）

**使用示例**:
```typescript
// 删除文件夹（会话自动移到根目录）
await api.deleteFolder(folderId);
```

### 会话移动和回收站 ✨ 新增

**⚠️ 注意**: 如果你的前端使用了占位接口 `PATCH /tasks/{id}/move`，请更新为 `PATCH /sessions/{id}/move`

#### PATCH /api/v1/sessions/{task_id}/move
移动会话到文件夹

**请求**:
```json
{
  "folder_id": "folder_abc123"
}
```

**响应**:
```json
{
  "success": true,
  "message": "会话已移动"
}
```

**说明**:
- `folder_id` 为 `null` 表示移到根目录（无文件夹）
- 验证目标文件夹存在且属于当前用户

**使用示例**:
```typescript
// ❌ 旧的占位接口（不要使用）
// await api.patch(`/tasks/${taskId}/move`, { folder_id: folderId });

// ✅ 真实接口
await api.patch(`/sessions/${taskId}/move`, { folder_id: 'folder_abc123' });

// 移到根目录
await api.patch(`/sessions/${taskId}/move`, { folder_id: null });
```

#### PATCH /api/v1/sessions/{task_id}/delete
软删除会话（移入回收站）

**响应**:
```json
{
  "success": true,
  "message": "会话已移至回收站"
}
```

**说明**:
- 设置 `is_deleted=true`
- 记录 `deleted_at` 时间戳
- 保留 `folder_id`（还原时恢复到原文件夹）

#### PATCH /api/v1/sessions/{task_id}/restore
还原会话

**响应**:
```json
{
  "success": true,
  "message": "会话已还原"
}
```

**说明**:
- 设置 `is_deleted=false`
- 清除 `deleted_at`
- 保留原 `folder_id`

#### DELETE /api/v1/sessions/{task_id}
彻底删除会话

**响应**:
```json
{
  "success": true,
  "message": "会话已彻底删除"
}
```

**警告**:
- 物理删除，不可恢复
- 删除所有关联数据（转写、说话人映射、衍生内容）

#### GET /api/v1/trash/sessions
列出回收站会话

**⚠️ 注意**: 如果你的前端使用了占位接口 `GET /tasks/trash`，请更新为 `GET /trash/sessions`

**响应**:
```json
{
  "items": [
    {
      "task_id": "task_abc123",
      "user_id": "user_123",
      "tenant_id": "tenant_456",
      "meeting_type": "weekly_sync",
      "folder_id": "folder_abc123",
      "duration": 300.5,
      "last_content_modified_at": "2026-01-16T14:30:00Z",
      "deleted_at": "2026-01-16T10:30:00Z",
      "created_at": "2026-01-16T10:00:00Z"
    }
  ],
  "total": 1
}
```

**说明**:
- 仅返回当前用户的已删除会话
- 按删除时间倒序排列
- `duration` 为音频总时长（秒），从转写记录获取，未完成转写时为 null
- `last_content_modified_at` 为内容最后修改时间，用于显示"最后编辑时间"

**使用示例**:
```typescript
// ❌ 旧的占位接口（不要使用）
// await api.get('/tasks/trash');

// ✅ 真实接口
const { items: trashedSessions } = await api.get('/trash/sessions');

// 显示删除倒计时（假设30天后自动清理）
function getTimeUntilPermanentDelete(deletedAt: string): number {
  const deleteTime = new Date(deletedAt);
  const expiryTime = new Date(deleteTime.getTime() + 30 * 24 * 60 * 60 * 1000);
  return expiryTime.getTime() - Date.now();
}
```

### 批量操作 ✨ 新增

#### POST /api/v1/sessions/batch-move
批量移动会话

**请求**:
```json
{
  "task_ids": ["task_001", "task_002", "task_003"],
  "folder_id": "folder_abc123"
}
```

**响应**:
```json
{
  "success": true,
  "moved_count": 3,
  "message": "已移动 3 个会话"
}
```

**说明**:
- `folder_id` 为 `null` 表示移到根目录
- 只移动属于当前用户的会话
- 返回实际移动的数量

#### POST /api/v1/sessions/batch-delete
批量软删除会话

**请求**:
```json
{
  "task_ids": ["task_001", "task_002", "task_003"]
}
```

**响应**:
```json
{
  "success": true,
  "deleted_count": 3,
  "message": "已删除 3 个会话"
}
```

#### POST /api/v1/sessions/batch-restore
批量还原会话

**请求**:
```json
{
  "task_ids": ["task_001", "task_002", "task_003"]
}
```

**响应**:
```json
{
  "success": true,
  "restored_count": 3,
  "message": "已还原 3 个会话"
}
```

**使用示例**:
```typescript
// 批量选择和操作
const selectedTaskIds = ['task_001', 'task_002', 'task_003'];

// 批量移动到文件夹
await api.batchMoveSessions(selectedTaskIds, 'folder_abc123');

// 批量删除
await api.batchDeleteSessions(selectedTaskIds);

// 批量还原
await api.batchRestoreSessions(selectedTaskIds);
```

### 任务列表增强 ✨ 更新

#### GET /api/v1/tasks
列出任务（新增筛选参数）

**查询参数**:
- `limit`: 每页数量 (默认 100)
- `offset`: 偏移量 (默认 0)
- `state`: 状态筛选 (pending/running/success/failed)
- `folder_id`: 文件夹筛选 ✨ 新增
- `include_deleted`: 是否包含已删除任务 (默认 false) ✨ 新增

**使用示例**:
```typescript
// 获取特定文件夹的会话
const folderTasks = await api.listTasks({ folder_id: 'folder_abc123' });

// 获取根目录的会话（无文件夹）
const rootTasks = await api.listTasks({ folder_id: '' });

// 获取所有会话（包括所有文件夹）
const allTasks = await api.listTasks();

// 包含已删除的任务（用于管理员查看）
const allTasksIncludingDeleted = await api.listTasks({ include_deleted: true });
```

**说明**:
- 默认排除已删除的任务（`is_deleted=false`）
- `folder_id=""` 表示根目录（无文件夹）
- `folder_id` 未指定时返回所有文件夹的任务
- `asr_language`: 过滤语言

---

### 任务确认

#### POST /api/v1/tasks/{task_id}/confirm
确认任务并归档

**请求**:
```json
{
  "confirmation_items": {
    "key_conclusions": true,
    "responsible_persons": true,
    "action_items": true,
    "time_nodes": true
  },
  "responsible_person": {
    "id": "user_123",
    "name": "张三"
  }
}
```

**确认项说明**:
- `key_conclusions`: 关键结论已确认
- `responsible_persons`: 负责人无误
- `action_items`: 行动项已明确
- `time_nodes`: 时间节点准确

**响应**:
```json
{
  "success": true,
  "task_id": "task_abc123",
  "state": "archived",
  "confirmed_by": "user_123",
  "confirmed_by_name": "张三",
  "confirmed_at": "2026-01-16T10:30:00Z",
  "message": "任务已确认并归档"
}
```

**注意事项**:
- 所有确认项必须为 `true` 才能提交
- 确认后任务状态变为 `archived`
- 责任人信息会注入到会议纪要中作为水印

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

| HTTP 状态码 | 错误类型 | 处理方式 | 适用场景 |
|------------|---------|---------|---------|
| 400 | 请求参数错误 | 检查请求参数 | 所有接口 |
| 401 | Token 无效或过期 | 重新登录 | 所有需要认证的接口 |
| 403 | 权限不足 | 提示无权操作 | 模板修改/删除、任务访问 |
| 404 | 资源不存在 | 提示用户 | 任务、模板、衍生内容查询 |
| 409 | 资源冲突 | 提示冲突原因 | 模板删除（正在使用中） |
| 413 | 文件过大 | 提示文件大小限制 (500MB) | 文件上传 |
| 415 | 不支持的文件格式 | 提示支持的格式 (.wav, .opus, .mp3, .m4a, .ogg) | 文件上传 |
| 422 | 请求参数验证错误 | 显示验证错误 | 创建任务、创建模板 |
| 429 | 请求过多 | 降低请求频率，稍后重试 | 文件上传、API 调用 |
| 500 | 服务器错误 | 联系管理员 | 所有接口 |
| 503 | 队列服务不可用 | 稍后重试 | 创建任务 |
| 507 | 存储空间不足 | 联系管理员 | 文件上传 |

### 文件上传错误处理

```typescript
const UPLOAD_ERROR_MESSAGES = {
  400: '请求格式错误，请检查文件',
  413: '文件大小超过 500MB，请压缩后重试',
  415: '不支持的文件格式，仅支持 .wav, .opus, .mp3, .m4a, .ogg',
  429: '上传过于频繁，请稍后重试',
  503: '上传服务暂时不可用，请稍后重试',
  507: '服务器存储空间不足，请联系管理员',
};

async function handleUploadError(error: any) {
  const message = UPLOAD_ERROR_MESSAGES[error.status] || `上传失败: ${error.message}`;
  showError(message);
  
  // 429 错误时，显示重试倒计时
  if (error.status === 429) {
    const retryAfter = error.headers?.['retry-after'] || 60;
    showRetryCountdown(retryAfter);
  }
}
```

### 模板管理错误处理

```typescript
async function handleTemplateError(error: any, operation: 'create' | 'update' | 'delete') {
  if (error.status === 403) {
    if (operation === 'update') {
      showError('无权修改此模板（仅私有模板创建者可修改）');
    } else if (operation === 'delete') {
      showError('无权删除此模板（仅私有模板创建者可删除）');
    }
  } else if (error.status === 404) {
    showError('模板不存在');
  } else if (error.status === 409) {
    showError('模板正在被使用中，无法删除');
  } else if (error.status === 422) {
    showError('模板内容格式错误，请检查参数');
  } else {
    showError(`操作失败: ${error.message}`);
  }
}
```

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


---

## 会话重命名功能 ✅ 已实现

### 接口说明

**接口**: `PATCH /api/v1/tasks/{task_id}/rename`

**请求体**:
```json
{
  "name": "2024年Q1产品规划会议"
}
```

**响应**:
```json
{
  "success": true,
  "message": "任务已重命名"
}
```

**使用示例**:
```typescript
async function renameTask(taskId: string, name: string) {
  return await api.patch(`/tasks/${taskId}/rename`, { name });
}
```

**注意事项**:
- 名称长度：1-255 字符
- 名称可以为空（null），表示使用默认名称
- 重命名后会立即生效，刷新页面后保留

---

## 🚨 旧版说明（已过时）

### ~~当前状态~~

~~**问题**: 后端没有实现会话重命名接口 `PATCH /tasks/{task_id}/rename`~~

~~**影响**: 前端如果使用了占位接口，重命名后刷新会丢失~~

### ~~临时方案~~

~~1. **前端继续使用本地占位**（刷新后丢失）~~
~~2. **提示用户**："重命名功能开发中，刷新后会恢复原名称"~~
~~3. **禁用重命名功能**，等待后端实现~~

### ~~后端实现建议~~

~~如果需要实现会话重命名功能，后端需要：~~

#### ~~1. 数据库迁移~~

```python
# ✅ 已完成
# scripts/migrate_add_task_name.py
```

#### ~~2. 更新模型~~

```python
# ✅ 已完成
# src/database/models.py
class Task(Base):
    name = Column(String(255), nullable=True)  # 任务名称
```

#### ~~3. 添加接口~~

```python
# ✅ 已完成
# src/api/routes/tasks.py
@router.patch("/{task_id}/rename")
async def rename_task(...):
    """重命名任务"""
```

#### ~~4. 添加 Schema~~

```python
# ✅ 已完成
# src/api/schemas.py
class RenameTaskRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class RenameTaskResponse(BaseModel):
    success: bool
    message: str
```

#### ~~5. 前端调用~~

```typescript
// ✅ 现在可以使用
async function renameTask(taskId: string, name: string) {
  return await api.patch(`/tasks/${taskId}/rename`, { name });
}
```

---

## 📋 前端对接检查清单

### 必须修改的地方

- [ ] **移除文件夹的本地 fallback 逻辑**
  ```typescript
  // ❌ 删除这些
  const localFolders = ref([]);
  localFolders.value.push({ ... });
  
  // ✅ 改为
  await api.post('/folders', { name: '新文件夹' });
  ```

- [ ] **移除回收站的本地 fallback 逻辑**
  ```typescript
  // ❌ 删除这些
  const localTrash = ref([]);
  
  // ✅ 改为
  const trash = await api.get('/trash/sessions');
  ```

- [ ] **更新会话移动接口路径**
  ```typescript
  // ❌ 旧路径
  await api.patch(`/tasks/${taskId}/move`, { folder_id });
  
  // ✅ 新路径
  await api.patch(`/sessions/${taskId}/move`, { folder_id });
  ```

- [ ] **更新回收站接口路径**
  ```typescript
  // ❌ 旧路径
  await api.get('/tasks/trash');
  
  // ✅ 新路径
  await api.get('/trash/sessions');
  ```

### 可选功能

- [x] **会话重命名** ✅ 已实现
  - 接口：`PATCH /tasks/{task_id}/rename`
  - 数据库字段已添加
  - 刷新后名称保留

### 测试清单

- [ ] 创建文件夹后刷新页面，文件夹仍存在
- [ ] 重命名文件夹后刷新页面，新名称保留
- [ ] 删除文件夹后，会话移到根目录
- [ ] 移动会话到文件夹，刷新后位置保留
- [ ] 软删除会话，在回收站中显示
- [ ] 还原会话，从回收站移除
- [ ] 彻底删除会话，数据库中删除
- [ ] 批量操作（移动/删除/还原）正常工作

---

## 🎯 快速参考：完整 API 客户端

```typescript
// api/client.ts
class MeetingAgentAPI {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = null;

  // ========================================================================
  // 文件夹管理（✅ 已实现，可直接使用）
  // ========================================================================

  async listFolders(): Promise<ListFoldersResponse> {
    return this.request('/folders');
  }

  async createFolder(name: string): Promise<CreateFolderResponse> {
    return this.request('/folders', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async renameFolder(folderId: string, name: string): Promise<UpdateFolderResponse> {
    return this.request(`/folders/${folderId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    });
  }

  async deleteFolder(folderId: string): Promise<DeleteFolderResponse> {
    return this.request(`/folders/${folderId}`, {
      method: 'DELETE',
    });
  }

  // ========================================================================
  // 会话操作（✅ 已实现，可直接使用）
  // ========================================================================

  async moveSession(taskId: string, folderId: string | null): Promise<MoveSessionResponse> {
    return this.request(`/sessions/${taskId}/move`, {
      method: 'PATCH',
      body: JSON.stringify({ folder_id: folderId }),
    });
  }

  async deleteSession(taskId: string): Promise<DeleteSessionResponse> {
    return this.request(`/sessions/${taskId}/delete`, {
      method: 'PATCH',
    });
  }

  async restoreSession(taskId: string): Promise<RestoreSessionResponse> {
    return this.request(`/sessions/${taskId}/restore`, {
      method: 'PATCH',
    });
  }

  async permanentDeleteSession(taskId: string): Promise<PermanentDeleteSessionResponse> {
    return this.request(`/sessions/${taskId}`, {
      method: 'DELETE',
    });
  }

  async listTrashSessions(): Promise<ListTrashSessionsResponse> {
    return this.request('/trash/sessions');
  }

  // ========================================================================
  // 批量操作（✅ 已实现，可直接使用）
  // ========================================================================

  async batchMoveSessions(taskIds: string[], folderId: string | null): Promise<BatchMoveSessionsResponse> {
    return this.request('/sessions/batch-move', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds, folder_id: folderId }),
    });
  }

  async batchDeleteSessions(taskIds: string[]): Promise<BatchDeleteSessionsResponse> {
    return this.request('/sessions/batch-delete', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds }),
    });
  }

  async batchRestoreSessions(taskIds: string[]): Promise<BatchRestoreSessionsResponse> {
    return this.request('/sessions/batch-restore', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds }),
    });
  }

  // ========================================================================
  // 会话重命名 ✅ 已实现，可直接使用
  // ========================================================================
  
  async renameTask(taskId: string, name: string): Promise<RenameTaskResponse> {
    return this.request(`/tasks/${taskId}/rename`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    });
  }

  // ========================================================================
  // 辅助方法
  // ========================================================================

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

    // 204 No Content
    if (response.status === 204) {
      return { success: true };
    }

    return response.json();
  }
}

export const api = new MeetingAgentAPI();
```

---

**最后更新**: 2026-01-16  
**维护者**: 后端开发团队  
**Swagger 文档**: http://localhost:8000/docs
