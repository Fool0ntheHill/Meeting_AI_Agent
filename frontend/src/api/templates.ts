import { request } from './request'
import type {
  CreatePromptTemplateRequest,
  CreatePromptTemplateResponse,
  DeletePromptTemplateResponse,
  ListPromptTemplatesResponse,
  PromptTemplateDetailResponse,
  UpdatePromptTemplateRequest,
  UpdatePromptTemplateResponse,
} from '@/types/frontend-types'

export const listTemplates = (userId?: string, tenantId?: string) =>
  request<ListPromptTemplatesResponse>({
    url: '/prompt-templates',
    method: 'GET',
    params: {
      ...(userId ? { user_id: userId } : {}),
      ...(tenantId ? { tenant_id: tenantId } : {}),
    },
  })

export const getTemplateDetail = (templateId: string) =>
  request<PromptTemplateDetailResponse>({
    url: `/prompt-templates/${templateId}`,
    method: 'GET',
  })

export const createTemplate = (payload: CreatePromptTemplateRequest, userId?: string) =>
  request<CreatePromptTemplateResponse>({
    url: '/prompt-templates',
    method: 'POST',
    data: payload,
    params: userId ? { user_id: userId } : undefined,
  })

export const updateTemplate = (templateId: string, payload: UpdatePromptTemplateRequest, userId?: string) =>
  request<UpdatePromptTemplateResponse>({
    url: `/prompt-templates/${templateId}`,
    method: 'PUT',
    data: payload,
    params: userId ? { user_id: userId } : undefined,
  })

export const deleteTemplate = (templateId: string, userId?: string) =>
  request<DeletePromptTemplateResponse>({
    url: `/prompt-templates/${templateId}`,
    method: 'DELETE',
    params: userId ? { user_id: userId } : undefined,
  })
