# 提示词构建流程完整说明

## 📋 概览

本文档详细说明了从用户上传音频到前端显示会议纪要的完整流程，重点展示提示词是如何构建的。

---

## 🔄 完整流程图

```
用户上传音频
    ↓
ASR 转写 (火山引擎)
    ↓
声纹识别 (讯飞)
    ↓
【提示词构建】← 你在这里
    ↓
LLM 生成 (Gemini)
    ↓
存储到数据库
    ↓
API 返回给前端
    ↓
前端 Markdown 渲染
```

---

## 🎯 提示词构建的 4 个组成部分

### 0️⃣ System Instruction（全局底层约束）⭐ NEW

**来源**: `src/providers/gemini_llm.py` 中的 `GLOBAL_SYSTEM_INSTRUCTION` 常量

**性质**: Gemini API 的 `system_instruction` 参数（不是 prompt 的一部分）

**内容**: 底层约束和格式清洗规则

**示例**:
```
【底层约束】

1. 核心原则：严格基于提供的【转写内容】生成回答，绝对不要编造转写中未提及的事实或细节。
   如果信息缺失，请直接说明或标记为 [???]。

2. 格式兼容性：为了适配企业微信文档的粘贴格式，请严格遵守以下 Markdown 规范：
   - 严禁使用 Checkbox 复选框语法（即禁止出现 "- [ ]" 或 "- [x]"）。
   - 所有列表项（包括待办事项、行动项）必须强制使用标准的无序列表符号 "-" 开头。
```

**特点**:
- ✅ 全局生效，所有任务类型共享
- ✅ 防幻觉：强制基于转写内容，禁止编造
- ✅ 格式兼容：禁用复选框，确保企微文档兼容
- ✅ 不定义角色：保持用户模板的灵活性

**设计原则**:
- ❌ **不在这里定义**: "你是什么角色"（如"你是会议助手"）
- ✅ **只定义**: 负向约束（不要做什么）和格式清洗（必须遵守的格式规范）
- ✅ **目的**: 让用户模板保持完全的任务类型灵活性

---

### 1️⃣ 模板主体 (prompt_body)

**来源**: 数据库 `prompt_templates` 表

**内容**: 用户定义的内容要求和格式说明

**示例**:
```markdown
请根据以下会议转写内容，生成一份详细的会议摘要。

## 要求

请以 Markdown 格式输出，包含以下章节：

### 1. 会议基本信息
- 会议标题
- 参与者列表

### 2. 会议概要
简要总结整个会议的主要内容和目的

### 3. 讨论要点
按照讨论顺序列出各个议题

### 4. 决策事项
列出会议中做出的所有决策

### 5. 行动项
列出所有待办事项，格式：
- **[负责人]**: 任务描述

### 6. 其他
其他需要记录的信息
```

**特点**:
- ✅ 用户可以自定义修改
- ✅ 支持参数占位符 `{参数名}`
- ✅ 支持多语言版本

---

### 2️⃣ 转写内容 ({transcript})

**来源**: ASR 转写结果 + 声纹识别结果

**格式化方式**: `GeminiLLM.format_transcript()` 方法

**示例**:
```
[蓝为一] 今天我们讨论一下新功能的设计方案，主要是关于用户认证模块 (00:00:05 - 00:00:12)
[张三] 我建议采用 JWT 方案，这样可以实现无状态认证 (00:00:13 - 00:00:18)
[李四] JWT 有安全风险，需要考虑 token 刷新机制 (00:00:19 - 00:00:25)
[蓝为一] 那我们就采用 JWT + Refresh Token 的方案 (00:00:26 - 00:00:30)
[张三] 好的，我负责实现这个功能 (00:00:31 - 00:00:33)
```

**特点**:
- ✅ 包含说话人信息
- ✅ 包含时间戳
- ✅ 自动替换模板中的 `{transcript}` 占位符

---

### 3️⃣ 输出语言指令

**来源**: `output_language` 参数

**添加位置**: 提示词末尾

**支持的语言**:
- `zh-CN`: "请使用中文生成会议纪要。"
- `en-US`: "Please generate the meeting minutes in English."
- `ja-JP`: "日本語で議事録を作成してください。"
- `ko-KR`: "한국어로 회의록을 작성해 주세요。"

**特点**:
- ✅ 自动根据参数添加
- ✅ 确保输出语言一致

---

### 4️⃣ JSON Schema (强制输出格式)

**来源**: `GeminiLLM._build_response_schema()` 方法

**配置方式**: Gemini API 参数

**Schema 定义**:
```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "string",
      "description": "Markdown 格式的内容，可以包含任意结构的文本、列表、表格等"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "title": {"type": "string", "description": "标题"},
        "summary": {"type": "string", "description": "简短摘要"}
      },
      "description": "可选的元数据"
    }
  },
  "required": ["content"]
}
```

**Gemini API 配置**:
```python
config = types.GenerateContentConfig(
    max_output_tokens=8192,
    temperature=0.7,
    response_mime_type="application/json",  # 强制 JSON 输出
    response_schema=schema  # 强制输出格式
)
```

**特点**:
- ✅ 100% 保证输出格式统一
- ✅ Gemini 会自动验证输出是否符合 Schema
- ✅ 极简设计：只有 `content` 和 `metadata` 两个字段
- ✅ 内容完全灵活：Markdown 可以表达任何结构

---

## 🔧 代码实现位置

### System Instruction（全局约束）⭐ NEW
- **文件**: `src/providers/gemini_llm.py`
- **常量**: `GLOBAL_SYSTEM_INSTRUCTION`
- **作用**: 防幻觉 + 格式兼容性（企微文档）
- **传递方式**: API 参数 `system_instruction`

### 提示词构建
- **文件**: `src/providers/gemini_llm.py`
- **方法**: `_build_prompt()`
- **调用链**:
  ```
  generate_artifact()
    → _build_prompt()
      → 替换 {transcript}
      → 替换其他参数
      → 添加语言指令
  ```

### Schema 构建
- **文件**: `src/providers/gemini_llm.py`
- **方法**: `_build_response_schema()`
- **特点**: 极简 Markdown schema，适用于所有 artifact 类型

### 转写格式化
- **文件**: `src/providers/gemini_llm.py`
- **方法**: `format_transcript()`
- **格式**: `[说话人] 文本 (开始时间 - 结束时间)`

---

## 📊 完整示例

### 输入数据

**模板** (来自数据库):
```markdown
请根据以下会议转写内容，生成一份详细的会议摘要。

## 转写内容
{transcript}

## 输出格式
请以 JSON 格式输出...
```

**转写结果**:
```python
TranscriptionResult(
    segments=[
        Segment(speaker="蓝为一", text="今天讨论认证模块", start_time=5.0, end_time=12.0),
        Segment(speaker="张三", text="建议用JWT", start_time=13.0, end_time=18.0),
        ...
    ]
)
```

**参数**:
```python
output_language = OutputLanguage.ZH_CN
```

---

### 构建过程

**步骤 1**: 格式化转写
```
[蓝为一] 今天讨论认证模块 (00:00:05 - 00:00:12)
[张三] 建议用JWT (00:00:13 - 00:00:18)
```

**步骤 2**: 替换占位符
```markdown
请根据以下会议转写内容，生成一份详细的会议摘要。

## 转写内容
[蓝为一] 今天讨论认证模块 (00:00:05 - 00:00:12)
[张三] 建议用JWT (00:00:13 - 00:00:18)

## 输出格式
请以 JSON 格式输出...
```

**步骤 3**: 添加语言指令
```markdown
...（上面的内容）...

请使用中文生成会议纪要。
```

**步骤 4**: 配置 Schema
```python
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "metadata": {"type": "object"}
        },
        "required": ["content"]
    }
)
```

---

### Gemini 返回结果

```json
{
  "content": "## 会议基本信息\n\n**会议标题**: 用户认证模块设计讨论\n**参与者**: 蓝为一、张三\n\n## 会议概要\n\n本次会议讨论了用户认证模块的技术方案...",
  "metadata": {
    "title": "用户认证模块设计讨论",
    "summary": "讨论并决定了认证方案"
  }
}
```

---

### 存储到数据库

**表**: `generated_artifacts`

**字段**:
```python
{
    "artifact_id": "art_task_xxx_meeting_minutes_v1",
    "task_id": "task_xxx",
    "artifact_type": "meeting_minutes",
    "version": 1,
    "content": '{"content": "## 会议基本信息...", "metadata": {...}}',  # JSON 字符串
    "prompt_instance": {
        "template_id": "meeting_minutes_detailed_summary",
        "language": "zh-CN",
        "parameters": {}
    }
}
```

---

### API 返回给前端

**接口**: `GET /api/v1/artifacts/{artifact_id}`

**返回格式** (经过 MarkdownConverter 转换):
```json
{
  "artifact_id": "art_task_xxx_meeting_minutes_v1",
  "display_type": "markdown",
  "data": {
    "title": "用户认证模块设计讨论",
    "content": "## 会议基本信息\n\n**会议标题**: 用户认证模块设计讨论\n..."
  }
}
```

---

### 前端渲染

```typescript
// 前端代码（极简）
const ArtifactView = ({ artifactId }) => {
  const { data } = useArtifact(artifactId);
  
  return (
    <div>
      <h1>{data.title}</h1>
      <MarkdownRenderer content={data.content} />
    </div>
  );
};
```

---

## 🎨 关键设计决策

### 为什么使用 Markdown Schema？

**问题**: 之前的 Schema 太具体（如 `topics`, `action_items`），导致：
- ❌ 用户自定义模板时，字段不匹配
- ❌ 不同类型的 artifact 需要不同的 Schema
- ❌ Schema 变化时前端也要改

**解决方案**: 极简 Markdown Schema
- ✅ 只有 `content` 字段（必需）
- ✅ Markdown 可以表达任何结构
- ✅ 适用于所有 artifact 类型
- ✅ 用户可以自由定义内容格式

### 为什么后端统一转换？

**问题**: 历史数据格式不一致
- 格式 1: `[{"会议概要": "..."}]` (数组)
- 格式 2: `{"meeting_minutes": "..."}` (Markdown 字符串)
- 格式 3: `{"topics": [...]}` (结构化 JSON)
- 格式 4: `{"content": "..."}` (新 Markdown)

**解决方案**: MarkdownConverter 万能转接头
- ✅ 后端统一转换为 `{title, content}`
- ✅ 前端永远只收到一种格式
- ✅ 不会白屏（完全兜底）
- ✅ 零维护（格式变化前端不用改）

---

## 📝 总结

### 提示词的 4 个组成部分

0. **System Instruction** - 全局底层约束（防幻觉 + 格式兼容）⭐ NEW
1. **模板主体** - 用户定义的内容要求
2. **转写内容** - 实际的会议对话（包含声纹识别结果）
3. **语言指令** - 确保输出语言一致
4. **JSON Schema** - 强制输出格式统一（API 参数）

### 关键优势

- ✅ **用户友好**: 只需修改模板主体，不用关心技术细节
- ✅ **格式统一**: Schema 保证 100% 输出一致
- ✅ **前端稳定**: 永远收到相同格式，不会白屏
- ✅ **完全兜底**: 历史数据通过转换器统一处理
- ✅ **零维护**: 格式变化前端不用改代码

### 相关文档

- [Markdown 统一格式方案](./MARKDOWN_UNIFIED_FORMAT.md)
- [前端开发指南](./FRONTEND_DEVELOPMENT_GUIDE.md)
- [API 快速参考](./API_QUICK_REFERENCE.md)
