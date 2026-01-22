# 错误码快速参考

## 完整错误码列表

### 网络/基础设施 (可重试 ✅)

```
NETWORK_TIMEOUT          网络连接超时，请稍后重试
NETWORK_DNS              网络连接失败，请检查网络设置
STORAGE_UNAVAILABLE      文件存储服务暂时不可用，请稍后重试
```

### 鉴权/配额

```
AUTH_FAILED              身份验证失败，请重新登录
PERMISSION_DENIED        您没有权限访问此资源
RATE_LIMITED             请求过于频繁，请稍后再试 (可重试 ✅)
BILLING_EXCEEDED         账户余额不足或已超出配额限制
```

### 输入/数据

```
INPUT_MISSING_FILE       音频文件缺失，请重新上传
INPUT_UNSUPPORTED_FORMAT 不支持的音频格式，请上传 WAV/MP3/OGG 格式
INPUT_TOO_LARGE          音频文件过大，请上传小于 2GB 的文件
INPUT_CORRUPTED          音频文件已损坏，请重新上传
INPUT_INVALID            输入参数无效，请检查后重试
```

### ASR 服务

```
ASR_SERVICE_ERROR        语音识别服务暂时不可用，请稍后重试 (可重试 ✅)
ASR_AUTH_ERROR           语音识别服务鉴权失败，请联系管理员
ASR_TIMEOUT              语音识别超时，请稍后重试 (可重试 ✅)
```

### LLM 服务

```
LLM_SERVICE_ERROR        AI 生成服务暂时不可用，请稍后重试 (可重试 ✅)
LLM_AUTH_ERROR           AI 生成服务鉴权失败，请联系管理员
LLM_TIMEOUT              AI 生成超时，请稍后重试 (可重试 ✅)
LLM_CONTENT_BLOCKED      内容包含敏感信息，无法生成
```

### 声纹服务

```
VOICEPRINT_SERVICE_ERROR 声纹识别服务暂时不可用，请稍后重试 (可重试 ✅)
VOICEPRINT_AUTH_ERROR    声纹识别服务鉴权失败，请联系管理员
```

### 业务流程

```
SPEAKER_RECOGNITION_FAILED 无法识别说话人，请检查音频质量 (可重试 ✅)
CORRECTION_FAILED          说话人校正失败，请稍后重试 (可重试 ✅)
SUMMARY_FAILED             生成会议纪要失败，请稍后重试 (可重试 ✅)
TRANSCRIPTION_EMPTY        转写结果为空，请检查音频内容
```

### 系统内部

```
INTERNAL_ERROR           系统内部错误，请联系管理员
DB_ERROR                 数据库错误，请联系管理员
CACHE_ERROR              缓存服务异常，请稍后重试 (可重试 ✅)
QUEUE_ERROR              任务队列异常，请联系管理员
```

## 前端处理建议

### 可重试错误 (retryable=true)
- 显示"重试"按钮
- 提示"稍后重试"或"更换模型/通道后重试"

### 配置类错误
- `AUTH_*`, `*_AUTH_ERROR`, `LLM_CONTENT_BLOCKED`
- 提示检查密钥、权限或调整提示词/内容

### 输入类错误
- `INPUT_*`
- 提示重新上传/换格式/拆分

### 配额类错误
- `RATE_LIMITED`, `BILLING_EXCEEDED`
- 提示联系管理员或等待额度恢复

### 内部错误
- `INTERNAL_ERROR`, `DB_ERROR`, `QUEUE_ERROR`
- 提示联系管理员

## API 响应示例

### 成功状态
```json
{
  "task_id": "task_abc123",
  "state": "success",
  "progress": 100.0,
  "error_code": null,
  "error_message": null,
  "error_details": null,
  "retryable": null
}
```

### 失败状态（可重试）
```json
{
  "task_id": "task_abc123",
  "state": "failed",
  "progress": 40.0,
  "error_code": "ASR_SERVICE_ERROR",
  "error_message": "语音识别服务暂时不可用，请稍后重试",
  "error_details": "火山引擎 ASR API 返回 500 错误: Internal Server Error",
  "retryable": true
}
```

### 失败状态（不可重试）
```json
{
  "task_id": "task_abc123",
  "state": "failed",
  "progress": 0.0,
  "error_code": "INPUT_UNSUPPORTED_FORMAT",
  "error_message": "不支持的音频格式，请上传 WAV/MP3/OGG 格式",
  "error_details": "文件格式: video/mp4, 不支持视频文件",
  "retryable": false
}
```

## 使用示例

### Python (后端)
```python
from src.core.error_codes import ErrorCode, create_error

# 创建错误
error = create_error(
    error_code=ErrorCode.ASR_SERVICE_ERROR,
    error_message="语音识别服务暂时不可用，请稍后重试",
    error_details="火山引擎 ASR API 返回 500 错误",
)

# 更新任务错误
task_repo.update_error(
    task_id=task_id,
    error_code=error.error_code.value,
    error_message=error.error_message,
    error_details=error.error_details,
    retryable=error.retryable,
)
```

### TypeScript (前端)
```typescript
// 检查错误
if (status.state === 'failed' && status.error_code) {
  // 基于错误码显示友好提示
  const message = getErrorMessage(status.error_code, status.error_message);
  
  // 显示重试按钮
  if (status.retryable) {
    showRetryButton();
  }
  
  // 发送企微告警
  if (status.error_details) {
    sendAlert(status);
  }
}
```
