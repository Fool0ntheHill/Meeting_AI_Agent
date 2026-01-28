/**
 * 前端 TypeScript 类型定义
 * 
 * 基于后端 API 生成的类型定义
 * 可以直接复制到前端项目中使用
 */

// ============================================================================
// 认证相关
// ============================================================================

export interface LoginRequest {
  username: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  tenant_id: string;
  expires_in: number;
}

// ============================================================================
// 任务管理
// ============================================================================

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
  | 'partial_success';

export interface AudioFile {
  file_path: string;
  speaker_id: string;
}

export interface PromptInstance {
  template_id: string;
  language?: string;
  parameters?: Record<string, any>;
}

export interface CreateTaskRequest {
  audio_files: AudioFile[];
  file_order?: number[];
  meeting_type: string;
  asr_language?: string;  // 默认 "zh-CN+en-US"
  output_language?: string;  // 默认 "zh-CN"
  prompt_instance?: PromptInstance;
  skip_speaker_recognition?: boolean;
}

export interface CreateTaskResponse {
  success: boolean;
  task_id: string;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  state: TaskState;
  progress: number;  // 0-100
  estimated_time?: number;  // 秒
  error_details?: string;
  updated_at: string;
}

export interface TaskDetailResponse {
  task_id: string;
  user_id: string;
  tenant_id: string;
  meeting_type: string;
  audio_files: string[];
  file_order: number[];
  asr_language: string;
  output_language: string;
  state: TaskState;
  progress: number;
  error_details?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

// ============================================================================
// 成本预估
// ============================================================================

export interface EstimateCostRequest {
  audio_duration: number;  // 秒
  meeting_type: string;
  enable_speaker_recognition?: boolean;
}

export interface EstimateCostResponse {
  total_cost: number;  // 元
  cost_breakdown: {
    asr: number;
    voiceprint: number;
    llm: number;
  };
}

// ============================================================================
// 转写修正
// ============================================================================

export interface CorrectTranscriptRequest {
  corrected_text: string;
  regenerate_artifacts?: boolean;
}

export interface CorrectTranscriptResponse {
  success: boolean;
  message: string;
  regenerated_artifacts?: string[];
}

export interface CorrectSpeakersRequest {
  speaker_mapping: Record<string, string>;  // 原标签 -> 新名称
  regenerate_artifacts?: boolean;
}

export interface CorrectSpeakersResponse {
  success: boolean;
  message: string;
  regenerated_artifacts?: string[];
}

// ============================================================================
// 衍生内容管理
// ============================================================================

export interface ArtifactInfo {
  artifact_id: string;
  task_id: string;
  artifact_type: string;  // meeting_minutes, action_items, summary_notes
  version: number;
  prompt_instance: PromptInstance;
  created_at: string;
  created_by: string;
}

export interface ListArtifactsResponse {
  task_id: string;
  artifacts_by_type: Record<string, ArtifactInfo[]>;
  total_count: number;
}

export interface GeneratedArtifact {
  artifact_id: string;
  task_id: string;
  artifact_type: string;
  version: number;
  prompt_instance: PromptInstance;
  content: string;  // JSON 字符串，需要 JSON.parse()
  metadata?: Record<string, any>;
  created_at: string;
  created_by: string;
}

export interface ArtifactDetailResponse {
  artifact: GeneratedArtifact;
}

export interface GenerateArtifactRequest {
  prompt_instance: PromptInstance;
}

export interface GenerateArtifactResponse {
  success: boolean;
  artifact_id: string;
  version: number;
  content: Record<string, any>;
  message: string;
}

// ============================================================================
// 会议纪要结构
// ============================================================================

export interface MeetingMinutes {
  title: string;
  participants: string[];
  summary: string;
  key_points: string[];
  action_items: string[];
  created_at: string;
  responsible_person?: string;
}

// ============================================================================
// 提示词模板
// ============================================================================

export interface PromptTemplate {
  template_id: string;
  title: string;
  description: string;
  prompt_body: string;
  artifact_type: string;
  supported_languages: string[];
  parameter_schema: Record<string, any>;
  is_system: boolean;
  scope: string;
  scope_id?: string;
  created_at: string;
}

export interface ListPromptTemplatesResponse {
  templates: PromptTemplate[];
}

export interface PromptTemplateDetailResponse {
  template: PromptTemplate;
}

export interface CreatePromptTemplateRequest {
  title: string;
  description?: string;
  prompt_body: string;
  artifact_type: string;
  supported_languages?: string[];
  parameter_schema: Record<string, any>;
}

export interface CreatePromptTemplateResponse {
  success: boolean;
  template_id: string;
  message: string;
}

export interface UpdatePromptTemplateRequest {
  title?: string;
  description?: string;
  prompt_body?: string;
  supported_languages?: string[];
  parameter_schema?: Record<string, any>;
}

export interface UpdatePromptTemplateResponse {
  success: boolean;
  message: string;
}

export interface DeletePromptTemplateResponse {
  success: boolean;
  message: string;
}

// ============================================================================
// 热词管理
// ============================================================================

export interface CreateHotwordSetRequest {
  name: string;
  scope: string;  // global, tenant, user
  scope_id?: string;
  asr_language: string;
  description?: string;
  // hotwords_file 通过 FormData 上传
}

export interface CreateHotwordSetResponse {
  success: boolean;
  hotword_set_id: string;
  boosting_table_id: string;
  word_count: number;
  message: string;
}

export interface HotwordSetInfo {
  hotword_set_id: string;
  name: string;
  provider: string;
  provider_resource_id: string;
  scope: string;
  scope_id?: string;
  asr_language: string;
  description?: string;
  word_count?: number;
  word_size?: number;
  preview?: string[];
  created_at: string;
  updated_at: string;
}

export interface ListHotwordSetsResponse {
  hotword_sets: HotwordSetInfo[];
  total: number;
}

export interface DeleteHotwordSetResponse {
  success: boolean;
  message: string;
}

export interface UpdateHotwordSetRequest {
  name?: string;
  description?: string;
  // hotwords_file 通过 FormData 上传
}

export interface UpdateHotwordSetResponse {
  success: boolean;
  word_count: number;
  message: string;
}

// ============================================================================
// 任务确认
// ============================================================================

export interface ConfirmTaskRequest {
  confirmation_items: Record<string, boolean>;
  responsible_person: {
    id: string;
    name: string;
  };
}

export interface ConfirmTaskResponse {
  success: boolean;
  task_id: string;
  state: string;
  confirmed_by: string;
  confirmed_by_name: string;
  confirmed_at: string;
  message: string;
}

// ============================================================================
// 错误响应
// ============================================================================

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
}

// ============================================================================
// 健康检查
// ============================================================================

export interface HealthCheckResponse {
  status: string;
  version: string;
  timestamp: string;
  dependencies: Record<string, string>;
}

// ============================================================================
// 工具类型
// ============================================================================

export interface PaginationParams {
  limit?: number;
  offset?: number;
}

export interface APIResponse<T> {
  data?: T;
  error?: ErrorResponse;
}

// ============================================================================
// API 客户端类型
// ============================================================================

export interface APIClientConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
}

export interface RequestOptions extends RequestInit {
  params?: Record<string, any>;
  timeout?: number;
}
