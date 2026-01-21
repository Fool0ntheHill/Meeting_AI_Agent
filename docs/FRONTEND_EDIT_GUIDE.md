# 前端编辑功能集成指南

## 概述

后端已提供完整的 transcript 和 artifact 编辑接口，前端可以实现以下功能：

1. **修改逐字稿文本** - 修正 ASR 识别错误
2. **修改说话人映射** - 更正说话人姓名
3. **重新生成会议纪要** - 使用修改后的内容重新生成

## API 接口

### 1. 修改逐字稿文本

**接口**: `PUT /api/v1/tasks/{task_id}/corrections/{task_id}/transcript`

**用途**: 修正 ASR 识别错误的文本

**请求**:
```typescript
interface CorrectTranscriptRequest {
  corrected_text: string;           // 修正后的完整文本
  regenerate_artifacts?: boolean;   // 是否重新生成会议纪要（可选）
}
```

**响应**:
```typescript
interface CorrectTranscriptResponse {
  success: boolean;
  message: string;
  regenerated_artifacts?: string[];  // 重新生成的 artifact IDs
}
```

**示例**:
```typescript
async function correctTranscript(taskId: string, correctedText: string) {
  const response = await fetch(
    `/api/v1/tasks/${taskId}/corrections/${taskId}/transcript`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        corrected_text: correctedText,
        regenerate_artifacts: true  // 自动重新生成会议纪要
      })
    }
  );
  
  return await response.json();
}
```

### 2. 修改说话人映射

**接口**: `PATCH /api/v1/tasks/{task_id}/corrections/{task_id}/speakers`

**用途**: 修正说话人姓名（如将 "Speaker 1" 改为 "张三"）

**请求**:
```typescript
interface CorrectSpeakersRequest {
  speaker_mapping: Record<string, string>;  // 说话人映射
  regenerate_artifacts?: boolean;           // 是否重新生成会议纪要
}
```

**响应**:
```typescript
interface CorrectSpeakersResponse {
  success: boolean;
  message: string;
  regenerated_artifacts?: string[];
}
```

**示例**:
```typescript
async function correctSpeakers(taskId: string, mapping: Record<string, string>) {
  const response = await fetch(
    `/api/v1/tasks/${taskId}/corrections/${taskId}/speakers`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        speaker_mapping: {
          "Speaker 1": "张三",
          "Speaker 2": "李四"
        },
        regenerate_artifacts: true
      })
    }
  );
  
  return await response.json();
}
```

### 3. 重新生成会议纪要

**接口**: `POST /api/v1/tasks/{task_id}/corrections/{task_id}/artifacts/{artifact_type}/regenerate`

**用途**: 使用修改后的 transcript 重新生成会议纪要

**请求**:
```typescript
interface GenerateArtifactRequest {
  prompt_instance: {
    template_id: string;              // 提示词模板 ID
    language: string;                 // 语言（zh-CN 或 en-US）
    parameters: Record<string, any>;  // 模板参数
  };
}
```

**响应**:
```typescript
interface GenerateArtifactResponse {
  success: boolean;
  artifact_id: string;
  version: number;
  content: Record<string, any>;  // 生成的内容
  message: string;
}
```

**示例**:
```typescript
async function regenerateArtifact(taskId: string, artifactType: string) {
  const response = await fetch(
    `/api/v1/tasks/${taskId}/corrections/${taskId}/artifacts/${artifactType}/regenerate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        prompt_instance: {
          template_id: "meeting_minutes_detailed_summary",
          language: "zh-CN",
          parameters: {}
        }
      })
    }
  );
  
  return await response.json();
}
```

### 4. 直接修改会议纪要内容

**接口**: `PUT /api/v1/artifacts/{artifact_id}`

**用途**: 直接编辑会议纪要的内容（原地更新，不创建新版本）

**请求**:
```typescript
// 直接发送修改后的 content 对象
const content = {
  "会议概要": "修改后的概要...",
  "讨论要点": ["要点1", "要点2"],
  "决策事项": ["决策1"],
  "行动项": ["行动1"],
  "其他": ""
};
```

**响应**:
```typescript
interface UpdateArtifactResponse {
  success: boolean;
  artifact_id: string;  // 相同的 artifact_id（原地更新）
  message: string;
}
```

**示例**:
```typescript
async function updateArtifact(artifactId: string, content: Record<string, any>) {
  const response = await fetch(
    `/api/v1/artifacts/${artifactId}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(content)  // 直接发送 content 对象
    }
  );
  
  return await response.json();
}
```

**重要说明**：
- **原地更新**：直接修改现有 artifact，不创建新版本
- artifact_id 和 version 保持不变
- 内容被直接替换为新内容
- 自动添加元数据标记：`manually_edited: true`、`last_edited_at`、`last_edited_by`
- 自动更新任务的 `last_content_modified_at` 时间戳

**与重新生成的区别**：
- `PUT /artifacts/{artifact_id}` - 原地更新，不创建新版本（用于手动编辑）
- `POST /corrections/{task_id}/artifacts/{type}/regenerate` - 创建新版本（用于 LLM 重新生成）

## 前端实现建议

### 1. 逐字稿编辑器

```typescript
// 组件状态
const [transcript, setTranscript] = useState<string>('');
const [isEditing, setIsEditing] = useState(false);
const [isSaving, setIsSaving] = useState(false);

// 保存修改
async function handleSave() {
  setIsSaving(true);
  
  try {
    const result = await correctTranscript(taskId, transcript);
    
    if (result.success) {
      toast.success('逐字稿已保存');
      setIsEditing(false);
      
      // 如果重新生成了会议纪要，刷新页面
      if (result.regenerated_artifacts) {
        await refreshArtifacts();
      }
    }
  } catch (error) {
    toast.error('保存失败');
  } finally {
    setIsSaving(false);
  }
}

// UI
<div>
  {isEditing ? (
    <textarea
      value={transcript}
      onChange={(e) => setTranscript(e.target.value)}
      className="w-full h-96 p-4 border rounded"
    />
  ) : (
    <div className="whitespace-pre-wrap">{transcript}</div>
  )}
  
  <div className="mt-4 flex gap-2">
    {isEditing ? (
      <>
        <button onClick={handleSave} disabled={isSaving}>
          {isSaving ? '保存中...' : '保存'}
        </button>
        <button onClick={() => setIsEditing(false)}>取消</button>
      </>
    ) : (
      <button onClick={() => setIsEditing(true)}>编辑</button>
    )}
  </div>
</div>
```

### 2. 说话人编辑器

```typescript
// 组件状态
const [speakerMapping, setSpeakerMapping] = useState<Record<string, string>>({
  "Speaker 1": "林煜东",
  "Speaker 2": "蓝为一"
});

// 修改说话人
function handleSpeakerChange(label: string, newName: string) {
  setSpeakerMapping(prev => ({
    ...prev,
    [label]: newName
  }));
}

// 保存修改
async function handleSaveSpeakers() {
  try {
    const result = await correctSpeakers(taskId, speakerMapping);
    
    if (result.success) {
      toast.success('说话人已更新');
      
      // 刷新逐字稿（说话人名称已更新）
      await refreshTranscript();
      
      // 如果重新生成了会议纪要，刷新
      if (result.regenerated_artifacts) {
        await refreshArtifacts();
      }
    }
  } catch (error) {
    toast.error('保存失败');
  }
}

// UI
<div>
  {Object.entries(speakerMapping).map(([label, name]) => (
    <div key={label} className="flex items-center gap-2 mb-2">
      <span className="w-24">{label}:</span>
      <input
        type="text"
        value={name}
        onChange={(e) => handleSpeakerChange(label, e.target.value)}
        className="flex-1 px-3 py-2 border rounded"
      />
    </div>
  ))}
  
  <button onClick={handleSaveSpeakers} className="mt-4">
    保存说话人
  </button>
</div>
```

### 3. 会议纪要重新生成

```typescript
// 重新生成按钮
async function handleRegenerate() {
  const confirmed = confirm('确定要重新生成会议纪要吗？这将创建一个新版本。');
  
  if (!confirmed) return;
  
  try {
    const result = await regenerateArtifact(taskId, 'meeting_minutes');
    
    if (result.success) {
      toast.success(`已生成新版本 v${result.version}`);
      
      // 刷新会议纪要列表
      await refreshArtifacts();
      
      // 切换到新版本
      setCurrentVersion(result.version);
    }
  } catch (error) {
    toast.error('生成失败');
  }
}

// UI
<button onClick={handleRegenerate} className="btn-primary">
  重新生成会议纪要
</button>
```

### 4. 会议纪要直接编辑（原地更新）

```typescript
// 组件状态
const [artifactContent, setArtifactContent] = useState<Record<string, any>>({
  "会议概要": "",
  "讨论要点": [],
  "决策事项": [],
  "行动项": [],
  "其他": ""
});
const [isEditing, setIsEditing] = useState(false);

// 修改字段
function handleFieldChange(field: string, value: any) {
  setArtifactContent(prev => ({
    ...prev,
    [field]: value
  }));
}

// 保存修改（原地更新）
async function handleSaveArtifact() {
  try {
    const result = await updateArtifact(currentArtifactId, artifactContent);
    
    if (result.success) {
      toast.success('已保存修改');
      setIsEditing(false);
      
      // 刷新当前 artifact（artifact_id 不变）
      await refreshCurrentArtifact();
    }
  } catch (error) {
    toast.error('保存失败');
  }
}

// UI
<div>
  {isEditing ? (
    <div className="space-y-4">
      {/* 会议概要 */}
      <div>
        <label className="font-bold">会议概要</label>
        <textarea
          value={artifactContent["会议概要"]}
          onChange={(e) => handleFieldChange("会议概要", e.target.value)}
          className="w-full h-32 p-2 border rounded"
        />
      </div>
      
      {/* 讨论要点 */}
      <div>
        <label className="font-bold">讨论要点</label>
        {artifactContent["讨论要点"].map((point, i) => (
          <input
            key={i}
            value={point}
            onChange={(e) => {
              const newPoints = [...artifactContent["讨论要点"]];
              newPoints[i] = e.target.value;
              handleFieldChange("讨论要点", newPoints);
            }}
            className="w-full p-2 border rounded mb-2"
          />
        ))}
        <button onClick={() => {
          handleFieldChange("讨论要点", [...artifactContent["讨论要点"], ""]);
        }}>
          + 添加要点
        </button>
      </div>
      
      {/* 其他字段类似... */}
      
      <div className="flex gap-2">
        <button onClick={handleSaveArtifact} className="btn-primary">
          保存
        </button>
        <button onClick={() => setIsEditing(false)} className="btn-secondary">
          取消
        </button>
      </div>
    </div>
  ) : (
    <div>
      {/* 显示模式 */}
      <div className="mb-4">
        <h3 className="font-bold">会议概要</h3>
        <p>{artifactContent["会议概要"]}</p>
      </div>
      
      {/* 其他字段... */}
      
      <button onClick={() => setIsEditing(true)} className="btn-primary">
        编辑
      </button>
    </div>
  )}
</div>
```

## 完整工作流程

### 场景 1：修正 ASR 识别错误

1. 用户点击"编辑逐字稿"
2. 进入编辑模式，显示可编辑的文本框
3. 用户修改错误的文本
4. 点击"保存"
5. 调用 `PUT /corrections/{task_id}/transcript`
6. 可选：勾选"重新生成会议纪要"
7. 保存成功，退出编辑模式

### 场景 2：修正说话人姓名

1. 用户点击"编辑说话人"
2. 显示说话人列表，每个可编辑
3. 用户修改姓名（如 "Speaker 1" -> "张三"）
4. 点击"保存"
5. 调用 `PATCH /corrections/{task_id}/speakers`
6. 后端自动更新 transcript 中的所有 speaker 标签
7. 可选：自动重新生成会议纪要
8. 保存成功，刷新页面

### 场景 3：手动重新生成

1. 用户修改了逐字稿或说话人
2. 点击"重新生成会议纪要"
3. 调用 `POST /corrections/{task_id}/artifacts/meeting_minutes/regenerate`
4. 后端使用最新的 transcript 生成新版本
5. 版本号自动递增（v1 -> v2）
6. 显示新版本的内容

## 版本管理

### 查看历史版本

```typescript
// 获取所有版本
const versions = await fetch(
  `/api/v1/tasks/${taskId}/artifacts/meeting_minutes/versions`
).then(r => r.json());

// 显示版本列表
<select onChange={(e) => setCurrentVersion(Number(e.target.value))}>
  {versions.versions.map(v => (
    <option key={v.version} value={v.version}>
      v{v.version} - {new Date(v.created_at).toLocaleString()}
    </option>
  ))}
</select>
```

### 版本对比

```typescript
// 获取两个版本的内容
const v1 = await fetchArtifact(taskId, artifactIdV1);
const v2 = await fetchArtifact(taskId, artifactIdV2);

// 使用 diff 库对比
import { diffWords } from 'diff';

const diff = diffWords(
  JSON.stringify(v1.content, null, 2),
  JSON.stringify(v2.content, null, 2)
);

// 显示差异
<div>
  {diff.map((part, i) => (
    <span
      key={i}
      className={
        part.added ? 'bg-green-200' :
        part.removed ? 'bg-red-200' :
        ''
      }
    >
      {part.value}
    </span>
  ))}
</div>
```

## 权限控制

所有编辑接口都会验证：

1. **用户认证** - 必须登录
2. **任务所有权** - 只能编辑自己的任务
3. **任务状态** - 只有成功的任务才能编辑

前端应该：

```typescript
// 检查是否可以编辑
function canEdit(task: Task): boolean {
  // 检查任务状态
  if (!['success', 'partial_success'].includes(task.state)) {
    return false;
  }
  
  // 检查是否已确认（已确认的任务不能编辑）
  if (task.is_confirmed) {
    return false;
  }
  
  return true;
}

// UI
{canEdit(task) ? (
  <button onClick={handleEdit}>编辑</button>
) : (
  <span className="text-gray-400">不可编辑</span>
)}
```

## 错误处理

```typescript
async function handleSave() {
  try {
    const result = await correctTranscript(taskId, transcript);
    
    if (result.success) {
      toast.success('保存成功');
    }
  } catch (error) {
    if (error.status === 400) {
      toast.error('任务状态不允许编辑');
    } else if (error.status === 403) {
      toast.error('无权编辑此任务');
    } else if (error.status === 404) {
      toast.error('任务不存在');
    } else {
      toast.error('保存失败，请重试');
    }
  }
}
```

## 总结

后端已提供完整的编辑接口：

- ✅ `PUT /corrections/{task_id}/transcript` - 修改逐字稿
- ✅ `PATCH /corrections/{task_id}/speakers` - 修改说话人
- ✅ `POST /corrections/{task_id}/artifacts/{type}/regenerate` - 重新生成（创建新版本）
- ✅ `PUT /artifacts/{artifact_id}` - 直接修改会议纪要内容（原地更新）

前端需要实现：

1. **编辑器 UI** - 文本编辑器、说话人编辑器、会议纪要编辑器
2. **保存逻辑** - 调用对应的 API
3. **版本管理** - 显示历史版本、版本对比（仅用于 LLM 重新生成的版本）
4. **权限控制** - 检查任务状态和所有权
5. **错误处理** - 友好的错误提示

**两种修改方式的区别**：

| 操作 | 接口 | 是否创建新版本 | 用途 |
|------|------|---------------|------|
| 手动编辑 | `PUT /artifacts/{artifact_id}` | ❌ 否（原地更新） | 用户直接修改内容 |
| LLM 重新生成 | `POST /corrections/{task_id}/artifacts/{type}/regenerate` | ✅ 是 | 使用修改后的 transcript 重新生成 |

所有修改都会：
- 自动更新 `last_content_modified_at` 时间戳
- 手动编辑的会标记 `manually_edited: true`
- 验证用户权限和任务状态
