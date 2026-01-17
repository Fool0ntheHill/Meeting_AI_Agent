# 前端类型定义更新总结

**更新日期**: 2026-01-16  
**文件**: `docs/frontend-types.ts`

---

## 📝 更新内容

### 1. 任务状态类型扩展

```typescript
export type TaskState =
  | 'pending'
  | 'queued'
  | 'running'
  | 'transcribing'
  | 'identifying'
  | 'correcting'
  | 'summarizing'
  | 'success'
  | 'failed'
  | 'partial_success'
  | 'confirmed'  // ✨ 新增：已确认
  | 'archived';  // ✨ 新增：已归档
```

### 2. 分页参数增强

```typescript
export interface PaginationParams {
  limit?: number;
  offset?: number;
  state?: TaskState;  // ✨ 新增：状态筛选
}
```

### 3. 前端工作流程相关类型

#### 音频文件上传
```typescript
export interface AudioFileUpload {
  file: File;
  order: number;
  file_path?: string;
  duration?: number;
  size: number;
  status?: 'pending' | 'uploading' | 'success' | 'error';
  progress?: number;
  error?: string;
}
```

#### 会议类型选项
```typescript
export interface MeetingTypeOption {
  id: string;
  icon: string;
  name: string;
  description: string;
  template_id: string;
  focus_points: string[];
}
```

#### 编辑器 Tab
```typescript
export interface EditorTab {
  id: string;
  title: string;
  type: 'transcript' | 'minutes' | 'custom';
  content: string;
  template_id?: string;
  template_title?: string;
  version?: number;
  is_modified: boolean;
  created_at: string;
}
```

#### 提示词编辑状态
```typescript
export interface PromptEditorState {
  base_template_id: string;
  current_prompt: string;
  is_modified: boolean;
  parameters: Record<string, any>;
}

export interface PromptEditorDialog {
  show: boolean;
  base_template: PromptTemplate;
  current_prompt: string;
  is_modified: boolean;
  save_as_new: boolean;
  new_template_name?: string;
}
```

#### 说话人修正
```typescript
export interface SpeakerCorrectionMenu {
  segment_id: string;
  current_speaker: string;
  options: Array<{
    label: string;
    action: 'single' | 'global';
  }>;
}
```

#### 确认状态
```typescript
export interface ConfirmationState {
  is_confirmed: boolean;
  is_modified: boolean;
  can_copy: boolean;
}
```

#### 责任水印
```typescript
export interface ResponsibilityHeader {
  generated_at: string;
  responsible_person: string;
  department: string;
  ai_disclaimer: string;
}
```

### 4. API 客户端接口定义

```typescript
export interface MeetingAgentAPI {
  // 认证
  login(username: string): Promise<LoginResponse>;
  
  // 文件上传
  uploadAudio(file: File): Promise<UploadResponse>;
  deleteUpload(filePath: string): Promise<DeleteUploadResponse>;
  
  // 任务管理
  createTask(request: CreateTaskRequest): Promise<CreateTaskResponse>;
  getTaskStatus(taskId: string): Promise<TaskStatusResponse>;
  listTasks(params?: PaginationParams): Promise<TaskDetailResponse[]>;
  
  // 转写文本
  getTranscript(taskId: string): Promise<TranscriptResponse>;
  correctTranscript(taskId: string, request: CorrectTranscriptRequest): Promise<CorrectTranscriptResponse>;
  correctSpeakers(taskId: string, request: CorrectSpeakersRequest): Promise<CorrectSpeakersResponse>;
  
  // 衍生内容
  getArtifacts(taskId: string): Promise<ListArtifactsResponse>;
  generateArtifact(taskId: string, artifactType: string, request: GenerateArtifactRequest): Promise<GenerateArtifactResponse>;
  
  // 提示词模板
  listPromptTemplates(params?: { scope?: string; artifact_type?: string; user_id?: string }): Promise<ListPromptTemplatesResponse>;
  createPromptTemplate(request: CreatePromptTemplateRequest, userId: string): Promise<CreatePromptTemplateResponse>;
  
  // 任务确认
  confirmTask(taskId: string, request: ConfirmTaskRequest): Promise<ConfirmTaskResponse>;
}
```

### 5. 常量定义

```typescript
// 支持的音频格式
export const SUPPORTED_AUDIO_FORMATS = ['.wav', '.opus', '.mp3', '.m4a'];

// 最大文件大小
export const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

// 会议类型
export const MEETING_TYPES = [
  { id: 'general', icon: '🃏', name: '通用会议', template_id: 'global_general_meeting_v1' },
  { id: 'brainstorming', icon: '🧠', name: '头脑风暴', template_id: 'global_brainstorming_v1' },
  // ... 更多类型
];

// 任务状态标签
export const TASK_STATE_LABELS: Record<TaskState, string> = {
  pending: '待处理',
  running: '处理中',
  success: '已完成',
  // ... 更多状态
};

// 错误消息
export const ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数错误',
  401: 'Token 无效或过期，请重新登录',
  413: '文件过大，最大支持 500MB',
  // ... 更多错误码
};
```

---

## 🎯 使用方式

### 1. 复制到项目中

```bash
# 复制整个文件到前端项目
cp docs/frontend-types.ts src/types/api.ts
```

### 2. 导入使用

```typescript
import {
  TaskState,
  CreateTaskRequest,
  TaskDetailResponse,
  PromptTemplate,
  EditorTab,
  MEETING_TYPES,
  TASK_STATE_LABELS,
} from '@/types/api';

// 使用类型
const task: TaskDetailResponse = await api.getTaskDetail(taskId);

// 使用常量
const meetingType = MEETING_TYPES[0];
const stateLabel = TASK_STATE_LABELS[task.state];
```

### 3. 实现 API 客户端

```typescript
import { MeetingAgentAPI } from '@/types/api';

class APIClient implements MeetingAgentAPI {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = null;

  async login(username: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseURL}/auth/dev/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    });
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  async uploadAudio(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${this.baseURL}/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` },
      body: formData,
    });
    
    return await response.json();
  }

  // ... 实现其他方法
}

export const api = new APIClient();
```

---

## 📦 完整类型列表

### 核心类型
- ✅ `TaskState` - 任务状态枚举
- ✅ `TranscriptSegment` - 转写片段
- ✅ `TranscriptResponse` - 转写文本响应
- ✅ `UploadResponse` - 上传响应
- ✅ `LoginResponse` - 登录响应
- ✅ `CreateTaskRequest` - 创建任务请求
- ✅ `TaskDetailResponse` - 任务详情响应
- ✅ `PromptTemplate` - 提示词模板
- ✅ `ArtifactInfo` - 衍生内容信息
- ✅ `MeetingMinutes` - 会议纪要结构

### 工作流程类型
- ✅ `AudioFileUpload` - 音频文件上传
- ✅ `MeetingTypeOption` - 会议类型选项
- ✅ `EditorTab` - 编辑器标签页
- ✅ `PromptEditorState` - 提示词编辑状态
- ✅ `SpeakerCorrectionMenu` - 说话人修正菜单
- ✅ `ConfirmationState` - 确认状态
- ✅ `ResponsibilityHeader` - 责任水印

### API 接口类型
- ✅ `MeetingAgentAPI` - API 客户端接口
- ✅ `PaginationParams` - 分页参数
- ✅ `ErrorResponse` - 错误响应

### 常量
- ✅ `SUPPORTED_AUDIO_FORMATS` - 支持的音频格式
- ✅ `MAX_FILE_SIZE` - 最大文件大小
- ✅ `MEETING_TYPES` - 会议类型列表
- ✅ `TASK_STATE_LABELS` - 任务状态标签
- ✅ `ERROR_MESSAGES` - 错误消息映射

---

## ✅ 类型安全检查

所有类型定义都经过以下验证：
- ✅ 与后端 API Schema 一致
- ✅ 包含所有必需字段
- ✅ 可选字段正确标记
- ✅ 枚举类型完整
- ✅ 嵌套类型正确引用

---

**维护者**: 后端开发团队  
**最后更新**: 2026-01-16
