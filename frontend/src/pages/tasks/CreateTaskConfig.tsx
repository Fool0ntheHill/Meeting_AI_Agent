import { useEffect, useRef } from 'react'
import { Button, Card, Typography, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useCreateTaskDraftStore } from '@/store/createTaskDraft'
import { useTaskStore } from '@/store/task'
import { useTaskRunnerStore } from '@/store/task-runner'
import { ENV } from '@/config/env'
import type { CreateTaskRequest } from '@/types/frontend-types'
import CreateTaskSteps from './CreateTaskSteps'
import TaskConfigForm, { type CreateTaskFormValues } from '@/components/TaskConfigForm'
import './create-task.css'

const CreateTaskConfig = () => {
  const navigate = useNavigate()
  const suppressGuardRef = useRef(false)
  const { createTask } = useTaskStore()
  const { ensureTask } = useTaskRunnerStore()
  const {
    uploads,
    meeting_type,
    output_language,
    asr_languages,
    skip_speaker_recognition,
    description,
    template,
    updateConfig,
    setTemplate,
    reset,
  } = useCreateTaskDraftStore()

  useEffect(() => {
    if (suppressGuardRef.current) {
      return
    }
    if (uploads.length === 0) {
      message.warning('请先上传音频文件')
      navigate('/tasks/create')
    }
  }, [uploads.length, navigate])

  const onSubmit = async (values: CreateTaskFormValues) => {
    if (uploads.length === 0) {
      message.warning('请先上传音频文件')
      navigate('/tasks/create')
      return
    }
    if (!template) {
      message.warning('请选择提示词模板')
      return
    }
    const taskName = values.meeting_type?.trim() || uploads[0]?.name?.replace(/\.[^/.]+$/, '') || '通用会议'
    const asr_language = values.asr_languages && values.asr_languages.length > 0 ? values.asr_languages.join('+') : undefined
    const promptParameters = values.description ? { meeting_description: values.description } : {}
    const totalDuration = uploads.reduce((sum, item) => sum + (item.duration ?? 0), 0)
    const promptText = (values.prompt_text?.trim() || template?.prompt_body?.trim() || '')
    if (template.template_id === '__blank__' && !promptText) {
      message.error('空白模板必须填写提示词')
      return
    }
    const payload: CreateTaskRequest = {
      audio_files: uploads.map((item) => item.file_path),
      file_order: uploads.map((_, index) => index),
      original_filenames: uploads.map((item) => item.original_filename || item.name),
      audio_duration: totalDuration > 0 ? totalDuration : undefined,
      meeting_type: taskName,
      output_language: values.output_language,
      asr_language,
      skip_speaker_recognition: values.skip_speaker_recognition,
      prompt_instance: template
        ? {
            template_id: template.template_id,
            language: values.output_language,
            prompt_text: promptText,
            parameters: promptParameters,
          }
        : undefined,
    }
    try {
      let taskId = ''
      if (ENV.ENABLE_MOCK) {
        try {
          const res = await createTask(payload)
          taskId = res.task_id
        } catch {
          taskId = `mock_${Date.now()}`
        }
      } else {
        const res = await createTask(payload)
        taskId = res.task_id
      }
      message.success('任务创建成功')
      suppressGuardRef.current = true
      ensureTask(taskId, {
        title: template?.title ? `处理任务 · ${template.title}` : `任务 ${taskId.slice(0, 6)}`,
        fileNames: uploads.map((item) => item.name),
        duration: totalDuration > 0 ? totalDuration : undefined,
        config: {
          templateName: template?.title,
          meetingType: values.meeting_type,
          outputLanguage: values.output_language,
          asrLanguages: values.asr_languages ?? [],
          modelVersion: 'v2.1',
          keywordMode: '自动抽取',
        },
      })
      navigate(`/tasks/${taskId}/workbench`)
      window.setTimeout(() => reset(), 0)
    } catch (err) {
      message.error((err as Error)?.message || '创建失败')
    }
  }

  const defaultName = uploads[0]?.name?.replace(/\.[^/.]+$/, '')
  const initialValues = {
    meeting_type: meeting_type && meeting_type !== 'general' ? meeting_type : defaultName || '通用会议',
    output_language,
    asr_languages,
    skip_speaker_recognition,
    description,
    template_id: template?.template_id,
  }

  return (
    <div className="page-container create-task">
      <div className="create-task__center">
        <Typography.Title level={3} className="create-task__title">
          选择配置
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="create-task__subtitle">
          模板、语言与高级设置可在此完成。确认模板后将返回本页显示选择结果。
        </Typography.Paragraph>
        <CreateTaskSteps current={1} />
        <Card className="create-task__step-card" bordered={false}>
          <TaskConfigForm
            initialValues={initialValues}
            onFinish={onSubmit}
            onValuesChange={(changed, all) => {
              updateConfig({
                meeting_type: all.meeting_type,
                output_language: all.output_language,
                asr_languages: all.asr_languages ?? [],
                skip_speaker_recognition: all.skip_speaker_recognition ?? false,
                description: all.description,
              })
            }}
            templateOverride={template}
            onTemplateChange={setTemplate}
            renderExtraActions={() => (
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks/create')}>
                上一步：上传与排序
              </Button>
            )}
          />
        </Card>
      </div>
    </div>
  )
}

export default CreateTaskConfig
