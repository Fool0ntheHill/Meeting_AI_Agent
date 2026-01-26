# 新建 Artifact 调试指南

## 问题描述

生成新 artifact 时提示"没有 prompt"或"模板不存在"。

## 快速诊断

### 1️⃣ 检查前端请求（浏览器）

**步骤**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 **Network** 标签
3. 清空现有请求
4. 在前端输入自定义提示词，点击生成
5. 找到 `generate` 请求
6. 查看 **Request Payload**

**✅ 正确的请求格式**:
```json
{
  "prompt_instance": {
    "template_id": "__blank__",
    "language": "zh-CN",
    "prompt_text": "用户输入的内容在这里",  ← 重点检查这个字段
    "parameters": {}
  }
}
```

**❌ 常见错误**:
- 没有 `prompt_text` 字段
- `prompt_text` 是 `null`
- `prompt_text` 是空字符串 `""`
- `prompt_text` 的值不是用户输入的内容

---

### 2️⃣ 检查后端日志（控制台）

**关键日志 1**: API 接收
```
搜索: "Generating artifact with prompt_instance"
示例: Generating artifact with prompt_instance: template_id=__blank__, has_prompt_text=True
```

- ✅ `has_prompt_text=True` → 后端接收到了
- ❌ `has_prompt_text=False` → 后端没有接收到

**关键日志 2**: 服务层处理
```
搜索: "Converting dict to PromptInstance"
然后查看:
  - "Has prompt_text: True"
  - "prompt_text type: <class 'str'>, length: 25 chars"
  - "prompt_text preview: 用户输入的内容..."
```

- ✅ `length > 0` → 有内容
- ❌ `length = 0` → 空字符串

**关键日志 3**: 模板处理
```
搜索以下任一:
  - "Using prompt_text from prompt_instance"  ← 正常
  - "Template is __blank__, creating blank template"  ← 正常
  - "模板不存在: __blank__"  ← 错误
```

---

## 问题诊断表

| 前端请求 | 后端日志 | 问题原因 | 解决方案 |
|---------|---------|---------|---------|
| 没有 `prompt_text` | `has_prompt_text=False` | 前端没传 | 修复前端代码 |
| `prompt_text: ""` | `has_prompt_text=True, length: 0` | 前端传了空字符串 | 检查前端输入绑定 |
| `prompt_text: "内容"` | `has_prompt_text=False` | 后端没解析 | 检查后端模型 |
| `prompt_text: "内容"` | `has_prompt_text=True, length > 0` 但报错 | 后端没使用 | 检查服务层逻辑 |

---

## 常见前端问题

### 问题 1: 没有绑定用户输入

**症状**: 用户输入了内容，但请求中 `prompt_text` 为空

**检查**:
```typescript
// ❌ 错误：没有绑定
<textarea></textarea>

// ✅ 正确：绑定到状态
<textarea v-model="promptText"></textarea>
// 或
<textarea onChange={(e) => setPromptText(e.target.value)}></textarea>
```

### 问题 2: 发送前清空了字段

**症状**: 用户输入了内容，但请求中 `prompt_text` 为空

**检查**:
```typescript
// ❌ 错误：发送前清空了
const generateArtifact = () => {
  const data = {
    prompt_instance: {
      template_id: "__blank__",
      language: "zh-CN",
      prompt_text: "",  // 硬编码为空字符串
      parameters: {}
    }
  };
  api.post('/generate', data);
};

// ✅ 正确：使用状态中的值
const generateArtifact = () => {
  const data = {
    prompt_instance: {
      template_id: "__blank__",
      language: "zh-CN",
      prompt_text: promptText,  // 使用状态变量
      parameters: {}
    }
  };
  api.post('/generate', data);
};
```

### 问题 3: 字段名拼写错误

**症状**: 后端日志显示 `has_prompt_text=False`

**检查**:
```typescript
// ❌ 错误的字段名
{
  promptText: "内容",  // 驼峰命名
  prompt: "内容",      // 缺少 _text
  Prompt_Text: "内容"  // 大写
}

// ✅ 正确的字段名
{
  prompt_text: "内容"  // 下划线命名
}
```

### 问题 4: 没有包含在 prompt_instance 中

**症状**: 后端报错 "字段缺失"

**检查**:
```typescript
// ❌ 错误：prompt_text 在外层
{
  prompt_text: "内容",
  prompt_instance: {
    template_id: "__blank__",
    language: "zh-CN"
  }
}

// ✅ 正确：prompt_text 在 prompt_instance 内
{
  prompt_instance: {
    template_id: "__blank__",
    language: "zh-CN",
    prompt_text: "内容",
    parameters: {}
  }
}
```

---

## 测试后端是否正常

使用 curl 测试后端：

```bash
curl -X POST 'http://localhost:8000/api/v1/tasks/task_1c8f2c5d561048db/artifacts/meeting_minutes/generate' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt_instance": {
      "template_id": "__blank__",
      "language": "zh-CN",
      "prompt_text": "请生成一份简短的会议纪要",
      "parameters": {}
    }
  }'
```

**结果判断**:
- ✅ 成功 → 后端正常，问题在前端
- ❌ 失败 → 后端有问题，需要修复

---

## 前端代码示例

### React 示例

```typescript
import { useState } from 'react';

function ArtifactGenerator({ taskId }: { taskId: string }) {
  const [promptText, setPromptText] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    // 验证用户输入
    if (!promptText.trim()) {
      alert('请输入提示词');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/tasks/${taskId}/artifacts/meeting_minutes/generate`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            prompt_instance: {
              template_id: '__blank__',
              language: 'zh-CN',
              prompt_text: promptText,  // 使用状态变量
              parameters: {}
            }
          })
        }
      );

      if (!response.ok) {
        throw new Error(`生成失败: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('生成成功:', result);
    } catch (error) {
      console.error('生成失败:', error);
      alert('生成失败，请查看控制台');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea
        value={promptText}
        onChange={(e) => setPromptText(e.target.value)}
        placeholder="请输入自定义提示词"
        rows={10}
        cols={80}
      />
      <button onClick={handleGenerate} disabled={loading}>
        {loading ? '生成中...' : '生成 Artifact'}
      </button>
    </div>
  );
}
```

### Vue 示例

```vue
<template>
  <div>
    <textarea
      v-model="promptText"
      placeholder="请输入自定义提示词"
      rows="10"
      cols="80"
    />
    <button @click="handleGenerate" :disabled="loading">
      {{ loading ? '生成中...' : '生成 Artifact' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{ taskId: string }>();
const promptText = ref('');
const loading = ref(false);

const handleGenerate = async () => {
  // 验证用户输入
  if (!promptText.value.trim()) {
    alert('请输入提示词');
    return;
  }

  loading.value = true;
  try {
    const response = await fetch(
      `/api/v1/tasks/${props.taskId}/artifacts/meeting_minutes/generate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt_instance: {
            template_id: '__blank__',
            language: 'zh-CN',
            prompt_text: promptText.value,  // 使用 ref 的值
            parameters: {}
          }
        })
      }
    );

    if (!response.ok) {
      throw new Error(`生成失败: ${response.statusText}`);
    }

    const result = await response.json();
    console.log('生成成功:', result);
  } catch (error) {
    console.error('生成失败:', error);
    alert('生成失败，请查看控制台');
  } finally {
    loading.value = false;
  }
};
</script>
```

---

## 需要提供的调试信息

如果问题仍未解决，请提供：

1. **前端请求** (从浏览器开发者工具复制):
   ```json
   {
     "prompt_instance": { ... }
   }
   ```

2. **后端日志** (包含以下关键字的行):
   - `Generating artifact with prompt_instance`
   - `Converting dict to PromptInstance`
   - `Has prompt_text`
   - `prompt_text type`

3. **错误信息** (如果有):
   - 完整的错误堆栈
   - 错误发生的位置

---

## 相关文档

- [Artifact 模板使用指南](./ARTIFACT_TEMPLATE_USAGE_GUIDE.md)
- [空白模板 404 修复总结](./summaries/BLANK_TEMPLATE_404_FIX.md)
- [前端 API 集成指南](./api_references/FRONTEND_INTEGRATION_GUIDE.md)

---

**更新日期**: 2026-01-26  
**相关脚本**: 
- `scripts/debug_generate_artifact_request.py`
- `scripts/check_generate_request_logs.py`
