/**
 * 前端 TypeScript 类型定义
 * 
 * 基于后端 API 生成的类型定义
 * 可以直接复制到前端项目中使用
 * 
 * ⚠️ 重要：占位接口替换指南
 * 
 * 如果你的前端正在使用占位接口，请参考以下映射表替换为真实接口：
 * 
 * | 功能         | 占位路径                      | 真实路径                          | 状态      |
 * |-------------|------------------------------|----------------------------------|----------|
 * | 会话重命名   | PATCH /tasks/{id}/rename     | PATCH /tasks/{id}/rename         | ✅ 已实现 |
 * | 会话移动     | PATCH /tasks/{id}/move       | PATCH /sessions/{id}/move        | ✅ 已实现 |
 * | 回收站列表   | GET /tasks/trash             | GET /trash/sessions              | ✅ 已实现 |
 * | 列出文件夹   | -                            | GET /folders                     | ✅ 已实现 |
 * | 创建文件夹   | -                            | POST /folders                    | ✅ 已实现 |
 * | 重命名文件夹 | -                            | PATCH /folders/{id}              | ✅ 已实现 |
 * | 删除文件夹   | -                            | DELETE /folders/{id}             | ✅ 已实现 |
 * | 软删除会话   | -                            | PATCH /sessions/{id}/delete      | ✅ 已实现 |
 * | 还原会话     | -                            | PATCH /sessions/{id}/restore     | ✅ 已实现 |
 * | 彻底删除     | -                            | DELETE /sessions/{id}            | ✅ 已实现 |
 * | 批量移动     | -                            | POST /sessions/batch-move        | ✅ 已实现 |
 * | 批量删除     | -                            | POST /sessions/batch-delete      | ✅ 已实现 |
 * | 批量还原     | -                            | POST /sessions/batch-restore     | ✅ 已实现 |
 * 
 * 关键修改：
 * 1. 移除文件夹和回收站的本地 fallback 逻辑
 * 2. 更新接口路径：/tasks/{id}/move → /sessions/{id}/move
 * 3. 更新接口路径：/tasks/trash → /trash/sessions
 * 4. 会话重命名接口：PATCH /tasks/{id}/rename ✅ 已实现
 * 
 * 详细文档：docs/FRONTEND_DEVELOPMENT_GUIDE.md
 */

// ============================================================================
// 转写文本
// ============================================================================

export interface TranscriptSegment {
  text: string;
  start_time: number;
  end_time: number;
  speaker?: string;
  confidence?: number;
}

export interface TranscriptResponse {
  task_id: string;
  segments: TranscriptSegment[];
  full_text: string;
  duration: number;
  language: string;
  provider: string;
}

// ============================================================================
// 文件上传 ✨ 已实现
// ============================================================================

export interface UploadResponse {
  success: boolean;
  file_path: string;
  original_filename: string;  // 原始文件名 ✨ 新增
  file_size: number;
  duration?: number;
}

export interface DeleteUploadResponse {
  success: boolean;
  message: string;
}

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
  | 'partial_success'
  | 'confirmed'  // 已确认
  | 'archived';  // 已归档

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
  audio_files: string[];  // 文件路径列表
  file_order?: number[];
  original_filenames?: string[];  // 原始文件名列表 ✨ 新增
  audio_duration?: number;  // 音频总时长（秒），从上传接口获取 ✨ 新增
  meeting_type: string;
  meeting_date?: string;  // 会议日期，格式：YYYY-MM-DD ✨ 新增
  meeting_time?: string;  // 会议时间，格式：HH:MM ✨ 新增
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
  audio_duration?: number;  // 音频总时长（秒），从 progress=0 开始可用 ✨ 新增
  asr_language?: string;  // ASR识别语言（如 "zh-CN+en-US"）✨ 新增
  error_details?: string;
  updated_at: string;
}

export interface TaskDetailResponse {
  task_id: string;
  user_id: string;
  tenant_id: string;
  name?: string;  // 任务名称（可选）✨ 新增
  meeting_type: string;
  audio_files: string[];
  file_order: number[];
  asr_language: string;
  output_language: string;
  state: TaskState;
  progress: number;
  error_details?: string;
  duration?: number;  // 音频总时长(秒) ✨ 新增
  created_at: string;
  updated_at: string;
  completed_at?: string;
  last_content_modified_at?: string;  // 内容最后修改时间 ✨ 新增
}

// ============================================================================
// 任务重命名 ✨ 新增
// ============================================================================

export interface RenameTaskRequest {
  name: string;  // 1-255 字符
}

export interface RenameTaskResponse {
  success: boolean;
  message: string;
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
  description: string;
  prompt_body: string;
  artifact_type: string;
  supported_languages: string[];
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

export type TemplateScope = 'global' | 'private';

export interface TemplatePermission {
  canRead: boolean;
  canUpdate: boolean;
  canDelete: boolean;
  reason?: string;
}

// ============================================================================
// 热词管理相关类型
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
  state?: TaskState;  // 状态筛选
}

export interface APIResponse<T> {
  data?: T;
  error?: ErrorResponse;
}

// ============================================================================
// 前端工作流程相关类型
// ============================================================================

// 音频文件上传
export interface AudioFileUpload {
  file: File;
  order: number;  // 拼接顺序
  file_path?: string;  // 上传后的路径
  duration?: number;  // 音频时长（秒）
  size: number;  // 文件大小（字节）
  status?: 'pending' | 'uploading' | 'success' | 'error';
  progress?: number;  // 上传进度 0-100
  error?: string;
}

// 会议类型选项
export interface MeetingTypeOption {
  id: string;
  icon: string;
  name: string;
  description: string;
  template_id: string;
  focus_points: string[];
}

// 提示词编辑状态
export interface PromptEditorState {
  base_template_id: string;  // 基础模板 ID
  current_prompt: string;  // 当前提示词内容
  is_modified: boolean;  // 是否已修改
  parameters: Record<string, any>;  // 参数值
}

// 编辑器 Tab
export interface EditorTab {
  id: string;
  title: string;
  type: 'transcript' | 'minutes' | 'custom';
  content: string;
  template_id?: string;  // 使用的模板 ID
  template_title?: string;  // 模板名称
  version?: number;  // 版本号
  is_modified: boolean;
  created_at: string;
}

// 说话人修正菜单
export interface SpeakerCorrectionMenu {
  segment_id: string;
  current_speaker: string;
  options: Array<{
    label: string;
    action: 'single' | 'global';
  }>;
}

// 用户反馈
export interface UserFeedback {
  task_id: string;
  feedback_text?: string;
  allow_ai_learning: boolean;  // 默认 false
  submitted_at?: string;
}

// 企业微信通知
export interface WeChatNotification {
  title: string;  // 会议名称
  meeting_time: string;
  link: string;  // 纪要链接
  summary: string;  // 50字摘要
  status: 'success' | 'failed';
}

// 企业微信登录响应
export interface WeChatLoginResponse {
  access_token: string;
  user_id: string;
  tenant_id: string;
  user_name: string;
  department: string;
  expires_in: number;
}

// 重新生成选项
export interface RegenerateOptions {
  template_id: string;
  template_title: string;
  parameters: Record<string, any>;
  modified_prompt?: string;  // 如果用户修改了提示词
}

// 提示词编辑对话框
export interface PromptEditorDialog {
  show: boolean;
  base_template: PromptTemplate;
  current_prompt: string;
  is_modified: boolean;
  save_as_new: boolean;
  new_template_name?: string;
}

// 新建 Tab 选项
export interface NewTabOptions {
  template_id: string;
  template_title: string;
  tab_title: string;
}

// 工作台提示词编辑器
export interface WorkbenchPromptEditor {
  show_editor: boolean;
  current_template: PromptTemplate;
  modified_prompt: string;
}

// 确认状态
export interface ConfirmationState {
  is_confirmed: boolean;
  is_modified: boolean;
  can_copy: boolean;
}

// 责任水印
export interface ResponsibilityHeader {
  generated_at: string;
  responsible_person: string;
  department: string;
  ai_disclaimer: string;
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

// ============================================================================
// API 客户端接口定义
// 
// ⚠️ 注意：以下接口定义基于真实后端实现
// 如果你的代码中使用了占位接口，请参考文件开头的映射表进行替换
// ============================================================================

// 版本管理相关类型
export interface ListArtifactVersionsResponse {
  task_id: string;
  artifact_type: string;
  versions: ArtifactInfo[];
  total_count: number;
}

export interface VersionComparison {
  version1: {
    artifact_id: string;
    version: number;
    content: any;
    created_at: string;
    created_by: string;
  };
  version2: {
    artifact_id: string;
    version: number;
    content: any;
    created_at: string;
    created_by: string;
  };
  diff: {
    added: string[];
    removed: string[];
    unchanged: string[];
  };
}

// 模板管理相关类型（已在前面定义，这里删除重复）

// 上传相关增强类型
export type UploadProgressCallback = (progress: number) => void;

export enum UploadErrorType {
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  UNSUPPORTED_FORMAT = 'UNSUPPORTED_FORMAT',
  NETWORK_ERROR = 'NETWORK_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  STORAGE_FULL = 'STORAGE_FULL',
  TOO_MANY_REQUESTS = 'TOO_MANY_REQUESTS',
}

export interface UploadError {
  type: UploadErrorType;
  message: string;
  statusCode?: number;
  retryAfter?: number;
}

export interface MultiFileUploadState {
  files: Array<{
    file: File;
    status: 'pending' | 'uploading' | 'success' | 'error';
    progress: number;
    result?: UploadResponse;
    error?: UploadError;
  }>;
  totalProgress: number;
}

// ============================================================================
// 文件夹管理 ✨ 新增
// 注意：文件夹为扁平结构（单层），不支持嵌套
// ============================================================================

export interface FolderInfo {
  folder_id: string;
  name: string;
  parent_id: string | null;  // 始终为 null（扁平结构）
  owner_user_id: string;
  owner_tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface CreateFolderRequest {
  name: string;
  // 不支持 parent_id（扁平结构）
}

export interface CreateFolderResponse {
  success: boolean;
  folder_id: string;
  message: string;
}

export interface ListFoldersResponse {
  items: FolderInfo[];
  total: number;
}

export interface UpdateFolderRequest {
  name: string;
}

export interface UpdateFolderResponse {
  success: boolean;
  message: string;
}

export interface DeleteFolderResponse {
  success: boolean;
  message: string;
}

// ============================================================================
// 会话移动和回收站 ✨ 新增
// ============================================================================

export interface MoveSessionRequest {
  folder_id: string | null;
}

export interface MoveSessionResponse {
  success: boolean;
  message: string;
}

export interface DeleteSessionResponse {
  success: boolean;
  message: string;
}

export interface RestoreSessionResponse {
  success: boolean;
  message: string;
}

export interface PermanentDeleteSessionResponse {
  success: boolean;
  message: string;
}

export interface TrashSessionInfo {
  task_id: string;
  user_id: string;
  tenant_id: string;
  meeting_type: string;
  folder_id: string | null;
  duration?: number;  // 音频总时长(秒) ✨ 新增
  last_content_modified_at?: string;  // 内容最后修改时间 ✨ 新增
  deleted_at: string;
  created_at: string;
}

export interface ListTrashSessionsResponse {
  items: TrashSessionInfo[];
  total: number;
}

// ============================================================================
// 批量操作 ✨ 新增
// ============================================================================

export interface BatchMoveSessionsRequest {
  task_ids: string[];
  folder_id: string | null;
}

export interface BatchMoveSessionsResponse {
  success: boolean;
  moved_count: number;
  message: string;
}

export interface BatchDeleteSessionsRequest {
  task_ids: string[];
}

export interface BatchDeleteSessionsResponse {
  success: boolean;
  deleted_count: number;
  message: string;
}

export interface BatchRestoreSessionsRequest {
  task_ids: string[];
}

export interface BatchRestoreSessionsResponse {
  success: boolean;
  restored_count: number;
  message: string;
}

// ============================================================================
// API 客户端接口
// ============================================================================

export interface MeetingAgentAPI {
  // ========================================================================
  // 认证
  // ========================================================================
  login(username: string): Promise<LoginResponse>;
  refreshToken(): Promise<LoginResponse>;
  
  // ========================================================================
  // 文件上传
  // ========================================================================
  uploadAudio(file: File): Promise<UploadResponse>;
  deleteUpload(filePath: string): Promise<DeleteUploadResponse>;
  
  // ========================================================================
  // 任务管理
  // ========================================================================
  createTask(request: CreateTaskRequest): Promise<CreateTaskResponse>;
  getTaskStatus(taskId: string): Promise<TaskStatusResponse>;
  getTaskDetail(taskId: string): Promise<TaskDetailResponse>;
  listTasks(params?: {
    limit?: number;
    offset?: number;
    state?: TaskState;
    folder_id?: string;  // ✨ 新增：文件夹筛选
    include_deleted?: boolean;  // ✨ 新增：是否包含已删除
  }): Promise<TaskDetailResponse[]>;
  deleteTask(taskId: string): Promise<void>;
  
  // ========================================================================
  // 文件夹管理 ✅ 已实现，可直接使用
  // ========================================================================
  listFolders(): Promise<ListFoldersResponse>;
  createFolder(request: CreateFolderRequest): Promise<CreateFolderResponse>;
  updateFolder(folderId: string, request: UpdateFolderRequest): Promise<UpdateFolderResponse>;
  deleteFolder(folderId: string): Promise<DeleteFolderResponse>;
  
  // ========================================================================
  // 会话操作 ✅ 已实现，可直接使用
  // ⚠️ 注意：路径是 /sessions/{id}，不是 /tasks/{id}
  // ========================================================================
  moveSession(taskId: string, request: MoveSessionRequest): Promise<MoveSessionResponse>;
  deleteSession(taskId: string): Promise<DeleteSessionResponse>;
  restoreSession(taskId: string): Promise<RestoreSessionResponse>;
  permanentDeleteSession(taskId: string): Promise<PermanentDeleteSessionResponse>;
  listTrashSessions(): Promise<ListTrashSessionsResponse>;
  
  // ========================================================================
  // 批量操作 ✅ 已实现，可直接使用
  // ========================================================================
  batchMoveSessions(request: BatchMoveSessionsRequest): Promise<BatchMoveSessionsResponse>;
  batchDeleteSessions(request: BatchDeleteSessionsRequest): Promise<BatchDeleteSessionsResponse>;
  batchRestoreSessions(request: BatchRestoreSessionsRequest): Promise<BatchRestoreSessionsResponse>;
  
  // ========================================================================
  // 会话重命名 ✅ 已实现，可直接使用
  // ========================================================================
  renameTask(taskId: string, name: string): Promise<RenameTaskResponse>;
  
  // ========================================================================
  // 成本预估
  // ========================================================================
  estimateCost(request: EstimateCostRequest): Promise<EstimateCostResponse>;
  
  // ========================================================================
  // 转写文本
  // ========================================================================
  getTranscript(taskId: string): Promise<TranscriptResponse>;
  correctTranscript(taskId: string, request: CorrectTranscriptRequest): Promise<CorrectTranscriptResponse>;
  correctSpeakers(taskId: string, request: CorrectSpeakersRequest): Promise<CorrectSpeakersResponse>;
  
  // ========================================================================
  // 衍生内容
  // ========================================================================
  getArtifacts(taskId: string): Promise<ListArtifactsResponse>;
  getArtifactDetail(artifactId: string): Promise<ArtifactDetailResponse>;
  generateArtifact(taskId: string, artifactType: string, request: GenerateArtifactRequest): Promise<GenerateArtifactResponse>;
  regenerateArtifact(taskId: string, artifactType: string, request: GenerateArtifactRequest): Promise<GenerateArtifactResponse>;
  listArtifactVersions(taskId: string, artifactType: string): Promise<ListArtifactVersionsResponse>;
  compareVersions(taskId: string, artifactType: string, version1: number, version2: number): Promise<VersionComparison>;
  
  // ========================================================================
  // 提示词模板
  // ========================================================================
  listPromptTemplates(params?: { scope?: string; artifact_type?: string; user_id?: string }): Promise<ListPromptTemplatesResponse>;
  getPromptTemplate(templateId: string, userId?: string): Promise<PromptTemplateDetailResponse>;
  createPromptTemplate(request: CreatePromptTemplateRequest, userId: string): Promise<CreatePromptTemplateResponse>;
  updatePromptTemplate(templateId: string, request: UpdatePromptTemplateRequest, userId: string): Promise<UpdatePromptTemplateResponse>;
  deletePromptTemplate(templateId: string, userId: string): Promise<DeletePromptTemplateResponse>;
  checkTemplatePermission(templateId: string, userId: string): Promise<TemplatePermission>;
  
  // ========================================================================
  // 热词管理
  // ========================================================================
  createHotwordSet(formData: FormData): Promise<CreateHotwordSetResponse>;
  listHotwordSets(params?: { scope?: string; asr_language?: string }): Promise<ListHotwordSetsResponse>;
  deleteHotwordSet(hotwordSetId: string): Promise<DeleteHotwordSetResponse>;
  updateHotwordSet(hotwordSetId: string, formData: FormData): Promise<UpdateHotwordSetResponse>;
  
  // ========================================================================
  // 任务确认
  // ========================================================================
  confirmTask(taskId: string, request: ConfirmTaskRequest): Promise<ConfirmTaskResponse>;
  
  // ========================================================================
  // 健康检查
  // ========================================================================
  healthCheck(): Promise<HealthCheckResponse>;
}

// ============================================================================
// 常量定义
// ============================================================================

export const SUPPORTED_AUDIO_FORMATS = ['.wav', '.opus', '.mp3', '.m4a', '.ogg'] as const;
export const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

export const MEETING_TYPES = [
  { id: 'general', icon: '🃏', name: '通用会议', template_id: 'global_general_meeting_v1' },
  { id: 'brainstorming', icon: '🧠', name: '头脑风暴', template_id: 'global_brainstorming_v1' },
  { id: 'interview', icon: '🤝', name: '面试/HR', template_id: 'global_interview_v1' },
  { id: 'standup', icon: '🚀', name: '每日站会', template_id: 'global_daily_standup_v1' },
  { id: 'weekly', icon: '📊', name: '周会', template_id: 'global_weekly_meeting_v1' },
  { id: 'requirement', icon: '📝', name: '需求评审', template_id: 'global_requirement_review_v1' },
] as const;

export const ASR_LANGUAGES = {
  ZH_CN: 'zh-CN',
  EN_US: 'en-US',
  ZH_EN: 'zh-CN+en-US',
  JA_JP: 'ja-JP',
  KO_KR: 'ko-KR',
} as const;

export const OUTPUT_LANGUAGES = {
  ZH_CN: 'zh-CN',
  EN_US: 'en-US',
  JA_JP: 'ja-JP',
  KO_KR: 'ko-KR',
} as const;

export const TASK_STATE_LABELS: Record<TaskState, string> = {
  pending: '待处理',
  queued: '队列中',
  running: '处理中',
  transcribing: '转写中',
  identifying: '识别说话人',
  correcting: '修正中',
  summarizing: '生成纪要',
  success: '已完成',
  failed: '失败',
  partial_success: '部分成功',
  confirmed: '已确认',
  archived: '已归档',
};

export const ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数错误',
  401: 'Token 无效或过期，请重新登录',
  403: '无权访问此资源',
  404: '资源不存在',
  413: '文件过大，最大支持 500MB',
  415: '不支持的文件格式',
  422: '请求参数验证失败',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误',
  503: '服务暂时不可用',
  507: '存储空间不足',
};
