import { create } from 'zustand'
import { getArtifactDetail, listArtifacts, regenerateArtifact } from '@/api/artifacts'
import type {
  ArtifactDetailResponse,
  GenerateArtifactRequest,
  GenerateArtifactResponse,
  ListArtifactsResponse,
} from '@/types/frontend-types'

interface ArtifactState {
  list: ListArtifactsResponse | null
  current: ArtifactDetailResponse | null
  parsedContent: Record<string, unknown> | null
  parsedContentById: Record<string, Record<string, unknown> | null>
  currentArtifactId: string | null
  loading: boolean
  fetchList: (taskId: string) => Promise<void>
  fetchDetail: (artifactId: string) => Promise<ArtifactDetailResponse>
  regenerate: (taskId: string, artifactType: string, payload: GenerateArtifactRequest) => Promise<GenerateArtifactResponse>
}

export const useArtifactStore = create<ArtifactState>((set) => ({
  list: null,
  current: null,
  parsedContent: null,
  parsedContentById: {},
  currentArtifactId: null,
  loading: false,
  fetchList: async (taskId) => {
    set({ loading: true, list: null, current: null, parsedContent: null, parsedContentById: {}, currentArtifactId: null })
    try {
      const data = await listArtifacts(taskId)
      const mapped = {
        ...data,
        artifacts_by_type: Object.fromEntries(
          Object.entries(data.artifacts_by_type || {}).map(([key, arr]) => [
            key,
            (arr || []).map((item) => ({
              ...item,
              task_id: (item as any).task_id ?? taskId,
            })),
          ])
        ),
      }
      set({ list: mapped })
    } finally {
      set({ loading: false })
    }
  },
  fetchDetail: async (artifactId) => {
    const data = await getArtifactDetail(artifactId)
    const artifact = (data as { data?: unknown; artifact?: unknown }).artifact ?? data
    let parsed: Record<string, unknown> | null = null

    // 新版后端契约：artifact.data.content 为 markdown 字符串
    const asRecord = artifact as Record<string, unknown>
    const dataField = (asRecord.data ?? null) as Record<string, unknown> | null
    const markdownDirect =
      (dataField && typeof dataField.content === 'string' && dataField.content.trim()) || null

    if (markdownDirect) {
      parsed = { content: markdownDirect, title: (dataField?.title as string) || '' }
    } else {
      // 兼容旧格式：artifact.content
      try {
        if (asRecord.content && typeof asRecord.content === 'string') {
          const maybe = JSON.parse(asRecord.content)
          parsed = typeof maybe === 'string' ? { content: maybe } : (maybe as Record<string, unknown>)
        } else if (asRecord.content && typeof asRecord.content === 'object') {
          parsed = asRecord.content as Record<string, unknown>
        }
      } catch {
        parsed = null
      }
    }

    set((prev) => ({
      current: { artifact: artifact as any },
      parsedContent: parsed,
      currentArtifactId: artifactId,
      parsedContentById: { ...(prev.parsedContentById || {}), [artifactId]: parsed },
    }))

    return { artifact: artifact as any }
  },
  regenerate: async (taskId, artifactType, payload) => {
    const res = await regenerateArtifact(taskId, artifactType || 'meeting_minutes', payload)
    return res
  },
}))
