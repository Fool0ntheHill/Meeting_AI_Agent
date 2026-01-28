import { request } from './request'

export interface FolderItem {
  id: string
  name: string
  parent_id: string | null
  created_at?: string
  updated_at?: string
}

export interface CreateFolderRequest {
  name: string
  parent_id?: string | null
}

export interface UpdateFolderRequest {
  name?: string
  parent_id?: string | null
}

export const listFolders = () =>
  request<{ items?: FolderItem[]; total?: number } | FolderItem[]>({
    url: '/folders',
    method: 'GET',
  })

export const createFolder = (data: CreateFolderRequest) =>
  request<FolderItem>({
    url: '/folders',
    method: 'POST',
    data,
  })

export const updateFolder = (id: string, data: UpdateFolderRequest) =>
  request<FolderItem>({
    url: `/folders/${id}`,
    method: 'PATCH',
    data,
  })

export const deleteFolder = (id: string) =>
  request<{ success: boolean }>({
    url: `/folders/${id}`,
    method: 'DELETE',
  })
