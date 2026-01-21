# 前端提示词传递指南

## 问题说明

后端发现前端在创建任务时没有传递 `prompt_instance` 参数，导致 worker 处理时使用默认模板。如果前端UI上提示词选择是必选的，需要将用户选择的提示词传递给后端。

## 后端期望的数据格式

### 创建任务 API

**端点**: `POST /api/v1/tasks`

**请求体中的 `prompt_instance` 字段**:

```typescript
interface PromptInstance {
  template_id: string;      // 必填：模板ID（用户在前端选择的提示词ID）
  language?: string;        // 可选：语言，默认 "zh-CN"
  parameters?: Record<string, any>;  // 可选：模板参数
}
```

### 完整请求示例

```json
{
  "audio_files": ["uploads/user_test_user/abc123.ogg"],
  "file_order": [0],
  "meeting_type": "weekly_sync",
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN",
  "prompt_instance": {
    "template_id": "tpl_standard_minutes",
    "language": "zh-CN",
    "parameters": {
      "meeting_description": "产品规划会议"
    }
  },
  "skip_speaker_recognition": false
}
```

## 前端实现建议

### 1. 获取用户选择的模板ID

假设前端有一个模板选择器，用户选择了某个提示词模板：

```typescript
// 用户选择的模板
const selectedTemplate = {
  template_id: "tpl_standard_minutes",  // 从模板列表中获取
  title: "标准会议纪要",
  // ... 其他模板信息
};
```

### 2. 构建 prompt_instance 对象

```typescript
// 构建提示词实例
const promptInstance = {
  template_id: selectedTemplate.template_id,
  language: "zh-CN",  // 或从用户设置中获取
  parameters: {}  // 如果有额外参数可以添加
};
```

### 3. 在创建任务时传递

```typescript
// 创建任务请求
const createTaskRequest = {
  audio_files: uploadedFiles.map(f => f.file_path),
  file_order: uploadedFiles.map((_, index) => index),
  meeting_type: "weekly_sync",
  asr_language: "zh-CN+en-US",
  output_language: "zh-CN",
  prompt_instance: promptInstance,  // ← 关键：传递提示词实例
  skip_speaker_recognition: false
};

// 发送请求
const response = await fetch('/api/v1/tasks', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(createTaskRequest)
});
```

## 常见场景

### 场景1：用户选择了标准会议纪要模板

```json
{
  "prompt_instance": {
    "template_id": "tpl_standard_minutes",
    "language": "zh-CN",
    "parameters": {}
  }
}
```

### 场景2：用户选择了技术会议模板并添加了描述

```json
{
  "prompt_instance": {
    "template_id": "tpl_technical_minutes",
    "language": "zh-CN",
    "parameters": {
      "meeting_description": "技术架构评审会议\n讨论新系统设计方案"
    }
  }
}
```

### 场景3：用户选择了英文模板

```json
{
  "prompt_instance": {
    "template_id": "tpl_standard_minutes_en",
    "language": "en-US",
    "parameters": {}
  }
}
```

## 验证方法

### 1. 检查请求体

在浏览器开发者工具的 Network 标签中，查看创建任务的请求：

- 请求 URL: `POST /api/v1/tasks`
- 请求体应该包含 `prompt_instance` 字段
- `prompt_instance.template_id` 应该是用户选择的模板ID

### 2. 检查后端日志

后端 worker 日志中应该能看到：

```
Task task_xxx: Starting artifact generation phase
Generated artifact: task_id=task_xxx, type=meeting_minutes, version=1, language=zh-CN
```

如果看到 `"Template repository not configured"` 错误，说明 `prompt_instance` 没有正确传递。

## 注意事项

1. **template_id 必须存在**：确保传递的 `template_id` 是后端已知的模板ID
2. **language 要匹配**：`language` 应该与 `output_language` 保持一致
3. **parameters 可选**：如果模板不需要额外参数，可以传空对象 `{}`
4. **不要传 null**：如果用户选择了模板，一定要传递完整的 `prompt_instance` 对象，不要传 `null` 或省略该字段

## 后端兼容性说明

后端已经做了兼容处理：
- ✅ 如果前端传递了 `prompt_instance`，后端会使用指定的模板
- ✅ 如果前端没有传递（`null` 或省略），后端会使用默认模板（但这不是推荐做法）

**建议**：前端应该始终传递用户选择的 `prompt_instance`，这样可以确保生成的内容符合用户期望。
