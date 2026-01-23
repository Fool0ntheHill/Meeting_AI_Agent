# 提示词传递前端集成指南

## 重要更新

后端已修复提示词处理逻辑，现在**完全支持用户在前端编辑的提示词**。

## 核心概念

### `prompt_instance` 数据结构

```typescript
interface PromptInstance {
  template_id: string;           // 必填：模板ID（或 "__blank__" 表示空白模板）
  language?: string;             // 可选：语言，默认 "zh-CN"
  prompt_text?: string;          // 可选：用户编辑后的完整提示词文本
  parameters?: Record<string, any>;  // 可选：模板参数（用于占位符替换）
  custom_instructions?: string;  // 可选：用户补充指令（追加到提示词末尾）
}
```

### 处理逻辑

后端会按以下优先级使用提示词：

1. **如果提供了 `prompt_text`** → 使用用户编辑的完整提示词
2. **如果没有 `prompt_text`** → 从模板加载 `prompt_body`
3. **如果有 `custom_instructions`** → 追加到提示词末尾

---

## 三种使用场景

### 场景 1: 使用模板，不修改

用户选择了一个模板，没有编辑提示词内容。

**前端传递**:
```json
{
  "template_id": "tpl_standard_minutes",
  "language": "zh-CN",
  "parameters": {
    "meeting_description": "产品规划会议"
  }
}
```

**后端行为**: 使用模板的原始 `prompt_body`

---

### 场景 2: 使用模板，但用户修改了提示词

用户基于模板修改了提示词内容（删除了一些部分，或者改了措辞）。

**前端传递**:
```json
{
  "template_id": "tpl_standard_minutes",
  "language": "zh-CN",
  "prompt_text": "请生成简洁的会议纪要，重点关注以下内容：\n1. 核心决策\n2. 待办事项\n\n会议转写：\n{transcript}",
  "parameters": {}
}
```

**后端行为**: 使用用户编辑的 `prompt_text`，忽略模板原文

**关键点**:
- `prompt_text` 必须包含 `{transcript}` 占位符，后端会替换为实际转写内容
- 如果没有 `{transcript}`，后端会自动追加转写内容

---

### 场景 3: 空白模板，完全自定义

用户选择"空白模板"，从零开始编写提示词。

**前端传递**:
```json
{
  "template_id": "__blank__",
  "language": "zh-CN",
  "prompt_text": "请分析这次技术会议，提取以下信息：\n- 技术决策和理由\n- 潜在风险点\n- 需要跟进的技术问题\n\n会议内容：\n{transcript}",
  "parameters": {}
}
```

**后端行为**: 使用用户的 `prompt_text` 作为完整提示词

---

## 前端实现建议

### 1. 模板选择器

```typescript
// 用户选择模板
const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
const [promptText, setPromptText] = useState<string>("");
const [isEdited, setIsEdited] = useState(false);

// 当用户选择模板时
const handleTemplateSelect = (template: Template) => {
  setSelectedTemplate(template);
  setPromptText(template.prompt_body);  // 加载模板原文到编辑器
  setIsEdited(false);
};

// 当用户编辑提示词时
const handlePromptEdit = (newText: string) => {
  setPromptText(newText);
  setIsEdited(true);  // 标记为已编辑
};
```

### 2. 构建 prompt_instance

```typescript
const buildPromptInstance = (): PromptInstance => {
  const instance: PromptInstance = {
    template_id: selectedTemplate?.template_id || "__blank__",
    language: "zh-CN",
    parameters: {}
  };

  // 如果用户编辑了提示词，传递 prompt_text
  if (isEdited || selectedTemplate?.template_id === "__blank__") {
    instance.prompt_text = promptText;
  }

  return instance;
};
```

### 3. 创建任务

```typescript
const createTask = async () => {
  const promptInstance = buildPromptInstance();

  const request = {
    audio_files: uploadedFiles.map(f => f.file_path),
    file_order: uploadedFiles.map((_, i) => i),
    meeting_type: meetingType,
    asr_language: "zh-CN+en-US",
    output_language: "zh-CN",
    prompt_instance: promptInstance,  // ← 传递提示词实例
    audio_duration: totalDuration,
    skip_speaker_recognition: false
  };

  const response = await fetch('/api/v1/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(request)
  });

  return response.json();
};
```

---

## 完整示例

### React 组件示例

```typescript
import React, { useState } from 'react';

interface Template {
  template_id: string;
  title: string;
  prompt_body: string;
}

const TaskCreator: React.FC = () => {
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [promptText, setPromptText] = useState<string>("");
  const [isEdited, setIsEdited] = useState(false);

  // 模板列表
  const templates: Template[] = [
    {
      template_id: "tpl_standard_minutes",
      title: "标准会议纪要",
      prompt_body: "请生成标准的会议纪要...\n\n{transcript}"
    },
    {
      template_id: "__blank__",
      title: "空白模板",
      prompt_body: ""
    }
  ];

  const handleTemplateSelect = (template: Template) => {
    setSelectedTemplate(template);
    setPromptText(template.prompt_body);
    setIsEdited(false);
  };

  const handlePromptEdit = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPromptText(e.target.value);
    setIsEdited(true);
  };

  const handleSubmit = async () => {
    const promptInstance = {
      template_id: selectedTemplate?.template_id || "__blank__",
      language: "zh-CN",
      ...(isEdited || selectedTemplate?.template_id === "__blank__" 
        ? { prompt_text: promptText } 
        : {}
      ),
      parameters: {}
    };

    const request = {
      audio_files: ["uploads/user_xxx/audio.ogg"],
      file_order: [0],
      meeting_type: "weekly_sync",
      asr_language: "zh-CN+en-US",
      output_language: "zh-CN",
      prompt_instance: promptInstance,
      audio_duration: 300.5,
      skip_speaker_recognition: false
    };

    const response = await fetch('/api/v1/tasks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(request)
    });

    const result = await response.json();
    console.log('Task created:', result);
  };

  return (
    <div>
      <h2>选择提示词模板</h2>
      <select onChange={(e) => {
        const template = templates.find(t => t.template_id === e.target.value);
        if (template) handleTemplateSelect(template);
      }}>
        <option value="">请选择...</option>
        {templates.map(t => (
          <option key={t.template_id} value={t.template_id}>
            {t.title}
          </option>
        ))}
      </select>

      <h3>编辑提示词</h3>
      <textarea
        value={promptText}
        onChange={handlePromptEdit}
        rows={10}
        cols={80}
        placeholder="在这里编辑提示词..."
      />

      {isEdited && (
        <p style={{ color: 'orange' }}>
          ⚠️ 提示词已修改，将使用您编辑的版本
        </p>
      )}

      <button onClick={handleSubmit}>创建任务</button>
    </div>
  );
};

export default TaskCreator;
```

---

## 重要注意事项

### 1. `{transcript}` 占位符

- **必须包含**: 提示词中必须有 `{transcript}` 占位符
- **自动追加**: 如果忘记写，后端会自动追加转写内容
- **建议**: 前端编辑器可以提示用户必须包含此占位符

### 2. 空白模板

- **template_id**: 使用 `"__blank__"` 表示空白模板
- **必须提供 prompt_text**: 空白模板必须传递 `prompt_text`
- **不会使用默认模板**: 后端不会使用任何预设模板

### 3. 向后兼容

- **旧版本前端**: 如果不传 `prompt_text`，后端会使用模板原文
- **新版本前端**: 传递 `prompt_text` 后，后端优先使用用户编辑的版本

### 4. 参数替换

如果提示词中有占位符（如 `{meeting_description}`），需要在 `parameters` 中提供：

```json
{
  "template_id": "tpl_001",
  "prompt_text": "会议描述：{meeting_description}\n\n{transcript}",
  "parameters": {
    "meeting_description": "产品规划会议"
  }
}
```

---

## 验证方法

### 1. 检查请求

在浏览器开发者工具中查看请求体：

```json
{
  "prompt_instance": {
    "template_id": "tpl_standard_minutes",
    "language": "zh-CN",
    "prompt_text": "用户编辑的提示词...",  // ← 应该包含这个字段
    "parameters": {}
  }
}
```

### 2. 检查后端日志

后端日志会显示使用的提示词来源：

```
Using user-edited prompt_text from prompt_instance  // ← 使用用户编辑的
```

或

```
Using prompt_body from template: tpl_standard_minutes  // ← 使用模板原文
```

---

## 常见问题

### Q1: 用户选择模板但没有编辑，需要传 `prompt_text` 吗？

**A**: 不需要。如果用户没有编辑，不传 `prompt_text`，后端会自动使用模板原文。

### Q2: 空白模板必须传 `prompt_text` 吗？

**A**: 是的。空白模板 (`__blank__`) 必须传递 `prompt_text`，否则后端会使用一个最简单的默认提示。

### Q3: `custom_instructions` 和 `prompt_text` 有什么区别？

**A**: 
- `prompt_text`: 完整的提示词文本（替代模板原文）
- `custom_instructions`: 补充指令（追加到提示词末尾）

通常只需要使用 `prompt_text`。

### Q4: 如何知道用户是否编辑了提示词？

**A**: 前端需要跟踪编辑状态：

```typescript
const [isEdited, setIsEdited] = useState(false);

// 当用户修改文本时
const handleEdit = (newText: string) => {
  setPromptText(newText);
  setIsEdited(true);  // 标记为已编辑
};

// 构建请求时
const promptInstance = {
  template_id: selectedTemplate.template_id,
  ...(isEdited ? { prompt_text: promptText } : {})
};
```

---

## 提示词存储与回溯

### 自动存储

后端会自动将每次生成时使用的提示词信息保存到 `artifact.metadata.prompt` 中：

```typescript
interface ArtifactMetadata {
  prompt: {
    template_id: string;           // 模板ID
    language: string;               // 语言
    parameters: Record<string, any>; // 参数
    prompt_text: string;            // 实际使用的完整提示词
    is_user_edited: boolean;        // 是否用户编辑
    custom_instructions?: string;   // 补充指令（可选）
  };
}
```

### 查看提示词

在 Workspace 中可以查看任何 artifact 生成时使用的提示词：

```typescript
const artifact = await getArtifactDetail(taskId, artifactId);
const promptInfo = artifact.metadata?.prompt;

if (promptInfo) {
  console.log('模板:', promptInfo.template_id);
  console.log('提示词:', promptInfo.prompt_text);
  console.log('是否编辑:', promptInfo.is_user_edited);
}
```

### 重新生成

可以使用相同的提示词重新生成：

```typescript
const regenerateWithSamePrompt = async (artifact: Artifact) => {
  const promptInfo = artifact.metadata?.prompt;
  
  const promptInstance = {
    template_id: promptInfo.template_id,
    language: promptInfo.language,
    parameters: promptInfo.parameters,
    ...(promptInfo.is_user_edited ? {
      prompt_text: promptInfo.prompt_text
    } : {})
  };
  
  // 调用重新生成 API
  await regenerateArtifact(taskId, artifactType, promptInstance);
};
```

详细文档: [Artifact 提示词存储与回溯指南](./ARTIFACT_PROMPT_STORAGE_GUIDE.md)

---

## 总结

✅ **用户编辑了提示词** → 传递 `prompt_text`，后端使用用户版本  
✅ **用户没有编辑** → 不传 `prompt_text`，后端使用模板原文  
✅ **空白模板** → 必须传递 `prompt_text`  
✅ **向后兼容** → 旧版本前端不传 `prompt_text` 仍然可以工作

现在后端完全支持用户自定义提示词，前端只需要正确传递 `prompt_text` 字段即可！
