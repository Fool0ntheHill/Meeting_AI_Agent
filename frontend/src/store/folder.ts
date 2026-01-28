import { create } from 'zustand'
import { createFolder, deleteFolder, listFolders, updateFolder } from '@/api/folders'
import { message } from 'antd'
import type { FolderItem } from '@/api/folders'

interface FolderState {
  folders: Array<FolderItem & { id: string }>
  loading: boolean
  fetch: () => Promise<void>
  add: (name: string, parent_id?: string | null) => Promise<void>
  rename: (id: string, name: string) => Promise<void>
  remove: (id: string) => Promise<void>
}

type RawFolderItem = Partial<FolderItem> & {
  folder_id?: string
  id?: string
}

const normalizeFolder = (item: RawFolderItem): FolderItem & { id: string; folder_id: string } => {
  const folderId = typeof item.folder_id === 'string' ? item.folder_id : typeof item.id === 'string' ? item.id : ''
  return {
    id: folderId,
    folder_id: folderId,
    name: item.name ?? '',
    parent_id: item.parent_id ?? null,
    created_at: item.created_at,
    updated_at: item.updated_at,
  }
}

export const useFolderStore = create<FolderState>((set, get) => ({
  folders: [],
  loading: false,
  fetch: async () => {
    set({ loading: true })
    try {
      const res = await listFolders()
      const itemsRaw: RawFolderItem[] = Array.isArray(res) ? res : Array.isArray(res?.items) ? res.items : []
      const items = itemsRaw.map((f) => normalizeFolder(f))
      set({ folders: items })
    } catch {
      message.error('获取文件夹失败')
      set({ folders: [] })
    } finally {
      set({ loading: false })
    }
  },
  add: async (name, parent_id = null) => {
    await createFolder({ name, parent_id })
    await get().fetch()
  },
  rename: async (id, name) => {
    await updateFolder(id, { name })
    await get().fetch()
  },
  remove: async (id) => {
    await deleteFolder(id)
    await get().fetch()
  },
}))
