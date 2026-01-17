# 任务确认 API 文档

## 概述

任务确认 API 提供了会议纪要确认和归档的功能,建立了 AI 生成内容与用户确认内容之间的责任边界。

## 端点

### POST /api/v1/tasks/{task_id}/confirm

确认任务并归档,注入责任人水印。

## 请求

### 路径参数

- `task_id` (string, required): 任务 ID

### 请求头

- `Authorization` (string, required): JWT Bearer token

**示例**: `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**获取 Token**: 调用 `POST /api/v1/auth/dev/login` 获取 JWT token

### 请求体

```json
{
  "confirmation_items": {
    "key_conclusions": true,
    "responsible_persons": true,
    "action_items": true
  },
  "responsible_person": {
    "id": "user_001",
    "name": "张三"
  }
}
```

#### 字段说明

- `confirmation_items` (object, required): 确认项状态
  - `key_conclusions` (boolean, required): 关键结论已确认
  - `responsible_persons` (boolean, required): 负责人无误
  - 其他自定义确认项 (boolean, optional)

- `responsible_person` (object, required): 责任人信息
  - `id` (string, required): 责任人 ID
  - `name` (string, required): 责任人姓名

## 响应

### 成功响应 (200 OK)

```json
{
  "success": true,
  "task_id": "task_abc123",
  "state": "archived",
  "confirmed_by": "user_001",
  "confirmed_by_name": "张三",
  "confirmed_at": "2026-01-14T10:30:00Z",
  "message": "任务已确认并归档"
}
```

### 错误响应

#### 404 Not Found - 任务不存在

```json
{
  "detail": "任务不存在"
}
```

#### 403 Forbidden - 无权访问

```json
{
  "detail": "无权访问此任务"
}
```

#### 400 Bad Request - 任务状态不允许确认

```json
{
  "detail": "任务状态为 pending,无法确认任务"
}
```

#### 400 Bad Request - 任务已被确认

```json
{
  "detail": "任务已被确认,无法重复确认"
}
```

#### 400 Bad Request - 确认项未完成

```json
{
  "detail": "以下确认项未完成: key_conclusions, responsible_persons"
}
```

#### 400 Bad Request - 责任人信息不完整

```json
{
  "detail": "责任人信息不完整,需要包含 id 和 name"
}
```

## 功能说明

### 1. 验证流程

1. 验证任务存在
2. 验证用户权限(只能确认自己的任务)
3. 验证任务状态(只有 SUCCESS 或 PARTIAL_SUCCESS 可确认)
4. 验证任务未被确认过
5. 验证所有必需的确认项都已勾选
6. 验证责任人信息完整性

### 2. 水印注入

确认后,系统会自动将责任人水印注入到所有衍生内容的元数据中:

```json
{
  "artifact_metadata": {
    "watermark": {
      "confirmed_by_id": "user_001",
      "confirmed_by_name": "张三",
      "confirmed_at": "2026-01-14T10:30:00Z",
      "confirmation_items": {
        "key_conclusions": true,
        "responsible_persons": true,
        "action_items": true
      }
    }
  }
}
```

### 3. 任务归档

确认后,任务状态会自动更新为 `archived`,表示任务已完成并归档。

### 4. 责任边界

通过确认机制,系统明确区分:
- **AI 自动生成内容**: 未确认的任务,内容由 AI 生成
- **用户确认后的最终内容**: 已确认的任务,用户对内容负责

## 使用示例

### Python 示例

```python
import requests

API_BASE_URL = "http://localhost:8000/api/v1"

# 1. 先登录获取 JWT token
login_response = requests.post(
    f"{API_BASE_URL}/auth/dev/login",
    json={"username": "test_user"}
)
token = login_response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# 2. 确认任务
response = requests.post(
    f"{API_BASE_URL}/tasks/task_abc123/confirm",
    json={
        "confirmation_items": {
            "key_conclusions": True,
            "responsible_persons": True,
            "action_items": True,
        },
        "responsible_person": {
            "id": "user_001",
            "name": "张三",
        },
    },
    headers=headers,
)

if response.status_code == 200:
    result = response.json()
    print(f"任务已确认: {result['task_id']}")
    print(f"确认人: {result['confirmed_by_name']}")
    print(f"确认时间: {result['confirmed_at']}")
else:
    print(f"确认失败: {response.json()['detail']}")
```

### cURL 示例

```bash
# 1. 先登录获取 token
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/dev/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}' | jq -r '.access_token')

# 2. 使用 token 确认任务
curl -X POST "http://localhost:8000/api/v1/tasks/task_abc123/confirm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation_items": {
      "key_conclusions": true,
      "responsible_persons": true,
      "action_items": true
    },
    "responsible_person": {
      "id": "user_001",
      "name": "张三"
    }
  }'
```

## 注意事项

1. **必需的确认项**: `key_conclusions` 和 `responsible_persons` 是必需的,必须设置为 `true`
2. **一次性操作**: 任务确认后无法撤销,请谨慎操作
3. **权限控制**: 只能确认自己创建的任务
4. **状态限制**: 只有成功或部分成功的任务才能确认
5. **水印持久化**: 水印信息会永久保存在衍生内容的元数据中

## 相关 API

- [GET /api/v1/tasks/{task_id}/status](./task_status_api.md) - 查询任务状态
- [GET /api/v1/tasks/{task_id}/artifacts](./artifacts_api.md) - 查询衍生内容
- [PUT /api/v1/tasks/{task_id}/transcript](./transcript_correction_api.md) - 修正转写文本
- [PATCH /api/v1/tasks/{task_id}/speakers](./speaker_correction_api.md) - 修正说话人映射

## 测试

测试脚本位于 `scripts/test_task_confirmation_api.py`,包含以下测试用例:

1. 完整确认流程测试
2. 缺少必需项测试
3. 重复确认测试
4. 不存在的任务测试
5. 无效责任人信息测试

运行测试:

```bash
python scripts/test_task_confirmation_api.py
```
