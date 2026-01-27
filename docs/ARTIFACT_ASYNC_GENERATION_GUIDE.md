# Artifact 异步生成实现指南

## 概述

为了提升用户体验，我们实现了 artifact 异步生成机制，允许前端实时追踪生成状态。

## 关键设计决策

### 1. 错误信息存储位置

**统一规则**：失败时，错误信息**直接存储在 `content` 字段中**，而不是 `metadata`。

**原因**：
- 前端获取 artifact 时，`content` 是必读字段
- 避免前端需要同时检查 `content` 和 `metadata` 两个位置
- 状态接口 `GET /artifacts/{id}/status` 可以直接从 `content` 提取错误信息

**失败时的 content 格式（固定字段）**：

```json
{
  "error_code": "LLM_TIMEOUT",
  "error_message": "LLM 生成超时",
  "hint": "可在 Workspace 首版纪要查看已有内容"
}
```

**字段说明**：
- `error_code` (必填): 结构化错误码，如 `LLM_TIMEOUT`、`LLM_API_ERROR`
- `error_message` (必填): 用户可读的错误消息
- `hint` (可选): 给用户的提示或建议

### 2. HTTP 状态码

**生成/重新生成接口返回 202 Accepted**：

```
POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate
→ HTTP 202 Accepted
```

**原因**：
- 202 表示"请求已接受，但处理尚未完成"，语义更准确
- 201 Created 通常表示资源已完全创建，但异步场景下内容尚未生成
- 符合 REST API 最佳实践

### 3. 占位 Artifact 必须有 ID

**保证**：
- ✅ 占位 artifact 在创建时**立即分配** `artifact_id`
- ✅ 生成接口**立即返回** `artifact_id`（不等待 LLM 生成）
- ✅ 前端可以**立即使用** `artifact_id` 进行轮询和 Tab 占位

**流程**：
```python
# 1. 立即生成 artifact_id
artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"

# 2. 创建占位 artifact
artifact_repo.create_placeholder(
    artifact_id=artifact_id,  # 使用预生成的 ID
    task_id=task_id,
    state="processing",
    ...
)

# 3. 立即返回给前端
return {
    "artifact_id": artifact_id,  # 前端可以立即使用
    "state": "processing",
    ...
}
```

## API 流程

### 1. 生成/重新生成入口

**端点**：
- `POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}` (生成新笔记)
- `POST /api/v1/tasks/{task_id}/corrections/regenerate/{artifact_type}` (重新生成)

**流程**：

1. **创建占位 artifact**：
   ```python
   artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"
   
   # 创建占位记录
   artifact_repo.create(
       artifact_id=artifact_id,
       task_id=task_id,
       artifact_type=artifact_type,
       version=next_version,
       prompt_instance=prompt_instance.dict(),
       content=json.dumps({}),  # 空内容
       state="processing",  # 处理中
       created_by=user_id,
       metadata={},
       display_name=display_name
   )
   ```

2. **立即返回响应**：
   ```json
   {
     "success": true,
     "artifact_id": "artifact_xxx",
     "version": 2,
     "state": "processing",
     "message": "正在生成中..."
   }
   ```

3. **异步生成**：
   ```python
   # 使用 asyncio.create_task 异步执行
   asyncio.create_task(_generate_artifact_async(
       artifact_id=artifact_id,
       task_id=task_id,
       ...
   ))
   ```

4. **生成成功**：
   ```python
   # 更新 artifact
   artifact_repo.update_content_and_state(
       artifact_id=artifact_id,
       content=json.dumps(generated_content),
       state="success"
   )
   
   # 发送企微通知
   send_wecom_notification(...)
   ```

5. **生成失败**：
   ```python
   # 更新 artifact 为失败状态
   artifact_repo.update_content_and_state(
       artifact_id=artifact_id,
       content=json.dumps({
           "error_code": error_code,
           "error_message": error_message,
           "hint": "可在 Workspace 首版纪要查看已有内容"
       }),
       state="failed"
   )
   
   # 发送失败通知
   send_wecom_failure_notification(...)
   ```

### 2. 状态查询接口

**端点**：`GET /api/v1/artifacts/{artifact_id}/status`

**响应**：
```json
{
  "artifact_id": "artifact_xxx",
  "state": "processing|success|failed",
  "version": 2,
  "display_name": "会议纪要",
  "created_at": "2026-01-27T16:00:00",
  "error": {
    "error_code": "LLM_TIMEOUT",
    "error_message": "LLM 生成超时",
    "hint": "可在 Workspace 首版纪要查看已有内容"
  }
}
```

**使用场景**：
- 前端轮询查询生成状态
- 前端根据状态显示不同 UI（加载中、成功、失败）

### 3. 详情接口增强

**端点**：`GET /api/v1/artifacts/{artifact_id}`

**响应增强**：
```json
{
  "artifact": {
    "artifact_id": "artifact_xxx",
    "state": "success",
    "content": {...},
    ...
  }
}
```

## Repository 层新增方法

### ArtifactRepository

```python
def create_placeholder(
    self,
    artifact_id: str,
    task_id: str,
    artifact_type: str,
    version: int,
    prompt_instance: dict,
    created_by: str,
    display_name: Optional[str] = None
) -> GeneratedArtifactRecord:
    """创建占位 artifact（state=processing）"""
    pass

def update_content_and_state(
    self,
    artifact_id: str,
    content: str,
    state: str
) -> bool:
    """更新 artifact 内容和状态"""
    pass

def get_status(
    self,
    artifact_id: str
) -> Optional[dict]:
    """获取 artifact 状态"""
    pass
```

## 前端集成

### 1. 调用生成 API

```typescript
const response = await fetch(`/api/v1/tasks/${taskId}/artifacts/meeting_minutes`, {
  method: 'POST',
  body: JSON.stringify({
    name: "会议纪要",
    prompt_instance: {...}
  })
});

const { artifact_id, state } = await response.json();

// 立即创建 tab（占位）
createArtifactTab(artifact_id, "会议纪要", state);
```

### 2. 轮询状态

```typescript
const pollStatus = async (artifactId: string) => {
  const response = await fetch(`/api/v1/artifacts/${artifactId}/status`);
  const { state, error } = await response.json();
  
  if (state === "processing") {
    // 显示加载中
    showLoading(artifactId);
    setTimeout(() => pollStatus(artifactId), 2000); // 2秒后再次查询
  } else if (state === "success") {
    // 加载完整内容
    loadArtifactContent(artifactId);
  } else if (state === "failed") {
    // 显示错误
    showError(artifactId, error);
  }
};
```

### 3. UI 状态

- **processing**: 显示骨架屏或加载动画
- **success**: 显示完整内容
- **failed**: 显示错误提示 + 重试按钮

## 优势

1. **即时反馈**：用户立即看到 tab，不需要等待生成完成
2. **状态可见**：用户可以看到生成进度
3. **错误处理**：失败时有明确的错误信息和提示
4. **并发支持**：可以同时生成多个 artifact
5. **向后兼容**：现有 artifact 的 state 默认为 "success"

## 迁移步骤

1. 运行数据库迁移：`python scripts/migrate_add_artifact_state.py`
2. 更新 repository 层代码
3. 更新 API 端点代码
4. 添加状态查询接口
5. 前端集成轮询逻辑

## 注意事项

1. **超时处理**：LLM 生成超时后应该标记为 failed
2. **重试机制**：前端可以提供重试按钮
3. **清理机制**：长时间 processing 的 artifact 需要定期清理
4. **通知时机**：只在 success 或 failed 时发送企微通知，processing 时不发送


---

## 实现完成总结

### ✅ 已完成的工作

1. **数据库层**
   - ✅ 迁移脚本已运行：`scripts/migrate_add_artifact_state.py`
   - ✅ `GeneratedArtifactRecord` 模型已添加 `state` 字段

2. **Repository 层** (`src/database/repositories.py`)
   - ✅ `create_placeholder()` - 创建占位 artifact（state=processing）
   - ✅ `update_content_and_state()` - 更新 artifact 内容和状态
   - ✅ `get_status()` - 获取 artifact 状态（轻量级）
   - ✅ `create()` - 添加 `state` 参数支持（默认 success，向后兼容）

3. **API 端点**
   - ✅ `POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate` - 异步生成
   - ✅ `POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/regenerate` - 异步重新生成
   - ✅ `GET /api/v1/artifacts/{artifact_id}/status` - 状态查询接口
   - ✅ `_generate_artifact_async()` - 后台异步生成任务函数

4. **Response Schema** (`src/api/schemas.py`)
   - ✅ `GenerateArtifactResponse` - 添加 `state` 字段
   - ✅ `ArtifactInfo` - 添加 `state` 字段
   - ✅ `ArtifactStatusResponse` - 新增状态响应 schema

5. **测试**
   - ✅ `scripts/test_async_artifact_generation.py` - 完整的异步生成测试流程

### 实现细节

#### 异步生成流程

1. **立即响应**：
   - 创建占位 artifact（state=processing）
   - 立即返回 artifact_id 和 state
   - HTTP 201 Created

2. **后台生成**：
   - 使用 `asyncio.create_task()` 启动后台任务
   - 独立的数据库会话
   - 完成后更新 artifact 的 content 和 state

3. **前端轮询**：
   - 使用 `GET /api/v1/artifacts/{artifact_id}/status` 轮询
   - 轻量级响应，只返回状态信息
   - 建议轮询间隔：1-2 秒

#### 错误处理

- 使用 `src/utils/error_handler.py` 的 `classify_exception` 分类错误
- 失败时更新 artifact 为 state=failed
- content 包含结构化错误信息
- 发送企微失败通知

#### 企微通知

- 成功：绿色标题 + 粗体字段 + 跳转链接
- 失败：红色标题 + 黄色警告 + 灰色错误码

### 前端集成建议

```typescript
// 1. 发起生成请求
const response = await fetch(`/api/v1/tasks/${taskId}/artifacts/meeting_minutes/generate`, {
  method: 'POST',
  body: JSON.stringify({
    prompt_instance: {...},
    name: "会议纪要"
  })
});

const { artifact_id, state } = await response.json();

// 2. 轮询状态
const pollStatus = async () => {
  const statusResponse = await fetch(`/api/v1/artifacts/${artifact_id}/status`);
  const { state, error } = await statusResponse.json();
  
  if (state === 'success') {
    // 获取完整内容
    const artifactResponse = await fetch(`/api/v1/artifacts/${artifact_id}`);
    const artifact = await artifactResponse.json();
    // 显示内容
  } else if (state === 'failed') {
    // 显示错误
    console.error(error);
  } else if (state === 'processing') {
    // 继续轮询
    setTimeout(pollStatus, 1000);
  }
};

pollStatus();
```

### 测试方法

```bash
# 运行测试脚本
python scripts/test_async_artifact_generation.py
```

测试流程：
1. 选择一个已完成的任务
2. 发起异步生成请求
3. 轮询状态直到完成
4. 验证最终内容

---

**实现日期**: 2026-01-27
**实现者**: Kiro AI Assistant
