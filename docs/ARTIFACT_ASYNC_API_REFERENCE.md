# Artifact 异步生成 API 快速参考

## 概述

Artifact 异步生成 API 允许前端立即获得响应，然后通过轮询接口实时追踪生成状态。

## API 端点

### 1. 生成新 Artifact（异步）

**端点**: `POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate`

**请求体**:
```json
{
  "prompt_instance": {
    "template_id": "tpl_meeting_minutes_zh",
    "language": "zh-CN",
    "parameters": {}
  },
  "name": "会议纪要"
}
```

**响应** (HTTP 202 Accepted):
```json
{
  "success": true,
  "artifact_id": "artifact_abc123",
  "version": 1,
  "content": {
    "status": "generating",
    "message": "内容生成中，请稍候..."
  },
  "display_name": "会议纪要",
  "state": "processing",
  "message": "衍生内容生成已启动 (版本 1)，请稍候..."
}
```

**关键点**:
- ✅ 立即返回（不等待 LLM 生成）
- ✅ HTTP 202 Accepted（异步处理）
- ✅ `state` 为 `processing`
- ✅ 返回 `artifact_id` 供后续查询（**必然存在**）

---

### 2. 重新生成 Artifact（异步）

**端点**: `POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/regenerate`

**请求体**: 同上

**响应**: 同上（版本号递增）

---

### 3. 查询 Artifact 状态（轻量级）

**端点**: `GET /api/v1/artifacts/{artifact_id}/status`

**响应** (HTTP 200):

#### 生成中
```json
{
  "artifact_id": "artifact_abc123",
  "state": "processing",
  "created_at": "2026-01-27T10:00:00Z"
}
```

#### 生成成功
```json
{
  "artifact_id": "artifact_abc123",
  "state": "success",
  "created_at": "2026-01-27T10:00:00Z"
}
```

#### 生成失败
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

**关键点**:
- ✅ 轻量级响应（不包含完整内容）
- ✅ 适合高频轮询
- ✅ 建议轮询间隔：1-2 秒
- ✅ 错误信息固定字段：`code`（必填）、`message`（必填）、`hint`（可选）

---

### 4. 获取完整 Artifact 内容

**端点**: `GET /api/v1/artifacts/{artifact_id}`

**响应** (HTTP 200):
```json
{
  "artifact": {
    "artifact_id": "artifact_abc123",
    "task_id": "task_xyz789",
    "artifact_type": "meeting_minutes",
    "version": 1,
    "prompt_instance": {...},
    "content": {
      "title": "会议纪要",
      "summary": "...",
      "key_points": [...]
    },
    "metadata": {...},
    "created_at": "2026-01-27T10:00:00Z",
    "created_by": "user_001"
  }
}
```

**关键点**:
- ✅ 包含完整内容
- ✅ 仅在 `state=success` 时调用
- ✅ 失败时 content 包含错误信息

---

## 前端集成示例

### React/TypeScript

```typescript
import { useState, useEffect } from 'react';

interface ArtifactStatus {
  artifact_id: string;
  state: 'processing' | 'success' | 'failed';
  created_at: string;
  error?: {
    code: string;
    message: string;
  };
}

function useArtifactGeneration(taskId: string, artifactType: string) {
  const [status, setStatus] = useState<ArtifactStatus | null>(null);
  const [artifact, setArtifact] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const generate = async (promptInstance: any, name: string) => {
    try {
      // 1. 发起生成请求
      const response = await fetch(
        `/api/v1/tasks/${taskId}/artifacts/${artifactType}/generate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ prompt_instance: promptInstance, name })
        }
      );

      const result = await response.json();
      const artifactId = result.artifact_id;

      // 2. 开始轮询状态
      pollStatus(artifactId);
    } catch (err) {
      setError(err.message);
    }
  };

  const pollStatus = async (artifactId: string) => {
    try {
      const response = await fetch(
        `/api/v1/artifacts/${artifactId}/status`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      const statusData: ArtifactStatus = await response.json();
      setStatus(statusData);

      if (statusData.state === 'success') {
        // 获取完整内容
        fetchArtifact(artifactId);
      } else if (statusData.state === 'failed') {
        setError(statusData.error?.message || '生成失败');
      } else if (statusData.state === 'processing') {
        // 继续轮询
        setTimeout(() => pollStatus(artifactId), 1000);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const fetchArtifact = async (artifactId: string) => {
    try {
      const response = await fetch(
        `/api/v1/artifacts/${artifactId}`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      const data = await response.json();
      setArtifact(data.artifact);
    } catch (err) {
      setError(err.message);
    }
  };

  return { generate, status, artifact, error };
}

// 使用示例
function ArtifactGenerator() {
  const { generate, status, artifact, error } = useArtifactGeneration(
    'task_123',
    'meeting_minutes'
  );

  const handleGenerate = () => {
    generate(
      {
        template_id: 'tpl_meeting_minutes_zh',
        language: 'zh-CN',
        parameters: {}
      },
      '会议纪要'
    );
  };

  return (
    <div>
      <button onClick={handleGenerate}>生成会议纪要</button>
      
      {status?.state === 'processing' && (
        <div>生成中，请稍候...</div>
      )}
      
      {status?.state === 'success' && artifact && (
        <div>
          <h2>{artifact.content.title}</h2>
          <p>{artifact.content.summary}</p>
        </div>
      )}
      
      {error && <div className="error">{error}</div>}
    </div>
  );
}
```

---

## 状态转换图

```
[用户发起请求]
      ↓
[创建占位 artifact]
      ↓
  processing ──────→ success (生成成功)
      │
      └──────────→ failed (生成失败)
```

---

## 错误码

| 错误码 | 说明 | 可重试 |
|--------|------|--------|
| `LLM_TIMEOUT` | LLM 生成超时 | ✅ |
| `LLM_API_ERROR` | LLM API 错误 | ✅ |
| `LLM_RATE_LIMIT` | LLM API 限流 | ✅ |
| `INVALID_PROMPT` | 提示词无效 | ❌ |
| `TRANSCRIPT_NOT_FOUND` | 转写记录不存在 | ❌ |

---

## 最佳实践

### 1. 轮询策略

```typescript
// 推荐：指数退避
let pollInterval = 1000; // 初始 1 秒
let maxInterval = 5000;  // 最大 5 秒

const poll = async () => {
  const status = await fetchStatus(artifactId);
  
  if (status.state === 'processing') {
    pollInterval = Math.min(pollInterval * 1.2, maxInterval);
    setTimeout(poll, pollInterval);
  }
};
```

### 2. 超时处理

```typescript
const MAX_POLL_TIME = 60000; // 60 秒
const startTime = Date.now();

const poll = async () => {
  if (Date.now() - startTime > MAX_POLL_TIME) {
    setError('生成超时，请稍后重试');
    return;
  }
  
  // 继续轮询...
};
```

### 3. 用户体验

```typescript
// 显示进度提示
<div className="generating">
  <Spinner />
  <p>正在生成会议纪要...</p>
  <p className="hint">预计需要 10-30 秒</p>
</div>
```

---

## 相关文档

- [完整实现指南](./ARTIFACT_ASYNC_GENERATION_GUIDE.md)
- [前端集成指南](./FRONTEND_INTEGRATION_GUIDE.md)
- [API 快速参考](./API_QUICK_REFERENCE.md)

---

**更新日期**: 2026-01-27
