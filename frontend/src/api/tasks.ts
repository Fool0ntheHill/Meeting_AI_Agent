import { request } from './request'
import type {
  CreateTaskRequest,
  CreateTaskResponse,
  TaskDetailResponse,
  TaskStatusResponse,
  CorrectTranscriptRequest,
  CorrectTranscriptResponse,
  CorrectSpeakersRequest,
  CorrectSpeakersResponse,
  PaginationParams,
} from '@/types/frontend-types'

export interface ListTasksParams extends PaginationParams {
  state?: string
  folder_id?: string | null
  include_deleted?: boolean
}

export const listTasks = (params?: ListTasksParams) =>
  request<{ items: TaskDetailResponse[]; total: number }>({
    url: '/tasks',
    method: 'GET',
    params,
  })

export const createTask = (payload: CreateTaskRequest) =>
  request<CreateTaskResponse>({
    url: '/tasks',
    method: 'POST',
    data: payload,
  })

export const getTaskDetail = (taskId: string) =>
  request<TaskDetailResponse>({
    url: `/tasks/${taskId}`,
    method: 'GET',
  })

export const getTaskStatus = (taskId: string) =>
  request<TaskStatusResponse>({
    url: `/tasks/${taskId}/status`,
    method: 'GET',
    headers: {
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache',
    },
  })

export interface TranscriptParagraph {
  paragraph_id: string
  start_time: number
  end_time: number
  speaker: string
  text: string
}

export interface TranscriptResponse {
  task_id: string
  audio_duration: number
  paragraphs: TranscriptParagraph[]
}

export const getTranscript = (taskId: string) =>
  request<TranscriptResponse>({
    url: `/tasks/${taskId}/transcript`,
    method: 'GET',
  })

export const correctTranscript = (taskId: string, payload: CorrectTranscriptRequest) =>
  request<CorrectTranscriptResponse>({
    url: `/tasks/${taskId}/transcript`,
    method: 'PUT',
    data: payload,
  })

export const correctSpeakers = (taskId: string, payload: CorrectSpeakersRequest) =>
  request<CorrectSpeakersResponse>({
    url: `/tasks/${taskId}/speakers`,
    method: 'PATCH',
    data: payload,
  })

export const renameTask = (taskId: string, name: string) =>
  request<{ success: boolean; message?: string }>({
    url: `/tasks/${taskId}/rename`,
    method: 'PATCH',
    data: { name },
  })

export const moveTaskToFolder = (taskId: string, folder_id: string | null) =>
  request<{ success: boolean; message?: string }>({
    url: `/sessions/${taskId}/move`,
    method: 'PATCH',
    data: { folder_id },
  })

export const cancelTask = (taskId: string) =>
  request<{ success: boolean; message?: string; task_id?: string; previous_state?: string }>({
    url: `/tasks/${taskId}/cancel`,
    method: 'POST',
  })

export const deleteTaskSoft = (taskId: string) =>
  request<{ success: boolean; message?: string }>({
    url: `/sessions/${taskId}/delete`,
    method: 'PATCH',
  })

export const restoreTask = (taskId: string) =>
  request<{ success: boolean; message?: string }>({
    url: `/sessions/${taskId}/restore`,
    method: 'PATCH',
  })

export const deleteTaskPermanent = (taskId: string) =>
  request<{ success: boolean; message?: string }>({
    url: `/sessions/${taskId}`,
    method: 'DELETE',
  })

export const listTrashSessions = (params?: PaginationParams) =>
  request<{ items?: TaskDetailResponse[]; total?: number } | TaskDetailResponse[]>({
    url: '/trash/sessions',
    method: 'GET',
    params,
  })

export const batchMoveTasks = (taskIds: string[], folder_id: string | null) =>
  request<{ success: boolean; moved_count?: number; message?: string }>({
    url: '/sessions/batch-move',
    method: 'POST',
    data: { task_ids: taskIds, folder_id },
  })

export const batchDeleteTasks = (taskIds: string[]) =>
  request<{ success: boolean; deleted_count?: number; message?: string }>({
    url: '/sessions/batch-delete',
    method: 'POST',
    data: { task_ids: taskIds },
  })

export const batchRestoreTasks = (taskIds: string[]) =>
  request<{ success: boolean; restored_count?: number; message?: string }>({
    url: '/sessions/batch-restore',
    method: 'POST',
    data: { task_ids: taskIds },
  })

export const uploadAudio = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request<{ file_path: string; original_filename?: string }>({
    url: '/upload',
    method: 'POST',
    data: formData,
    headers: {
      // Content-Type 由浏览器自动设置
    },
  })
}
