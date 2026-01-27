# Artifact 异步生成 - 关键澄清已应用

**日期**: 2026-01-27  
**状态**: ✅ 完成

## 问题背景

用户提出了三个关键问题，需要明确和统一：

1. **错误结构位置不统一**：文档中描述错误在 `content`，但代码实现在 `metadata`
2. **占位 artifact 是否必然有 ID**：前端依赖 `artifact_id` 进行轮询和 Tab 占位
3. **HTTP 状态码**：异步场景应该返回 202 Accepted 而不是 201 Created

## 已应用的修复

### 1. 统一错误信息存储位置

**修改文件**: `src/database/repositories.py`

#### 修改前
```python
# 错误信息存储在 metadata 中
if state == "failed" and (error_code or error_message):
    metadata = artifact.get_metadata_dict() or {}
    metadata["error"] = {
        "code": error_code,
        "message": error_message,
    }
    artifact.set_metadata_dict(metadata)
```

#### 修改后
```python
# 错误信息直接存储在 content 中（统一位置）
# 失败时 content 格式：
# {
#     "error_code": "LLM_TIMEOUT",
#     "error_message": "LLM 生成超时",
#     "hint": "可在 Workspace 首版纪要查看已有内容"
# }
```

**影响**：
- ✅ `update_content_and_state()` 方法简化，移除 `error_code` 和 `error_message` 参数
- ✅ `get_status()` 方法从 `content` 中提取错误信息（而不是 `metadata`）
- ✅ 前端只需检查一个位置（`content`）

### 2. 明确 HTTP 状态码

**修改文件**: `src/api/routes/artifacts.py`, `src/api/routes/corrections.py`

#### 修改前
```python
@router.post(
    "/{task_id}/artifacts/{artifact_type}/generate",
    response_model=GenerateArtifactResponse,
    status_code=201,  # 201 Created
)
```

#### 修改后
```python
@router.post(
    "/{task_id}/artifacts/{artifact_type}/generate",
    response_model=GenerateArtifactResponse,
    status_code=202,  # 202 Accepted - 异步处理
)
```

**影响**：
- ✅ 语义更准确：202 表示"请求已接受，处理中"
- ✅ 符合 REST API 最佳实践
- ✅ 前端明确知道需要轮询状态

### 3. 确认占位 Artifact 必然有 ID

**确认**: 代码实现已保证占位 artifact 必然有 ID

```python
# 1. 立即生成 artifact_id
artifact_id = f"artifact_{uuid.uuid4().hex[:16]}"

# 2. 创建占位 artifact
placeholder_artifact = artifact_repo.create_placeholder(
    artifact_id=artifact_id,  # 使用预生成的 ID
    ...
)

# 3. 提交数据库
db.commit()

# 4. 立即返回给前端
return GenerateArtifactResponse(
    artifact_id=artifact_id,  # 前端可以立即使用
    state="processing",
    ...
)
```

**保证**：
- ✅ `artifact_id` 在创建占位 artifact 时立即分配
- ✅ 生成接口立即返回 `artifact_id`（不等待 LLM 生成）
- ✅ 前端可以立即使用 `artifact_id` 进行轮询和 Tab 占位

## 更新的文档

### 1. 实现指南

**文件**: `docs/ARTIFACT_ASYNC_GENERATION_GUIDE.md`

新增章节：
- **关键设计决策**
  - 错误信息存储位置（统一在 `content`）
  - HTTP 状态码（202 Accepted）
  - 占位 Artifact 必然有 ID

### 2. API 参考

**文件**: `docs/ARTIFACT_ASYNC_API_REFERENCE.md`

更新内容：
- HTTP 状态码从 201 改为 202
- 错误响应示例添加 `hint` 字段
- 明确 `artifact_id` 必然存在

### 3. 新增澄清文档

**文件**: `docs/ARTIFACT_ASYNC_CLARIFICATIONS.md`

完整说明：
- 错误信息存储位置和格式（固定字段）
- HTTP 状态码选择原因
- 占位 Artifact ID 保证机制
- 前端轮询策略
- 完整 API 流程示例
- TypeScript 类型定义
- 测试检查清单

## 错误信息格式（固定）

### 失败时的 content

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
| `error_code` | string | ✅ | 结构化错误码 |
| `error_message` | string | ✅ | 用户可读的错误消息 |
| `hint` | string | ❌ | 给用户的提示（可选） |

### 状态接口返回

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

## API 流程确认

```
1. 前端发起请求
   POST /api/v1/tasks/{task_id}/artifacts/{type}/generate
   
   ↓

2. 后端立即响应（HTTP 202 Accepted）
   {
     "artifact_id": "artifact_abc123",  ← 必然存在
     "state": "processing",
     "version": 1,
     ...
   }
   
   ↓

3. 前端立即创建 Tab 占位
   使用 artifact_id: "artifact_abc123"
   
   ↓

4. 前端开始轮询
   GET /api/v1/artifacts/artifact_abc123/status
   
   ↓

5. 生成完成
   state: "success" 或 "failed"
   失败时 error 从 content 中提取
```

## 前端集成要点

### 1. 立即使用 artifact_id

```typescript
const response = await fetch('/api/v1/tasks/xxx/artifacts/meeting_minutes/generate', {
  method: 'POST',
  body: JSON.stringify({...})
});

// HTTP 202 Accepted
const { artifact_id, state } = await response.json();

// artifact_id 必然存在，可以立即使用
createTab(artifact_id, "生成中...");
pollStatus(artifact_id);
```

### 2. 错误处理

```typescript
const { state, error } = await fetchStatus(artifactId);

if (state === 'failed') {
  // error 对象固定字段
  showError(
    error.message,  // 必填
    error.hint      // 可选
  );
  
  // 可以根据 error.code 做特殊处理
  if (error.code === 'LLM_TIMEOUT') {
    showRetryButton();
  }
}
```

## 测试验证

### 后端测试

- [x] 生成接口返回 HTTP 202
- [x] 响应包含 `artifact_id`（非空）
- [x] 响应 `state` 为 `processing`
- [x] 占位 artifact 已写入数据库
- [x] 失败时错误在 `content` 中
- [x] 状态接口正确提取错误

### 前端测试（待验证）

- [ ] 收到 202 后立即创建 Tab
- [ ] 使用 `artifact_id` 轮询
- [ ] 成功时显示内容
- [ ] 失败时显示错误和提示

## 代码质量

- ✅ 所有文件通过语法检查
- ✅ 无 TypeScript/Python 错误
- ✅ 文档与代码一致

## 相关文档

- [关键澄清文档](../ARTIFACT_ASYNC_CLARIFICATIONS.md)
- [实现指南](../ARTIFACT_ASYNC_GENERATION_GUIDE.md)
- [API 参考](../ARTIFACT_ASYNC_API_REFERENCE.md)
- [实现总结](./ARTIFACT_ASYNC_GENERATION_IMPLEMENTATION.md)

---

**实现者**: Kiro AI Assistant  
**审核者**: 待审核  
**部署状态**: 待部署
