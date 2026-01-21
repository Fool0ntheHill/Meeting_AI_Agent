# Markdown 统一格式方案

## 🎯 核心思想

**后端全权兜底，统一转 Markdown** - 在后端加一个"万能转接头"，不管数据库里存的是什么格式，前端永远只收到一种格式。

## 📋 API 契约

### 前端接收的统一格式

```json
{
  "artifact_id": "art_12345",
  "display_type": "markdown",
  "data": {
    "title": "会议纪要 - 2026/01/21",
    "content": "## 会议概要\n本次会议讨论了...\n\n## 待办事项\n- [ ] 易松：修复组件库\n..."
  },
  "metadata": {
    "task_id": "task_xxx",
    "artifact_type": "meeting_minutes",
    "version": 1,
    "created_at": "2026-01-21T10:00:00",
    "created_by": "user_123"
  }
}
```

### 前端代码（极简）

```javascript
const ArtifactView = ({ data }) => {
  return (
    <div className="artifact-container">
      <h1>{data.title}</h1>
      <MarkdownRenderer content={data.content} />
    </div>
  );
};
```

## 🔄 后端转换策略

### 支持的格式

| 原始格式 | 示例 | 转换策略 |
|---------|------|---------|
| **v1 数组格式** | `[{"会议概要": "..."}]` | 遍历键值对，转为 Markdown 章节 |
| **v2 Markdown 字符串** | `{"meeting_minutes": "## ..."}` | 直接提取 Markdown 内容 |
| **v3 结构化 JSON** | `{"title": "...", "topics": [...]}` | 模板渲染为 Markdown |
| **新 Markdown 格式** | `{"content": "## ...", "metadata": {...}}` | 直通，无需转换 |
| **通用字典** | `{"标题": "...", "内容": "..."}` | 智能映射为 Markdown |
| **完全未知** | 任意格式 | 包装在 JSON 代码块中 |

### 转换示例

#### 示例 1: v1 数组格式

**输入:**
```json
[{
  "会议概要": "讨论了新功能",
  "讨论要点": ["要点1", "要点2"],
  "决策事项": ["决策1"]
}]
```

**输出:**
```markdown
## 会议概要

讨论了新功能

## 讨论要点

- 要点1
- 要点2

## 决策事项

- 决策1
```

#### 示例 2: v3 结构化 JSON

**输入:**
```json
{
  "title": "技术评审会议",
  "topics": [
    {
      "title": "架构设计",
      "key_points": ["使用微服务", "考虑性能"],
      "decisions": ["采用 Kubernetes"]
    }
  ],
  "action_items": [
    {
      "title": "搭建环境",
      "assignee": "张三",
      "deadline": "2026-01-30"
    }
  ]
}
```

**输出:**
```markdown
## 会议概要

...

## 讨论议题

### 架构设计

- 使用微服务
- 考虑性能

**决策**:
- ✅ 采用 Kubernetes

## 行动项

- [ ] **[张三]**: 搭建环境 (截止: 2026-01-30)
```

## ✅ 解决的问题

1. **彻底解决前端白屏**
   - 前端不再需要复杂的格式判断逻辑
   - 永远不会因为字段不存在而报错

2. **阅读体验一致**
   - 所有历史数据都被转换成统一的文档样式
   - 用户无感知

3. **开发维护成本低**
   - 以后无论 Prompt 怎么变，只需要在后端改转换逻辑
   - 前端一行代码都不用动

4. **兜底策略完善**
   - 即使遇到完全未知的格式，也会包装在 JSON 代码块中
   - 绝对不会让前端崩溃

## 🔧 实现细节

### 核心组件

1. **MarkdownConverter** (`src/utils/markdown_converter.py`)
   - 万能转接头，处理所有格式转换
   - 包含完善的兜底策略

2. **API 层** (`src/api/routes/artifacts.py`)
   - `GET /api/v1/artifacts/{id}` 使用转换器
   - 返回统一的 Markdown 格式

3. **LLM 层** (`src/providers/gemini_llm.py`)
   - 新数据使用 Markdown schema
   - 保证未来数据格式统一

### 测试覆盖

- ✅ v1 数组格式
- ✅ v2 Markdown 字符串格式
- ✅ v3 结构化 JSON 格式
- ✅ 通用字典格式
- ✅ 未知格式兜底

## 📊 性能影响

- **转换开销**: 极小（纯字符串拼接）
- **内存占用**: 无额外占用
- **响应时间**: 增加 < 10ms

## 🚀 未来扩展

如果需要支持其他渲染格式（如 PDF、Word），只需要：

1. 在转换器中添加新的输出格式
2. API 增加 `format` 参数
3. 前端根据 `display_type` 选择渲染器

```json
{
  "display_type": "pdf",  // 或 "markdown", "html"
  "data": {...}
}
```

## 📝 前端集成指南

### 1. 获取 Artifact

```javascript
const response = await fetch(`/api/v1/artifacts/${artifactId}`);
const data = await response.json();
```

### 2. 渲染

```javascript
// 使用任何 Markdown 渲染库
import ReactMarkdown from 'react-markdown';

<ReactMarkdown>{data.data.content}</ReactMarkdown>
```

### 3. 完整示例

```javascript
import React from 'react';
import ReactMarkdown from 'react-markdown';

const ArtifactViewer = ({ artifactId }) => {
  const [artifact, setArtifact] = React.useState(null);
  
  React.useEffect(() => {
    fetch(`/api/v1/artifacts/${artifactId}`)
      .then(res => res.json())
      .then(data => setArtifact(data));
  }, [artifactId]);
  
  if (!artifact) return <div>加载中...</div>;
  
  return (
    <div className="artifact-viewer">
      <h1>{artifact.data.title}</h1>
      <ReactMarkdown>{artifact.data.content}</ReactMarkdown>
    </div>
  );
};
```

## 🎉 总结

这个方案的核心优势是：

1. **简单** - 前端只需要处理一种格式
2. **稳定** - 后端保证永远不会返回错误格式
3. **灵活** - 支持任意历史格式和未来格式
4. **可维护** - 所有复杂逻辑都在后端，易于调试和优化

**前端开发者的福音：再也不用担心数据格式问题了！** 🎊
