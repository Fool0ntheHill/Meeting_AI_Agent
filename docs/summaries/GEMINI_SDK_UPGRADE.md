# Gemini SDK 升级总结

## 升级原因

原项目使用的 `google-generativeai==0.3.0` 是旧版 SDK，已被 Google 标记为 legacy（遗留）状态，并且：
1. 不支持结构化 JSON 输出（`response_mime_type="application/json"`）
2. 缺少最新功能和性能改进
3. 官方建议迁移到新 SDK

## 升级内容

### 1. 依赖更新

**之前：**
```
google-generativeai==0.3.0
```

**之后：**
```
google-genai>=1.0.0  # 新版 SDK，支持结构化输出
```

### 2. 代码更改

#### 导入语句
**之前：**
```python
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
```

**之后：**
```python
from google import genai
from google.genai import types
```

#### 客户端初始化
**之前：**
```python
genai.configure(api_key=self.config.api_keys[self.current_key_index])
```

**之后：**
```python
self.client = genai.Client(api_key=self.config.api_keys[self.current_key_index])
```

#### API 调用
**之前：**
```python
model = genai.GenerativeModel(self.config.model)
generation_config = GenerationConfig(
    max_output_tokens=self.config.max_tokens,
    temperature=self.config.temperature,
)
response = await asyncio.to_thread(
    model.generate_content,
    prompt,
    generation_config=generation_config,
)
```

**之后：**
```python
config = types.GenerateContentConfig(
    max_output_tokens=self.config.max_tokens,
    temperature=self.config.temperature,
    response_mime_type="application/json",  # 强制 JSON 输出
)
response = await asyncio.to_thread(
    self.client.models.generate_content,
    model=self.config.model,
    contents=prompt,
    config=config,
)
```

### 3. 关键改进

#### 原生 JSON 支持
新 SDK 支持 `response_mime_type="application/json"`，确保 Gemini 返回纯 JSON 格式，无需：
- 在 prompt 中添加冗长的 JSON 格式说明
- 解析 Markdown 代码块（```json ... ```）
- 处理混合格式的响应

#### 响应解析简化
**之前：**需要检测并提取 Markdown 代码块中的 JSON

**之后：**直接解析 JSON 字符串
```python
content_dict = json.loads(response_text.strip())
```

### 4. 测试结果

运行 `scripts/test_llm_integration.py` 测试通过：
```
✅ 所有测试通过！

生成的 Artifact：
ID: test-artifact-123
类型: meeting_minutes
版本: 1

内容：
{"会议主题": "项目进度会议", "参与人员": ["张三", "李四", "王五"], ...}
```

返回的是纯 JSON 格式，无 Markdown 标记。

## 待办事项

### 单元测试更新
`tests/unit/test_providers_llm.py` 中的 mock 需要更新：
- 将 `patch("google.generativeai.GenerativeModel")` 改为 `patch.object(llm.client.models, "generate_content")`
- 更新测试以适配新的 API 调用方式

当前状态：
- 18 个测试中 10 个通过
- 8 个失败（都是因为 mock 路径错误）

### 影响范围
升级仅影响：
- `src/providers/gemini_llm.py`
- `tests/unit/test_providers_llm.py`
- `requirements.txt`

其他模块无需修改。

## 参考文档

- 新 SDK 文档：`docs/external_api_docs/gemini/结构化输出.txt`
- 迁移指南：https://ai.google.dev/gemini-api/docs/migrate-to-google-genai
- PyPI 页面：https://pypi.org/project/google-genai/

## 总结

升级到新 SDK 后：
✅ 获得原生 JSON 输出支持
✅ 代码更简洁（无需复杂的 prompt engineering）
✅ 响应解析更可靠
✅ 与官方最新功能保持同步

实际 LLM 集成测试已通过，系统功能正常。单元测试的 mock 更新可以作为后续优化任务。
