import { create } from 'zustand'
import type { UploadFile } from 'antd/es/upload/interface'
import type { PromptTemplate } from '@/types/frontend-types'

export interface UploadedAudio {
  uid: string
  name: string
  file_path: string
  speaker_id: string
  original_filename?: string
  duration?: number
}

interface CreateTaskDraftState {
  fileList: UploadFile[]
  uploads: UploadedAudio[]
  meeting_type: string
  output_language: string
  asr_languages: string[]
  skip_speaker_recognition: boolean
  description?: string
  template?: PromptTemplate
  setFileList: (files: UploadFile[]) => void
  addUpload: (payload: Omit<UploadedAudio, 'speaker_id'>) => void
  removeUpload: (uid: string) => void
  reorderUploads: (next: UploadedAudio[]) => void
  setUploadsWithFiles: (items: Array<Omit<UploadedAudio, 'speaker_id'>>) => void
  updateConfig: (payload: Partial<CreateTaskDraftConfig>) => void
  setTemplate: (template?: PromptTemplate) => void
  reset: () => void
}

type CreateTaskDraftConfig = Pick<
  CreateTaskDraftState,
  'meeting_type' | 'output_language' | 'asr_languages' | 'skip_speaker_recognition' | 'description' | 'template'
>

const withSpeakerIds = (items: UploadedAudio[]) =>
  items.map((item, index) => ({
    ...item,
    speaker_id: `speaker_${index + 1}`,
  }))

const reorderFileList = (fileList: UploadFile[], uploads: UploadedAudio[]) => {
  const byUid = new Map(fileList.map((file) => [file.uid, file]))
  const ordered = uploads
    .map((item) => byUid.get(item.uid))
    .filter((item): item is UploadFile => Boolean(item))
  const remaining = fileList.filter((file) => !uploads.find((item) => item.uid === file.uid))
  return [...ordered, ...remaining]
}

export const useCreateTaskDraftStore = create<CreateTaskDraftState>((set) => ({
  fileList: [],
  uploads: [],
  meeting_type: 'general',
  output_language: 'zh-CN',
  asr_languages: ['zh-CN', 'en-US'],
  skip_speaker_recognition: false,
  description: undefined,
  template: undefined,
  setFileList: (files) =>
    set((state) => {
      const ordered = files
        .map((file) => state.uploads.find((item) => item.uid === file.uid))
        .filter((item): item is UploadedAudio => Boolean(item))
      const nextUploads = ordered.length > 0 ? withSpeakerIds(ordered) : state.uploads
      return {
        fileList: files,
        uploads: nextUploads,
      }
    }),
  addUpload: (payload) =>
    set((state) => {
      const exists = state.uploads.find((item) => item.uid === payload.uid)
      if (exists) {
        return state
      }
      const merged = [...state.uploads, { ...payload, speaker_id: '' }]
      const ordered = state.fileList
        .map((file) => merged.find((item) => item.uid === file.uid))
        .filter((item): item is UploadedAudio => Boolean(item))
      const nextUploads = withSpeakerIds(ordered.length > 0 ? ordered : merged)
      return {
        uploads: nextUploads,
        fileList: reorderFileList(state.fileList, nextUploads),
      }
    }),
  removeUpload: (uid) =>
    set((state) => {
      const nextUploads = withSpeakerIds(state.uploads.filter((item) => item.uid !== uid))
      return {
        uploads: nextUploads,
        fileList: reorderFileList(state.fileList, nextUploads),
      }
    }),
  reorderUploads: (next) =>
    set((state) => {
      const nextUploads = withSpeakerIds(next)
      return {
        uploads: nextUploads,
        fileList: reorderFileList(state.fileList, nextUploads),
      }
    }),
  setUploadsWithFiles: (items) =>
    set(() => {
      const uploads = withSpeakerIds(items.map((item) => ({ ...item, speaker_id: '', original_filename: item.name })))
      const fileList = items.map(
        (item) =>
          ({
            uid: item.uid,
            name: item.name,
            status: 'done',
          }) as UploadFile
      )
      return {
        uploads,
        fileList,
      }
    }),
  updateConfig: (payload) =>
    set((state) => ({
      ...state,
      ...payload,
    })),
  setTemplate: (template) => set({ template }),
  reset: () =>
    set({
      fileList: [],
      uploads: [],
      meeting_type: 'general',
      output_language: 'zh-CN',
      asr_languages: ['zh-CN', 'en-US'],
      skip_speaker_recognition: false,
      description: undefined,
      template: undefined,
    }),
}))
