import { create } from 'zustand'
import {
  createTemplate,
  deleteTemplate,
  getTemplateDetail,
  listTemplates,
  updateTemplate,
} from '@/api/templates'
import type { PromptTemplate } from '@/types/frontend-types'

const DEFAULT_TEMPLATE_KEY = 'default_template_id'

interface TemplateState {
  templates: PromptTemplate[]
  loading: boolean
  keyword: string
  filterBy: string
  defaultTemplateId: string | null
  fetchTemplates: (userId?: string, tenantId?: string) => Promise<void>
  setKeyword: (kw: string) => void
  setFilter: (filter: string) => void
  setDefaultTemplateId: (templateId: string | null) => void
  filtered: () => PromptTemplate[]
  getDetail: (id: string) => Promise<PromptTemplate | null>
  create: (payload: Partial<PromptTemplate>, userId?: string) => Promise<void>
  update: (id: string, payload: Partial<PromptTemplate>, userId?: string) => Promise<void>
  remove: (id: string, userId?: string) => Promise<void>
}

export const useTemplateStore = create<TemplateState>((set, get) => ({
  templates: [],
  loading: false,
  keyword: '',
  filterBy: 'all',
  defaultTemplateId:
    typeof window !== 'undefined' ? window.localStorage.getItem(DEFAULT_TEMPLATE_KEY) : null,
  fetchTemplates: async (userId?: string, tenantId?: string) => {
    set({ loading: true })
    try {
      const res = await listTemplates(userId, tenantId)
      set({ templates: res.templates })
    } catch {
      set({ templates: [] })
    } finally {
      set({ loading: false })
    }
  },
  setKeyword: (kw) => set({ keyword: kw }),
  setFilter: (filter) => set({ filterBy: filter }),
  setDefaultTemplateId: (templateId) => {
    if (typeof window !== 'undefined') {
      if (templateId) {
        window.localStorage.setItem(DEFAULT_TEMPLATE_KEY, templateId)
      } else {
        window.localStorage.removeItem(DEFAULT_TEMPLATE_KEY)
      }
    }
    set({ defaultTemplateId: templateId })
  },
  filtered: () => {
    const { templates, keyword, filterBy } = get()
    return templates.filter((tpl) => {
      const matchKeyword =
        !keyword ||
        tpl.title.toLowerCase().includes(keyword.toLowerCase()) ||
        tpl.description.toLowerCase().includes(keyword.toLowerCase())
      const matchFilter = filterBy === 'all' ? true : tpl.scope === filterBy
      return matchKeyword && matchFilter
    })
  },
  getDetail: async (id) => {
    try {
      const res = await getTemplateDetail(id)
      return res.template
    } catch {
      const fallback = get().templates.find((t) => t.template_id === id)
      return fallback || null
    }
  },
  create: async (payload, userId) => {
    const body = {
      title: payload.title || 'ÐÂ½¨Ä£°å',
      prompt_body: payload.prompt_body || '',
      artifact_type: payload.artifact_type || 'meeting_minutes',
      description: payload.description || '',
      supported_languages: payload.supported_languages || ['zh-CN'],
      parameter_schema: payload.parameter_schema || {},
    }
    const res = await createTemplate(body, userId)
    set((state) => ({
      templates: [
        ...state.templates,
        {
          ...body,
          template_id: res.template_id,
          is_system: false,
          scope: 'private',
          created_at: new Date().toISOString(),
        } as PromptTemplate,
      ],
    }))
  },
  update: async (id, payload, userId) => {
    await updateTemplate(
      id,
      {
        title: payload.title,
        description: payload.description,
        prompt_body: payload.prompt_body,
      },
      userId
    )
  },
  remove: async (id, userId) => {
    await deleteTemplate(id, userId)
  },
}))
