import { create } from 'zustand'

export type TaskRunStatus = 'PENDING' | 'PROCESSING' | 'PAUSED' | 'SUCCESS' | 'FAILED' | 'CANCELLED'
export type StepStatus = 'pending' | 'processing' | 'paused' | 'success' | 'failed'

export interface TaskStep {
  id: string
  title: string
  status: StepStatus
}

export interface TaskConfigSnapshot {
  templateName?: string
  meetingType?: string
  outputLanguage?: string
  asrLanguages?: string[]
  modelVersion?: string
  keywordMode?: string
}

export interface TaskInsight {
  keywords: string[]
  summarySentences: number
}

export interface TaskRunInfo {
  taskId: string
  title: string
  status: TaskRunStatus
  /**
   * 后端返回的原始状态（pending/transcribing/...），用于映射阶段
   */
  phase?: string
  progress: number
  steps: TaskStep[]
  fileNames: string[]
  config: TaskConfigSnapshot
  insights: TaskInsight
  etaSeconds: number
  resourceUsage: {
    cpu: number
    memory: number
  }
  updatedAt: number
}

interface TaskRunnerState {
  tasks: Record<string, TaskRunInfo>
  ensureTask: (taskId: string, meta?: Partial<Pick<TaskRunInfo, 'title' | 'fileNames' | 'config'>>) => void
  startTask: (taskId: string) => void
  pauseTask: (taskId: string) => void
  resumeTask: (taskId: string) => void
  abortTask: (taskId: string) => void
  deleteTask: (taskId: string) => void
  updateFromServer: (taskId: string, payload: Partial<TaskRunInfo>) => void
}

const STEP_TITLES = ['任务队列排序', '会议录音转写', '说话人识别', '声纹识别修正', '生成纪要']
const TOTAL_SECONDS = 240
const KEYWORD_POOL = ['项目评审', '预算', '上线时间', '风险', '里程碑', '资源排期']

const timers = new Map<string, number>()

const resolveStageIndex = (phase?: string, progress?: number) => {
  const normalized = (phase ?? '').toLowerCase()
  if (['pending', 'queued'].includes(normalized)) return 0
  // 后端 running 表示已开始处理，视为进入转写阶段
  if (normalized === 'running') return 1
  if (normalized === 'transcribing') return 1
  if (normalized === 'identifying') return 2
  if (normalized === 'correcting') return 3
  if (normalized === 'summarizing' || normalized === 'success') return 4
  if (typeof progress === 'number') {
    if (progress >= 70) return 4
    if (progress >= 60) return 3
    if (progress >= 40) return 2
    if (progress > 0) return 1
  }
  return 0
}

const buildSteps = (status: TaskRunStatus, progress: number, phase?: string): TaskStep[] => {
  const currentIndex = resolveStageIndex(phase, progress)
  return STEP_TITLES.map((title, index) => {
    if (status === 'SUCCESS') return { id: `${index}`, title, status: 'success' }
    if (status === 'FAILED' || status === 'CANCELLED') {
      if (index < currentIndex) return { id: `${index}`, title, status: 'success' }
      if (index === currentIndex) return { id: `${index}`, title, status: 'failed' }
      return { id: `${index}`, title, status: 'pending' }
    }
    if (status === 'PAUSED') {
      if (index < currentIndex) return { id: `${index}`, title, status: 'success' }
      if (index === currentIndex) return { id: `${index}`, title, status: 'paused' }
      return { id: `${index}`, title, status: 'pending' }
    }
    if (status === 'PROCESSING' || status === 'PENDING') {
      if (index < currentIndex) return { id: `${index}`, title, status: 'success' }
      if (index === currentIndex) return { id: `${index}`, title, status: 'processing' }
      return { id: `${index}`, title, status: 'pending' }
    }
    return { id: `${index}`, title, status: 'pending' }
  })
}

const makeTask = (taskId: string, meta?: Partial<Pick<TaskRunInfo, 'title' | 'fileNames' | 'config'>>): TaskRunInfo => {
  const title = meta?.title || `任务 ${taskId.slice(0, 6)}`
  const fileNames = meta?.fileNames ?? []
  const config: TaskConfigSnapshot = {
    templateName: meta?.config?.templateName,
    meetingType: meta?.config?.meetingType,
    outputLanguage: meta?.config?.outputLanguage,
    asrLanguages: meta?.config?.asrLanguages,
    modelVersion: meta?.config?.modelVersion ?? 'v2.1',
    keywordMode: meta?.config?.keywordMode ?? '自动抽取',
  }
  return {
    taskId,
    title,
    status: 'PENDING',
    phase: 'pending',
    progress: 0,
    steps: buildSteps('PENDING', 0),
    fileNames,
    config,
    insights: {
      keywords: [],
      summarySentences: 0,
    },
    etaSeconds: 0,
    resourceUsage: {
      cpu: 18 + Math.round(Math.random() * 22),
      memory: 1.1 + Math.round(Math.random() * 9) / 10,
    },
    updatedAt: Date.now(),
  }
}

const stopTimer = (taskId: string) => {
  const timer = timers.get(taskId)
  if (timer) {
    window.clearInterval(timer)
    timers.delete(taskId)
  }
}

const buildInsights = (progress: number): TaskInsight => {
  if (progress <= 0) {
    return { keywords: [], summarySentences: 0 }
  }
  const keywordCount = progress < 30 ? 2 : progress < 60 ? 3 : progress < 85 ? 4 : 5
  const summarySentences = Math.min(12, Math.max(2, Math.floor(progress / 8)))
  return {
    keywords: KEYWORD_POOL.slice(0, keywordCount),
    summarySentences,
  }
}

export const useTaskRunnerStore = create<TaskRunnerState>((set, get) => ({
  tasks: {},
  ensureTask: (taskId, meta) => {
    set((state) => {
      const existing = state.tasks[taskId]
      if (existing) {
        return {
          tasks: {
            ...state.tasks,
            [taskId]: {
              ...existing,
              title: meta?.title ?? existing.title,
              fileNames: meta?.fileNames ?? existing.fileNames,
              config: {
                ...existing.config,
                ...meta?.config,
              },
            },
          },
        }
      }
      return {
        tasks: {
          ...state.tasks,
          [taskId]: makeTask(taskId, meta),
        },
      }
    })
  },
  startTask: (taskId) => {
    const task = get().tasks[taskId]
    if (!task) return
    if (task.status === 'SUCCESS' || task.status === 'FAILED') return
    stopTimer(taskId)
    set((state) => ({
      tasks: {
        ...state.tasks,
        [taskId]: {
          ...task,
          status: 'PROCESSING',
          steps: buildSteps('PROCESSING', task.progress, task.phase),
          insights: buildInsights(task.progress),
          updatedAt: Date.now(),
        },
      },
    }))
    const timer = window.setInterval(() => {
      const current = get().tasks[taskId]
      if (!current || current.status !== 'PROCESSING') return
      const delta = 1 + Math.random() * 3
      const nextProgress = Math.min(100, current.progress + delta)
      const nextStatus: TaskRunStatus = nextProgress >= 100 ? 'SUCCESS' : 'PROCESSING'
      const insights = buildInsights(nextProgress)
      set((state) => ({
        tasks: {
          ...state.tasks,
          [taskId]: {
            ...current,
            status: nextStatus,
            progress: nextProgress,
            steps: buildSteps(nextStatus, nextProgress, current.phase),
            insights,
            etaSeconds: Math.max(0, Math.round(((100 - nextProgress) / 100) * TOTAL_SECONDS)),
            updatedAt: Date.now(),
          },
        },
      }))
      if (nextProgress >= 100) {
        stopTimer(taskId)
      }
    }, 1200)
    timers.set(taskId, timer)
  },
  pauseTask: (taskId) => {
    const task = get().tasks[taskId]
    if (!task || task.status !== 'PROCESSING') return
    stopTimer(taskId)
    set((state) => ({
      tasks: {
        ...state.tasks,
        [taskId]: {
          ...task,
          status: 'PAUSED',
          steps: buildSteps('PAUSED', task.progress, task.phase),
          updatedAt: Date.now(),
        },
      },
    }))
  },
  resumeTask: (taskId) => {
    const task = get().tasks[taskId]
    if (!task || task.status !== 'PAUSED') return
    get().startTask(taskId)
  },
  abortTask: (taskId) => {
    const task = get().tasks[taskId]
    if (!task) return
    stopTimer(taskId)
    set((state) => ({
      tasks: {
        ...state.tasks,
        [taskId]: {
          ...task,
          status: 'CANCELLED',
          phase: 'cancelled',
          steps: buildSteps('CANCELLED', task.progress, 'cancelled'),
          updatedAt: Date.now(),
        },
      },
    }))
  },
  deleteTask: (taskId) => {
    stopTimer(taskId)
    set((state) => {
      const next = { ...state.tasks }
      delete next[taskId]
      return { tasks: next }
    })
  },
  updateFromServer: (taskId, payload) => {
    set((state) => {
      const current = state.tasks[taskId]
      if (!current) return state
      const nextStatus = payload.status ?? current.status
      const nextProgress = payload.progress ?? current.progress
      const nextPhase = payload.phase ?? current.phase
      const nextSteps = payload.steps ?? buildSteps(nextStatus, nextProgress, nextPhase)
      return {
        tasks: {
          ...state.tasks,
          [taskId]: {
            ...current,
            ...payload,
            status: nextStatus,
            progress: nextProgress,
            phase: nextPhase,
            steps: nextSteps,
            updatedAt: Date.now(),
          },
        },
      }
    })
  },
}))
