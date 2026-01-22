# Pipeline 错误处理补丁

## 需要修改的文件

`src/services/pipeline.py`

## 修改内容

### 1. 添加导入

在文件顶部添加：

```python
from src.core.error_codes import ErrorCode, TaskError, create_error
from src.utils.error_handler import classify_exception
```

### 2. 修改 execute 方法的异常处理

将现有的 `except Exception as e:` 块替换为：

```python
except Exception as e:
    # 分类异常并设置结构化错误
    logger.error(
        f"Task {task_id}: Pipeline failed: {e}",
        exc_info=True,
    )
    
    # 根据当前阶段确定上下文
    context = "Pipeline"
    if transcript is None:
        context = "ASR"
    elif not speaker_mappings:
        context = "Voiceprint"
    else:
        context = "LLM"
    
    # 分类异常
    task_error = classify_exception(e, context=context)
    
    # 更新任务错误信息
    self.tasks.update_error(
        task_id=task_id,
        error_code=task_error.error_code.value,
        error_message=task_error.error_message,
        error_details=task_error.error_details,
        retryable=task_error.retryable,
    )
    
    # 更新任务状态为失败
    self._update_task_status(
        task_id, TaskState.FAILED, error_details=task_error.error_details
    )
    
    # 如果是 MeetingAgentError,直接抛出
    if isinstance(e, MeetingAgentError):
        raise
    
    # 否则包装为 MeetingAgentError
    raise MeetingAgentError(
        f"Pipeline processing failed: {task_error.error_message}",
        details={
            "task_id": task_id,
            "error_code": task_error.error_code.value,
            "error_message": task_error.error_message,
            "error_details": task_error.error_details,
            "retryable": task_error.retryable,
        },
    )
```

### 3. 在各个阶段添加特定的错误处理

#### ASR 阶段

```python
try:
    # 1. 转写音频
    transcript = await self._transcribe_audio(
        task_id, audio_files, asr_language, hotword_sets
    )
except Exception as e:
    task_error = classify_exception(e, context="ASR")
    self.tasks.update_error(
        task_id=task_id,
        error_code=task_error.error_code.value,
        error_message=task_error.error_message,
        error_details=task_error.error_details,
        retryable=task_error.retryable,
    )
    raise
```

#### 声纹识别阶段

```python
try:
    # 2. 声纹识别
    if enable_speaker_recognition:
        speaker_mappings = await self._recognize_speakers(
            task_id, local_audio_path, transcript, user_id, tenant_id
        )
except Exception as e:
    task_error = classify_exception(e, context="Voiceprint")
    self.tasks.update_error(
        task_id=task_id,
        error_code=task_error.error_code.value,
        error_message=task_error.error_message,
        error_details=task_error.error_details,
        retryable=task_error.retryable,
    )
    raise
```

#### LLM 生成阶段

```python
try:
    # 4. 生成会议纪要
    artifact = await self._generate_artifact(
        task_id,
        transcript,
        speaker_mappings,
        prompt_instance,
        output_language,
        meeting_type,
        user_id,
    )
except Exception as e:
    task_error = classify_exception(e, context="LLM")
    self.tasks.update_error(
        task_id=task_id,
        error_code=task_error.error_code.value,
        error_message=task_error.error_message,
        error_details=task_error.error_details,
        retryable=task_error.retryable,
    )
    raise
```

## 测试

创建一个测试任务来验证错误码是否正确设置：

```bash
# 测试 SSL 错误（应该返回 NETWORK_TIMEOUT）
python scripts/test_error_classification.py

# 检查任务状态
python scripts/check_task.py <task_id>
```

预期输出：

```json
{
  "task_id": "task_xxx",
  "state": "failed",
  "error_code": "NETWORK_TIMEOUT",
  "error_message": "网络连接异常（SSL），请稍后重试",
  "error_details": "LLM: SSL/TLS error: SSL: UNEXPECTED_EOF_WHILE_READING",
  "retryable": true
}
```

## 向后兼容性

- 保留 `error_details` 字段，用于存储详细的调试信息
- 新增 `error_code`, `error_message`, `retryable` 字段
- 旧任务没有这些字段时，前端应回退到 `error_details`
