import { useEffect, useMemo, useState } from 'react'
import { Button, Input, Modal, Space, Tooltip, Typography, message } from 'antd'
import { CopyOutlined } from '@ant-design/icons'
import type { PromptTemplate } from '@/types/frontend-types'
import './TemplateEditorModal.css'

type TemplateEditorMode = 'manage' | 'task_creation'

interface TemplateEditorModalProps {
  open: boolean
  mode: TemplateEditorMode
  template?: PromptTemplate | null
  onClose: () => void
  onSave?: (payload: { title: string; description: string; prompt_body: string }) => Promise<void>
  onApplyToTask?: (prompt: string) => void
  onSaveAsNew?: (payload: { title: string; description: string; prompt_body: string }) => Promise<void>
}

const TemplateEditorModal = ({
  open,
  mode,
  template,
  onClose,
  onSave,
  onApplyToTask,
  onSaveAsNew,
}: TemplateEditorModalProps) => {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [promptBody, setPromptBody] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveAsOpen, setSaveAsOpen] = useState(false)
  const [saveAsName, setSaveAsName] = useState('')

  const readOnlyMeta = mode === 'task_creation'
  const readOnlyAll = Boolean(template?.is_system && mode === 'manage')

  useEffect(() => {
    if (!open) return
    setTitle(template?.title || '')
    setDescription(template?.description || '')
    setPromptBody(template?.prompt_body || '')
  }, [open, template])

  const hasReset = useMemo(() => {
    if (!template?.prompt_body) return false
    return promptBody !== template.prompt_body
  }, [promptBody, template?.prompt_body])

  const handleCopy = async () => {
    if (!promptBody) return
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(promptBody)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = promptBody
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        textarea.remove()
      }
      message.success('已复制提示词内容')
    } catch {
      message.error('复制失败，请手动复制')
    }
  }

  const handleReset = () => {
    if (!template) return
    setPromptBody(template.prompt_body || '')
  }

  const handleSave = async () => {
    if (!onSave) return
    if (!title.trim()) {
      message.warning('请输入模板名称')
      return
    }
    if (!promptBody.trim()) {
      message.warning('请输入提示词内容')
      return
    }
    setSaving(true)
    try {
      await onSave({
        title: title.trim(),
        description: description.trim(),
        prompt_body: promptBody.trim(),
      })
    } finally {
      setSaving(false)
    }
  }

  const handleApply = () => {
    if (!promptBody.trim()) {
      message.warning('请输入提示词内容')
      return
    }
    onApplyToTask?.(promptBody.trim())
  }

  const handleSaveAsNew = async () => {
    if (!onSaveAsNew) return
    if (!saveAsName.trim()) {
      message.warning('请输入模板名称')
      return
    }
    if (!promptBody.trim()) {
      message.warning('请输入提示词内容')
      return
    }
    setSaving(true)
    try {
      await onSaveAsNew({
        title: saveAsName.trim(),
        description: description.trim(),
        prompt_body: promptBody.trim(),
      })
      setSaveAsName('')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onCancel={onClose} footer={null} width={960} className="template-editor-modal" destroyOnClose>
      <div className="template-editor">
        <div className="template-editor__header">
          <Typography.Text type="secondary">
            {mode === 'manage' ? (template ? '编辑模板' : '创建模板') : '配置任务提示词'}
          </Typography.Text>
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="给模板起个名字..."
            className="template-editor__title-input"
            disabled={readOnlyMeta || readOnlyAll}
            bordered={false}
          />
          <Typography.Text className="template-editor__label">
            描述
          </Typography.Text>
          <Input.TextArea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="简单说明该提示词的使用场景"
            autoSize={{ minRows: 1, maxRows: 3 }}
            className="template-editor__desc-input"
            disabled={readOnlyMeta || readOnlyAll}
          />
        </div>

        <div className="template-editor__panel">
          <div className="template-editor__toolbar">
            <Typography.Text className="template-editor__label">提示词内容</Typography.Text>
            <Space>
              <Tooltip title="复制提示词">
                <Button type="text" icon={<CopyOutlined />} onClick={handleCopy} />
              </Tooltip>
            </Space>
          </div>
          <div className="template-editor__body">
            <Input.TextArea
              value={promptBody}
              onChange={(event) => setPromptBody(event.target.value)}
              placeholder="示例：你是一名专业的会议助理，请根据逐字稿生成结构化纪要..."
              className="template-editor__textarea"
              disabled={readOnlyAll}
              autoSize={false}
              rows={12}
              style={{ height: 720, minHeight: 720 }}
            />
          </div>
        </div>

        <div className="template-editor__footer">
          <div>
            {hasReset && (
              <Button type="text" onClick={handleReset} disabled={readOnlyAll}>
                恢复初始内容
              </Button>
            )}
          </div>
          <Space>
            {mode === 'task_creation' ? (
              <Space>
                <Input
                  value={saveAsName}
                  onChange={(event) => setSaveAsName(event.target.value)}
                  placeholder="输入新模板名称"
                  style={{ width: 220 }}
                  allowClear
                />
                <Button type="primary" loading={saving} onClick={handleSaveAsNew}>
                  另存为新模板
                </Button>
              </Space>
            ) : (
              <Button type="primary" loading={saving} onClick={handleSave} disabled={readOnlyAll}>
                {template ? '保存修改' : '保存模板'}
              </Button>
            )}
          </Space>
        </div>
      </div>
    </Modal>
  )
}

export default TemplateEditorModal

