# 会议元数据前端集成指南

## 概述

后端已实现会议日期和时间的自动提取功能。前端可以选择性地提供这些信息，也可以完全依赖后端的自动提取。

## 后端策略

### 日期提取
优先级（从高到低）：
1. **用户提供** - 前端传入的 `meeting_date`
2. **文件名提取** - 从 `original_filenames` 中提取（支持多种格式）
3. **当前日期** - 使用任务创建时的日期

### 时间提取
- **仅使用用户明确提供的时间**
- 不从文件名提取（避免不准确）
- 不从任务创建时间推算（不可靠）
- 如果没有准确的时间，宁可不显示

## API 变更

### 1. 上传接口响应

**接口**: `POST /api/v1/upload`

**响应新增字段**:
```typescript
{
  "success": true,
  "file_path": "https://tos.example.com/audio/xxx.wav",
  "original_filename": "meeting_20260121_1430.wav",  // ✨ 新增
  "file_size": 1024000,
  "duration": 3600.5
}
```

### 2. 创建任务接口

**接口**: `POST /api/v1/tasks`

**请求新增字段**:
```typescript
{
  "audio_files": ["https://tos.example.com/audio/xxx.wav"],
  "file_order": [0],
  "original_filenames": ["meeting_20260121_1430.wav"],  // ✨ 新增（可选）
  "meeting_type": "weekly_sync",
  "meeting_date": "2026-01-21",  // ✨ 新增（可选）
  "meeting_time": "14:30",  // ✨ 新增（可选）
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN",
  "prompt_instance": { ... },
  "skip_speaker_recognition": false
}
```

## 前端实现方案

### 方案 1: 完全自动（推荐）

**适用场景**: 快速上线，减少用户操作

**实现**:
```typescript
// 1. 上传文件
const uploadResponse = await api.uploadAudio(file);

// 2. 创建任务（不提供日期时间）
const createTaskRequest = {
  audio_files: [uploadResponse.file_path],
  file_order: [0],
  original_filenames: [uploadResponse.original_filename],  // 传递原始文件名
  meeting_type: selectedMeetingType,
  // 不提供 meeting_date 和 meeting_time
  // 后端会自动从文件名提取日期，或使用当前日期
};

const taskResponse = await api.createTask(createTaskRequest);
```

**优点**:
- 用户无需手动输入
- 实现简单
- 适合大多数场景

**缺点**:
- 会议纪要中不会显示具体时间（只有日期）
- 如果文件名不包含日期，会使用当前日期

### 方案 2: 可选输入（推荐）

**适用场景**: 提供更好的用户体验，允许用户修正

**实现**:
```typescript
// 1. 上传文件后，尝试从文件名提取日期
const uploadResponse = await api.uploadAudio(file);
const extractedDate = extractDateFromFilename(uploadResponse.original_filename);

// 2. 显示日期选择器（预填充提取的日期）
const [meetingDate, setMeetingDate] = useState(extractedDate || getTodayDate());
const [meetingTime, setMeetingTime] = useState('');  // 时间默认为空

// 3. 创建任务
const createTaskRequest = {
  audio_files: [uploadResponse.file_path],
  file_order: [0],
  original_filenames: [uploadResponse.original_filename],
  meeting_type: selectedMeetingType,
  meeting_date: meetingDate,  // 用户可以修改
  meeting_time: meetingTime || undefined,  // 只有用户填写时才传递
};

const taskResponse = await api.createTask(createTaskRequest);
```

**UI 建议**:
```tsx
<FormGroup>
  <Label>会议日期</Label>
  <DatePicker 
    value={meetingDate}
    onChange={setMeetingDate}
    placeholder="自动识别或选择日期"
  />
  <HelpText>
    {extractedDate 
      ? `已从文件名识别：${extractedDate}` 
      : '将使用今天的日期'}
  </HelpText>
</FormGroup>

<FormGroup>
  <Label>会议时间（可选）</Label>
  <TimePicker 
    value={meetingTime}
    onChange={setMeetingTime}
    placeholder="如果知道准确时间可填写"
  />
  <HelpText>
    如不填写，纪要中将只显示日期
  </HelpText>
</FormGroup>
```

**优点**:
- 用户可以修正自动识别的日期
- 可以提供准确的会议时间
- 体验更好

**缺点**:
- 需要额外的 UI 组件
- 增加用户操作步骤

### 方案 3: 强制输入

**适用场景**: 需要准确的会议元数据

**实现**:
```typescript
// 1. 上传文件
const uploadResponse = await api.uploadAudio(file);

// 2. 强制要求用户输入日期和时间
const [meetingDate, setMeetingDate] = useState('');
const [meetingTime, setMeetingTime] = useState('');

// 3. 验证后创建任务
if (!meetingDate) {
  showError('请选择会议日期');
  return;
}

const createTaskRequest = {
  audio_files: [uploadResponse.file_path],
  file_order: [0],
  original_filenames: [uploadResponse.original_filename],
  meeting_type: selectedMeetingType,
  meeting_date: meetingDate,  // 必填
  meeting_time: meetingTime || undefined,  // 可选
};

const taskResponse = await api.createTask(createTaskRequest);
```

**优点**:
- 数据准确性高
- 适合正式场景

**缺点**:
- 用户体验较差
- 增加操作步骤

## 文件名日期提取工具

如果前端需要自己提取日期（方案 2），可以使用以下工具函数：

```typescript
/**
 * 从文件名提取日期
 * 支持格式：YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD
 */
function extractDateFromFilename(filename: string): string | null {
  if (!filename) return null;
  
  // 模式 1: YYYYMMDD (8位数字)
  const pattern1 = /(\d{8})/;
  const match1 = filename.match(pattern1);
  if (match1) {
    const dateStr = match1[1];
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    
    // 验证日期有效性
    const date = new Date(`${year}-${month}-${day}`);
    if (!isNaN(date.getTime())) {
      return `${year}-${month}-${day}`;
    }
  }
  
  // 模式 2: YYYY-MM-DD 或 YYYY_MM_DD
  const pattern2 = /(\d{4})[-_](\d{2})[-_](\d{2})/;
  const match2 = filename.match(pattern2);
  if (match2) {
    const [, year, month, day] = match2;
    
    // 验证日期有效性
    const date = new Date(`${year}-${month}-${day}`);
    if (!isNaN(date.getTime())) {
      return `${year}-${month}-${day}`;
    }
  }
  
  return null;
}

/**
 * 获取今天的日期（YYYY-MM-DD 格式）
 */
function getTodayDate(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
```

## 测试示例

### 示例 1: 文件名包含日期

```typescript
// 文件名: meeting_20260121_1430.wav
const uploadResponse = await api.uploadAudio(file);
// uploadResponse.original_filename = "meeting_20260121_1430.wav"

const extractedDate = extractDateFromFilename(uploadResponse.original_filename);
// extractedDate = "2026-01-21"

// 创建任务（不提供时间）
const task = await api.createTask({
  audio_files: [uploadResponse.file_path],
  original_filenames: [uploadResponse.original_filename],
  meeting_type: "weekly_sync",
  // 后端会从文件名提取日期：2026-01-21
});

// 生成的纪要中会显示：
// 会议时间：2026年01月21日
```

### 示例 2: 用户提供完整信息

```typescript
// 文件名: meeting.wav
const uploadResponse = await api.uploadAudio(file);

// 用户手动输入
const task = await api.createTask({
  audio_files: [uploadResponse.file_path],
  original_filenames: [uploadResponse.original_filename],
  meeting_type: "weekly_sync",
  meeting_date: "2026-01-21",
  meeting_time: "14:30",
});

// 生成的纪要中会显示：
// 会议时间：2026年01月21日 14:30
```

### 示例 3: 完全自动

```typescript
// 文件名: meeting.wav
const uploadResponse = await api.uploadAudio(file);

// 不提供任何日期时间信息
const task = await api.createTask({
  audio_files: [uploadResponse.file_path],
  original_filenames: [uploadResponse.original_filename],
  meeting_type: "weekly_sync",
  // 后端会使用当前日期
});

// 生成的纪要中会显示：
// 会议时间：2026年01月21日（假设今天是 2026-01-21）
```

## 推荐实现路径

### 第一阶段（最小实现）
使用**方案 1: 完全自动**
- 无需修改 UI
- 只需传递 `original_filenames`
- 后端自动处理日期

### 第二阶段（优化体验）
升级到**方案 2: 可选输入**
- 添加日期选择器（预填充自动识别的日期）
- 添加时间输入框（可选）
- 允许用户修正

### 第三阶段（完整功能）
- 支持批量上传时的日期时间管理
- 支持会议时间的智能推荐
- 支持历史会议时间的快速选择

## 注意事项

1. **时间的准确性**
   - 只有用户明确提供的时间才会显示在纪要中
   - 不要尝试从文件修改时间等推算会议时间
   - 宁可不显示时间，也不显示不准确的时间

2. **日期的容错性**
   - 日期可以使用默认值（当前日期）
   - 日期的容错性比时间高
   - 用户通常在会议当天或次日上传

3. **用户体验**
   - 减少必填字段
   - 提供智能默认值
   - 允许用户修正

4. **向后兼容**
   - 新字段都是可选的
   - 不影响现有功能
   - 可以逐步升级

## 相关文档

- [API 快速参考](./API_QUICK_REFERENCE.md)
- [前端开发指南](./FRONTEND_DEVELOPMENT_GUIDE.md)
- [前端类型定义](./frontend-types.ts)
- [会议元数据功能总结](./summaries/MEETING_METADATA_FEATURE.md)
