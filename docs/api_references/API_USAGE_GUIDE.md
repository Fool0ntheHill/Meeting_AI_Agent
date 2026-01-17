# Meeting Minutes Agent API 使用指南

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [认证方式](#认证方式)
- [核心流程](#核心流程)
- [API 端点详解](#api-端点详解)
- [错误处理](#错误处理)
- [常见场景示例](#常见场景示例)
- [最佳实践](#最佳实践)

---

## 概述

Meeting Minutes Agent API 是一个自动生成会议纪要的 AI 服务,提供以下核心功能:

- **会议转写**: 将音频文件转换为文字
- **说话人识别**: 识别会议中的说话人身份
- **智能摘要**: 使用 LLM 生成会议纪要、行动项等
- **内容管理**: 支持修正、重新生成、版本管理
- **热词管理**: 提升特定领域的转写准确率
- **提示词模板**: 自定义生成内容的格式和风格

### 技术栈

- **API 框架**: FastAPI 3.1.0
- **认证方式**: API Key (Phase 1) / JWT (Phase 2)
- **数据格式**: JSON
- **文档**: OpenAPI 3.1.0 / Swagger UI

### 服务地址

- **开发环境**: `http://localhost:8000`
- **API 文档**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI 规范**: `http://localhost:8000/openapi.json`

---

## 快速开始

### 1. 启动服务

```bash
# 启动 API 服务器
python main.py

# 启动 Worker (处理异步任务)
python worker.py
```


### 2. 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "2026-01-14T21:00:00Z"
}
```

### 3. 创建第一个任务

```bash
# 1. 先登录获取 token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}' | jq -r '.access_token')

# 2. 使用 token 创建任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_files": [
      {
        "file_path": "test_data/meeting_sample.wav",
        "speaker_id": "speaker_001"
      }
    ],
    "prompt_instance": {
      "template_id": "global_meeting_minutes_v1",
      "parameters": {}
    }
  }'
```

**响应示例**:
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "message": "任务已创建并加入处理队列"
}
```

---

## 认证方式

### JWT 认证 (当前)

系统使用 JWT (JSON Web Token) 进行身份认证。

#### 1. 开发环境登录

在开发环境中,使用简化的登录流程:

```bash
curl -X POST http://localhost:8000/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}'
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "user_test_user",
  "tenant_id": "tenant_test_user",
  "expires_in": 86400
}
```

#### 2. 使用 Token 访问 API

在所有 API 请求的 Header 中添加 `Authorization` 字段:

```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/v1/tasks
```

**示例**:
```bash
# 1. 登录获取 token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}' | jq -r '.access_token')

# 2. 使用 token 访问 API
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/tasks
```

#### 3. Token 特性

- **有效期**: 24 小时 (可配置)
- **自动续期**: 每次请求自动更新用户最后登录时间
- **安全性**: 使用 HS256 算法签名
- **包含信息**: user_id, tenant_id, 过期时间

#### 4. 错误处理

**未提供 Token**:
```json
{
  "detail": "Not authenticated"
}
```
HTTP 状态码: 403

**Token 无效或过期**:
```json
{
  "detail": "Could not validate credentials"
}
```
HTTP 状态码: 401

**用户不存在或已停用**:
```json
{
  "detail": "User not found or inactive"
}
```
HTTP 状态码: 401

### 生产环境认证 (Phase 2 计划)

生产环境将实现完整的认证流程:

1. **用户注册**: `POST /api/v1/auth/register`
2. **用户登录**: `POST /api/v1/auth/login` (用户名/密码)
3. **Token 刷新**: `POST /api/v1/auth/refresh`
4. **登出**: `POST /api/v1/auth/logout`
5. **多因素认证**: 2FA 支持

---

## 核心流程

### 完整的会议处理流程

```
1. 创建任务 (POST /api/v1/tasks)
   ↓
2. 任务进入队列 (异步处理)
   ↓
3. Worker 执行处理流程:
   - 音频转写 (ASR)
   - 说话人识别 (Voiceprint)
   - 结果修正 (Correction)
   - 生成会议纪要 (LLM)
   ↓
4. 查询任务状态 (GET /api/v1/tasks/{task_id}/status)
   ↓
5. 获取结果 (GET /api/v1/tasks/{task_id}/artifacts)
   ↓
6. (可选) 修正转写 (PUT /api/v1/tasks/{task_id}/transcript)
   ↓
7. (可选) 重新生成 (POST /api/v1/tasks/{task_id}/regenerate)
   ↓
8. 确认任务 (POST /api/v1/tasks/{task_id}/confirm)
```

### 任务状态流转

```
PENDING → PROCESSING → COMPLETED
                    ↓
                  FAILED
                    ↓
                  ARCHIVED (确认后)
```

---

## API 端点详解

### 1. 任务管理

#### 1.1 创建任务

**端点**: `POST /api/v1/tasks`

**请求体**:
```json
{
  "audio_files": [
    {
      "file_path": "path/to/audio.wav",
      "speaker_id": "speaker_001"
    }
  ],
  "prompt_instance": {
    "template_id": "global_meeting_minutes_v1",
    "parameters": {
      "meeting_type": "技术评审",
      "focus_areas": ["技术方案", "风险评估"]
    }
  },
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN"
}
```


**参数说明**:
- `audio_files`: 音频文件列表
  - `file_path`: 音频文件路径 (本地路径或 TOS URL)
  - `speaker_id`: 说话人 ID (用于声纹识别)
- `prompt_instance`: 提示词实例
  - `template_id`: 模板 ID (从提示词模板 API 获取)
  - `parameters`: 模板参数 (可选)
- `asr_language`: ASR 识别语言 (默认: zh-CN+en-US)
- `output_language`: 输出语言 (默认: zh-CN)

**响应**:
```json
{
  "task_id": "task_20260114_abc123",
  "status": "pending",
  "message": "Task created successfully"
}
```

#### 1.2 查询任务状态

**端点**: `GET /api/v1/tasks/{task_id}/status`

**响应**:
```json
{
  "task_id": "task_20260114_abc123",
  "status": "processing",
  "current_step": "transcription",
  "progress": 45,
  "created_at": "2026-01-14T21:00:00Z",
  "updated_at": "2026-01-14T21:05:00Z",
  "steps": [
    {
      "name": "transcription",
      "status": "in_progress",
      "started_at": "2026-01-14T21:00:00Z"
    },
    {
      "name": "speaker_recognition",
      "status": "pending"
    }
  ]
}
```

**状态说明**:
- `pending`: 等待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败
- `archived`: 已归档 (确认后)

#### 1.3 列出任务

**端点**: `GET /api/v1/tasks?limit=10&offset=0`

**响应**:
```json
[
  {
    "task_id": "task_20260114_abc123",
    "status": "completed",
    "created_at": "2026-01-14T21:00:00Z",
    "audio_duration": 3600
  }
]
```


#### 1.4 成本预估

**端点**: `POST /api/v1/tasks/estimate`

**请求体**:
```json
{
  "audio_duration": 3600,
  "num_speakers": 5
}
```

**响应**:
```json
{
  "estimated_cost": {
    "asr": 0.36,
    "voiceprint": 0.05,
    "llm": 0.02,
    "total": 0.43
  },
  "currency": "CNY",
  "breakdown": {
    "asr": "3600秒 × ¥0.0001/秒",
    "voiceprint": "5人 × ¥0.01/人",
    "llm": "约2000 tokens × ¥0.00001/token"
  }
}
```

---

### 2. 修正与重新生成

#### 2.1 修正转写结果

**端点**: `PUT /api/v1/tasks/{task_id}/transcript`

**请求体**:
```json
{
  "segments": [
    {
      "start_time": 0.0,
      "end_time": 5.2,
      "text": "大家好，今天我们讨论技术方案",
      "speaker": "张三"
    }
  ]
}
```

**响应**:
```json
{
  "task_id": "task_20260114_abc123",
  "message": "Transcript updated successfully",
  "version": 2
}
```

#### 2.2 重新生成会议纪要

**端点**: `POST /api/v1/tasks/{task_id}/regenerate`

**请求体**:
```json
{
  "prompt_instance": {
    "template_id": "global_action_items_v1",
    "parameters": {
      "focus": "行动项"
    }
  }
}
```

**响应**:
```json
{
  "artifact_id": "artifact_20260114_xyz789",
  "version": 2,
  "artifact_type": "meeting_minutes",
  "content": "# 会议纪要\n\n..."
}
```


#### 2.3 确认任务

**端点**: `POST /api/v1/tasks/{task_id}/confirm`

**请求体**:
```json
{
  "confirmation_items": {
    "key_conclusions": [
      "技术方案已通过评审",
      "下周开始开发"
    ],
    "responsible_persons": [
      {
        "id": "user_001",
        "name": "张三",
        "tasks": ["完成技术方案文档"]
      }
    ]
  },
  "confirmed_by": "user_001",
  "confirmed_by_name": "张三"
}
```

**响应**:
```json
{
  "task_id": "task_20260114_abc123",
  "status": "archived",
  "message": "Task confirmed successfully",
  "watermark": {
    "confirmed_by": "张三",
    "confirmed_at": "2026-01-14T21:30:00Z"
  }
}
```

---

### 3. 衍生内容管理

#### 3.1 列出所有衍生内容

**端点**: `GET /api/v1/tasks/{task_id}/artifacts`

**响应**:
```json
{
  "task_id": "task_20260114_abc123",
  "artifacts_by_type": {
    "meeting_minutes": [
      {
        "artifact_id": "artifact_001",
        "version": 2,
        "created_at": "2026-01-14T21:10:00Z"
      }
    ],
    "action_items": [
      {
        "artifact_id": "artifact_002",
        "version": 1,
        "created_at": "2026-01-14T21:15:00Z"
      }
    ]
  }
}
```

#### 3.2 获取特定版本

**端点**: `GET /api/v1/tasks/{task_id}/artifacts/{artifact_id}`

**响应**:
```json
{
  "artifact_id": "artifact_001",
  "artifact_type": "meeting_minutes",
  "version": 2,
  "content": "# 会议纪要\n\n## 会议信息\n...",
  "metadata": {
    "template_id": "global_meeting_minutes_v1",
    "generated_at": "2026-01-14T21:10:00Z"
  }
}
```


#### 3.3 生成新类型衍生内容

**端点**: `POST /api/v1/tasks/{task_id}/artifacts/{type}/generate`

**示例**: 生成行动项
```bash
curl -X POST http://localhost:8000/api/v1/tasks/task_123/artifacts/action_items/generate \
  -H "Authorization: test-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_instance": {
      "template_id": "global_action_items_v1",
      "parameters": {}
    }
  }'
```

**支持的类型**:
- `meeting_minutes`: 会议纪要
- `action_items`: 行动项
- `summary_notes`: 摘要笔记

---

### 4. 热词管理

#### 4.1 创建热词集

**端点**: `POST /api/v1/hotword-sets`

**请求体**:
```json
{
  "name": "医疗专业术语",
  "scope": "global",
  "language": "zh-CN",
  "words": [
    "心电图",
    "血压",
    "CT扫描"
  ]
}
```

**响应**:
```json
{
  "id": 1,
  "name": "医疗专业术语",
  "scope": "global",
  "language": "zh-CN",
  "word_count": 3,
  "provider_resource_id": "volcano_hotword_123"
}
```

#### 4.2 列出热词集

**端点**: `GET /api/v1/hotword-sets?scope=global`

**响应**:
```json
[
  {
    "id": 1,
    "name": "医疗专业术语",
    "scope": "global",
    "language": "zh-CN",
    "word_count": 3,
    "created_at": "2026-01-14T20:00:00Z"
  }
]
```

#### 4.3 删除热词集

**端点**: `DELETE /api/v1/hotword-sets/{id}`

**响应**:
```json
{
  "message": "Hotword set deleted successfully"
}
```


---

### 5. 提示词模板管理

#### 5.1 列出所有模板

**端点**: `GET /api/v1/prompt-templates?scope=global`

**响应**:
```json
[
  {
    "id": "global_meeting_minutes_v1",
    "name": "标准会议纪要模板",
    "scope": "global",
    "artifact_type": "meeting_minutes",
    "description": "生成标准格式的会议纪要",
    "parameters_schema": {
      "meeting_type": "string",
      "focus_areas": "array"
    }
  }
]
```

#### 5.2 获取模板详情

**端点**: `GET /api/v1/prompt-templates/{id}`

**响应**:
```json
{
  "id": "global_meeting_minutes_v1",
  "name": "标准会议纪要模板",
  "scope": "global",
  "artifact_type": "meeting_minutes",
  "template_text": "请根据以下会议转写内容生成会议纪要...",
  "parameters_schema": {
    "meeting_type": {
      "type": "string",
      "description": "会议类型"
    }
  }
}
```

#### 5.3 创建私有模板

**端点**: `POST /api/v1/prompt-templates`

**请求体**:
```json
{
  "name": "我的自定义模板",
  "scope": "private",
  "artifact_type": "meeting_minutes",
  "template_text": "请生成简洁的会议纪要...",
  "parameters_schema": {}
}
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 说明 | 示例场景 |
|--------|------|----------|
| 200 | 成功 | GET 请求成功 |
| 201 | 创建成功 | POST 创建任务成功 |
| 400 | 请求错误 | 参数验证失败 |
| 401 | 未授权 | JWT Token 无效或过期 |
| 403 | 禁止访问 | 未提供 Token 或无权访问资源 |
| 404 | 资源不存在 | 任务 ID 不存在 |
| 422 | 验证错误 | 请求体格式错误 |
| 429 | 请求过多 | 超过速率限制 |
| 500 | 服务器错误 | 内部错误 |


### 错误响应格式

```json
{
  "error": "validation_error",
  "message": "Invalid audio file format",
  "details": {
    "field": "audio_files[0].file_path",
    "reason": "File not found"
  }
}
```

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| `authentication_error` | 认证失败 | 检查 JWT Token 是否有效 |
| `token_expired` | Token 已过期 | 重新登录获取新 Token |
| `validation_error` | 参数验证失败 | 检查请求参数格式 |
| `resource_not_found` | 资源不存在 | 检查资源 ID 是否正确 |
| `asr_error` | ASR 服务错误 | 检查音频文件格式 |
| `voiceprint_error` | 声纹识别错误 | 检查说话人 ID |
| `llm_error` | LLM 服务错误 | 检查提示词模板 |
| `quota_exceeded` | 配额超限 | 联系管理员增加配额 |
| `rate_limit_exceeded` | 速率限制 | 降低请求频率 |

---

## 常见场景示例

### 场景 1: 完整的会议处理流程

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# 1. 登录获取 JWT token
response = requests.post(
    f"{BASE_URL}/auth/dev/login",
    json={"username": "test_user"}
)
token = response.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {token}"}

# 2. 创建任务
response = requests.post(
    f"{BASE_URL}/tasks",
    headers=HEADERS,
    json={
        "audio_files": [
            {"file_path": "meeting.wav", "speaker_id": "speaker_001"}
        ],
        "prompt_instance": {
            "template_id": "global_meeting_minutes_v1",
            "parameters": {}
        }
    }
)
task_id = response.json()["task_id"]
print(f"Task created: {task_id}")

# 3. 轮询任务状态
while True:
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/status",
        headers=HEADERS
    )
    status_data = response.json()
    status = status_data["state"]
    print(f"Status: {status}, Progress: {status_data.get('progress', 0)}%")
    
    if status in ["success", "failed"]:
        break
    
    time.sleep(5)

# 4. 获取结果
if status == "success":
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/artifacts",
        headers=HEADERS
    )
    artifacts = response.json()
    print(f"Artifacts: {artifacts}")
```
```


### 场景 2: 修正转写并重新生成

```python
# 1. 修正转写结果
response = requests.put(
    f"{BASE_URL}/tasks/{task_id}/transcript",
    headers=HEADERS,
    json={
        "segments": [
            {
                "start_time": 0.0,
                "end_time": 5.2,
                "text": "修正后的文本",
                "speaker": "张三"
            }
        ]
    }
)
print("Transcript updated")

# 2. 重新生成会议纪要
response = requests.post(
    f"{BASE_URL}/tasks/{task_id}/regenerate",
    headers=HEADERS,
    json={
        "prompt_instance": {
            "template_id": "global_meeting_minutes_v1",
            "parameters": {}
        }
    }
)
new_artifact = response.json()
print(f"New artifact: {new_artifact['artifact_id']}")
```

### 场景 3: 使用热词提升准确率

```python
# 1. 创建热词集
response = requests.post(
    f"{BASE_URL}/hotword-sets",
    headers=HEADERS,
    json={
        "name": "技术术语",
        "scope": "global",
        "language": "zh-CN",
        "words": ["Kubernetes", "Docker", "微服务"]
    }
)
hotword_id = response.json()["id"]
print(f"Hotword set created: {hotword_id}")

# 2. 创建任务 (热词会自动应用)
response = requests.post(
    f"{BASE_URL}/tasks",
    headers=HEADERS,
    json={
        "audio_files": [
            {"file_path": "tech_meeting.wav", "speaker_id": "speaker_001"}
        ],
        "prompt_instance": {
            "template_id": "global_meeting_minutes_v1",
            "parameters": {}
        }
    }
)
task_id = response.json()["task_id"]
print(f"Task created with hotwords: {task_id}")
```


### 场景 4: 生成多种衍生内容

```python
# 1. 生成会议纪要
response = requests.post(
    f"{BASE_URL}/tasks/{task_id}/artifacts/meeting_minutes/generate",
    headers=HEADERS,
    json={
        "prompt_instance": {
            "template_id": "global_meeting_minutes_v1",
            "parameters": {}
        }
    }
)
minutes = response.json()

# 2. 生成行动项
response = requests.post(
    f"{BASE_URL}/tasks/{task_id}/artifacts/action_items/generate",
    headers=HEADERS,
    json={
        "prompt_instance": {
            "template_id": "global_action_items_v1",
            "parameters": {}
        }
    }
)
action_items = response.json()

# 3. 生成摘要笔记
response = requests.post(
    f"{BASE_URL}/tasks/{task_id}/artifacts/summary_notes/generate",
    headers=HEADERS,
    json={
        "prompt_instance": {
            "template_id": "global_summary_notes_v1",
            "parameters": {}
        }
    }
)
summary = response.json()

print(f"Generated 3 types of artifacts")
```

---

## 最佳实践

### 1. 音频文件准备

- **格式**: WAV, MP3, M4A
- **采样率**: 16kHz 或更高
- **声道**: 单声道或双声道
- **时长**: 建议不超过 2 小时 (超过会自动切分)
- **质量**: 清晰无噪音,说话人声音清晰

### 2. 任务创建

- **批量处理**: 如有多个音频文件,建议分批创建任务
- **热词使用**: 提前创建领域相关的热词集
- **模板选择**: 根据会议类型选择合适的提示词模板
- **语言设置**: 明确指定 ASR 识别语言和输出语言

### 3. 状态轮询

- **轮询间隔**: 建议 5-10 秒
- **超时处理**: 设置合理的超时时间 (如 30 分钟)
- **WebSocket**: 对于实时性要求高的场景,使用 WebSocket


### 4. 错误处理

```python
import requests
from requests.exceptions import RequestException

def create_task_with_retry(audio_files, max_retries=3):
    """创建任务,带重试机制"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{BASE_URL}/tasks",
                headers=HEADERS,
                json={"audio_files": audio_files},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"Retry {attempt + 1}/{max_retries}")
            time.sleep(2 ** attempt)  # 指数退避
```

### 5. 性能优化

- **并发控制**: 避免同时创建过多任务
- **缓存利用**: 相同音频文件不要重复处理
- **资源清理**: 及时删除不需要的热词集和模板
- **成本控制**: 使用成本预估 API 评估费用

### 6. 安全建议

- **Token 保护**: 不要在代码中硬编码 Token,使用环境变量
- **Token 刷新**: Token 过期前及时刷新
- **HTTPS**: 生产环境必须使用 HTTPS
- **权限控制**: 仅授予必要的权限
- **日志脱敏**: 避免在日志中记录 Token 和敏感信息
- **Token 存储**: 客户端安全存储 Token (如 HttpOnly Cookie)

---

## 附录

### A. Postman 集合

我们提供了 Postman 集合文件,包含所有 API 端点的示例请求:

**导入步骤**:
1. 打开 Postman
2. 点击 Import
3. 选择 `docs/api_references/postman_collection.json`
4. 配置环境变量:
   - `base_url`: `http://localhost:8000/api/v1`
   - `api_key`: `test-api-key`

### B. 相关文档

- [OpenAPI 规范](./openapi.yaml)
- [Swagger UI](http://localhost:8000/docs)
- [数据库设计](../database_design_improvements.md)
- [快速测试指南](../testing/快速测试指南.md)

### C. 支持与反馈

- **问题反馈**: 提交 GitHub Issue
- **功能建议**: 提交 Feature Request
- **技术支持**: 联系开发团队

---

**最后更新**: 2026-01-14  
**API 版本**: 1.0.0  
**文档版本**: 1.0.0
