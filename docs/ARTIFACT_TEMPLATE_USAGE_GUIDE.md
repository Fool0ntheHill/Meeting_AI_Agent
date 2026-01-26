# Artifact 模板使用指南 (前端)

## 📋 概述

本文档说明前端如何正确使用 Artifact 生成 API，特别是关于模板和 `prompt_text` 的使用。

**重要更新 (2026-01-26)**:
- ✅ 后端现在优先使用 `prompt_text`（如果提供）
- ✅ 支持用户在前端修改模板内容
- ✅ 修改后的内容会被正确使用，不会丢失

---

## 🎯 核心原则

### 后端处理逻辑

```
如果 prompt_instance.prompt_text 存在且不为空:
  ✅ 使用 prompt_text（用户修改过的内容）
否则如果 template_id == "__blank__":
  ✅ 创建空白模板（使用默认提示词）
否则:
  ✅ 从数据库查询 template_id 对应的模板
```

**这意味着**:
- 用户修改模板 → 传 `prompt_text` → 使用修改后的内容
- 用户没修改 → 不传 `prompt_text` → 使用数据库中的原始模板
- 空白模板 + 有内容 → 传 `prompt_text` → 使用用户自定义内容
- 空白模板 + 无内容 → 不传或传空 `prompt_text` → 使用默认提示词

---

## 📡 API 接口

### 1. 新建 Artifact

**接口**: `POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate`

**请求体**:
```typescript
{
  prompt_instance: {
    template_id: string;      // 模板 ID 或 "__blank__"
    language: string;          // "zh-CN" 或 "en-US"
    prompt_text?: string;      // 可选：用户修改后的提示词
    parameters: object;        // 模板参数
  }
}
```

### 2. 重新生成 Artifact

**接口**: `POST /api/v1/tasks/{task_id}/artifacts/regenerate`

**请求体**: 同上

### 3. 修正转写后重新生成

**接口**: `POST /api/v1/tasks/{task_id}/corrections/apply`

**请求体**: 同上

---

## 💡 使用场景

### 场景 1: 使用原始模板（用户没修改）

**前端代码**:
```typescript
const response = await fetch(`/api/v1/tasks/${taskId}/artifacts/meeting_minutes/generate`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    prompt_instance: {
      template_id: "template_meeting_minutes_v1",
      language: "zh-CN",
      // ❌ 不传 prompt_text
      parameters: {}
    }
  })
});
```

**后端行为**:
- 从数据库查询 `template_meeting_minutes_v1`
- 使用数据库中的原始模板内容

---

### 场景 2: 用户修改了模板

**前端代码**:
```typescript
// 用户在编辑器中修改了模板
const userModifiedPrompt = editor.getValue(); // "请生成一份详细的会议纪要，重点关注..."

const response = await fetch(`/api/v1/tasks/${taskId}/artifacts/meeting_minutes/generate`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    prompt_instance: {
      template_id: "template_meeting_minutes_v1",  // 原始模板 ID
      language: "zh-CN",
      prompt_text: userModifiedPrompt,  // ✅ 传用户修改后的内容
      parameters: {}
    }
  })
});
```

**后端行为**:
- 检测到 `prompt_text` 存在
- ✅ 使用 `prompt_text`（用户修改后的内容）
- ❌ 不查询数据库模板

**关键点**:
- ✅ 用户的修改会被保留和使用
- ✅ 不会丢失用户的编辑内容

---

### 场景 3: 空白模板（自定义提示词）

**前端代码**:
```typescript
const customPrompt = "根据会议逐字稿，帮我统计每个参会人分别说了几句话。";

const response = await fetch(`/api/v1/tasks/${taskId}/artifacts/meeting_minutes/generate`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    prompt_instance: {
      template_id: "__blank__",  // 特殊标识：空白模板
      language: "zh-CN",
      prompt_text: customPrompt,  // ✅ 必须传自定义提示词
      parameters: {}
    }
  })
});
```

**后端行为**:
- 检测到 `prompt_text` 存在
- 创建临时空白模板
- 使用 `prompt_text` 作为提示词

---

## 🔄 完整的前端实现示例

### TypeScript 类型定义

```typescript
interface PromptInstance {
  template_id: string;
  language: 'zh-CN' | 'en-US';
  prompt_text?: string;  // 可选：用户修改后的内容
  parameters: Record<string, any>;
}

interface GenerateArtifactRequest {
  prompt_instance: PromptInstance;
}

interface GenerateArtifactResponse {
  success: boolean;
  artifact_id: string;
  version: number;
  content: any;
  message: string;
}
```

### 前端服务封装

```typescript
class ArtifactService {
  /**
   * 生成 Artifact
   * 
   * @param taskId 任务 ID
   * @param artifactType 类型 (meeting_minutes, action_items, summary_notes)
   * @param templateId 模板 ID 或 "__blank__"
   * @param language 语言
   * @param promptText 可选：用户修改后的提示词
   * @param parameters 模板参数
   */
  async generateArtifact(
    taskId: string,
    artifactType: string,
    templateId: string,
    language: 'zh-CN' | 'en-US',
    promptText?: string,
    parameters: Record<string, any> = {}
  ): Promise<GenerateArtifactResponse> {
    const request: GenerateArtifactRequest = {
      prompt_instance: {
        template_id: templateId,
        language: language,
        parameters: parameters
      }
    };

    // 关键：只有在用户修改了内容时才传 prompt_text
    if (promptText) {
      request.prompt_instance.prompt_text = promptText;
    }

    const response = await fetch(
      `/api/v1/tasks/${taskId}/artifacts/${artifactType}/generate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      }
    );

    if (!response.ok) {
      throw new Error(`生成失败: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * 重新生成 Artifact
   */
  async regenerateArtifact(
    taskId: string,
    artifactType: string,
    templateId: string,
    language: 'zh-CN' | 'en-US',
    promptText?: string,
    parameters: Record<string, any> = {}
  ): Promise<GenerateArtifactResponse> {
    const request: GenerateArtifactRequest = {
      prompt_instance: {
        template_id: templateId,
        language: language,
        parameters: parameters
      }
    };

    if (promptText) {
      request.prompt_instance.prompt_text = promptText;
    }

    const response = await fetch(
      `/api/v1/tasks/${taskId}/artifacts/regenerate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      }
    );

    if (!response.ok) {
      throw new Error(`重新生成失败: ${response.statusText}`);
    }

    return await response.json();
  }

  private getToken(): string {
    return localStorage.getItem('access_token') || '';
  }
}
```

### React 组件示例

```typescript
import React, { useState } from 'react';

interface ArtifactEditorProps {
  taskId: string;
  templateId: string;
  initialPrompt: string;
}

const ArtifactEditor: React.FC<ArtifactEditorProps> = ({
  taskId,
  templateId,
  initialPrompt
}) => {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [isModified, setIsModified] = useState(false);
  const [loading, setLoading] = useState(false);

  const handlePromptChange = (value: string) => {
    setPrompt(value);
    setIsModified(value !== initialPrompt);
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const service = new ArtifactService();
      
      // 关键：只有在用户修改了内容时才传 prompt_text
      const result = await service.generateArtifact(
        taskId,
        'meeting_minutes',
        templateId,
        'zh-CN',
        isModified ? prompt : undefined  // ✅ 根据是否修改决定是否传 prompt_text
      );

      console.log('生成成功:', result);
      // 显示结果...
    } catch (error) {
      console.error('生成失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea
        value={prompt}
        onChange={(e) => handlePromptChange(e.target.value)}
        rows={10}
        cols={80}
      />
      {isModified && (
        <div style={{ color: 'orange' }}>
          ⚠️ 您已修改模板内容
        </div>
      )}
      <button onClick={handleGenerate} disabled={loading}>
        {loading ? '生成中...' : '生成 Artifact'}
      </button>
    </div>
  );
};
```

---

## ⚠️ 注意事项

### 1. 何时传 `prompt_text`

✅ **应该传**:
- 用户在编辑器中修改了模板内容
- 使用空白模板（`template_id: "__blank__"`）
- 用户输入了自定义提示词

❌ **不应该传**:
- 用户没有修改模板，使用原始模板
- 想要使用数据库中的最新模板版本

### 2. 空白模板必须传 `prompt_text`

**重要更新 (2026-01-26 晚)**:
- ✅ 空白模板现在即使不传 `prompt_text` 也能正常工作
- ✅ 后端会自动处理 `template_id: "__blank__"` 的情况
- ✅ 如果 `prompt_text` 为空字符串或 null，会使用默认提示词

```typescript
// ✅ 正确：空白模板传自定义提示词
{
  template_id: "__blank__",
  language: "zh-CN",
  prompt_text: "自定义提示词",
  parameters: {}
}

// ✅ 也正确：空白模板不传 prompt_text（使用默认）
{
  template_id: "__blank__",
  language: "zh-CN",
  prompt_text: "",  // 或 null，后端会使用默认提示词
  parameters: {}
}
```

### 3. 性能考虑

- `prompt_text` 可能很长，只在需要时传递
- 如果用户没修改，不传 `prompt_text` 可以减少请求体大小

### 4. 用户体验

建议在 UI 中显示：
- 用户是否修改了模板（显示提示）
- 提供"恢复原始模板"按钮
- 保存用户的修改历史

---

## 🔍 调试技巧

### 检查请求

```typescript
// 在发送请求前打印
console.log('Request:', {
  template_id: templateId,
  has_prompt_text: !!promptText,
  prompt_text_length: promptText?.length
});
```

### 查看后端日志

后端会记录：
```
Generating artifact with prompt_instance: template_id=xxx, has_prompt_text=true
```

---

## 📊 对比表

| 场景 | template_id | prompt_text | 后端行为 |
|------|-------------|-------------|----------|
| 使用原始模板 | `template_xxx` | `undefined` | 从数据库查询模板 |
| 用户修改模板 | `template_xxx` | 用户修改的内容 | 使用 prompt_text |
| 空白模板（有内容） | `__blank__` | 用户自定义内容 | 使用 prompt_text |
| 空白模板（无内容） | `__blank__` | `""` 或 `null` | 使用默认提示词 |

---

## ✅ 总结

1. **优先使用 `prompt_text`**: 后端会优先使用 `prompt_text`（如果提供）
2. **用户修改会保留**: 传递 `prompt_text` 可以保留用户的修改
3. **灵活使用**: 根据用户是否修改决定是否传 `prompt_text`
4. **空白模板**: 使用 `__blank__` 时必须传 `prompt_text`

**最佳实践**:
```typescript
// 判断是否传 prompt_text
const shouldSendPromptText = 
  isBlankTemplate ||           // 空白模板
  userHasModified ||           // 用户修改了
  isCustomPrompt;              // 自定义提示词

const request = {
  prompt_instance: {
    template_id: templateId,
    language: language,
    ...(shouldSendPromptText && { prompt_text: promptText }),
    parameters: parameters
  }
};
```

---

**更新日期**: 2026-01-26  
**相关文档**: 
- `docs/PROMPT_INSTANCE_FRONTEND_GUIDE.md`
- `docs/summaries/BLANK_TEMPLATE_404_FIX.md`
