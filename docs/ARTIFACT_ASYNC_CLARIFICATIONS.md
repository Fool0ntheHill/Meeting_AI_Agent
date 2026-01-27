# Artifact 异步生成 - 关键设计澄清

**日期**: 2026-01-27  
**版本**: 1.0

## 概述

本文档澄清 Artifact 异步生成机制的关键设计决策，确保前后端对接时的一致性。

---

## 1. 错误信息存储位置

### ✅ 统一规则

**失败时，错误信息直接存储在 `content` 字段中，而不是 `metadata`。**

### 原因

1. **前端一致性**：前端获取 artifact 时，`content` 是必读字段，无需额外检查 `metadata`
2. **状态接口简化**：`GET /artifacts/{id}/status` 可以直接从 `content` 提取错误信息
3. **避免歧义**：单一数据源，避免前端需要同时检查两个位置

### 失败时的 content 格式（固定）

```json
{
  "error_code": "LLM_TIMEOUT",
  "error_message": "LLM 生成超时",
  "hint": "可在 Workspace 首版纪要查看已有内容"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `error_code` | string | ✅ | 结构化错误码，如 `LLM_TIMEOUT`、`LLM_API_ERROR` |
| `error_message` | string | ✅ | 用户可读的错误消息 |
| `hint` | string | ❌ | 给用户的提示或建议（可选） |

### 状态接口返回

`GET /api/v1/artifacts/{artifact_id}/status` 返回：

```json
{
  "artifact_id": "artifact_abc123",
  "state": "failed",
  "created_at": "2026-01-27T10:00:00Z",
  "error": {
    "code": "LLM_TIMEOUT",
    "message": "LLM 生成超时",
    "hint": "可在 Workspace 首版纪要查看已有内容"
  }
}
```

**注意**：`error` 对象直接从 `content` 中提取，字段名保持一致。

---

## 2. HTTP 状态码

### ✅ 生成/重新生成接口返回 202 Accepted

```http
POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate
→ HTTP 202 Accepted

POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/regenerate
→ HTTP 202 Accepted
```

### 原因

1. **语义准确**：202 表示"请求已接受，但处理尚未完成"
2. **REST 最佳实践**：201 Created 通常表示资源已完全创建，但异步场景下内容尚未生成
3. **前端预期**：202 明确告知前端需要轮询状态

### 对比

| 状态码 | 含义 | 适用场景 |
|--------|------|----------|
| 201 Created | 资源已创建完成 | 同步创建，内容已生成 |
| 202 Accepted | 请求已接受，处理中 | 异步处理，内容生成中 |

---

## 3. 占位 Artifact 必须有 ID

### ✅ 保证

1. **立即分配 ID**：占位 artifact 在创建时立即分配 `artifact_id`
2. **立即返回 ID**：生成接口立即返回 `artifact_id`（不等待 LLM 生成）
3. **前端可用**：前端可以立即使用 `artifact_id` 进行轮询和 Tab 占位

### 实现流程

```python
# 1. 立即生成 artifact_id（不等待 LLM）
artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"

# 2. 创建占位 artifact（state=processing）
artifact_repo.create_placeholder(
    artifact_id=artifact_id,  # 使用预生成的 ID
    task_id=task_id,
    state="processing",
    content={"status": "generating", "message": "内容生成中..."},
    ...
)

# 3. 提交数据库
db.commit()

# 4. 立即返回给前端（HTTP 202）
return {
    "success": True,
    "artifact_id": artifact_id,  # 前端可以立即使用
    "state": "processing",
    "version": new_version,
    ...
}

# 5. 启动后台任务（不阻塞响应）
asyncio.create_task(_generate_artifact_async(...))
```

### 前端使用

```typescript
// 1. 发起生成请求
const response = await fetch('/api/v1/tasks/xxx/artifacts/meeting_minutes/generate', {
  method: 'POST',
  body: JSON.stringify({...})
});

// 2. 立即获得 artifact_id（不等待生成完成）
const { artifact_id, state } = await response.json();
// artifact_id: "artifact_abc123"
// state: "processing"

// 3. 立即创建 Tab 占位
createTab(artifact_id, "生成中...");

// 4. 开始轮询状态
pollStatus(artifact_id);
```

---

## 4. 前端轮询策略

### 推荐实现

```typescript
async function pollArtifactStatus(artifactId: string) {
  const maxAttempts = 60;  // 最多轮询 60 次
  const interval = 1000;   // 每秒轮询一次
  
  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch(`/api/v1/artifacts/${artifactId}/status`);
    const { state, error } = await response.json();
    
    if (state === 'success') {
      // 获取完整内容
      await fetchArtifactContent(artifactId);
      return;
    } else if (state === 'failed') {
      // 显示错误
      showError(error.message, error.hint);
      return;
    }
    
    // 继续轮询
    await sleep(interval);
  }
  
  // 超时
  showError('生成超时，请稍后重试');
}
```

### 优化：指数退避

```typescript
let pollInterval = 1000;  // 初始 1 秒
const maxInterval = 5000; // 最大 5 秒

async function pollWithBackoff(artifactId: string) {
  while (true) {
    const { state, error } = await fetchStatus(artifactId);
    
    if (state === 'success' || state === 'failed') {
      break;
    }
    
    await sleep(pollInterval);
    pollInterval = Math.min(pollInterval * 1.2, maxInterval);
  }
}
```

---

## 5. 完整 API 流程示例

### 场景：生成会议纪要

```
1. 前端发起请求
   POST /api/v1/tasks/task_123/artifacts/meeting_minutes/generate
   Body: { prompt_instance: {...}, name: "会议纪要" }
   
   ↓

2. 后端立即响应（HTTP 202）
   {
     "artifact_id": "artifact_abc123",
     "state": "processing",
     "version": 1,
     "content": {"status": "generating", "message": "内容生成中..."}
   }
   
   ↓

3. 前端创建 Tab 占位
   Tab ID: artifact_abc123
   显示: "会议纪要（生成中...）"
   
   ↓

4. 前端开始轮询（每秒一次）
   GET /api/v1/artifacts/artifact_abc123/status
   
   ↓

5a. 生成成功
    {
      "state": "success",
      "artifact_id": "artifact_abc123",
      "created_at": "..."
    }
    
    → 前端获取完整内容
    GET /api/v1/artifacts/artifact_abc123
    
    → 显示会议纪要

5b. 生成失败
    {
      "state": "failed",
      "artifact_id": "artifact_abc123",
      "created_at": "...",
      "error": {
        "code": "LLM_TIMEOUT",
        "message": "LLM 生成超时",
        "hint": "可在 Workspace 首版纪要查看已有内容"
      }
    }
    
    → 前端显示错误提示
```

---

## 6. 常见错误码

| 错误码 | 说明 | 可重试 | 提示 |
|--------|------|--------|------|
| `LLM_TIMEOUT` | LLM 生成超时 | ✅ | 请稍后重试 |
| `LLM_API_ERROR` | LLM API 错误 | ✅ | LLM 服务暂时不可用 |
| `LLM_RATE_LIMIT` | LLM API 限流 | ✅ | 请求过于频繁，请稍后重试 |
| `INVALID_PROMPT` | 提示词无效 | ❌ | 请检查提示词配置 |
| `TRANSCRIPT_NOT_FOUND` | 转写记录不存在 | ❌ | 任务转写未完成 |
| `UNKNOWN_ERROR` | 未知错误 | ✅ | 生成失败，请重试 |

---

## 7. 前端 TypeScript 类型定义

```typescript
// 生成响应
interface GenerateArtifactResponse {
  success: boolean;
  artifact_id: string;
  version: number;
  content: {
    status: string;
    message: string;
  };
  display_name: string;
  state: 'processing' | 'success' | 'failed';
  message: string;
}

// 状态响应
interface ArtifactStatusResponse {
  artifact_id: string;
  state: 'processing' | 'success' | 'failed';
  created_at: string;
  error?: {
    code: string;      // 必填
    message: string;   // 必填
    hint?: string;     // 可选
  };
}

// 完整 Artifact（成功时）
interface Artifact {
  artifact_id: string;
  task_id: string;
  artifact_type: string;
  version: number;
  content: {
    title: string;
    summary: string;
    // ... 其他字段
  };
  // ...
}

// 完整 Artifact（失败时）
interface FailedArtifact {
  artifact_id: string;
  task_id: string;
  artifact_type: string;
  version: number;
  content: {
    error_code: string;
    error_message: string;
    hint?: string;
  };
  // ...
}
```

---

## 8. 测试检查清单

### 后端测试

- [ ] 生成接口返回 202 Accepted
- [ ] 响应中包含 `artifact_id`（非空）
- [ ] 响应中 `state` 为 `processing`
- [ ] 占位 artifact 已写入数据库
- [ ] 后台任务已启动（不阻塞响应）
- [ ] 失败时错误信息在 `content` 中（不在 `metadata`）
- [ ] 状态接口返回正确的错误结构

### 前端测试

- [ ] 收到 202 响应后立即创建 Tab
- [ ] 使用 `artifact_id` 进行轮询
- [ ] 轮询间隔合理（1-2 秒）
- [ ] 成功时获取完整内容并显示
- [ ] 失败时显示错误消息和提示
- [ ] 超时处理（60 秒后停止轮询）

---

## 9. 相关文档

- [完整实现指南](./ARTIFACT_ASYNC_GENERATION_GUIDE.md)
- [API 快速参考](./ARTIFACT_ASYNC_API_REFERENCE.md)
- [前端集成指南](./api_references/FRONTEND_INTEGRATION_GUIDE.md)

---

**维护者**: Kiro AI Assistant  
**最后更新**: 2026-01-27
