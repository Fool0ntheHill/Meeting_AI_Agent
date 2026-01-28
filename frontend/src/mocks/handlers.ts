import { http, HttpResponse } from 'msw'
import { API_URL } from '@/config/env'
import type { TaskDetailResponse, TaskState, TranscriptResponse, GeneratedArtifact } from '@/types/frontend-types'

const tasks: TaskDetailResponse[] = [
  {
    task_id: 'task_demo_1',
    user_id: 'user_test_user',
    tenant_id: 'tenant_test_user',
    meeting_type: 'general',
    audio_files: ['mock://demo.wav'],
    file_order: [0],
    asr_language: 'zh-CN+en-US',
    output_language: 'zh-CN',
    state: 'running',
    progress: 42,
    created_at: new Date(Date.now() - 600000).toISOString(),
    updated_at: new Date().toISOString(),
    completed_at: '',
  },
  {
    task_id: 'task_demo_2',
    user_id: 'user_test_user',
    tenant_id: 'tenant_test_user',
    meeting_type: 'sales',
    audio_files: ['mock://sales.wav'],
    file_order: [0],
    asr_language: 'zh-CN',
    output_language: 'zh-CN',
    state: 'success',
    progress: 100,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date(Date.now() - 600000).toISOString(),
    completed_at: new Date(Date.now() - 600000).toISOString(),
  },
]

const transcript: TranscriptResponse = {
  task_id: 'task_demo_1',
  audio_duration: 1800,
  paragraphs: [
    {
      paragraph_id: 'p1',
      start_time: 0,
      end_time: 20,
      speaker: 'Speaker A',
      text: '大家好，今天我们讨论季度 OKR 进展。',
    },
    {
      paragraph_id: 'p2',
      start_time: 20,
      end_time: 40,
      speaker: 'Speaker B',
      text: '目前销售完成 70%，技术项目按计划推进。',
    },
  ],
}

const artifacts: GeneratedArtifact[] = [
  {
    artifact_id: 'artifact_demo_1',
    task_id: 'task_demo_2',
    artifact_type: 'meeting_minutes',
    version: 1,
    prompt_instance: { template_id: 'tmpl_rec_1', parameters: {} },
    content: JSON.stringify({
      title: '季度复盘纪要 v1',
      summary: '整体进展良好，销售需冲刺。',
      key_points: ['销售完成度 70%', '技术按计划', '需新增营销资源'],
      action_items: ['销售本周提交补强方案', '技术评审性能优化'],
    }),
    metadata: {},
    created_at: new Date(Date.now() - 400000).toISOString(),
    created_by: 'ai',
  },
  {
    artifact_id: 'artifact_demo_2',
    task_id: 'task_demo_2',
    artifact_type: 'meeting_minutes',
    version: 2,
    prompt_instance: { template_id: 'tmpl_rec_1', parameters: { tone: '简洁' } },
    content: JSON.stringify({
      title: '季度复盘纪要 v2',
      summary: '销售需提速，技术稳定交付。',
      key_points: ['销售 70%，差 30%', '技术风险低', '追加市场预算'],
      action_items: ['市场下周前给出预算方案', '销售每日更新漏斗'],
    }),
    metadata: {},
    created_at: new Date(Date.now() - 200000).toISOString(),
    created_by: 'ai',
  },
]

const buildStatus = (task: TaskDetailResponse) => {
  const status: Record<TaskState, TaskState> = {
    pending: 'pending',
    queued: 'queued',
    running: 'running',
    transcribing: 'transcribing',
    identifying: 'identifying',
    correcting: 'correcting',
    summarizing: 'summarizing',
    success: 'success',
    failed: 'failed',
    partial_success: 'partial_success',
  }
  return status[task.state]
}

export const handlers = [
  http.post(`${API_URL}/auth/dev/login`, async () => {
    return HttpResponse.json({
      access_token: 'mock-token',
      token_type: 'bearer',
      user_id: 'user_mock',
      tenant_id: 'tenant_mock',
      expires_in: 86400,
    })
  }),

  http.get(`${API_URL}/tasks`, ({ request }) => {
    const url = new URL(request.url)
    const state = url.searchParams.get('state')
    const filtered = state ? tasks.filter((t) => t.state === state) : tasks
    return HttpResponse.json({ items: filtered, total: filtered.length })
  }),

  http.get(`${API_URL}/tasks/:id`, ({ params }) => {
    const target = tasks.find((t) => t.task_id === params.id)
    if (!target) return HttpResponse.json({ message: 'not found' }, { status: 404 })
    return HttpResponse.json(target)
  }),

  http.get(`${API_URL}/tasks/:id/status`, ({ params }) => {
    const target = tasks.find((t) => t.task_id === params.id)
    if (!target) return HttpResponse.json({ message: 'not found' }, { status: 404 })
    const progress = target.state === 'running' ? target.progress : 100
    return HttpResponse.json({
      task_id: target.task_id,
      state: buildStatus(target),
      progress,
      estimated_time: target.state === 'running' ? 120 : 0,
      updated_at: new Date().toISOString(),
    })
  }),

  http.get(`${API_URL}/tasks/:id/transcript`, ({ params }) => {
    if (params.id !== transcript.task_id) {
      return HttpResponse.json(transcript)
    }
    return HttpResponse.json(transcript)
  }),

  http.get(`${API_URL}/tasks/:id/artifacts`, ({ params }) => {
    const list = artifacts.filter((a) => a.task_id === params.id)
    const grouped = list.reduce<Record<string, typeof artifacts>>((acc, cur) => {
      if (!acc[cur.artifact_type]) acc[cur.artifact_type] = []
      acc[cur.artifact_type].push(cur)
      return acc
    }, {})
    return HttpResponse.json({
      task_id: params.id,
      artifacts_by_type: grouped,
      total_count: list.length,
    })
  }),

  http.get(`${API_URL}/artifacts/:id`, ({ params }) => {
    const target = artifacts.find((a) => a.artifact_id === params.id)
    if (!target) return HttpResponse.json({ message: 'not found' }, { status: 404 })
    return HttpResponse.json({ artifact: target })
  }),
]
