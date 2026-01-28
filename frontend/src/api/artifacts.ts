import { request } from './request'
import type {
  ArtifactDetailResponse,
  ArtifactStatusResponse,
  GenerateArtifactRequest,
  GenerateArtifactResponse,
  ListArtifactsResponse,
  DeleteArtifactResponse,
  RenameArtifactRequest,
  RenameArtifactResponse,
} from '@/types/frontend-types'

export const listArtifacts = (taskId: string) =>
  request<ListArtifactsResponse>({
    url: `/tasks/${taskId}/artifacts`,
    method: 'GET',
  })

export const getArtifactDetail = (artifactId: string) =>
  request<ArtifactDetailResponse>({
    url: `/artifacts/${artifactId}`,
    method: 'GET',
  })

export const regenerateArtifact = (taskId: string, artifactType: string, payload: GenerateArtifactRequest) =>
  request<GenerateArtifactResponse>({
    url: `/tasks/${taskId}/artifacts/${artifactType}/generate`,
    method: 'POST',
    data: payload,
    timeout: 60000, // 异步生成接口快速返回，1 分钟兜底
  })

export const updateArtifact = (artifactId: string, content: string) =>
  request<ArtifactDetailResponse>({
    url: `/artifacts/${artifactId}`,
    method: 'PUT',
    data: { content },
  })

export const renameArtifact = (artifactId: string, payload: RenameArtifactRequest) =>
  request<RenameArtifactResponse>({
    url: `/artifacts/${artifactId}`,
    method: 'PATCH',
    data: payload,
  })

export const deleteArtifact = (taskId: string, artifactId: string) =>
  request<DeleteArtifactResponse>({
    url: `/tasks/${taskId}/artifacts/${artifactId}`,
    method: 'DELETE',
  })

export const getArtifactStatus = (artifactId: string) =>
  request<ArtifactStatusResponse>({
    url: `/artifacts/${artifactId}/status`,
    method: 'GET',
  })
