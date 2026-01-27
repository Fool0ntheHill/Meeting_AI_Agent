# 说话人修正功能 - 前端集成指南

## 概述

后端提供两个 API 用于修正说话人：
1. **批量修改**（Workbench）：`PATCH /tasks/{taskId}/speakers` - 应用到该说话人的所有段落
2. **单个修改**（Workspace）：`PUT /tasks/{taskId}/transcript` - 只修改用户编辑的那一条

两个 API 都直接修改数据库中的 `segments`，确保数据一致性。

---

## 数据存储设计

### 数据库存储

**SpeakerMapping 表**：
- `speaker_label`: ASR 原始标签（如 `"Speaker 1"`, `"Speaker 2"`）
- `speaker_name`: **真实姓名**（如 `"张三"`, `"李四"`）- 这是最终显示的名字
- `speaker_id`: 声纹 ID（如 `"speaker_abc123"`）- 用于追踪声纹识别结果
- `is_corrected`: 是否经过用户修正
- `corrected_by`: 修正人 ID
- `corrected_at`: 修正时间

**Transcript segments**：
- 每个 segment 的 `speaker` 字段**直接存储真实姓名**（如 `"张三"`）
- Pipeline 在保存时会自动从 Speaker 表查询真实姓名
- 如果 Speaker 表中没有该声纹 ID，则使用声纹 ID 作为临时名称
- 用户修正后，segments 会更新为用户指定的名字

**Speaker 表**：
- `speaker_id`: 声纹 ID（如 `"speaker_abc123"`）
- `display_name`: 真实姓名（如 `"张三"`）
- 这是声纹 ID 到真实姓名的全局映射表

### 历史数据说明

**旧数据**（如 `task_295eb9a492a54181`）：
- segments 中可能存储的是声纹 ID（如 `"speaker_linyudong"`）
- 这是因为之前的 Pipeline 没有正确查询真实姓名

**新数据**（修复后）：
- segments 中直接存储真实姓名（如 `"林煜东"`）
- Pipeline 会自动从 Speaker 表查询并保存真实姓名

---

## 1. Workspace - 单个段落修改

### 使用场景
用户在 Workspace 中编辑转写文本，修改单个 segment 的 speaker。

### API 调用

**端点**: `PUT /tasks/{taskId}/transcript`

**请求体**:
```typescript
{
  corrected_text: string;      // 完整的转写文本（所有 segments 拼接）
  segments: Array<{            // 【新增】完整的 segments 数组
    text: string;
    start_time: number;
    end_time: number;
    speaker: string;           // 修改后的说话人名字
    confidence?: number;
  }>;
  regenerate_artifacts?: boolean;  // 默认 false
}
```

### 前端修改示例

**修改前**（只发送 corrected_text）:
```typescript
// Workspace.tsx - handleSaveTranscript
const handleSaveTranscript = async () => {
  const fullText = segments.map(s => s.text).join(' ');
  
  await correctTranscript(taskId, {
    corrected_text: fullText,
    regenerate_artifacts: false
  });
};
```

**修改后**（同时发送 segments）:
```typescript
// Workspace.tsx - handleSaveTranscript
const handleSaveTranscript = async () => {
  const fullText = segments.map(s => s.text).join(' ');
  
  await correctTranscript(taskId, {
    corrected_text: fullText,
    segments: segments,  // 【新增】传递完整的 segments 数组
    regenerate_artifacts: false
  });
};
```

### TypeScript 类型定义

**修改前**:
```typescript
// tasks.ts
interface CorrectTranscriptRequest {
  corrected_text: string;
  regenerate_artifacts?: boolean;
}
```

**修改后**:
```typescript
// tasks.ts
interface TranscriptSegment {
  text: string;
  start_time: number;
  end_time: number;
  speaker: string;
  confidence?: number;
}

interface CorrectTranscriptRequest {
  corrected_text: string;
  segments?: TranscriptSegment[];  // 【新增】可选的 segments 数组
  regenerate_artifacts?: boolean;
}
```

---

## 2. Workbench - 批量修改（应用到所有段落）

### 使用场景
用户在 Workbench 中批量修改说话人，应用到该说话人的所有段落。

### API 调用

**端点**: `PATCH /tasks/{taskId}/speakers`

**请求体**:
```typescript
{
  speaker_mapping: {
    [currentName: string]: string;  // 当前名字 -> 新名字
  };
  regenerate_artifacts?: boolean;
}
```

### 重要变更

**之前的逻辑**（错误）:
```typescript
// ❌ 错误：使用原始 ASR 标签作为 key
const speakerMapping = {
  "Speaker 1": "张三",  // 错误！
  "Speaker 2": "李四"
};
```

**现在的逻辑**（正确）:
```typescript
// ✅ 正确：使用当前显示的名字作为 key
const speakerMapping = {
  "林煜东": "张三",  // 正确！用户看到的是 "林煜东"，要改成 "张三"
  "蓝为一": "李四"
};
```

### 前端修改示例

**Workbench.tsx - handleBatchCorrectSpeakers**:
```typescript
const handleBatchCorrectSpeakers = async (oldName: string, newName: string) => {
  // oldName 是用户当前看到的名字（如 "林煜东"）
  // newName 是用户想改成的名字（如 "张三"）
  
  await correctSpeakers(taskId, {
    speaker_mapping: {
      [oldName]: newName  // 使用当前显示的名字作为 key
    },
    regenerate_artifacts: false
  });
  
  // 刷新转写数据
  await fetchTranscript();
};
```

### 完整示例

```typescript
// Workbench.tsx
const Workbench = () => {
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  
  // 获取转写数据
  const fetchTranscript = async () => {
    const data = await getTranscript(taskId);
    setTranscript(data);
  };
  
  // 批量修改说话人
  const handleBatchCorrectSpeakers = async () => {
    // 假设用户选择了 "林煜东"，要改成 "张三"
    const currentName = "林煜东";  // 用户当前看到的名字
    const newName = "张三";         // 用户输入的新名字
    
    await correctSpeakers(taskId, {
      speaker_mapping: {
        [currentName]: newName  // 关键：使用当前名字，不是 ASR 标签
      },
      regenerate_artifacts: false
    });
    
    // 刷新数据
    await fetchTranscript();
  };
  
  return (
    <div>
      {/* UI 组件 */}
    </div>
  );
};
```

---

## 3. 数据流说明

### 后端数据存储
```
数据库 transcript.segments:
[
  { speaker: "林煜东", text: "大家好" },
  { speaker: "林煜东", text: "今天讨论..." },
  { speaker: "蓝为一", text: "我觉得..." }
]

数据库 SpeakerMapping 表（仅用于记录）:
Speaker 1 -> 林煜东
Speaker 2 -> 蓝为一
```

### 前端显示
```typescript
// GET /tasks/{taskId}/transcript 返回
{
  segments: [
    { speaker: "林煜东", text: "大家好" },
    { speaker: "林煜东", text: "今天讨论..." },
    { speaker: "蓝为一", text: "我觉得..." }
  ],
  speaker_mapping: {
    "Speaker 1": "林煜东",
    "Speaker 2": "蓝为一"
  }
}
```

前端直接显示 `segments[i].speaker`，不需要应用 `speaker_mapping`。

---

## 4. 修改冲突处理

### 场景 1: 先批量改，再单个改
```
1. 批量改：所有 "林煜东" -> "张三"
2. 单个改：某一条 "张三" -> "李四"
结果：大部分是 "张三"，被单独修改的那一条是 "李四" ✓ 正确
```

### 场景 2: 先单个改，再批量改
```
1. 单个改：某一条 "林煜东" -> "李四"
2. 批量改：所有 "林煜东" -> "张三"
结果：
  - 之前没改过的：都变成 "张三"
  - 之前改成 "李四" 的：保持 "李四"（因为批量改只匹配 "林煜东"）
✓ 正确
```

### 场景 3: 批量改后再批量改
```
1. 批量改：所有 "林煜东" -> "张三"
2. 批量改：所有 "张三" -> "王五"
结果：所有原来是 "林煜东" 的都变成 "王五" ✓ 正确
```

---

## 5. 完整的 API 函数示例

```typescript
// api/tasks.ts

export interface TranscriptSegment {
  text: string;
  start_time: number;
  end_time: number;
  speaker: string;
  confidence?: number;
}

export interface CorrectTranscriptRequest {
  corrected_text: string;
  segments?: TranscriptSegment[];
  regenerate_artifacts?: boolean;
}

export interface CorrectSpeakersRequest {
  speaker_mapping: Record<string, string>;
  regenerate_artifacts?: boolean;
}

// 单个修改（Workspace）
export async function correctTranscript(
  taskId: string,
  request: CorrectTranscriptRequest
): Promise<void> {
  await api.put(`/tasks/${taskId}/transcript`, request);
}

// 批量修改（Workbench）
export async function correctSpeakers(
  taskId: string,
  request: CorrectSpeakersRequest
): Promise<void> {
  await api.patch(`/tasks/${taskId}/speakers`, request);
}
```

---

## 6. 测试检查清单

### Workspace 单个修改测试
- [ ] 修改单个 segment 的 speaker
- [ ] 保存后刷新页面，修改是否持久化
- [ ] 其他 segments 是否保持不变

### Workbench 批量修改测试
- [ ] 批量修改某个说话人
- [ ] 所有该说话人的 segments 是否都被修改
- [ ] 其他说话人的 segments 是否保持不变
- [ ] 刷新页面后修改是否持久化

### 混合场景测试
- [ ] 先批量改，再单个改
- [ ] 先单个改，再批量改
- [ ] 连续批量改多次

---

## 7. 常见问题

### Q: 为什么 speaker_mapping 的 key 要用当前名字而不是 ASR 标签？
A: 因为后端现在直接修改 segments，segments 中存储的是当前显示的名字（如 "林煜东"），不是原始 ASR 标签（如 "Speaker 1"）。

### Q: speaker_mapping 字段还有用吗？
A: `GET /tasks/{taskId}/transcript` 返回的 `speaker_mapping` 现在主要用于前端显示和追踪，实际数据以 `segments` 为准。

### Q: 如果用户修改后不刷新页面，会有问题吗？
A: 不会。前端的 state 已经是最新的，只要保存时把完整的 segments 发送给后端即可。

---

## 总结

**关键修改点**：
1. Workspace 保存时，同时发送 `segments` 数组
2. Workbench 批量修改时，使用**当前显示的名字**作为 key，不是 ASR 标签
3. 两个 API 都直接修改数据库 segments，确保数据一致性

**前端需要修改的文件**：
- `Workspace.tsx` - 添加 segments 到保存请求
- `Workbench.tsx` - 修改 speaker_mapping 的 key 逻辑
- `api/tasks.ts` - 更新类型定义
