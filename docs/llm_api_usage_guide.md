# LLM API 使用指南

## 服务信息

- **Base URL**: `http://llm-api.gs.com:4000`
- **API Key**: `sk-WTmUUql26vw3fBa2rwpxXQ`
- **接口格式**: OpenAI 兼容

## 可用模型

根据测试，以下模型可用：

### OpenAI 系列
- `openai/gpt-4o` - GPT-4 Optimized（推荐用于复杂任务）
- `openai/gpt-4o-mini` - GPT-4 Mini（推荐用于一般任务，性价比高）
- `openai/gpt-3.5-turbo` - GPT-3.5 Turbo

### 阿里通义千问系列
- `dashscope/qwen-plus` - 通义千问 Plus
- `dashscope/qwen-turbo` - 通义千问 Turbo

### 零一万物系列
- `one/yi-large` - Yi Large

## 使用方法

### 1. Python 使用示例

```python
import requests

BASE_URL = "http://llm-api.gs.com:4000"
API_KEY = "sk-WTmUUql26vw3fBa2rwpxXQ"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# 基本对话
payload = {
    "model": "openai/gpt-4o-mini",  # 选择模型
    "messages": [
        {
            "role": "system",
            "content": "你是一个专业的会议纪要助手。"
        },
        {
            "role": "user",
            "content": "请帮我总结这段会议内容..."
        }
    ],
    "temperature": 0.7,
    "max_tokens": 2000
}

response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    headers=headers,
    json=payload
)

result = response.json()
content = result["choices"][0]["message"]["content"]
print(content)
```

### 2. 结构化输出（JSON Schema）

```python
# 使用 JSON Schema 获取结构化输出
payload = {
    "model": "openai/gpt-4o-mini",
    "messages": [
        {
            "role": "user",
            "content": "分析这段会议内容并生成会议纪要..."
        }
    ],
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "meeting_minutes",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "participants": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string"},
                                "assignee": {"type": "string"},
                                "deadline": {"type": "string"}
                            },
                            "required": ["task", "assignee"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["title", "summary", "participants", "action_items"],
                "additionalProperties": False
            }
        }
    }
}

response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    headers=headers,
    json=payload
)

result = response.json()
structured_data = json.loads(result["choices"][0]["message"]["content"])
```

### 3. 使用 OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-WTmUUql26vw3fBa2rwpxXQ",
    base_url="http://llm-api.gs.com:4000/v1"
)

response = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是一个专业的会议纪要助手。"},
        {"role": "user", "content": "请帮我总结这段会议内容..."}
    ],
    temperature=0.7,
    max_tokens=2000
)

print(response.choices[0].message.content)
```

### 4. cURL 命令

```bash
curl http://llm-api.gs.com:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-WTmUUql26vw3fBa2rwpxXQ" \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [
      {
        "role": "user",
        "content": "你好"
      }
    ]
  }'
```

## 在项目中使用

### 修改配置文件

编辑 `config/development.yaml`:

```yaml
llm:
  provider: "openai"  # 使用 OpenAI 兼容接口
  api_key: "sk-WTmUUql26vw3fBa2rwpxXQ"
  base_url: "http://llm-api.gs.com:4000/v1"
  model: "openai/gpt-4o-mini"  # 推荐使用
  temperature: 0.7
  max_tokens: 4000
```

### 推荐模型选择

根据不同场景选择合适的模型：

1. **会议纪要生成**（推荐）
   - `openai/gpt-4o-mini` - 性价比最高，质量好
   - `dashscope/qwen-plus` - 中文理解能力强

2. **复杂分析任务**
   - `openai/gpt-4o` - 最强能力，适合复杂推理

3. **快速响应场景**
   - `openai/gpt-3.5-turbo` - 速度快
   - `dashscope/qwen-turbo` - 中文快速响应

## 注意事项

1. **模型名称格式**: 必须包含前缀，如 `openai/gpt-4o-mini`，不能只写 `gpt-4o-mini`

2. **权限限制**: 当前 API Key 只能访问以下模型前缀：
   - `openai/*`
   - `dashscope/*`
   - `one/*`
   - `deepseek/*`（测试时不可用）
   - `ollama/*`（未测试）

3. **接口兼容性**: 完全兼容 OpenAI API 格式，可以直接使用 OpenAI SDK

4. **Token 限制**: 不同模型有不同的 token 限制，建议设置合理的 `max_tokens`

## 测试脚本

项目中提供了测试脚本：

```bash
# 测试可用模型
python scripts/test_available_models.py

# 测试基本功能
python scripts/test_gemini_api.py
```

## 故障排查

### 401 错误 - 模型访问被拒绝
```
team not allowed to access model
```
**解决方案**: 检查模型名称是否正确，确保使用允许的模型前缀

### 403 错误 - API Key 被暂停
```
Consumer has been suspended
```
**解决方案**: 联系 API 服务提供者

### 连接超时
**解决方案**: 检查网络连接，确保可以访问 `llm-api.gs.com:4000`
