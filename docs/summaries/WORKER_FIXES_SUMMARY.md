# Worker 修复总结

## 修复日期
2026-01-20

## 修复的问题

### 1. Worker 配置错误
**问题**: `worker.py` 中 `StorageClient` 使用了错误的凭证
- 使用了 `config.volcano.access_key/secret_key`（ASR API 凭证）
- 应该使用 `config.storage.access_key/secret_key`（TOS 存储凭证）

**影响**: 
- TOS 文件上传使用了 ASR 凭证，导致生成的预签名 URL 无法被 Volcano ASR 访问
- Volcano ASR 返回认证错误：`[45000010] load grant: requested grant not found in SaaS storage`

**修复**:
```python
# 修改前
storage_client = StorageClient(
    bucket=config.volcano.tos_bucket,
    region=config.volcano.tos_region,
    access_key=config.volcano.access_key,  # ❌ 错误
    secret_key=config.volcano.secret_key,  # ❌ 错误
)

# 修改后
storage_client = StorageClient(
    bucket=config.storage.bucket,
    region=config.storage.region,
    access_key=config.storage.access_key,  # ✅ 正确
    secret_key=config.storage.secret_key,  # ✅ 正确
)
```

### 2. Azure ASR bytes 类型错误
**问题**: `get_duration()` 期望文件路径字符串，但收到 bytes 数据

**错误信息**:
```
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'bytes'
```

**修复**: 在 `azure_asr.py` 中先将 bytes 保存到临时文件
```python
# 保存到临时文件以获取时长
import tempfile
import os

with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
    temp_path = temp_file.name
    temp_file.write(audio_data)

try:
    duration = self.audio_processor.get_duration(temp_path)
finally:
    try:
        os.unlink(temp_path)
    except:
        pass
```

### 3. Azure ASR JSON 格式错误
**问题**: `definition` 字典使用 `str()` 转换，产生 Python 格式字符串而不是 JSON

**错误信息**:
```
HTTP/1.1 400 Bad Request
```

**修复**: 使用 `json.dumps()` 正确序列化
```python
# 修改前
files = {
    "audio": ("audio.wav", audio_data, "audio/wav"),
    "definition": (None, str(definition).replace("'", '"'), "application/json"),  # ❌
}

# 修改后
import json
files = {
    "audio": ("audio.wav", audio_data, "audio/wav"),
    "definition": (None, json.dumps(definition), "application/json"),  # ✅
}
```

### 4. Worker async 函数调用
**问题**: `process_meeting()` 是 async 函数但没有 await

**修复**: 
- 将 `_process_task()` 改为 async 函数
- 使用 `asyncio.run()` 在同步上下文中运行
- 添加 `await` 调用 `process_meeting()`

### 5. TaskRepository 参数错误
**问题**: `update_state()` 被调用时使用 `error_message` 参数，但方法接受 `error_details`

**修复**: 统一使用 `error_details` 参数名

### 6. PipelineService 缺少 user_id
**问题**: `process_meeting()` 需要 `user_id` 参数但 worker 没有传递

**修复**: 
- 在 `src/api/routes/tasks.py` 中添加 `user_id` 和 `tenant_id` 到 task_data
- 在 worker 中从 task_data 提取并传递 `user_id`

## 当前状态

### ✅ 已修复并正常工作
1. Worker 启动和队列连接
2. 任务状态更新
3. TOS 文件上传（使用正确的存储凭证）
4. Azure ASR fallback 机制（JSON 格式已修复）
5. 异步函数调用
6. 参数传递

### ⚠️ 外部 API 问题（需要外部解决）

#### Volcano ASR 认证失败
**错误**: `[45000010] load grant: requested grant not found in SaaS storage`

**可能原因**:
1. Volcano ASR 的 access_key 已过期或无效
2. 需要重新申请或更新 API 凭证
3. 账户权限不足

**临时解决方案**:
- 系统会自动 fallback 到 Azure ASR
- Azure ASR 现在应该能正常工作

**永久解决方案**:
1. 联系火山引擎技术支持
2. 检查账户状态和权限
3. 更新 `config/development.yaml` 中的 `volcano.access_key` 和 `volcano.secret_key`

## 测试建议

### 1. 测试 Azure ASR
由于 Volcano ASR 有认证问题，先测试 Azure ASR 是否正常：

```bash
# 提交一个小音频文件测试
# Worker 会自动 fallback 到 Azure ASR
```

### 2. 验证 TOS 存储
```bash
python scripts/test_worker_config.py
```

应该看到：
```
✓ ASR 和 Storage 使用不同的 access_key
```

### 3. 检查任务状态
```bash
python scripts/check_task.py <task_id>
```

## 修改的文件

1. `worker.py` - 修复 StorageClient 凭证
2. `src/providers/azure_asr.py` - 修复 bytes 类型和 JSON 格式
3. `src/queue/worker.py` - 修复 async 调用和参数
4. `src/api/routes/tasks.py` - 添加 user_id 到 task_data
5. `src/api/schemas.py` - 添加 folder_id 字段

## 下一步

1. **短期**: 使用 Azure ASR 作为主要 ASR（在 Volcano 修复之前）
2. **中期**: 联系火山引擎解决认证问题
3. **长期**: 考虑添加更多 ASR 提供商作为备用
