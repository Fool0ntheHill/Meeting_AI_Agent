# 前端开发快速参考

**一页纸速查表**

---

## 🚀 快速开始

```bash
# 1. 启动后端
python main.py

# 2. 启动 Worker
python worker.py

# 3. 访问 Swagger UI
http://localhost:8000/docs
```

---

## 🔐 认证

```typescript
// 登录
POST /api/v1/auth/dev/login
Body: { "username": "test_user" }
Response: { "access_token": "...", "expires_in": 86400 }

// 使用 Token
headers: { "Authorization": "Bearer <token>" }
```

---

## 📋 核心 API

### 创建任务
```typescript
POST /api/v1/tasks
{
  "audio_files": [{ "file_path": "...", "speaker_id": "..." }],
  "meeting_type": "weekly_sync",
  "prompt_instance": {
    "template_id": "global_meeting_minutes_v1",
    "parameters": { "meeting_description": "..." }
  }
}
→ { "task_id": "task_abc123" }
```

### 查询状态
```typescript
GET /api/v1/tasks/{task_id}/status
→ {
  "state": "transcribing",
  "progress": 35.5,
  "estimated_time": 120
}
```

### 获取结果
```typescript
GET /api/v1/tasks/{task_id}/artifacts
→ {
  "artifacts_by_type": {
    "meeting_minutes": [{ "artifact_id": "...", "version": 1 }]
  }
}

GET /api/v1/artifacts/{artifact_id}
→ {
  "artifact": {
    "content": "{...}"  // JSON 字符串，需 JSON.parse()
  }
}
```

---

## 🔄 任务状态流转

```
pending → queued → running → transcribing → identifying 
  → correcting → summarizing → success
                              ↓
                            failed
```

---

## 📊 数据模型

### 会议纪要
```typescript
interface MeetingMinutes {
  title: string;
  participants: string[];
  summary: string;
  key_points: string[];
  action_items: string[];
}
```

### 任务状态
```typescript
type TaskState = 
  | 'pending' | 'queued' | 'running'
  | 'transcribing' | 'identifying' | 'correcting' | 'summarizing'
  | 'success' | 'failed';
```

---

## 🛠️ 常用操作

### 轮询任务状态
```typescript
async function pollStatus(taskId: string) {
  const interval = setInterval(async () => {
    const status = await api.getTaskStatus(taskId);
    
    if (status.state === 'success' || status.state === 'failed') {
      clearInterval(interval);
    }
  }, 5000);
}
```

### 解析 Artifact Content
```typescript
const artifact = await api.getArtifact(artifactId);
const minutes: MeetingMinutes = JSON.parse(artifact.content);
```

### 修正转写
```typescript
PUT /api/v1/tasks/{task_id}/transcript
{
  "corrected_text": "...",
  "regenerate_artifacts": true
}
```

### 重新生成
```typescript
POST /api/v1/tasks/{task_id}/artifacts/meeting_minutes/generate
{
  "prompt_instance": {
    "template_id": "tpl_002",
    "parameters": { ... }
  }
}
```

### 确认任务
```typescript
POST /api/v1/tasks/{task_id}/confirm
{
  "confirmation_items": {
    "key_conclusions": true,
    "responsible_persons": true
  },
  "responsible_person": { "id": "...", "name": "..." }
}
```

---

## ⚠️ 错误处理

| 状态码 | 含义 | 处理 |
|-------|------|------|
| 401 | Token 过期 | 重新登录 |
| 403 | 未授权 | 跳转登录页 |
| 404 | 资源不存在 | 提示用户 |
| 422 | 参数错误 | 显示验证错误 |
| 500 | 服务器错误 | 联系管理员 |

```typescript
if (error.status === 401) {
  localStorage.removeItem('access_token');
  window.location.href = '/login';
}
```

---

## 🌐 语言配置

### ASR 语言 (转写识别)
- `zh-CN`: 纯中文
- `en-US`: 纯英文
- `zh-CN+en-US`: 中英混合 ⭐ (默认)
- `ja-JP`: 日文
- `ko-KR`: 韩文

### 输出语言 (纪要生成)
- `zh-CN`: 中文 ⭐ (默认)
- `en-US`: 英文
- `ja-JP`: 日文
- `ko-KR`: 韩文

---

## 📦 推荐技术栈

- **框架**: React + TypeScript
- **UI**: Ant Design
- **状态**: Zustand
- **HTTP**: Axios
- **上传**: react-dropzone
- **编辑**: Quill
- **导出**: jsPDF, docx

---

## 🔗 相关资源

- **Swagger UI**: http://localhost:8000/docs
- **完整指南**: `docs/FRONTEND_DEVELOPMENT_GUIDE.md`
- **功能清单**: `docs/FRONTEND_FEATURE_CHECKLIST.md`
- **类型定义**: `docs/frontend-types.ts`
- **API 文档**: `docs/api_references/API_USAGE_GUIDE.md`

---

## 💡 最佳实践

1. **Token 管理**: 自动检测过期，提前刷新
2. **轮询优化**: 使用指数退避 (2s → 5s → 10s)
3. **错误处理**: 统一拦截器处理 401/403
4. **内容解析**: 安全解析 JSON，处理异常
5. **请求重试**: 网络错误自动重试 3 次

---

## 🎯 开发优先级

### P0 (必须)
- 登录认证
- 创建任务
- 查询状态
- 查看纪要

### P1 (重要)
- 任务列表
- 重新生成
- 任务确认

### P2 (增强)
- 转写编辑
- 版本管理
- 模板管理

---

**快速上手**: 复制 `docs/frontend-types.ts` 到项目，参考 `FRONTEND_DEVELOPMENT_GUIDE.md` 实现功能！
