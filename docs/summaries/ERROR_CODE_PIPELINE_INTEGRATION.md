# 错误码系统 Pipeline 集成完成

## 概述

已成功将结构化错误码系统集成到 Pipeline 中，所有阶段的错误都会自动分类并设置正确的错误码。

## 完成时间

2026-01-22

## 实现内容

### 1. Pipeline 集成

**文件**: `src/services/pipeline.py`

**修改内容**:
- 导入 `classify_exception` 错误分类器
- 在 ASR 阶段添加 try-except 块，捕获并分类错误
- 在声纹识别阶段添加 try-except 块，捕获并分类错误
- 在 LLM 生成阶段添加 try-except 块，捕获并分类错误
- 添加 `_update_task_error()` 辅助方法，用于更新任务错误信息
- 在最外层 except 块中添加兜底错误分类

**错误处理流程**:
```python
try:
    # ASR 阶段
    transcript = await self.transcription.transcribe(...)
except Exception as e:
    error = classify_exception(e, context="ASR")
    self._update_task_error(task_id, error)
    self._update_task_status(task_id, TaskState.FAILED)
    raise
```

### 2. 错误分类器

**文件**: `src/utils/error_handler.py`

**功能**:
- 自动识别异常类型（网络、SSL、鉴权、文件、数据库等）
- 根据上下文（ASR/LLM/Voiceprint）映射到正确的错误码
- 返回结构化的 TaskError 对象（包含 error_code, error_message, error_details, retryable）

**支持的错误类型**:
- 网络错误: `NETWORK_TIMEOUT`, `NETWORK_DNS`
- SSL 错误: 自动识别为 `NETWORK_TIMEOUT`
- 鉴权错误: `ASR_AUTH_ERROR`, `LLM_AUTH_ERROR`, `VOICEPRINT_AUTH_ERROR`
- 频率限制: `RATE_LIMITED`
- 文件错误: `INPUT_MISSING_FILE`, `INPUT_UNSUPPORTED_FORMAT`, `INPUT_TOO_LARGE`, `INPUT_CORRUPTED`
- 上游服务: `ASR_SERVICE_ERROR`, `LLM_SERVICE_ERROR`, `LLM_CONTENT_BLOCKED`, `VOICEPRINT_SERVICE_ERROR`
- 数据库错误: `DB_ERROR`
- 内部错误: `INTERNAL_ERROR`

### 3. 数据库支持

**文件**: `src/database/repositories.py`

**方法**: `TaskRepository.update_error()`

**功能**:
- 使用独立 session 更新错误信息，确保立即可见
- 自动清除 Redis 缓存
- 记录错误码、错误消息、错误详情、是否可重试

### 4. API 响应

**文件**: `src/api/routes/tasks.py`

**端点**: `GET /api/v1/tasks/{task_id}/status`

**返回字段**:
```json
{
  "task_id": "task_xxx",
  "state": "failed",
  "progress": 70.0,
  "error_code": "NETWORK_TIMEOUT",
  "error_message": "网络连接异常（SSL），请稍后重试",
  "error_details": "LLM: SSL/TLS error: SSL: UNEXPECTED_EOF_WHILE_READING",
  "retryable": true,
  "updated_at": "2026-01-22T22:09:35"
}
```

## 测试结果

### 测试脚本

**文件**: `scripts/test_pipeline_error_handling.py`

**测试场景**:
1. ✅ ASR 阶段 SSL 错误 → `NETWORK_TIMEOUT` (retryable=true)
2. ✅ LLM 阶段内容过滤错误 → `LLM_CONTENT_BLOCKED` (retryable=false, progress=70%)
3. ✅ 声纹识别阶段鉴权错误 → `VOICEPRINT_AUTH_ERROR` (retryable=false)

**测试结果**: 所有测试通过 ✅

### 手动测试任务

**文件**: `scripts/create_failed_task_with_error_code.py`

**创建的测试任务**:
- Task ID: `task_d80d9802ccc242a9`
- Error Code: `NETWORK_TIMEOUT`
- Error Message: "网络连接异常（SSL），请稍后重试"
- Retryable: `true`

**前端测试步骤**:
```bash
# 查询任务状态
GET /api/v1/tasks/task_d80d9802ccc242a9/status

# 预期响应包含完整的错误信息
{
  "error_code": "NETWORK_TIMEOUT",
  "error_message": "网络连接异常（SSL），请稍后重试",
  "error_details": "LLM: SSL/TLS error: SSL: UNEXPECTED_EOF_WHILE_READING",
  "retryable": true
}
```

## 前端集成

### 错误类型映射

前端已支持的错误码（来自用户反馈）:
- 网络/基础设施: `NETWORK_TIMEOUT`, `NETWORK_DNS`, `STORAGE_UNAVAILABLE`
- 鉴权/配额: `AUTH_FAILED`, `PERMISSION_DENIED`, `RATE_LIMITED`, `BILLING_EXCEEDED`
- 输入类: `INPUT_MISSING_FILE`, `INPUT_UNSUPPORTED_FORMAT`, `INPUT_TOO_LARGE`, `INPUT_CORRUPTED`, `INPUT_INVALID`
- 上游/模型: `ASR_SERVICE_ERROR`, `ASR_AUTH_ERROR`, `ASR_TIMEOUT`, `LLM_SERVICE_ERROR`, `LLM_AUTH_ERROR`, `LLM_TIMEOUT`, `LLM_CONTENT_BLOCKED`, `VOICEPRINT_SERVICE_ERROR`, `VOICEPRINT_AUTH_ERROR`
- 业务流程: `SPEAKER_RECOGNITION_FAILED`, `CORRECTION_FAILED`, `SUMMARY_FAILED`, `TRANSCRIPTION_EMPTY`
- 内部: `INTERNAL_ERROR`, `DB_ERROR`, `CACHE_ERROR`, `QUEUE_ERROR`

### 显示逻辑

前端根据 `error_code` 显示:
1. **错误类型**: 中文分类（如"网络/上游服务异常"）
2. **错误消息**: 直接显示 `error_message`
3. **重试按钮**: 根据 `retryable` 字段决定是否显示

### 兜底逻辑

如果后端没有提供 `error_code`:
- 前端显示"未知错误"
- 建议: 后端务必在所有失败场景填充 `error_code`

## 关键特性

### 1. 自动错误分类

无需手动判断错误类型，`classify_exception()` 会自动:
- 识别 SSL 错误（如 `SSL: UNEXPECTED_EOF_WHILE_READING`）
- 识别鉴权错误（如 `Authentication failed`）
- 识别网络错误（如 `timeout`, `connection refused`）
- 识别内容过滤错误（如 `content blocked`）

### 2. 上下文感知

根据错误发生的阶段（ASR/LLM/Voiceprint），映射到正确的错误码:
- ASR 阶段的鉴权错误 → `ASR_AUTH_ERROR`
- LLM 阶段的鉴权错误 → `LLM_AUTH_ERROR`
- Voiceprint 阶段的鉴权错误 → `VOICEPRINT_AUTH_ERROR`

### 3. 进度保留

LLM 阶段失败时，保留 progress=70%，让前端知道失败发生在哪个阶段。

### 4. 立即可见

使用独立 session 更新错误信息，确保:
- API 查询立即能看到错误码
- Redis 缓存自动清除
- 前端轮询能及时获取错误信息

## 相关文档

- [错误码实现指南](../ERROR_CODE_IMPLEMENTATION_GUIDE.md)
- [错误码快速参考](../ERROR_CODE_QUICK_REFERENCE.md)
- [Pipeline 错误处理补丁](../PIPELINE_ERROR_HANDLING_PATCH.md)
- [前端集成指南](../api_references/FRONTEND_INTEGRATION_GUIDE.md)

## 下一步

1. ✅ 错误码系统已完全实现
2. ✅ Pipeline 集成已完成
3. ✅ 测试已通过
4. ⏳ 等待前端测试真实任务
5. ⏳ 根据前端反馈调整错误消息文案

## 总结

错误码系统已成功集成到 Pipeline 中，所有阶段的错误都会自动分类并设置正确的错误码。前端现在可以基于 `error_code` 显示友好的错误提示，并根据 `retryable` 字段决定是否显示重试按钮。

**关键改进**:
- ✅ 后端自动填充 `error_code`（不再显示"未知错误"）
- ✅ SSL 错误自动识别为 `NETWORK_TIMEOUT`
- ✅ 错误信息结构化（code + message + details + retryable）
- ✅ 前端可以基于 error_code 做定制化提示
- ✅ 支持重试逻辑（retryable 字段）
