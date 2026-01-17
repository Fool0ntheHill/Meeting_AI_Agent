# API 快速参考 - 真实接口速查表

**最后更新**: 2026-01-16  
**后端地址**: `http://localhost:8000/api/v1`  
**认证方式**: `Authorization: Bearer {token}`

---

## 📁 文件夹 CRUD

### 1. 列出文件夹

```http
GET /api/v1/folders
Authorization: Bearer {token}
```

**响应示例**:
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
    }
  ],
  "total": 1
}
```

**字段说明**:
- `parent_id`: 始终为 `null`（扁平结构，不支持嵌套）

---

### 2. 创建文件夹

```http
POST /api/v1/folders
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "2024年会议"
}
```

**请求字段**:
- `name` (string, 必填): 文件夹名称
- ❌ **不支持** `parent_id` 字段（扁平结构）

**响应示例**:
```json
{
  "success": true,
  "folder_id": "folder_abc123",
  "message": "文件夹已创建"
}
```

**错误响应**:
- `409 Conflict`: 文件夹名称已存在
  ```json
  {
    "detail": "文件夹名称已存在: 2024年会议"
  }
  ```

---

### 3. 重命名文件夹

```http
PATCH /api/v1/folders/{folder_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "2024年重要会议"
}
```

**请求字段**:
- `name` (string, 必填): 新名称

**响应示例**:
```json
{
  "success": true,
  "message": "文件夹已更新"
}
```

**错误响应**:
- `409 Conflict`: 新名称与其他文件夹重名
  ```json
  {
    "detail": "文件夹名称已存在: 2024年重要会议"
  }
  ```

---

### 4. 删除文件夹

```http
DELETE /api/v1/folders/{folder_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "message": "文件夹已删除，3 个会话已移至根目录"
}
```

**行为说明**:
- 删除文件夹时，该文件夹下的所有会话自动移到根目录（`folder_id=null`）
- ❌ **不需要** `force` 参数（扁平结构无子文件夹）

---

## 📝 任务操作

### ⚠️ 删除接口说明

后端提供了两种删除方式：

1. **软删除（推荐）**: `PATCH /api/v1/sessions/{task_id}/delete` - 移入回收站，可恢复
2. **硬删除（慎用）**: `DELETE /api/v1/tasks/{task_id}` - 直接删除，不可恢复

**前端应该使用软删除**，硬删除接口仅供特殊场景使用。

---

### 1. 重命名任务

```http
PATCH /api/v1/tasks/{task_id}/rename
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "2024年Q1产品规划会议"
}
```

**请求字段**:
- `name` (string, 必填): 新名称，1-255 字符

**响应示例**:
```json
{
  "success": true,
  "message": "任务已重命名"
}
```

---

### 2. 移动任务到文件夹

```http
PATCH /api/v1/sessions/{task_id}/move
Authorization: Bearer {token}
Content-Type: application/json

{
  "folder_id": "folder_abc123"
}
```

**请求字段**:
- `folder_id` (string | null, 必填): 目标文件夹 ID
  - 字符串: 移动到指定文件夹
  - `null`: 移动到根目录（无文件夹）
- ❌ **不使用** `folder_path` 字段

**响应示例**:
```json
{
  "success": true,
  "message": "会话已移动"
}
```

**移动到根目录示例**:
```json
{
  "folder_id": null
}
```

---

### 3. 软删除任务（单个）⭐ 推荐使用

```http
PATCH /api/v1/sessions/{task_id}/delete
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "message": "会话已移至回收站"
}
```

---

### 4. 批量软删除任务

```http
POST /api/v1/sessions/batch-delete
Authorization: Bearer {token}
Content-Type: application/json

{
  "task_ids": ["task_001", "task_002", "task_003"]
}
```

**请求字段**:
- `task_ids` (array, 必填): 任务 ID 列表

**响应示例**:
```json
{
  "success": true,
  "deleted_count": 3,
  "message": "已删除 3 个会话"
}
```

---

### 5. 还原任务（单个）

```http
PATCH /api/v1/sessions/{task_id}/restore
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "message": "会话已还原"
}
```

---

### 6. 批量还原任务

```http
POST /api/v1/sessions/batch-restore
Authorization: Bearer {token}
Content-Type: application/json

{
  "task_ids": ["task_001", "task_002", "task_003"]
}
```

**响应示例**:
```json
{
  "success": true,
  "restored_count": 3,
  "message": "已还原 3 个会话"
}
```

---

### 7. 彻底删除任务（单个）

```http
DELETE /api/v1/sessions/{task_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "message": "会话已彻底删除"
}
```

⚠️ **警告**: 物理删除，不可恢复！

---

## 📋 任务列表（包含文件夹信息）

### 获取任务列表

```http
GET /api/v1/tasks?folder_id=folder_abc123&include_deleted=false&state=success&limit=20&offset=0
Authorization: Bearer {token}
```

**查询参数**:
- `folder_id` (string, 可选): 文件夹筛选
  - 不传: 返回所有文件夹的任务
  - `""` (空字符串): 仅返回根目录任务
  - `"folder_xxx"`: 返回指定文件夹的任务
- `include_deleted` (boolean, 可选): 是否包含已删除任务，默认 `false`
- `state` (string, 可选): 状态筛选 (`pending`/`running`/`success`/`failed`)
- `limit` (number, 可选): 每页数量，默认 100
- `offset` (number, 可选): 偏移量，默认 0

**响应示例**:
```json
[
  {
    "task_id": "task_abc123",
    "user_id": "user_123",
    "tenant_id": "tenant_456",
    "name": "产品规划会议",
    "meeting_type": "weekly_sync",
    "audio_files": ["uploads/user_123/meeting.wav"],
    "file_order": [0],
    "asr_language": "zh-CN+en-US",
    "output_language": "zh-CN",
    "state": "success",
    "progress": 100,
    "error_details": null,
    "folder_id": "folder_abc123",
    "duration": 300.5,
    "created_at": "2026-01-16T10:00:00Z",
    "updated_at": "2026-01-16T10:15:00Z",
    "completed_at": "2026-01-16T10:15:00Z",
    "last_content_modified_at": "2026-01-16T14:30:00Z"
  }
]
```

**关键字段说明**:
- `folder_id` (string | null): 
  - 字符串: 任务所属文件夹 ID
  - `null`: 任务在根目录（无文件夹）
  - ❌ **不返回** `folder_path` 或 `folder_name` 字段
- `name` (string | null): 任务名称，`null` 时前端显示默认名称
- `duration` (number | null): 音频总时长（秒），未完成转写时为 `null`
- `last_content_modified_at` (string | null): 内容最后修改时间
- `updated_at` (string): 任务任何字段更新时间

---

## 🗑️ 回收站

### 列出回收站

```http
GET /api/v1/trash/sessions
Authorization: Bearer {token}
```

**响应示例**（实际数据）:
```json
{
  "items": [
    {
      "task_id": "task_bfb9662a3d0a435d",
      "user_id": "user_test_user",
      "tenant_id": "tenant_test_user",
      "meeting_type": "integration_test",
      "folder_id": null,
      "duration": null,
      "last_content_modified_at": "2026-01-15T19:19:11.149477",
      "deleted_at": "2026-01-17T08:48:41.889384",
      "created_at": "2026-01-15T19:19:11.149477"
    },
    {
      "task_id": "task_integration_test_completed",
      "user_id": "user_test_user",
      "tenant_id": "tenant_test_user",
      "meeting_type": "common",
      "folder_id": null,
      "duration": 10.0,
      "last_content_modified_at": "2026-01-16T03:55:58.609275",
      "deleted_at": "2026-01-16T14:24:48.157225",
      "created_at": "2026-01-16T03:55:58.609275"
    }
  ],
  "total": 2
}
```

**字段说明**:
- `folder_id` (string | null): 删除前所属的文件夹 ID（还原时恢复到此文件夹），`null` 表示在根目录
- `duration` (number | null): 音频时长（秒），`null` 表示没有转写记录
- `last_content_modified_at` (string | null): 内容最后修改时间，`null` 表示从未修改
- `deleted_at` (string): 删除时间（ISO 8601 格式）
- `created_at` (string): 创建时间（ISO 8601 格式）

---

## 🔄 批量移动

```http
POST /api/v1/sessions/batch-move
Authorization: Bearer {token}
Content-Type: application/json

{
  "task_ids": ["task_001", "task_002", "task_003"],
  "folder_id": "folder_abc123"
}
```

**请求字段**:
- `task_ids` (array, 必填): 任务 ID 列表
- `folder_id` (string | null, 必填): 目标文件夹 ID（`null` = 根目录）

**响应示例**:
```json
{
  "success": true,
  "moved_count": 3,
  "message": "已移动 3 个会话"
}
```

---

## 📊 字段对照表

### 文件夹相关字段

| 前端可能用的名称 | 后端实际字段 | 类型 | 说明 |
|----------------|------------|------|------|
| folderId | `folder_id` | string \| null | 文件夹 ID |
| folderName | ❌ 不返回 | - | 需要前端自己维护映射 |
| folderPath | ❌ 不返回 | - | 不使用路径概念 |
| parentId | `parent_id` | null | 始终为 null（扁平结构） |

### 任务相关字段

| 前端可能用的名称 | 后端实际字段 | 类型 | 说明 |
|----------------|------------|------|------|
| taskId | `task_id` | string | 任务 ID |
| taskName | `name` | string \| null | 任务名称 |
| folderId | `folder_id` | string \| null | 所属文件夹 ID |
| duration | `duration` | number \| null | 音频时长（秒） |
| lastModified | `last_content_modified_at` | string \| null | 内容修改时间 |
| updatedAt | `updated_at` | string | 任务更新时间 |

---

## 🎯 前端实现建议

### 1. 获取文件夹名称

后端只返回 `folder_id`，不返回 `folder_name`。前端需要：

```typescript
// 1. 先获取文件夹列表
const { items: folders } = await api.get('/folders');

// 2. 建立 ID 到名称的映射
const folderMap = new Map(
  folders.map(f => [f.folder_id, f.name])
);

// 3. 在任务列表中使用
tasks.forEach(task => {
  const folderName = task.folder_id 
    ? folderMap.get(task.folder_id) || '未知文件夹'
    : '根目录';
  console.log(`${task.name} - ${folderName}`);
});
```

### 2. 显示任务名称

```typescript
function getDisplayName(task: Task): string {
  return task.name || `会议 - ${formatDate(task.created_at)}`;
}
```

### 3. 筛选文件夹任务

```typescript
// 获取特定文件夹的任务
const folderTasks = await api.get(`/tasks?folder_id=${folderId}`);

// 获取根目录任务
const rootTasks = await api.get('/tasks?folder_id=');

// 获取所有任务（不筛选文件夹）
const allTasks = await api.get('/tasks');
```

---

## ⚠️ 常见错误

### 1. 使用了错误的路径

```typescript
// ❌ 错误
await api.patch(`/tasks/${taskId}/move`, { folder_id });

// ✅ 正确
await api.patch(`/sessions/${taskId}/move`, { folder_id });
```

### 2. 尝试创建嵌套文件夹

```typescript
// ❌ 错误（不支持 parent_id）
await api.post('/folders', { 
  name: '子文件夹', 
  parent_id: 'folder_xxx' 
});

// ✅ 正确（扁平结构）
await api.post('/folders', { 
  name: '新文件夹' 
});
```

### 3. 期望返回 folder_name

```typescript
// ❌ 错误（后端不返回 folder_name）
const folderName = task.folder_name;

// ✅ 正确（前端维护映射）
const folderName = folderMap.get(task.folder_id);
```

---

## 📝 完整示例代码

```typescript
// API 客户端
class MeetingAgentAPI {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = null;

  // 文件夹操作
  async listFolders() {
    return this.request('/folders');
  }

  async createFolder(name: string) {
    return this.request('/folders', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async renameFolder(folderId: string, name: string) {
    return this.request(`/folders/${folderId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    });
  }

  async deleteFolder(folderId: string) {
    return this.request(`/folders/${folderId}`, {
      method: 'DELETE',
    });
  }

  // 任务操作
  async renameTask(taskId: string, name: string) {
    return this.request(`/tasks/${taskId}/rename`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    });
  }

  async moveTask(taskId: string, folderId: string | null) {
    return this.request(`/sessions/${taskId}/move`, {
      method: 'PATCH',
      body: JSON.stringify({ folder_id: folderId }),
    });
  }

  async deleteTask(taskId: string) {
    return this.request(`/sessions/${taskId}/delete`, {
      method: 'PATCH',
    });
  }

  async restoreTask(taskId: string) {
    return this.request(`/sessions/${taskId}/restore`, {
      method: 'PATCH',
    });
  }

  async permanentDeleteTask(taskId: string) {
    return this.request(`/sessions/${taskId}`, {
      method: 'DELETE',
    });
  }

  // 批量操作
  async batchMove(taskIds: string[], folderId: string | null) {
    return this.request('/sessions/batch-move', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds, folder_id: folderId }),
    });
  }

  async batchDelete(taskIds: string[]) {
    return this.request('/sessions/batch-delete', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds }),
    });
  }

  async batchRestore(taskIds: string[]) {
    return this.request('/sessions/batch-restore', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds }),
    });
  }

  // 列表查询
  async listTasks(params?: {
    folder_id?: string;
    include_deleted?: boolean;
    state?: string;
    limit?: number;
    offset?: number;
  }) {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return this.request(`/tasks?${query}`);
  }

  async listTrash() {
    return this.request('/trash/sessions');
  }

  // 辅助方法
  private async request(endpoint: string, options: RequestInit = {}) {
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

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }

    if (response.status === 204) {
      return { success: true };
    }

    return response.json();
  }
}

export const api = new MeetingAgentAPI();
```

---

**Swagger 文档**: http://localhost:8000/docs  
**详细文档**: `docs/FRONTEND_DEVELOPMENT_GUIDE.md`
