# Artifact 提示词存储与回溯指南

## 概述

每个 artifact 现在会完整保存生成时使用的提示词信息，支持在 Workspace 中查看"当时使用的提示词"。

---

## 存储结构

### artifact.metadata.prompt 字段

```typescript
interface ArtifactMetadata {
  // LLM 信息
  llm_model: string;
  token_count: number;
  prompt_token_count: number;
  candidates_token_count: number;
  
  // 提示词信息（新增）
  prompt: {
    template_id: string;           // 模板ID（或 "__blank__"）
    language: string;               // 语言
    parameters: Record<string, any>; // 模板参数
    prompt_text: string;            // 实际使用的完整提示词文本
    is_user_edited: boolean;        // 是否用户编辑过
    custom_instructions?: string;   // 补充指令（可选）
  };
}
```

---

## 存储逻辑

### 场景 1: 使用模板，未编辑

**前端传递**:
```json
{
  "template_id": "tpl_standard_minutes",
  "language": "zh-CN",
  "parameters": {}
}
```

**存储到 metadata.prompt**:
```json
{
  "template_id": "tpl_standard_minutes",
  "language": "zh-CN",
  "parameters": {},
  "prompt_text": "请生成标准会议纪要...\n\n{transcript}",
  "is_user_edited": false
}
```

### 场景 2: 使用模板，用户编辑了

**前端传递**:
```json
{
  "template_id": "tpl_standard_minutes",
  "language": "zh-CN",
  "prompt_text": "请生成简洁的会议纪要...\n\n{transcript}",
  "parameters": {}
}
```

**存储到 metadata.prompt**:
```json
{
  "template_id": "tpl_standard_minutes",
  "language": "zh-CN",
  "parameters": {},
  "prompt_text": "请生成简洁的会议纪要...\n\n{transcript}",
  "is_user_edited": true
}
```

### 场景 3: 空白模板

**前端传递**:
```json
{
  "template_id": "__blank__",
  "language": "zh-CN",
  "prompt_text": "分析会议，提取技术决策\n\n{transcript}",
  "parameters": {}
}
```

**存储到 metadata.prompt**:
```json
{
  "template_id": "__blank__",
  "language": "zh-CN",
  "parameters": {},
  "prompt_text": "分析会议，提取技术决策\n\n{transcript}",
  "is_user_edited": true
}
```

---

## API 返回格式

### GET /api/v1/tasks/{task_id}/artifacts/{artifact_id}

**响应示例**:
```json
{
  "artifact": {
    "artifact_id": "art_task_xxx_meeting_minutes_v1",
    "task_id": "task_xxx",
    "artifact_type": "meeting_minutes",
    "version": 1,
    "prompt_instance": {
      "template_id": "tpl_standard_minutes",
      "language": "zh-CN",
      "prompt_text": "用户编辑的提示词...",
      "parameters": {}
    },
    "content": "{\"content\": \"会议纪要内容...\", \"metadata\": {...}}",
    "metadata": {
      "llm_model": "gemini-2.0-flash-exp",
      "token_count": 1500,
      "prompt_token_count": 800,
      "candidates_token_count": 700,
      "prompt": {
        "template_id": "tpl_standard_minutes",
        "language": "zh-CN",
        "parameters": {},
        "prompt_text": "用户编辑的提示词...\n\n{transcript}",
        "is_user_edited": true
      }
    },
    "created_at": "2026-01-23T12:00:00Z",
    "created_by": "user_xxx"
  }
}
```

---

## 前端使用示例

### 1. 获取 artifact 详情

```typescript
const getArtifactDetail = async (taskId: string, artifactId: string) => {
  const response = await fetch(
    `/api/v1/tasks/${taskId}/artifacts/${artifactId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const data = await response.json();
  return data.artifact;
};
```

### 2. 显示提示词信息

```typescript
const ArtifactPromptViewer: React.FC<{ artifact: Artifact }> = ({ artifact }) => {
  const promptInfo = artifact.metadata?.prompt;
  
  if (!promptInfo) {
    return <div>此 artifact 没有提示词信息（旧数据）</div>;
  }
  
  return (
    <div className="prompt-viewer">
      <h3>生成时使用的提示词</h3>
      
      <div className="prompt-meta">
        <p>模板: {promptInfo.template_id}</p>
        <p>语言: {promptInfo.language}</p>
        <p>
          来源: {promptInfo.is_user_edited ? '用户编辑' : '模板原文'}
        </p>
      </div>
      
      <div className="prompt-text">
        <h4>提示词内容</h4>
        <pre>{promptInfo.prompt_text}</pre>
      </div>
      
      {promptInfo.custom_instructions && (
        <div className="custom-instructions">
          <h4>补充指令</h4>
          <pre>{promptInfo.custom_instructions}</pre>
        </div>
      )}
    </div>
  );
};
```

### 3. Workspace 提示词弹窗

```typescript
const PromptModal: React.FC<{ 
  isOpen: boolean; 
  onClose: () => void;
  artifact: Artifact;
}> = ({ isOpen, onClose, artifact }) => {
  const promptInfo = artifact.metadata?.prompt;
  
  if (!isOpen) return null;
  
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader>查看提示词</ModalHeader>
      <ModalBody>
        {promptInfo ? (
          <>
            <InfoRow label="模板ID" value={promptInfo.template_id} />
            <InfoRow label="语言" value={promptInfo.language} />
            <InfoRow 
              label="来源" 
              value={promptInfo.is_user_edited ? '用户编辑' : '模板原文'} 
            />
            
            <Divider />
            
            <Label>提示词内容</Label>
            <CodeBlock language="text">
              {promptInfo.prompt_text}
            </CodeBlock>
            
            {promptInfo.custom_instructions && (
              <>
                <Label>补充指令</Label>
                <CodeBlock language="text">
                  {promptInfo.custom_instructions}
                </CodeBlock>
              </>
            )}
            
            {Object.keys(promptInfo.parameters).length > 0 && (
              <>
                <Label>参数</Label>
                <CodeBlock language="json">
                  {JSON.stringify(promptInfo.parameters, null, 2)}
                </CodeBlock>
              </>
            )}
          </>
        ) : (
          <Alert type="info">
            此 artifact 是旧版本生成的，没有保存提示词信息
          </Alert>
        )}
      </ModalBody>
      <ModalFooter>
        <Button onClick={onClose}>关闭</Button>
      </ModalFooter>
    </Modal>
  );
};
```

---

## 向后兼容

### 旧数据处理

**旧 artifact（没有 metadata.prompt）**:
- `metadata.prompt` 为 `null` 或 `undefined`
- 前端显示"此 artifact 没有提示词信息"
- 不影响正常使用

**新 artifact（有 metadata.prompt）**:
- 完整显示提示词信息
- 支持查看用户编辑历史

### 前端兼容代码

```typescript
const getPromptInfo = (artifact: Artifact) => {
  // 向后兼容：旧数据没有 prompt 字段
  if (!artifact.metadata?.prompt) {
    return {
      hasPromptInfo: false,
      message: '此 artifact 是旧版本生成的，没有保存提示词信息'
    };
  }
  
  return {
    hasPromptInfo: true,
    promptInfo: artifact.metadata.prompt
  };
};

// 使用
const { hasPromptInfo, promptInfo, message } = getPromptInfo(artifact);

if (!hasPromptInfo) {
  return <Alert>{message}</Alert>;
}

// 显示提示词信息
return <PromptViewer promptInfo={promptInfo} />;
```

---

## 数据库存储

### artifacts 表

```sql
-- metadata 字段（JSON 类型）
{
  "llm_model": "gemini-2.0-flash-exp",
  "token_count": 1500,
  "prompt": {
    "template_id": "tpl_001",
    "language": "zh-CN",
    "prompt_text": "完整的提示词文本...",
    "is_user_edited": true,
    "parameters": {},
    "custom_instructions": "补充指令..."
  }
}
```

### 查询示例

```sql
-- 查询使用特定模板的 artifacts
SELECT * FROM artifacts 
WHERE metadata->>'$.prompt.template_id' = 'tpl_standard_minutes';

-- 查询用户编辑过的 artifacts
SELECT * FROM artifacts 
WHERE metadata->>'$.prompt.is_user_edited' = 'true';

-- 查询空白模板生成的 artifacts
SELECT * FROM artifacts 
WHERE metadata->>'$.prompt.template_id' = '__blank__';
```

---

## 重新生成 Artifact

### 使用相同提示词重新生成

```typescript
const regenerateWithSamePrompt = async (artifact: Artifact) => {
  const promptInfo = artifact.metadata?.prompt;
  
  if (!promptInfo) {
    throw new Error('无法获取原始提示词信息');
  }
  
  // 构建 prompt_instance
  const promptInstance = {
    template_id: promptInfo.template_id,
    language: promptInfo.language,
    parameters: promptInfo.parameters,
    // 如果是用户编辑的，使用保存的 prompt_text
    ...(promptInfo.is_user_edited ? {
      prompt_text: promptInfo.prompt_text
    } : {}),
    // 如果有补充指令，也带上
    ...(promptInfo.custom_instructions ? {
      custom_instructions: promptInfo.custom_instructions
    } : {})
  };
  
  // 调用重新生成 API
  const response = await fetch(
    `/api/v1/tasks/${artifact.task_id}/artifacts/${artifact.artifact_type}/generate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        prompt_instance: promptInstance,
        output_language: promptInfo.language
      })
    }
  );
  
  return response.json();
};
```

---

## 总结

✅ **自动存储**: 每次生成 artifact 时自动保存提示词信息  
✅ **完整回溯**: 可以查看任何版本使用的提示词  
✅ **用户编辑标记**: 区分模板原文和用户编辑版本  
✅ **向后兼容**: 旧数据没有提示词信息不影响使用  
✅ **重新生成**: 可以使用相同提示词重新生成  

现在 Workspace 可以完整展示每个 artifact 生成时使用的提示词了！
