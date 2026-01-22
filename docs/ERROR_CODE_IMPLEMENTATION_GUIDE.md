# 结构化错误码实现指南

## 概述

本文档说明如何在后端实现和使用结构化错误码系统，为前端提供友好的错误提示和重试建议。

## 错误信息结构

### 数据库字段

```sql
-- tasks 表新增字段
error_code TEXT,        -- 错误码（如 "ASR_SERVICE_ERROR"）
error_message TEXT,     -- 用户可读的错误消息
error_details TEXT,     -- 详细的调试信息（已存在）
retryable INTEGER       -- 是否可重试（0/1）
```

### API 响应

```json
{
  "task_id": "task_abc123",
  "state": "failed",
  "progress": 40.0,
  "error_code": "ASR_SERVICE_ERROR",
  "error_message": "语音识别服务暂时不可用，请稍后重试",
  "error_details": "火山引擎 ASR API 返回 500 错误: Internal Server Error",
  "retryable": true,
  "updated_at": "2026-01-22T14:30:00Z"
}
```

## 错误码分类

### 1. 网络/基础设施错误（可重试）

| 错误码 | 说明 | 用户提示 |
|--------|------|---------|
| `NETWORK_TIMEOUT` | 网络超时 | 网络连接超时，请稍后重试 |
| `NETWORK_DNS` | DNS解析失败 | 网络连接失败，请检查网络设置 |
| `STORAGE_UNAVAILABLE` | 存储不可用 | 文件存储服务暂时不可用，请稍后重试 |

### 2. 鉴权/配额错误（需检查配置）

| 错误码 | 说明 | 用户提示 |
|--------|------|---------|
| `AUTH_FAILED` | 鉴权失败 | 身份验证失败，请重新登录 |
| `PERMISSION_DENIED` | 权限不足 | 您没有权限访问此资源 |
| `RATE_LIMITED` | 频率限制 | 请求过于频繁，请稍后再试 |
| `BILLING_EXCEEDED` | 账单超限 | 账户余额不足或已超出配额限制 |

### 3. 输入/数据问题（需用户处理）

| 错误码 | 说明 | 用户提示 |
|--------|------|---------|
| `INPUT_MISSING_FILE` | 文件缺失 | 音频文件缺失，请重新上传 |
| `INPUT_UNSUPPORTED_FORMAT` | 格式不支持 | 不支持的音频格式，请上传 WAV/MP3/OGG 格式 |
| `INPUT_TOO_LARGE` | 文件过大 | 音频文件过大，请上传小于 2GB 的文件 |
| `INPUT_CORRUPTED` | 文件损坏 | 音频文件已损坏，请重新上传 |
| `INPUT_INVALID` | 输入无效 | 输入参数无效，请检查后重试 |

### 4. 上游模型/服务错误

| 错误码 | 说明 | 用户提示 | 可重试 |
|--------|------|---------|--------|
| `ASR_SERVICE_ERROR` | ASR服务异常 | 语音识别服务暂时不可用，请稍后重试 | ✅ |
| `ASR_AUTH_ERROR` | ASR鉴权失败 | 语音识别服务鉴权失败，请联系管理员 | ❌ |
| `ASR_TIMEOUT` | ASR超时 | 语音识别超时，请稍后重试 | ✅ |
| `LLM_SERVICE_ERROR` | LLM服务异常 | AI 生成服务暂时不可用，请稍后重试 | ✅ |
| `LLM_AUTH_ERROR` | LLM鉴权失败 | AI 生成服务鉴权失败，请联系管理员 | ❌ |
| `LLM_TIMEOUT` | LLM超时 | AI 生成超时，请稍后重试 | ✅ |
| `LLM_CONTENT_BLOCKED` | 内容被拦截 | 内容包含敏感信息，无法生成 | ❌ |
| `VOICEPRINT_SERVICE_ERROR` | 声纹服务异常 | 声纹识别服务暂时不可用，请稍后重试 | ✅ |
| `VOICEPRINT_AUTH_ERROR` | 声纹鉴权失败 | 声纹识别服务鉴权失败，请联系管理员 | ❌ |

### 5. 业务流程错误

| 错误码 | 说明 | 用户提示 | 可重试 |
|--------|------|---------|--------|
| `SPEAKER_RECOGNITION_FAILED` | 声纹识别失败 | 无法识别说话人，请检查音频质量 | ✅ |
| `CORRECTION_FAILED` | 校正失败 | 说话人校正失败，请稍后重试 | ✅ |
| `SUMMARY_FAILED` | 生成失败 | 生成会议纪要失败，请稍后重试 | ✅ |
| `TRANSCRIPTION_EMPTY` | 转写为空 | 转写结果为空，请检查音频内容 | ❌ |

### 6. 系统内部错误（联系管理员）

| 错误码 | 说明 | 用户提示 |
|--------|------|---------|
| `INTERNAL_ERROR` | 内部错误 | 系统内部错误，请联系管理员 |
| `DB_ERROR` | 数据库错误 | 数据库错误，请联系管理员 |
| `CACHE_ERROR` | 缓存错误 | 缓存服务异常，请稍后重试 |
| `QUEUE_ERROR` | 队列错误 | 任务队列异常，请联系管理员 |

## 后端使用方法

### 1. 导入错误码模块

```python
from src.core.error_codes import (
    ErrorCode,
    TaskError,
    create_error,
    get_error_message,
)
```

### 2. 在 Pipeline 中捕获错误

```python
# src/services/pipeline.py

async def _transcribe_audio(self, task_id: str, audio_files: List[str]):
    """转写音频"""
    try:
        # 调用 ASR 服务
        result = await self.asr_provider.transcribe(audio_files)
        return result
    
    except TimeoutError as e:
        # 超时错误
        error = create_error(
            error_code=ErrorCode.ASR_TIMEOUT,
            error_message="语音识别超时，请稍后重试",
            error_details=f"ASR 请求超时: {str(e)}",
        )
        self._update_task_error(task_id, error)
        raise
    
    except AuthenticationError as e:
        # 鉴权错误
        error = create_error(
            error_code=ErrorCode.ASR_AUTH_ERROR,
            error_message="语音识别服务鉴权失败，请联系管理员",
            error_details=f"ASR 鉴权失败: {str(e)}",
        )
        self._update_task_error(task_id, error)
        raise
    
    except Exception as e:
        # 通用服务错误
        error = create_error(
            error_code=ErrorCode.ASR_SERVICE_ERROR,
            error_message="语音识别服务暂时不可用，请稍后重试",
            error_details=f"ASR 服务异常: {str(e)}",
        )
        self._update_task_error(task_id, error)
        raise


def _update_task_error(self, task_id: str, error: TaskError):
    """更新任务错误信息"""
    self.tasks.update_error(
        task_id=task_id,
        error_code=error.error_code.value,
        error_message=error.error_message,
        error_details=error.error_details,
        retryable=error.retryable,
    )
```

### 3. 更新 Repository

```python
# src/database/repositories.py

def update_error(
    self,
    task_id: str,
    error_code: str,
    error_message: str,
    error_details: Optional[str] = None,
    retryable: bool = False,
) -> None:
    """更新任务错误信息"""
    from src.database.session import session_scope
    
    with session_scope() as independent_session:
        task = independent_session.query(Task).filter(Task.task_id == task_id).first()
        if task:
            task.error_code = error_code
            task.error_message = error_message
            task.error_details = error_details
            task.retryable = retryable
            task.updated_at = datetime.now()
            
            logger.info(f"Task error updated: {task_id} -> {error_code}: {error_message}")
    
    # 清除缓存
    self._clear_task_cache(task_id)
```

### 4. 更新 API 路由

```python
# src/api/routes/tasks.py

@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, ...):
    """获取任务状态"""
    # ... 查询任务 ...
    
    return TaskStatusResponse(
        task_id=task.task_id,
        state=TaskState(task.state),
        progress=task.progress,
        estimated_time=task.estimated_time,
        audio_duration=audio_duration,
        asr_language=asr_language,
        error_code=task.error_code,
        error_message=task.error_message,
        error_details=task.error_details,
        retryable=task.retryable,
        updated_at=task.updated_at,
    )
```

## 前端使用方法

### 1. TypeScript 类型定义

```typescript
export interface TaskStatusResponse {
  task_id: string;
  state: TaskState;
  progress: number;
  estimated_time?: number;
  audio_duration?: number;
  asr_language?: string;
  error_code?: string;
  error_message?: string;
  error_details?: string;
  retryable?: boolean;
  updated_at: string;
}
```

### 2. 错误处理逻辑

```typescript
function handleTaskError(status: TaskStatusResponse) {
  if (status.state !== 'failed') return;
  
  const { error_code, error_message, error_details, retryable } = status;
  
  // 基于错误码显示友好提示
  switch (error_code) {
    case 'ASR_SERVICE_ERROR':
    case 'LLM_SERVICE_ERROR':
    case 'NETWORK_TIMEOUT':
      showError({
        title: '服务暂时不可用',
        message: error_message || '请稍后重试',
        action: retryable ? '重试' : null,
      });
      break;
    
    case 'INPUT_MISSING_FILE':
    case 'INPUT_UNSUPPORTED_FORMAT':
    case 'INPUT_TOO_LARGE':
    case 'INPUT_CORRUPTED':
      showError({
        title: '文件问题',
        message: error_message || '请重新上传文件',
        action: '重新上传',
      });
      break;
    
    case 'AUTH_FAILED':
    case 'PERMISSION_DENIED':
      showError({
        title: '权限问题',
        message: error_message || '请重新登录',
        action: '重新登录',
      });
      break;
    
    case 'RATE_LIMITED':
      showError({
        title: '请求过于频繁',
        message: error_message || '请稍后再试',
        action: null,
      });
      break;
    
    case 'BILLING_EXCEEDED':
      showError({
        title: '配额不足',
        message: error_message || '请联系管理员',
        action: '联系管理员',
      });
      break;
    
    default:
      // 回退到 error_message
      showError({
        title: '任务失败',
        message: error_message || '未知错误',
        action: retryable ? '重试' : null,
      });
  }
  
  // 发送企微告警（包含 error_details）
  if (error_details) {
    sendWeChatAlert({
      task_id: status.task_id,
      error_code,
      error_message,
      error_details,
    });
  }
}
```

### 3. 重试逻辑

```typescript
async function retryTask(taskId: string, status: TaskStatusResponse) {
  if (!status.retryable) {
    showError({
      title: '无法重试',
      message: '此错误不支持自动重试，请检查后重新创建任务',
    });
    return;
  }
  
  // 重新提交任务到队列
  await api.retryTask(taskId);
  
  showSuccess({
    message: '任务已重新提交，请稍候...',
  });
}
```

## 企微告警集成

### Webhook Payload

```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "## 任务失败告警\n\n**任务ID**: task_abc123\n**错误码**: ASR_SERVICE_ERROR\n**错误消息**: 语音识别服务暂时不可用\n**详细信息**: 火山引擎 ASR API 返回 500 错误\n**可重试**: 是\n**时间**: 2026-01-22 14:30:00"
  }
}
```

## 测试

### 测试脚本

```bash
python scripts/test_error_codes.py
```

### 预期输出

```
✓ Error code created: ASR_SERVICE_ERROR
✓ Error message: 语音识别服务暂时不可用，请稍后重试
✓ Retryable: True
✓ Error details saved to database
✓ API returns structured error
```

## 迁移清单

- [x] 创建错误码枚举 (`src/core/error_codes.py`)
- [x] 添加数据库字段 (`error_code`, `error_message`, `retryable`)
- [x] 运行数据库迁移 (`scripts/migrate_add_error_fields.py`)
- [ ] 更新 Repository (`update_error()` 方法)
- [ ] 更新 Pipeline 错误处理
- [ ] 更新 API 路由返回错误字段
- [ ] 更新前端类型定义
- [ ] 实现前端错误处理逻辑
- [ ] 集成企微告警
- [ ] 测试所有错误场景

## 向后兼容性

- `error_details` 字段保留，用于存储详细的调试信息
- 旧任务没有 `error_code` 和 `error_message`，前端应回退到 `error_details`
- 新任务同时填充所有错误字段

## 相关文档

- [Error Code Reference](./ERROR_CODE_REFERENCE.md)
- [Frontend Error Handling Guide](./FRONTEND_ERROR_HANDLING_GUIDE.md)
- [WeChat Alert Integration](./WECHAT_ALERT_INTEGRATION.md)
