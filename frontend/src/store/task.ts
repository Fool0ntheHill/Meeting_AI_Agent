import { create } from 'zustand'
import {
  createTask,
  getTaskDetail,
  getTaskStatus,
  getTranscript,
  listTasks,
  listTrashSessions,
  type ListTasksParams,
  type TranscriptResponse,
} from '@/api/tasks'
import type { CreateTaskRequest, CreateTaskResponse, TaskDetailResponse, TaskStatusResponse } from '@/types/frontend-types'

const getRecord = (value: unknown): Record<string, unknown> => (value && typeof value === 'object' ? (value as Record<string, unknown>) : {})

const getString = (value: unknown): string | undefined => (typeof value === 'string' ? value : undefined)
const getStringLike = (value: unknown): string | undefined =>
  typeof value === 'string' ? value : typeof value === 'number' ? String(value) : undefined

const normalizeTask = (raw: unknown): TaskDetailResponse & {
  folder_id?: string | null
  folder_path?: string
  display_name?: string
  name?: string
  session_id?: string
} => {
  const obj = getRecord(raw)
  const folderObj = getRecord(obj.folder)
  const rawFolder =
    getStringLike(obj.folder_id) ??
    getStringLike(obj.folderId) ??
    getStringLike(folderObj.id) ??
    getStringLike(folderObj.folder_id) ??
    (typeof obj.folder === 'string' ? obj.folder : null)
  const folder_id = typeof rawFolder === 'string' && rawFolder.trim() ? rawFolder : null
  const folder_path =
    getString(obj.folder_path) ??
    getString(obj.folderPath) ??
    getString(folderObj.name) ??
    getString(obj.folder_name) ??
    undefined
  const base = typeof raw === 'object' && raw !== null ? (raw as TaskDetailResponse) : ({} as TaskDetailResponse)
  return {
    ...base,
    task_id: getStringLike(obj.task_id) ?? getStringLike(obj.session_id) ?? getStringLike(obj.id) ?? '',
    display_name: getString(obj.display_name) ?? getString(obj.name) ?? getString(obj.title) ?? undefined,
    name: getString(obj.name) ?? getString(obj.display_name) ?? getString(obj.title) ?? undefined,
    folder_id,
    folder_path,
  }
}

interface TaskState {
  list: TaskDetailResponse[]
  total: number
  loading: boolean
  trash: TaskDetailResponse[]
  trashTotal: number
  currentTask: TaskDetailResponse | null
  status: TaskStatusResponse | null
  transcript: TranscriptResponse | null
  fetchList: (params?: ListTasksParams) => Promise<void>
  fetchTrash: (params?: ListTasksParams) => Promise<void>
  fetchDetail: (taskId: string) => Promise<void>
  fetchStatus: (taskId: string) => Promise<TaskStatusResponse>
  fetchTranscript: (taskId: string) => Promise<void>
  createTask: (payload: CreateTaskRequest) => Promise<CreateTaskResponse>
}

export const useTaskStore = create<TaskState>((set) => ({
  list: [],
  total: 0,
  loading: false,
  trash: [],
  trashTotal: 0,
  currentTask: null,
  status: null,
  transcript: null,
  fetchList: async (params) => {
    set({ loading: true })
    try {
      const res = await listTasks(params)
      const itemsRaw = Array.isArray((res as { items?: TaskDetailResponse[] })?.items)
        ? (res as { items: TaskDetailResponse[] }).items
        : Array.isArray(res)
          ? (res as TaskDetailResponse[])
          : []
      const items = itemsRaw.map((t) => normalizeTask(t))
      const total = typeof (res as { total?: number })?.total === 'number' ? (res as { total: number }).total : items.length
      set({ list: items, total })
    } finally {
      set({ loading: false })
    }
  },
  fetchTrash: async (params) => {
    set({ loading: true })
    try {
      const res = await listTrashSessions(params)
      const itemsRaw = Array.isArray((res as { items?: TaskDetailResponse[] })?.items)
        ? (res as { items: TaskDetailResponse[] }).items
        : Array.isArray(res)
          ? (res as TaskDetailResponse[])
          : []
      const items = itemsRaw.map((t) => {
        const normalized = normalizeTask(t)
        return {
          ...normalized,
          name: normalized.name ?? normalized.task_id ?? normalized.meeting_type ?? '',
        }
      })
      const total = typeof (res as { total?: number })?.total === 'number' ? (res as { total: number }).total : items.length
      set({ trash: items, trashTotal: total })
    } finally {
      set({ loading: false })
    }
  },
  fetchDetail: async (taskId) => {
    const detail = await getTaskDetail(taskId)
    set({ currentTask: detail })
  },
  fetchStatus: async (taskId) => {
    const status = await getTaskStatus(taskId)
    set({ status })
    return status
  },
  fetchTranscript: async (taskId) => {
    const transcript = await getTranscript(taskId)
    const asRecord = getRecord(transcript)
    const segments = (asRecord.segments as Array<Record<string, unknown>> | undefined) ?? undefined
    const rawSpeakerMap =
      (asRecord.speaker_mapping as Record<string, unknown> | undefined) ??
      (asRecord.speaker_map as Record<string, unknown> | undefined) ??
      (asRecord.speakerMap as Record<string, unknown> | undefined) ??
      undefined
    const speakerMap =
      rawSpeakerMap && typeof rawSpeakerMap === 'object'
        ? Object.fromEntries(
            Object.entries(rawSpeakerMap).map(([key, value]) => [key, typeof value === 'string' ? value : key])
          )
        : null
    if (Array.isArray(segments)) {
      const paragraphs = segments.map((seg, index) => ({
        paragraph_id: `seg_${index + 1}`,
        start_time: Number(seg.start_time ?? 0),
        end_time: Number(seg.end_time ?? 0),
        speaker: speakerMap
          ? String(speakerMap[String(seg.speaker ?? '')] ?? seg.speaker ?? 'Speaker')
          : String(seg.speaker ?? 'Speaker'),
        text: String(seg.text ?? ''),
      }))
      const duration = typeof asRecord.duration === 'number' ? asRecord.duration : undefined
      set({
        transcript: {
          task_id: String(asRecord.task_id ?? taskId),
          audio_duration: duration ?? 0,
          paragraphs,
        },
      })
      return
    }
    set({ transcript })
  },
  createTask: async (payload) => {
    const res = await createTask(payload)
    return res
  },
}))
