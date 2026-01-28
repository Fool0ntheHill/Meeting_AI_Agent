import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Drawer, Dropdown, Input, Modal, Tabs, Tooltip, Typography, message, Spin } from 'antd'
import {
  DeleteOutlined,
  DislikeOutlined,
  DownOutlined,
  EditOutlined,
  LikeOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  RedoOutlined,
  FormOutlined,
  BookOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Group, Panel, Separator } from 'react-resizable-panels'

import { useTaskStore } from '@/store/task'
import { useFolderStore } from '@/store/folder'
import { useArtifactStore } from '@/store/artifact'
import { correctSpeakers, correctTranscript } from '@/api/tasks'
import { updateArtifact, deleteArtifact, getArtifactStatus, renameArtifact } from '@/api/artifacts'
import type VditorType from 'vditor'
import { useTemplateStore } from '@/store/template'
import { useAuthStore } from '@/store/auth'
import { ENV } from '@/config/env'
import MarkdownEditor from '@/components/MarkdownEditor'
import TaskConfigForm, { type CreateTaskFormValues } from '@/components/TaskConfigForm'
import type { Template } from '@/store/template'
import TemplateEditorModal from '@/components/TemplateEditorModal'

import FileSidebar from './components/FileSidebar'
import AudioPlayer, { type AudioPlayerRef } from './components/AudioPlayer'
import TranscriptEditor from './components/TranscriptEditor'
import ActionFooter from './components/ActionFooter'
import './workspace.css'

const PROMPT_OVERRIDE_KEY = 'artifact_prompt_overrides'

type PromptOverride = {
  prompt_body: string
  title?: string
  description?: string
  template_id?: string
}

type ConfigMode = 'create' | 'regenerate'

const renderMinutes = (raw: Record<string, unknown> | Array<Record<string, unknown>>) => {
  // 已在 store 层优先解析 data.content（markdown），此处只兜底旧格式
  const content = Array.isArray(raw) ? raw[0] || {} : raw

  const summary =
    content.summary ?? content['会议概要'] ?? content['会议总结'] ?? content['会议纪要'] ?? content['概述'] ?? ''
  const title = content.title ?? content['会议标题'] ?? content['标题'] ?? '纪要'
  const rawKeyPoints =
    content.key_points ??
    content['讨论要点'] ??
    content['关键要点'] ??
    content['要点'] ??
    content['决策事项'] ??
    content['决策'] ??
    []
  const rawActionItems =
    content.action_items ?? content['行动项'] ?? content['待办事项'] ?? content['待办'] ?? []
  const normalizeList = (value: unknown) => {
    if (Array.isArray(value)) return value
    if (typeof value === 'string') {
      return value
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean)
    }
    return []
  }
  const keyPoints = normalizeList(rawKeyPoints)
  const actionItems = normalizeList(rawActionItems)
  return `# ${String(title)}

${String(summary || '')}

## 关键要点
${keyPoints.map((p) => `- ${String(p)}`).join('\n')}

## 行动项
${actionItems.map((p) => `- [ ] ${String(p)}`).join('\n')}
`
}

const resolveMarkdown = (raw: Record<string, unknown> | Array<Record<string, unknown>> | null) => {
  if (!raw) return ''
  const obj = Array.isArray(raw) ? (raw[0] as Record<string, unknown> | undefined) ?? {} : raw
  if (!obj || (typeof obj === 'object' && Object.keys(obj).length === 0)) return ''
  // 后端占位/失败提示
  if (typeof obj.status === 'string') {
    const msg = (obj as any).message || (obj as any).error_message || ''
    return msg ? String(msg) : `状态：${obj.status}`
  }
  const direct =
    (typeof obj.content === 'string' && obj.content.trim()) ||
    (typeof obj.markdown === 'string' && obj.markdown.trim())
  if (direct) return direct

  // 没有内容字段且缺少关键信息时，不再渲染默认模板
  const hasStructuredContent =
    obj.summary || obj.title || obj.key_points || obj.action_items || obj['会议概要'] || obj['讨论要点']
  if (!hasStructuredContent) return ''
  return renderMinutes(obj)
}

const inlineImages = async (content: string) => {
  const imageRegex = /!\[([^\]]*)]\(([^)]+)\)/g
  const matches = [...content.matchAll(imageRegex)]
  if (matches.length === 0) return content

  const cache = new Map<string, string>()
  const toDataUrl = async (url: string) => {
    if (cache.has(url)) return cache.get(url) as string
    if (url.startsWith('data:')) {
      cache.set(url, url)
      return url
    }
    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error('fetch failed')
      const blob = await res.blob()
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result as string)
        reader.onerror = () => reject(new Error('reader failed'))
        reader.readAsDataURL(blob)
      })
      cache.set(url, dataUrl)
      return dataUrl
    } catch {
      return url
    }
  }

  let result = content
  for (const match of matches) {
    const alt = match[1]
    const url = match[2]
    const dataUrl = await toDataUrl(url)
    result = result.replace(match[0], `![${alt}](${dataUrl})`)
  }
  return result
}

const markdownToBasicHtml = (md: string) => {
  // 仅做基础转换，保证粘贴时图片可见
  let html = md
  html = html.replace(/!\[([^\]]*)]\(([^)]+)\)/g, (_m, alt, src) => {
    const safeAlt = (alt as string) || ''
    return `<img src="${src}" alt="${safeAlt}" style="max-width:100%;height:auto;" />`
  })
  // 保留换行
  html = html.replace(/\n{2,}/g, '<br/><br/>').replace(/\n/g, '<br/>')
  return `<div>${html}</div>`
}

const buildWatermarkHtml = (username?: string | null) => {
  const now = new Date()
  const timeStr = now.toLocaleString('zh-CN', { hour12: false })
  const owner = username || '未指定'
  const line = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
  return [
    `<p style="margin: 0;"><b style="color: #d97373;">${line}</b></p>`,
    `<p style="margin: 5px 0;"><b>生成时间：</b>${timeStr}</p>`,
    `<p style="margin: 5px 0;"><b>责任人：</b>${owner}</p>`,
    `<p style="margin: 5px 0;"><b style="color: #d97373;">AI 声明：</b><span style="color: #d97373;">本纪要初稿由 AI 模型生成，已由责任人校对确认。</span></p>`,
    `<p style="margin: 0 0 20px 0;"><b style="color: #d97373;">${line}</b></p>`,
  ].join('')
}

const MoveFolderIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path d="M3 7.5h7l1.8-2h9.2a1 1 0 0 1 1 1v10.5a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8.5a1 1 0 0 1 1-1z" />
    <path d="M10 14h6m0 0-2-2m2 2-2 2" />
  </svg>
)

const FindReplaceIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6">
    <circle cx="10" cy="10" r="6" />
    <path d="M14.5 14.5L20 20" />
    <path d="M16 6h4m0 0-1.5-1.5M20 6l-1.5 1.5" />
    <path d="M16 10h4m0 0-1.5-1.5M20 10l-1.5 1.5" />
  </svg>
)

const Workspace = () => {
  const { id } = useParams<{ id: string }>()
  const { username, userId, tenantId } = useAuthStore()
  const { fetchDetail, currentTask, fetchTranscript, transcript } = useTaskStore()
  const {
    fetchList,
    fetchDetail: fetchArtifactDetail,
    list,
    parsedContentById,
    currentArtifactId,
    regenerate,
    current: currentArtifactDetail,
  } = useArtifactStore()
  const { folders, fetch: fetchFolders } = useFolderStore()
  const { getDetail: getTemplateDetail, create: createTemplate, templates, fetchTemplates } = useTemplateStore()

  const audioPlayerRef = useRef<AudioPlayerRef>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [paragraphs, setParagraphs] = useState(transcript?.paragraphs || [])
  const [activeArtifact, setActiveArtifact] = useState<string | undefined>(undefined)
  const [mode, setMode] = useState<'preview' | 'edit'>('preview')
  const [markdownByArtifact, setMarkdownByArtifact] = useState<Record<string, string>>({})
  const [dirtyByArtifact, setDirtyByArtifact] = useState<Record<string, boolean>>({})
  const [allowTrain, setAllowTrain] = useState(false)
  const [isConfirmed, setIsConfirmed] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [transcriptDirty, setTranscriptDirty] = useState(false)
  const [transcriptStatus, setTranscriptStatus] = useState<'saved' | 'saving' | 'error'>('saved')
  const [artifactStatus, setArtifactStatus] = useState<Record<string, 'saved' | 'saving' | 'error'>>({})
  const [promptModalOpen, setPromptModalOpen] = useState(false)
  const [promptTemplate, setPromptTemplate] = useState<Template | null>(null)
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false)
  const [localTemplate, setLocalTemplate] = useState<Template | null>(null)
  const [speakerMap, setSpeakerMap] = useState<Record<string, string>>({})
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const [artifactNameOverrides, setArtifactNameOverrides] = useState<Record<string, string>>({})
  const [pendingArtifacts, setPendingArtifacts] = useState<Record<string, { name: string; artifact_type: string }>>({})
  const [promptOverrides, setPromptOverrides] = useState<Record<string, PromptOverride>>(() => {
    if (typeof window === 'undefined') return {}
    try {
      return JSON.parse(window.localStorage.getItem(PROMPT_OVERRIDE_KEY) || '{}') as Record<string, PromptOverride>
    } catch {
      return {}
    }
  })
  const [configMode, setConfigMode] = useState<ConfigMode>('regenerate')
  const [configFormKey, setConfigFormKey] = useState(0)
  const [hiddenArtifacts, setHiddenArtifacts] = useState<Set<string>>(new Set())
  const [syncedArtifacts, setSyncedArtifacts] = useState<Set<string>>(new Set())
  const [activeEditor, setActiveEditor] = useState<'transcript' | 'artifact' | null>(null)
  const [transcriptHistory, setTranscriptHistory] = useState<{ past: TranscriptParagraph[][]; future: TranscriptParagraph[][] }>({
    past: [],
    future: [],
  })
  const [artifactFeedback, setArtifactFeedback] = useState<Record<string, 'like' | 'dislike' | null>>({})
  const [transcriptFeedback, setTranscriptFeedback] = useState<Record<string, 'like' | 'dislike' | null>>({})
  const transcriptHistoryTimer = useRef<number | null>(null)
  const transcriptSnapshotRef = useRef<TranscriptParagraph[]>([])
  const statusTimersRef = useRef<Record<string, number>>({})
  const applyingHistoryRef = useRef(false)
  const paragraphsRef = useRef<TranscriptParagraph[]>(paragraphs)
  const reviewContentRef = useRef<HTMLDivElement>(null)
  const reviewOutlineRef = useRef<HTMLDivElement>(null)
  const vditorRef = useRef<VditorType | null>(null)
  const resolvePromptTitle = useCallback(
    (tplId?: string, metaTitle?: string, edited?: boolean) => {
      const normalizedId = (tplId || '').trim()
      const normalizedMeta = (metaTitle || '').trim()
      const found = tplId ? templates.find((tpl) => tpl.template_id === tplId) : null
      const base =
        (normalizedMeta && normalizedMeta.toLowerCase() !== '__blank__' ? normalizedMeta : undefined) ||
        found?.title ||
        (normalizedId.toLowerCase() === '__blank__' ? '临时空白模板' : normalizedId || '临时提示词')
      return edited ? `${base}（修改版）` : base
    },
    [templates]
  )

  const syncPromptOverride = useCallback(
    (artifactId: string, artifactData: any) => {
      const metaPrompt = (artifactData?.metadata as any)?.prompt
      const promptText =
        (metaPrompt?.prompt_text as string | undefined) ??
        (artifactData?.prompt_instance?.prompt_text as string | undefined)
      if (!promptText) return
      setPromptOverrides((prev) => ({
        ...prev,
        [artifactId]: {
          prompt_body: String(promptText),
          title: metaPrompt?.title || undefined,
          description: metaPrompt?.description || '',
          template_id: metaPrompt?.template_id || artifactData?.prompt_instance?.template_id,
        },
      }))
    },
    []
  )

  useEffect(() => {
    // 切换任务时重置当前 artifact 相关状态，避免串任务
    setActiveArtifact(undefined)
    setMarkdownByArtifact({})
    setDirtyByArtifact({})
    setArtifactStatus({})
    setArtifactNameOverrides({})
    setHiddenArtifacts(new Set())
    setSyncedArtifacts(new Set())
    setArtifactFeedback({})
    setTranscriptFeedback({})
  }, [id])

  useEffect(() => {
    if (!id) return
    fetchDetail(id)
    fetchTranscript(id)
    void fetchList(id)
  }, [id, fetchDetail, fetchTranscript, fetchList])

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.setItem(PROMPT_OVERRIDE_KEY, JSON.stringify(promptOverrides))
    } catch {
      // ignore
    }
  }, [promptOverrides])

  useEffect(() => {
    if (folders.length === 0) {
      void fetchFolders()
    }
  }, [fetchFolders, folders.length])

  useEffect(() => {
    if (transcript) {
      setParagraphs(transcript.paragraphs)
      transcriptSnapshotRef.current = cloneParagraphs(transcript.paragraphs)
      setTranscriptHistory({ past: [], future: [] })
      setIsDirty(false)
      setIsConfirmed(false)
      setSpeakerMap({})
      setTranscriptDirty(false)
      setTranscriptStatus('saved')
      setSyncedArtifacts((prev) => {
        const next = new Set(prev)
        if (activeArtifact) next.delete(activeArtifact)
        return next
      })
    }
  }, [transcript, activeArtifact])

  useEffect(() => {
    const parsed = activeArtifact ? parsedContentById[activeArtifact] : null
    if (!parsed || !activeArtifact) return
    if (syncedArtifacts.has(activeArtifact)) return
    const next = resolveMarkdown(parsed)
    setMarkdownByArtifact((prev) => {
      if (prev[activeArtifact] === next) return prev
      return { ...prev, [activeArtifact]: next }
    })
    setSyncedArtifacts((prev) => {
      const nextSet = new Set(prev)
      nextSet.add(activeArtifact)
      return nextSet
    })
    setIsDirty(false)
    setIsConfirmed(false)
  }, [parsedContentById, activeArtifact, syncedArtifacts])

  useEffect(() => {
    if (!activeArtifact) return
    setIsDirty(Boolean(dirtyByArtifact[activeArtifact]))
  }, [activeArtifact, dirtyByArtifact])

  const artifactTabs = useMemo(() => {
    const base: Array<{
      key: string
      label: React.ReactNode
      artifact: any
      isDefaultMinutes: boolean
      processing?: boolean
    }> = []
    if (!list) {
      // 当列表未加载时，也允许展示 pending 占位
      Object.entries(pendingArtifacts).forEach(([id, info]) => {
        base.push({
          key: id,
          label: info.name || '生成中',
          artifact: { artifact_id: id, artifact_type: info.artifact_type },
          isDefaultMinutes: false,
          processing: true,
        })
      })
      return base
    }

    const typeLabelMap: Record<string, string> = {
      meeting_minutes: '纪要',
      summary_notes: '摘要',
      action_items: '行动项',
    }

    const entries = Object.values(list.artifacts_by_type)
      .flat()
      .map((item) => ({
        ...item,
        task_id: (item as any).task_id ?? id,
      }))
      .filter((item) => {
        const taskId = (item as { task_id?: string }).task_id
        if (!taskId) return true
        return taskId === id
      })
      .filter((item) => !hiddenArtifacts.has(item.artifact_id))

    // 按 display_name 分组重新计算版本号
    const groups = new Map<string, typeof entries>()
    const getCreated = (it: any) => {
      const ts = new Date(it.created_at || '').getTime()
      if (Number.isFinite(ts) && ts > 0) return ts
      // fallback: use backend version to keep顺序，新版在后
      return (it.version ?? 0) * 1000
    }
    const keyFor = (it: any) =>
      (
        (it as any).name?.trim() ||
        it.display_name?.trim() ||
        (it.artifact_type ? typeLabelMap[it.artifact_type] || it.artifact_type : undefined) ||
        (it.artifact_type === 'meeting_minutes' ? currentTask?.meeting_type : undefined) ||
        'artifact'
      ).trim()

    // 排序整体，确保时间顺序稳定
    const sorted = [...entries].sort((a, b) => getCreated(a) - getCreated(b))
    sorted.forEach((item) => {
      const key = keyFor(item)
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)?.push(item)
    })

    const result: Array<{
      key: string
      label: React.ReactNode
      artifact: any
      isDefaultMinutes: boolean
      processing?: boolean
    }> = []

    const defaultMinutesName = '纪要'
    Array.from(groups.entries()).forEach(([groupKey, arr]) => {
      const group = [...arr].sort((a, b) => getCreated(a) - getCreated(b))
      group.forEach((item, idx) => {
        const computedVersion = item.version ?? idx + 1
        const overrideName = artifactNameOverrides[item.artifact_id]
        const baseName =
          overrideName ||
          item.display_name?.trim() ||
          (item as any).name?.trim() ||
          groupKey ||
          (item.artifact_type ? typeLabelMap[item.artifact_type] || item.artifact_type : undefined) ||
          (item.artifact_type === 'meeting_minutes' ? currentTask?.meeting_type : undefined) ||
          'artifact'
        const label =
          computedVersion === 1 ? baseName : `${baseName} v${computedVersion}`
        const resolvedName = (item.display_name?.trim() || baseName).trim()
        const isDefaultMinutes = computedVersion === 1 && resolvedName === defaultMinutesName
        result.push({
          key: item.artifact_id,
          label,
          artifact: { ...item, computed_version: computedVersion },
          isDefaultMinutes,
          processing: (item as any).state === 'processing',
        })
      })
    })

    return result
      // 追加 pending 占位（尚未出现在列表里的）
      Object.entries(pendingArtifacts).forEach(([id, info]) => {
        const exists = result.some((r) => r.key === id)
        if (!exists) {
          result.push({
            key: id,
            label: info.name || '生成中',
            artifact: { artifact_id: id, artifact_type: info.artifact_type },
            isDefaultMinutes: false,
            processing: true,
          })
        }
      })

    // 如果当前激活的是待生成的占位，也确保被渲染出来
    if (
      activeArtifact &&
      pendingArtifacts[activeArtifact] &&
      !result.some((r) => r.key === activeArtifact)
    ) {
      const info = pendingArtifacts[activeArtifact]
      result.push({
        key: activeArtifact,
        label: info.name || '生成中',
        artifact: { artifact_id: activeArtifact, artifact_type: info.artifact_type },
        isDefaultMinutes: false,
        processing: true,
      })
    }

    return result
  }, [list, artifactNameOverrides, hiddenArtifacts, id, pendingArtifacts, activeArtifact])


  useEffect(() => {
    if (!list) return
    const entries = Object.values(list.artifacts_by_type).flat()
    const filtered = entries.filter((item) => {
      const taskId = (item as { task_id?: string }).task_id
      if (!taskId) return true
      return taskId === id
    })
    // 如果当前激活的 artifact 仍在 pending，占位即可，无需切走
    if (activeArtifact && pendingArtifacts[activeArtifact]) return
    if (filtered.length === 0) return
    const currentActive = filtered.find((item) => item.artifact_id === activeArtifact)
    const next = currentActive ?? filtered[0]
    if (!activeArtifact || !currentActive || activeArtifact !== next.artifact_id) {
      setActiveArtifact(next.artifact_id)
      setSyncedArtifacts(new Set())
      void fetchArtifactDetail(next.artifact_id).then((res) => {
        const artifactData = (res as any)?.artifact ?? res
        if (artifactData) syncPromptOverride(next.artifact_id, artifactData)
      })
    }
  }, [list, id, activeArtifact, fetchArtifactDetail, syncPromptOverride, pendingArtifacts])

  const activeArtifactInfo = useMemo(
    () => artifactTabs.find((tab) => tab.key === activeArtifact)?.artifact,
    [artifactTabs, activeArtifact]
  )

  // 当列表里已经有对应 artifact 时，清理 pending，占位避免重复
  useEffect(() => {
    if (!list) return
    const existingIds = new Set<string>()
    Object.values(list.artifacts_by_type || {}).forEach((arr) => {
      arr?.forEach((item) => existingIds.add(item.artifact_id))
    })
    setPendingArtifacts((prev) =>
      Object.fromEntries(Object.entries(prev).filter(([id]) => !existingIds.has(id)))
    )
  }, [list])

  const initialConfigValues: Partial<CreateTaskFormValues> = useMemo(() => {
    const metaPrompt = (activeArtifactInfo?.metadata as any)?.prompt
    const stripVersion = (name?: string) => (name ? name.replace(/\s*v\d+$/i, '').trim() : '')
    const tabLabel = artifactTabs.find((tab) => tab.key === activeArtifact)?.label
    const baseName =
      stripVersion(
        artifactNameOverrides[activeArtifact || ''] ||
          activeArtifactInfo?.display_name ||
          tabLabel ||
          activeArtifactInfo?.artifact_type
      ) ||
      (activeArtifactInfo?.artifact_type === 'meeting_minutes' ? '纪要' : activeArtifactInfo?.artifact_type) ||
      currentTask?.meeting_type ||
      '纪要'

    const meetingName = baseName || '纪要'

    // 创建新笔记时不预填名称/模板，避免默认“纪要”或沿用上一个模板
    if (configMode === 'create') {
      return {
        meeting_type: '',
        output_language: currentTask?.output_language,
        asr_languages: currentTask?.asr_language ? currentTask.asr_language.split('+') : [],
        skip_speaker_recognition: false,
        description: '',
        template_id: undefined,
      }
    }

    if (!currentTask) return { meeting_type: meetingName }

    return {
      meeting_type: meetingName,
      output_language: currentTask.output_language,
      asr_languages: currentTask.asr_language ? currentTask.asr_language.split('+') : [],
      skip_speaker_recognition: false,
      description: '',
      template_id:
        localTemplate?.template_id ||
        metaPrompt?.template_id ||
        activeArtifactInfo?.prompt_instance?.template_id ||
        (metaPrompt?.template_id === '__blank__' ? '__blank__' : undefined),
      prompt_text:
        localTemplate?.prompt_body ||
        metaPrompt?.prompt_text ||
        (metaPrompt?.template_id === '__blank__' ? metaPrompt?.prompt_body : undefined) ||
        activeArtifactInfo?.prompt_instance?.prompt_text ||
        activeArtifactInfo?.prompt_instance?.prompt_body ||
        undefined,
    }
  }, [currentTask, activeArtifactInfo, activeArtifact, artifactTabs, artifactNameOverrides, configMode])

  // 将待生成的占位与已有 tabs 合并，确保无刷新也可见
    const displayTabs = useMemo(() => {
      const seen = new Set<string>()
      const items = artifactTabs.map((tab) => {
        seen.add(tab.key)
        return tab
      })
      Object.entries(pendingArtifacts).forEach(([id, info]) => {
        if (seen.has(id)) return
        items.push({
          key: id,
          label: info.name || '生成中',
          artifact: { artifact_id: id, artifact_type: info.artifact_type },
          isDefaultMinutes: false,
          processing: true,
        })
        seen.add(id)
      })
      // activeArtifact 若已在 pendingArtifacts 中，前面的循环已经加入并标记 seen，不再重复追加
      return items
    }, [artifactTabs, pendingArtifacts, activeArtifact])

  const listFilter = useMemo(() => new URLSearchParams(location.search).get('folder'), [location.search])
  const editorToolbar = useMemo(
    () => ['headings', 'list', 'ordered-list', 'check', 'quote', 'code', '|', 'undo', 'redo'],
    []
  )
  const audioUrl = useMemo(() => {
    const file = currentTask?.audio_files?.[0]
    if (!file) return undefined
    if (/^https?:\/\//i.test(file)) return file
    const base = ENV.API_BASE_URL.replace(/\/$/, '')
    return `${base}/${String(file).replace(/^\/+/, '')}`
  }, [currentTask?.audio_files])

  const markDirty = () => {
    if (!isDirty) {
      setIsDirty(true)
    }
    if (isConfirmed) {
      setIsConfirmed(false)
    }
  }

  const pollArtifactStatus = useCallback(
    (artifactId: string) => {
      if (!artifactId) return
      // 确保占位存在并切换到它
      setPendingArtifacts((prev) => {
        if (prev[artifactId]) return prev
        return {
          ...prev,
          [artifactId]: { name: '生成中', artifact_type: 'meeting_minutes' },
        }
      })
      setActiveArtifact((prev) => prev || artifactId)
      const tick = async () => {
        try {
          const status = await getArtifactStatus(artifactId)
          if (status.state === 'processing') {
            statusTimersRef.current[artifactId] = window.setTimeout(tick, 2000)
            return
          }
          if (status.state === 'failed') {
            message.error(status.error?.message || '生成失败')
          } else {
            message.success('生成成功')
          }
          if (id) {
            await fetchList(id)
          }
          setPendingArtifacts((prev) => {
            const next = { ...prev }
            delete next[artifactId]
            return next
          })
        } catch (error) {
          // 网络波动重试
          statusTimersRef.current[artifactId] = window.setTimeout(tick, 3000)
        }
      }
      tick()
    },
    [fetchList, id]
  )

  const cloneParagraphs = useCallback((items: TranscriptParagraph[]) => items.map((p) => ({ ...p })), [])

  const pushTranscriptHistory = useCallback(
    (nextParagraphs: TranscriptParagraph[]) => {
      if (applyingHistoryRef.current) return
      const snapshot = cloneParagraphs(nextParagraphs)
      const last = transcriptSnapshotRef.current
      if (last.length === snapshot.length && last.every((p, idx) => p.text === snapshot[idx].text && p.speaker === snapshot[idx].speaker)) {
        return
      }
      setTranscriptHistory((prev) => {
        const past = [...prev.past, cloneParagraphs(last)].slice(-50)
        return { past, future: [] }
      })
      transcriptSnapshotRef.current = snapshot
    },
    [cloneParagraphs]
  )

  const scheduleTranscriptHistory = useCallback(
    (nextParagraphs: TranscriptParagraph[]) => {
      if (transcriptHistoryTimer.current) {
        window.clearTimeout(transcriptHistoryTimer.current)
      }
      transcriptHistoryTimer.current = window.setTimeout(() => pushTranscriptHistory(nextParagraphs), 300)
    },
    [pushTranscriptHistory]
  )

  const handleUpdateParagraph = (id: string, text: string) => {
    setParagraphs((prev) => {
      const updated = prev.map((p) => (p.paragraph_id === id ? { ...p, text } : p))
      scheduleTranscriptHistory(updated)
      return updated
    })
    setTranscriptDirty(true)
    markDirty()
  }

  const handleRenameSpeaker = (from: string, to: string, scope: 'single' | 'global', pid?: string) => {
    if (scope === 'single' && pid) {
      setParagraphs((prev) => {
        const updated = prev.map((p) => (p.paragraph_id === pid ? { ...p, speaker: to } : p))
        scheduleTranscriptHistory(updated)
        return updated
      })
    } else {
      setParagraphs((prev) => {
        const updated = prev.map((p) => (p.speaker === from ? { ...p, speaker: to } : p))
        scheduleTranscriptHistory(updated)
        return updated
      })
      setSpeakerMap((prev) => ({ ...prev, [from]: to }))
    }
    setTranscriptDirty(true)
    markDirty()
  }

  const saveTranscript = useCallback(async () => {
    if (!id) return
    const text = paragraphs.map((p) => `[${p.speaker}] ${p.text}`).join('\n')
    const segments = paragraphs.map((p) => ({
      text: p.text,
      start_time: p.start_time,
      end_time: p.end_time,
      speaker: p.speaker,
      confidence: (p as any).confidence,
    }))
    setTranscriptStatus('saving')
    try {
      await correctTranscript(id, { corrected_text: text, segments, regenerate_artifacts: false })
      if (Object.keys(speakerMap).length > 0) {
        await correctSpeakers(id, { speaker_mapping: speakerMap, segments, regenerate_artifacts: false })
      }
      transcriptSnapshotRef.current = cloneParagraphs(paragraphs)
      setTranscriptDirty(false)
      setTranscriptStatus('saved')
    } catch (err) {
    setTranscriptStatus('error')
      message.error((err as Error)?.message || '保存失败')
    }
  }, [id, paragraphs, speakerMap, cloneParagraphs])

  useEffect(() => {
    if (!transcriptDirty) return
    const timer = setTimeout(() => {
      void saveTranscript()
    }, 1000)
    return () => clearTimeout(timer)
  }, [transcriptDirty, paragraphs, speakerMap, saveTranscript])

  const saveArtifact = useCallback(
    async (artifactId: string) => {
      const content = markdownByArtifact[artifactId] ?? ''
      setArtifactStatus((prev) => ({ ...prev, [artifactId]: 'saving' }))
      try {
        await updateArtifact(artifactId, content)
        setDirtyByArtifact((prev) => ({ ...prev, [artifactId]: false }))
        setArtifactStatus((prev) => ({ ...prev, [artifactId]: 'saved' }))
        setSyncedArtifacts((prev) => {
          const next = new Set(prev)
          next.add(artifactId)
          return next
        })
      } catch (err) {
        setArtifactStatus((prev) => ({ ...prev, [artifactId]: 'error' }))
        message.error((err as Error)?.message || '保存失败')
      }
    },
    [markdownByArtifact]
  )

  useEffect(() => {
    if (!activeArtifact) return
    if (!dirtyByArtifact[activeArtifact]) return
    const timer = setTimeout(() => {
      void saveArtifact(activeArtifact)
    }, 1000)
    return () => clearTimeout(timer)
  }, [activeArtifact, dirtyByArtifact, saveArtifact])

  useEffect(() => {
    return () => {
      if (transcriptDirty) {
        void saveTranscript()
      }
      if (activeArtifact && dirtyByArtifact[activeArtifact]) {
        void saveArtifact(activeArtifact)
      }
    }
  }, [transcriptDirty, saveTranscript, activeArtifact, dirtyByArtifact, saveArtifact])

  useEffect(() => {
    paragraphsRef.current = paragraphs
  }, [paragraphs])

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase()
      if (!(event.ctrlKey || event.metaKey)) return
      if (key !== 'z' && key !== 'y') return
      const activeEl = document.activeElement as HTMLElement | null
      const inArtifact = activeEl?.closest('.workspace-markdown-surface--edit')
      const inTranscript = activeEl?.closest('.workspace-transcript')
      const editorScope = inArtifact ? 'artifact' : inTranscript ? 'transcript' : activeEditor
      if (editorScope === 'artifact' && vditorRef.current) {
        const editor = vditorRef.current as unknown as { undo?: () => void; redo?: () => void }
        if (key === 'z') {
          editor.undo?.()
        } else {
          editor.redo?.()
        }
        event.preventDefault()
        return
      }
      if (editorScope === 'transcript') {
        event.preventDefault()
        setParagraphs((prev) => {
          const currentSnapshot = cloneParagraphs(prev)
          setTranscriptHistory((history) => {
            if (key === 'z') {
              if (history.past.length === 0) return history
              const past = [...history.past]
              const previous = past.pop() as TranscriptParagraph[]
              const future = [currentSnapshot, ...history.future].slice(0, 50)
              applyingHistoryRef.current = true
              setParagraphs(previous)
              applyingHistoryRef.current = false
              transcriptSnapshotRef.current = cloneParagraphs(previous)
              return { past, future }
            } else {
              if (history.future.length === 0) return history
              const [next, ...restFuture] = history.future
              const past = [...history.past, currentSnapshot].slice(-50)
              applyingHistoryRef.current = true
              setParagraphs(next)
              applyingHistoryRef.current = false
              transcriptSnapshotRef.current = cloneParagraphs(next)
              return { past, future: restFuture }
            }
          })
          return prev
        })
        return
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [activeEditor])

  const handleRegenerate = async (values: CreateTaskFormValues) => {
    if (!id) return
    try {
      const metaPrompt = (activeArtifactInfo?.metadata as any)?.prompt
      const artifactName = values.meeting_type?.trim() || ''
      const promptText =
        (values.prompt_text?.trim() || '') ||
        (localTemplate?.prompt_body && localTemplate.prompt_body.trim()) ||
        (configMode === 'regenerate' && activeArtifact && promptOverrides[activeArtifact]?.prompt_body?.trim()) ||
        (activeArtifactInfo?.prompt_instance?.prompt_text?.trim() || '') ||
        ''
      const templateId = values.template_id || localTemplate?.template_id || activeArtifactInfo?.prompt_instance?.template_id
      if (templateId === '__blank__' && !promptText) {
        message.error('空白模板必须填写提示词')
        return
      }
      const payload = {
        ...(artifactName ? { name: artifactName } : {}),
        ...(artifactName ? { name: artifactName } : {}),
        prompt_instance: {
          template_id: templateId || activeArtifactInfo?.prompt_instance?.template_id || 'tmpl_rec_1',
          language: values.output_language || currentTask?.output_language || 'zh-CN',
          ...(promptText ? { prompt_text: promptText } : {}),
          parameters: {
            meeting_description: values.description || '',
          },
        },
      }
      const artifactType =
        configMode === 'create'
          ? localTemplate?.artifact_type || metaPrompt?.artifact_type || 'meeting_minutes'
          : activeArtifactInfo?.artifact_type || 'meeting_minutes'
      const res = await regenerate(id, artifactType, payload)
      message.loading({ content: '已提交，后台生成中...', key: 'artifact-gen', duration: 2 })
      setConfigDrawerOpen(false)
      if (localTemplate?.prompt_body?.trim() && res.artifact_id) {
        setPromptOverrides((prev) => ({
          ...prev,
          [res.artifact_id]: {
            prompt_body: localTemplate.prompt_body.trim(),
            title: localTemplate.title,
            description: localTemplate.description,
            template_id: localTemplate.template_id,
          },
        }))
      }
      if (artifactName && res.artifact_id) {
        setArtifactNameOverrides((prev) => ({ ...prev, [res.artifact_id]: artifactName }))
      }
      if (!res.artifact_id) {
        await fetchList(id)
        return
      }
      setPendingArtifacts((prev) => ({
        ...prev,
        [res.artifact_id]: {
          name: artifactName || '生成中',
          artifact_type: artifactType,
        },
      }))
      setActiveArtifact(res.artifact_id)
      setMarkdownByArtifact((prev) => ({
        ...prev,
        [res.artifact_id]: '内容生成中，请稍候...',
      }))
      setDirtyByArtifact((prev) => ({ ...prev, [res.artifact_id]: false }))
      pollArtifactStatus(res.artifact_id)
    } catch (err) {
      message.error((err as Error)?.message || '重新生成失败')
    }
  }

  const handleMarkdownChange = (next: string) => {
    if (!activeArtifact) return
    setMarkdownByArtifact((prev) => ({ ...prev, [activeArtifact]: next }))
    setDirtyByArtifact((prev) => ({ ...prev, [activeArtifact]: true }))
    markDirty()
  }

  const handleCopy = async () => {
    if (!isConfirmed) return
    try {
      const inlined = await inlineImages(currentMarkdown)
      const html = buildWatermarkHtml(username || currentTask?.user_id) + markdownToBasicHtml(inlined)
      if (navigator.clipboard?.write) {
        const item = new ClipboardItem({
          'text/html': new Blob([html], { type: 'text/html' }),
          'text/plain': new Blob([inlined], { type: 'text/plain' }),
        })
        await navigator.clipboard.write([item])
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(inlined)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = inlined
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        textarea.remove()
      }
      message.success('已复制！请切换至企微文档按 Ctrl+V 粘贴')
    } catch (err) {
      message.error((err as Error)?.message || '复制失败')
    }
  }

  const handleConfirmChange = (checked: boolean) => {
    setIsConfirmed(checked)
    if (checked) {
      setIsDirty(false)
    }
  }

  const showDislikePlaceholder = () => message.info('不满意反馈入口待接入')

  const handleArtifactFeedback = (type: 'like' | 'dislike', reason?: string) => {
    if (!activeArtifact) return
    setArtifactFeedback((prev) => ({ ...prev, [activeArtifact]: type }))
    // TODO: 接入后端反馈接口时在此提交 reason/type（artifact 维度）
    if (type === 'dislike') {
      showDislikePlaceholder()
      console.log('Artifact dislike reason:', reason)
      return
    }
    console.log('Artifact feedback:', type)
  }

  const handleTranscriptFeedback = (type: 'like' | 'dislike', reason?: string) => {
    const taskId = id || 'current_task'
    setTranscriptFeedback((prev) => ({ ...prev, [taskId]: type }))
    // TODO: 接入后端反馈接口时在此提交 reason/type（transcript 维度）
    if (type === 'dislike') {
      showDislikePlaceholder()
      console.log('Transcript dislike reason:', reason)
      return
    }
    console.log('Transcript feedback:', type)
  }

  const renderStatusText = (status: 'saved' | 'saving' | 'error') => {
    if (status === 'saving') return '保存中...'
    if (status === 'error') return '保存失败'
    return '已保存'
  }

  useEffect(() => {
    if (mode === 'preview') {
      setActiveEditor(null)
    }
  }, [mode])

  useEffect(() => {
    return () => {
      Object.values(statusTimersRef.current).forEach((timer) => window.clearTimeout(timer))
      statusTimersRef.current = {}
    }
  }, [])

const pageTitle = currentTask?.meeting_type || currentTask?.task_id || "会议记录"
const folderLabel = useMemo(() => {
  if (!listFilter) return "全部任务"
  if (listFilter === "uncategorized") return "未分类"
  const typed = currentTask as { folder_path?: string; folder_id?: string | null } | null
  const folderMap = new Map(folders.map((folder) => [folder.id, folder.name]))
  const folderId = typed?.folder_id || listFilter
  return folderMap.get(folderId ?? "") || typed?.folder_path || folderId || listFilter
}, [currentTask, folders, listFilter])

const currentMarkdown = activeArtifact ? markdownByArtifact[activeArtifact] ?? '' : ''

  useEffect(() => {
    if (mode !== 'preview') return
    const container = reviewContentRef.current
    if (!container) return
    let cancelled = false
    const render = async () => {
      const { default: Vditor } = await import('vditor')
      if (cancelled) return
      const markdown =
        currentMarkdown ||
        resolveMarkdown(parsedContentById[activeArtifact || ''] || parsedContentById[currentArtifactId || ''] || null)
      if (!markdown.trim()) {
        container.innerHTML = ''
        return
      }
      const baseUrl = import.meta.env.BASE_URL || '/'
      const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`
      const cdn = `${window.location.origin}${normalizedBase}vditor`
      try {
        await Vditor.preview(container, markdown, {
          cdn,
          icon: '',
          i18n: {},
          hljs: { enable: false },
          theme: { current: '', path: '' },
        })
      } catch {
        container.textContent = markdown
      }
      if (cancelled) return
      const outline = reviewOutlineRef.current
      if (outline) {
        outline.innerHTML = ''
        try {
          Vditor.outlineRender(container, outline)
        } catch {
          outline.innerHTML = ''
        }
      }
    }
    void render()
    return () => {
      cancelled = true
    }
  }, [mode, currentMarkdown, parsedContentById, activeArtifact, currentArtifactId])

  useEffect(() => {
    if (mode !== 'preview') return
    const outline = reviewOutlineRef.current
    const content = reviewContentRef.current
    if (!outline || !content) return
    const handleClick = (event: MouseEvent) => {
      const target = (event.target as HTMLElement).closest('[data-target-id]') as HTMLElement | null
      if (!target) return
      const id = target.getAttribute('data-target-id')
      if (!id) return
      const heading = content.querySelector(`#${CSS.escape(id)}`) as HTMLElement | null
      if (!heading) return
      content.scrollTop = heading.offsetTop
    }
    outline.addEventListener('click', handleClick)
    return () => outline.removeEventListener('click', handleClick)
  }, [mode])

const taskFolderTarget = useMemo(() => {
  if (!listFilter) return '/tasks'
  if (listFilter === 'uncategorized') return '/tasks?folder=uncategorized'
  return `/tasks?folder=${encodeURIComponent(listFilter)}`
}, [listFilter])

  const handleTabAction = async (action: 'delete' | 'regenerate' | 'rename', artifactId?: string) => {
    if (action === 'regenerate') {
      setConfigMode('regenerate')
      setConfigDrawerOpen(true)
      return
    }
    if (action === 'delete' && artifactId) {
      const target = artifactTabs.find((tab) => tab.key === artifactId)
      if (target?.isDefaultMinutes) {
        message.info('默认纪要版本不可删除')
        return
      }
      if (!id) {
        message.error('任务信息缺失，无法删除')
        return
      }
      Modal.confirm({
        title: '确认删除该版本？',
        content: '此操作不可恢复，删除后可重新生成新版本。',
        okText: '删除',
        okButtonProps: { danger: true },
        onOk: async () => {
          try {
            await deleteArtifact(id, artifactId)
            setPromptOverrides((prev) => {
              const { [artifactId]: _, ...rest } = prev
              return rest
            })
            setArtifactNameOverrides((prev) => {
              const { [artifactId]: _, ...rest } = prev
              return rest
            })
            message.success('已删除该版本')
            await fetchList(id)
          } catch (err) {
            message.error((err as Error)?.message || '删除失败')
            throw err
          }
        },
      })
      return
    }
    if (action === 'rename' && artifactId) {
      const currentLabel = artifactNameOverrides[artifactId] || artifactTabs.find((tab) => tab.key === artifactId)?.label
      let value = currentLabel || ''
      Modal.confirm({
        title: '重命名版本',
        content: <Input defaultValue={value} onChange={(e) => (value = e.target.value)} />,
        onOk: () => {
          if (!value.trim()) {
            message.warning('名称不能为空')
            return Promise.reject()
          }
          return renameArtifact(artifactId, { display_name: value.trim() })
            .then(() => {
              setArtifactNameOverrides((prev) => ({ ...prev, [artifactId]: value.trim() }))
              return fetchList(id)
            })
            .catch((err) => {
              message.error((err as Error)?.message || '重命名失败')
              return Promise.reject(err)
            })
        },
      })
      return
    }
  }

  const handleMoveFolder = () => {
    message.info('移至文件夹功能待接入')
  }

  const handleFindReplace = () => {
    message.info('查找替换功能待接入')
  }

  const handleOpenPromptModal = useCallback(async () => {
    const artifactId = activeArtifactInfo?.artifact_id
    const override = artifactId ? promptOverrides[artifactId] : undefined
    const tplId = activeArtifactInfo?.prompt_instance?.template_id
    const metaPrompt = (currentArtifactDetail?.artifact as any)?.metadata?.prompt
    const promptText = override?.prompt_body || metaPrompt?.prompt_text || activeArtifactInfo?.prompt_instance?.prompt_text
    // 确保模板列表已加载，便于回填标题
    await fetchTemplates(userId || undefined, tenantId || undefined)
    const storeTemplates = (useTemplateStore as any).getState?.().templates || templates
    const storeTpl = tplId ? storeTemplates.find((tpl: Template) => tpl.template_id === tplId) : null
    const metaTitle =
      (override?.title && override.title.toLowerCase() !== '__blank__' ? override.title : undefined) ||
      (metaPrompt?.title && metaPrompt.title.toLowerCase() !== '__blank__' ? metaPrompt.title : undefined) ||
      storeTpl?.title

    if (!tplId && !override?.prompt_body && !promptText) {
      message.info('当前版本没有提示词')
      return
    }

    setPromptModalOpen(true)

    const promptBody = override?.prompt_body || promptText || storeTpl?.prompt_body || ''
    if (promptBody) {
      const fallbackId = tplId || metaPrompt?.template_id || 'temp_template'
      const originalBody = storeTpl?.prompt_body?.trim() || ''
      const currentBody = promptBody.trim()
      const edited = originalBody && currentBody && originalBody !== currentBody
      const title = resolvePromptTitle(override?.template_id || metaPrompt?.template_id || tplId, metaTitle, edited)
      setPromptTemplate({
        template_id: override?.template_id || metaPrompt?.template_id || fallbackId,
        title,
        description: override?.description || metaPrompt?.description || '',
        prompt_body: promptBody,
        artifact_type: activeArtifactInfo?.artifact_type || 'meeting_minutes',
        supported_languages: ['zh-CN'],
        parameter_schema: {},
        is_system: false,
        scope: 'private',
        created_at: '',
      })
      return
    }

    setPromptTemplate(null)
    try {
      const tpl = await getTemplateDetail(tplId as string)
      setPromptTemplate(tpl)
    } catch (err) {
      setPromptTemplate(null)
      message.error((err as Error)?.message || '提示词加载失败')
    }
  }, [activeArtifactInfo, currentArtifactDetail?.artifact, getTemplateDetail, promptOverrides, resolvePromptTitle])

  const handleSavePromptAsNew = useCallback(
    async (payload: { title: string; description: string; prompt_body: string }) => {
      const title = payload.title?.trim()
      if (!title) {
        message.warning('请输入新模板名称')
        return
      }
      const exists = templates.some((tpl) => tpl.title.trim().toLowerCase() === title.toLowerCase())
      if (exists) {
        message.warning('已存在同名模板，请更换名称')
        return
      }
      try {
        await createTemplate(
          {
            title,
            description: payload.description,
            prompt_body: payload.prompt_body,
            artifact_type: activeArtifactInfo?.artifact_type || 'meeting_minutes',
            supported_languages: promptTemplate?.supported_languages || ['zh-CN'],
            parameter_schema: promptTemplate?.parameter_schema || {},
          },
          userId || undefined
        )
        message.success('已保存为新模板')
        setPromptModalOpen(false)
      } catch (err) {
        message.error((err as Error)?.message || '保存新模板失败')
      }
    },
    [templates, createTemplate, activeArtifactInfo?.artifact_type, promptTemplate?.parameter_schema, promptTemplate?.supported_languages, username]
  )

  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        const active = document.activeElement as HTMLElement | null
        const inTranscript = active?.closest('.workspace-transcript')
        const inArtifact = active?.closest('.workspace-markdown-surface--edit')
        event.preventDefault()
        if (inTranscript && !inArtifact) {
          void saveTranscript()
          return
        }
        if (inArtifact) {
          if (activeArtifact) {
            void saveArtifact(activeArtifact)
          }
          return
        }
        void saveTranscript()
        if (activeArtifact) {
          void saveArtifact(activeArtifact)
        }
      }
    }
    window.addEventListener('keydown', handleKeydown)
    return () => window.removeEventListener('keydown', handleKeydown)
  }, [saveTranscript, saveArtifact, activeArtifact])

  const handleCreateArtifact = () => {
    setLocalTemplate(null)
    setConfigMode('create')
    setConfigFormKey((k) => k + 1)
    setConfigDrawerOpen(true)
  }

  useEffect(() => {
    if (!configDrawerOpen || !activeArtifactInfo || configMode === 'create') return
    // 将当前 artifact 的模板信息同步到抽屉
    const metaPrompt = (activeArtifactInfo.metadata as any)?.prompt
    const override = promptOverrides[activeArtifactInfo.artifact_id]
    const templateId = activeArtifactInfo.prompt_instance?.template_id || '__blank__'
    const storeTpl = templates.find((tpl) => tpl.template_id === templateId)
    const promptBody =
      override?.prompt_body ||
      metaPrompt?.prompt_text ||
      metaPrompt?.prompt_body ||
      activeArtifactInfo.prompt_instance?.prompt_text ||
      activeArtifactInfo.prompt_instance?.prompt_body ||
      ''
    const isBlank = templateId === '__blank__'
    const hasEdited =
      Boolean(override?.prompt_body) ||
      Boolean(metaPrompt?.prompt_text) ||
      Boolean(activeArtifactInfo.prompt_instance?.prompt_text)
    const baseTitle = override?.title || metaPrompt?.title || storeTpl?.title
    const title = resolvePromptTitle(templateId, baseTitle, hasEdited)
    const synced: Template = {
      template_id: templateId,
      title,
      description: override?.description || metaPrompt?.description || storeTpl?.description || '',
      prompt_body: promptBody,
      artifact_type: activeArtifactInfo.artifact_type || 'meeting_minutes',
      is_system: false,
      supported_languages: ['zh-CN'],
      scope: 'private',
      created_at: '',
      updated_at: '',
    }
    setLocalTemplate(synced)
  }, [configDrawerOpen, activeArtifactInfo, promptOverrides, templates])

  useEffect(() => {
    if (!configDrawerOpen) return
    fetchTemplates(userId || undefined, tenantId || undefined)
  }, [configDrawerOpen, fetchTemplates, userId, tenantId])

  return (
    <div className="page-container workspace-page">
      <div className="workspace-header">
        <div className="workspace-header__left">
          <Button
            type="text"
            size="small"
            icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setSidebarCollapsed((prev) => !prev)}
          />
          <div className="workspace-header__meta">
            <button type="button" className="workspace-header__folder-link" onClick={() => navigate(taskFolderTarget)}>
              <Typography.Text type="secondary">{folderLabel}</Typography.Text>
            </button>
            <span className="workspace-header__divider">/</span>
            <Typography.Text className="workspace-header__title-text">{pageTitle}</Typography.Text>
          </div>
        </div>
        <div className="workspace-header__actions">
          <Tooltip placement="bottom" title="移至文件夹">
            <button type="button" className="workspace-header__action-btn" onClick={handleMoveFolder}>
              <MoveFolderIcon />
            </button>
          </Tooltip>
          <Tooltip placement="bottom" title="查找替换">
            <button type="button" className="workspace-header__action-btn" onClick={handleFindReplace}>
              <FindReplaceIcon />
            </button>
          </Tooltip>
        </div>
      </div>

      <div className={`workspace-body${sidebarCollapsed ? ' is-collapsed' : ''}`}>
        <div className={`workspace-sidebar${sidebarCollapsed ? ' is-collapsed' : ''}`}>
          <FileSidebar listFilter={listFilter} />
        </div>

        <div className="workspace-main">
          <Group orientation="horizontal" className="workspace-panels">
            <Panel defaultSize={45} minSize={35} maxSize={70} style={{ minWidth: 340 }}>
                <div className="workspace-pane">
                  <AudioPlayer
                    ref={audioPlayerRef}
                    url={audioUrl}
                    onTimeUpdate={setCurrentTime}
                  />
                <div className="workspace-pane__toolbar">
                  <Typography.Text type="secondary">逐字稿编辑</Typography.Text>
                  <Typography.Text type={transcriptStatus === 'error' ? 'danger' : 'secondary'}>
                    {renderStatusText(transcriptStatus)}
                  </Typography.Text>
                </div>
                <div className="workspace-pane__body workspace-pane__body--scroll">
                  <TranscriptEditor
                    paragraphs={paragraphs}
                    currentTime={currentTime}
                    onSeek={(t) => audioPlayerRef.current?.seekTo(t)}
                    onUpdateParagraph={handleUpdateParagraph}
                    onRenameSpeaker={handleRenameSpeaker}
                    onFocusArea={() => setActiveEditor('transcript')}
                  />
                  <div className="workspace-pane__divider workspace-pane__divider--inset" />
                  <div className="workspace-feedback">
                        <Button
                          size="small"
                          type={(transcriptFeedback[id || 'current_task'] || '') === 'like' ? 'primary' : 'default'}
                          icon={<LikeOutlined />}
                          onClick={() => handleTranscriptFeedback('like')}
                        >
                          满意
                        </Button>
                        <Button
                          size="small"
                          type={(transcriptFeedback[id || 'current_task'] || '') === 'dislike' ? 'primary' : 'default'}
                          danger={(transcriptFeedback[id || 'current_task'] || '') === 'dislike'}
                          icon={<DislikeOutlined />}
                          onClick={() => handleTranscriptFeedback('dislike')}
                        >
                          不满意
                        </Button>
                  </div>
                </div>
              </div>
            </Panel>

            <Separator className="workspace-separator" />

            <Panel defaultSize={55} minSize={35} maxSize={70} style={{ minWidth: 340 }}>
              <div className="workspace-pane">
                <div className="workspace-pane__toolbar workspace-pane__toolbar--tabs">
                  <Tabs
                    activeKey={activeArtifact}
                    onChange={(key) => {
                      setActiveArtifact(key)
                      fetchArtifactDetail(key).then((res) => {
                        const artifactData = (res as any)?.artifact ?? res
                        if (artifactData) syncPromptOverride(key, artifactData)
                      })
                    }}
                    tabBarExtraContent={{
                      right: (
                        <Tooltip title="生成新笔记">
                          <Button
                            type="text"
                            size="small"
                            icon={<PlusOutlined />}
                            onClick={handleCreateArtifact}
                            className="workspace-tabs__add"
                          />
                        </Tooltip>
                      ),
                    }}
                    items={displayTabs.map((tab) => {
                      const isPending = tab.processing
                      const menuItems = isPending
                        ? []
                        : [
                            ...(tab.isDefaultMinutes ? [] : [{ key: 'rename', label: '重命名', icon: <EditOutlined /> }]),
                            { key: 'regenerate', label: '重新生成', icon: <RedoOutlined className="workspace-tab-action-icon" /> },
                            ...(tab.isDefaultMinutes ? [] : [{ key: 'delete', label: '删除', icon: <DeleteOutlined />, danger: true }]),
                          ]
                      return {
                        key: tab.key,
                        label: (
                          <span className={`workspace-tab-label${isPending ? ' is-pending' : ''}`}>
                            <span className="workspace-tab-label__name">
                              {isPending ? (
                                <>
                                  <Spin size="small" style={{ marginRight: 4 }} /> {tab.label || '生成中'}
                                </>
                              ) : (
                                tab.label
                              )}
                            </span>
                            {!isPending && (
                              <Dropdown
                                trigger={['click']}
                                menu={{
                                  items: menuItems,
                                  onClick: ({ key }) =>
                                    handleTabAction(key as 'delete' | 'regenerate' | 'rename', tab.key),
                                }}
                              >
                                <button
                                  type="button"
                                  className="workspace-tab-label__menu"
                                  onClick={(event) => event.stopPropagation()}
                                >
                                  <DownOutlined className="workspace-tab-label__icon" />
                                </button>
                              </Dropdown>
                            )}
                          </span>
                        ),
                        disabled: isPending,
                      }
                    })}
                    size="small"
                    className="workspace-tabs"
                  />
                  <div className="workspace-pane__actions">
                    <Tooltip title="查看提示词">
                      <Button
                        type="text"
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={handleOpenPromptModal}
                      />
                    </Tooltip>
                    <Tooltip title={mode === 'preview' ? '预览模式' : '编辑模式'}>
                      <Button
                        type="text"
                        size="small"
                        icon={mode === 'preview' ? <BookOutlined /> : <FormOutlined />}
                        onClick={() => setMode(mode === 'preview' ? 'edit' : 'preview')}
                      />
                    </Tooltip>
                    <Typography.Text
                      type={
                        artifactStatus[activeArtifact || ''] === 'error'
                          ? 'danger'
                          : 'secondary'
                      }
                    >
                      {renderStatusText(artifactStatus[activeArtifact || ''] || 'saved')}
                    </Typography.Text>
                  </div>
                </div>

                <div className="workspace-pane__body workspace-pane__body--markdown">
                  {!activeArtifact && <div className="workspace-empty">请在上方选择或生成一个纪要版本</div>}
                  {activeArtifact ? (
                    <>
                      <div
                        className="workspace-markdown-surface workspace-markdown-surface--edit"
                        style={{
                          display: mode === 'preview' ? 'none' : 'block',
                          minHeight: 320,
                          width: '100%',
                        }}
                        onFocusCapture={() => setActiveEditor('artifact')}
                      >
                        <MarkdownEditor
                          value={currentMarkdown}
                          onChange={handleMarkdownChange}
                          outline
                          height="auto"
                          hidePreviewActions
                          toolbarItems={editorToolbar}
                          previewMode="editor"
                          mode="sv"
                          onInstance={(inst) => {
                            vditorRef.current = inst
                          }}
                        />
                      </div>
                      {mode === 'preview' ? (
                        <div className="workspace-review">
                          <div className="workspace-review__content vditor-reset" ref={reviewContentRef} />
                          <div className="workspace-review__outline" ref={reviewOutlineRef} />
                        </div>
                      ) : null}
                    </>
                  ) : null}

                  {mode === 'preview' && (
                    <>
                      <div className="workspace-pane__divider workspace-pane__divider--inset" />
                      <div className="workspace-feedback workspace-feedback--aligned">
                        <Button
                          size="small"
                          type={artifactFeedback[activeArtifact || ''] === 'like' ? 'primary' : 'default'}
                          icon={<LikeOutlined />}
                          onClick={() => handleArtifactFeedback('like')}
                        >
                          满意
                        </Button>
                        <Button
                          size="small"
                          type={artifactFeedback[activeArtifact || ''] === 'dislike' ? 'primary' : 'default'}
                          danger={artifactFeedback[activeArtifact || ''] === 'dislike'}
                          icon={<DislikeOutlined />}
                          onClick={() => handleArtifactFeedback('dislike')}
                        >
                          不满意
                        </Button>
                      </div>
                    </>
                  )}
                </div>
                <div className="workspace-pane__footer">
                  <ActionFooter
                    isConfirmed={isConfirmed}
                    onConfirmChange={handleConfirmChange}
                    onCopy={handleCopy}
                    allowTrain={allowTrain}
                    onAllowTrainChange={setAllowTrain}
                  />
                </div>
              </div>
            </Panel>
          </Group>
      </div>
    </div>

      <TemplateEditorModal
        open={promptModalOpen}
        mode="task_creation"
        template={promptTemplate || undefined}
        onSaveAsNew={handleSavePromptAsNew}
        onClose={() => {
          setPromptModalOpen(false)
          setPromptTemplate(null)
        }}
      />

      <Drawer
        title={configMode === 'create' ? '新笔记生成配置' : '重新生成配置'}
        width={600}
        onClose={() => setConfigDrawerOpen(false)}
        open={configDrawerOpen}
        styles={{ body: { paddingBottom: 80 } }}
      >
        <TaskConfigForm
          key={configFormKey}
          initialValues={initialConfigValues}
          onFinish={handleRegenerate}
          submitText={configMode === 'create' ? '确认并生成' : '确认并重新生成'}
          meetingTypeLabel="名称"
          meetingTypePlaceholder="默认使用当前名称"
          templateOverride={localTemplate}
          disableDefaultTemplate={configMode === 'create'}
          onTemplateChange={setLocalTemplate}
        />
      </Drawer>
    </div>
  )
}

export default Workspace








