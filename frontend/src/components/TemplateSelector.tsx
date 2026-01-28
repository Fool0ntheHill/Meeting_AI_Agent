import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Input, Modal, Popover, Segmented, Space, Tag, Typography, message } from 'antd'
import { CheckOutlined, RollbackOutlined, SaveOutlined } from '@ant-design/icons'
import { useTemplateStore } from '@/store/template'
import { useAuthStore } from '@/store/auth'
import type { PromptTemplate } from '@/types/frontend-types'
import type { InputRef } from 'antd'
import './TemplateSelector.css'

interface Props {
  open: boolean
  onClose: () => void
  onApply: (payload: { template: PromptTemplate; prompt: string; description?: string; originalPrompt?: string }) => void
  initialTemplate?: PromptTemplate | null
  initialContent?: string | null
}

const TemplateSelector = ({ open, onClose, onApply, initialTemplate, initialContent }: Props) => {
  const { fetchTemplates, filtered, setKeyword, setFilter, templates, loading, create } = useTemplateStore()
  const { userId, tenantId } = useAuthStore()
  const [search, setSearch] = useState('')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [editorTitle, setEditorTitle] = useState('')
  const [editorBody, setEditorBody] = useState('')
  const [dirty, setDirty] = useState(false)
  const [savePopoverOpen, setSavePopoverOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveDesc, setSaveDesc] = useState('')
  const historyRef = useRef<{ stack: string[]; index: number }>({ stack: [], index: -1 })
  const originalPromptRef = useRef('')
  const saveNameInputRef = useRef<InputRef | null>(null)
  const appliedInitialRef = useRef(false)

  const blankTemplate: PromptTemplate = {
    template_id: '__blank__',
    title: '临时空白模板',
    description: '新建一个空白模板',
    prompt_body: '',
    artifact_type: 'meeting_minutes',
    is_system: false,
    supported_languages: ['zh-CN'],
    scope: 'private',
    created_at: '',
    updated_at: '',
  }

  const list = useMemo(() => [blankTemplate, ...filtered()], [blankTemplate, filtered])

  useEffect(() => {
    if (open) {
      fetchTemplates(userId || undefined, tenantId || undefined)
    }
  }, [fetchTemplates, open, tenantId, userId])

  useEffect(() => {
    // 打开弹窗或初始模板变更时，允许重新应用默认值一次
    if (!open) {
      appliedInitialRef.current = false
      return
    }
    appliedInitialRef.current = false
  }, [open, initialTemplate?.template_id])

  useEffect(() => {
    if (!open || list.length === 0 || appliedInitialRef.current) return

    const pickByInitial = () =>
      initialTemplate ? list.find((tpl) => tpl.template_id === initialTemplate.template_id) : null
    const pickFallback = () => list.find((tpl) => tpl.template_id !== '__blank__') || list[0]

    const target = pickByInitial() || (!activeId && pickFallback())
    if (!target) return

    const body = initialContent ?? target.prompt_body ?? ''
    setActiveId(target.template_id)
    setEditorTitle(target.title || '')
    setEditorBody(body)
    setSaveName(target.title || '')
    setSaveDesc(target.description || '')
    originalPromptRef.current = target.prompt_body || ''
    historyRef.current = { stack: [body], index: 0 }
    setDirty(false)
    appliedInitialRef.current = true
  }, [open, list, activeId, initialTemplate, initialContent])

  useEffect(() => {
    if (savePopoverOpen) {
      window.setTimeout(() => {
        saveNameInputRef.current?.focus()
      }, 0)
    }
  }, [savePopoverOpen])

  const activeTemplate = list.find((tpl) => tpl.template_id === activeId) || null
  const hasSelection = Boolean(activeTemplate)

  const resetLocalState = () => {
    setSearch('')
    setActiveId(null)
    setKeyword('')
    setFilter('all')
    setEditorTitle('')
    setEditorBody('')
    setDirty(false)
    setSavePopoverOpen(false)
    setSaveName('')
    setSaveDesc('')
    historyRef.current = { stack: [], index: -1 }
    originalPromptRef.current = ''
  }

  const handleClose = () => {
    resetLocalState()
    onClose()
  }

  const handleSelectTemplate = (tpl: PromptTemplate) => {
    if (dirty && activeTemplate && tpl.template_id !== activeTemplate.template_id) {
      Modal.confirm({
        title: '放弃当前修改？',
        content: '切换模板将丢失未保存的编辑内容。',
        okText: '切换',
        cancelText: '取消',
        onOk: () => {
          setActiveId(tpl.template_id)
          setEditorTitle(tpl.title || '')
          setEditorBody(tpl.prompt_body || '')
          setSaveName(tpl.title || '')
          setSaveDesc(tpl.description || '')
          originalPromptRef.current = tpl.prompt_body || ''
          historyRef.current = { stack: [tpl.prompt_body || ''], index: 0 }
          setDirty(false)
        },
      })
      return
    }
    setActiveId(tpl.template_id)
    setEditorTitle(tpl.title || '')
    setEditorBody(tpl.prompt_body || '')
    setSaveName(tpl.title || '')
    setSaveDesc(tpl.description || '')
    originalPromptRef.current = tpl.prompt_body || ''
    historyRef.current = { stack: [tpl.prompt_body || ''], index: 0 }
    setDirty(false)
  }

  const handleConfirm = () => {
    if (!activeTemplate) return
    onApply({
      template: {
        ...activeTemplate,
        title: editorTitle || activeTemplate.title,
        prompt_body: editorBody,
        description: saveDesc,
      },
      prompt: editorBody,
      originalPrompt: originalPromptRef.current,
      description: saveDesc,
    })
    resetLocalState()
  }

  const handleReset = () => {
    if (!activeTemplate) return
    setEditorTitle(activeTemplate.title || '')
    setEditorBody(activeTemplate.prompt_body || '')
    setSaveName(activeTemplate.title || '')
    setSaveDesc(activeTemplate.description || '')
    historyRef.current = { stack: [activeTemplate.prompt_body || ''], index: 0 }
    setDirty(false)
  }

  const pushHistory = (val: string) => {
    const hist = historyRef.current
    const stack = hist.stack.slice(0, hist.index + 1)
    if (stack[stack.length - 1] === val) return
    stack.push(val)
    historyRef.current = { stack, index: stack.length - 1 }
  }

  const handleUndo = () => {
    const hist = historyRef.current
    if (hist.index > 0) {
      const nextIndex = hist.index - 1
      historyRef.current = { ...hist, index: nextIndex }
      setEditorBody(hist.stack[nextIndex])
    }
  }

  const handleRedo = () => {
    const hist = historyRef.current
    if (hist.index < hist.stack.length - 1) {
      const nextIndex = hist.index + 1
      historyRef.current = { ...hist, index: nextIndex }
      setEditorBody(hist.stack[nextIndex])
    }
  }

  const handleSaveAs = async () => {
    if (!editorBody.trim()) {
      message.warning('内容不能为空')
      return
    }
    const title = saveName.trim() || `${editorTitle || activeTemplate?.title || '新模板'}-副本`
    await create(
      {
        title,
        prompt_body: editorBody,
        description: saveDesc.trim() || activeTemplate?.description || '',
        artifact_type: activeTemplate?.artifact_type || 'meeting_minutes',
        supported_languages: activeTemplate?.supported_languages || ['zh-CN'],
        parameter_schema: activeTemplate?.parameter_schema || {},
      },
      userId || undefined
    )
    message.success('已另存为新模板')
    setSavePopoverOpen(false)
    setSaveName(title)
  }

  return (
    <Modal title="选择并编辑提示词" width="90vw" style={{ top: 20 }} open={open} onCancel={handleClose} destroyOnClose footer={null}>
      <div className="template-selector master-detail">
        <div className="template-selector__list master">
          <Space direction="vertical" style={{ width: '100%', marginBottom: 12 }}>
            <Input.Search
              placeholder="搜索名称/描述"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setKeyword(e.target.value)
              }}
            />
            <Segmented
              options={[
                { label: '全部', value: 'all' },
                { label: '官方', value: 'global' },
                { label: '自定义', value: 'private' },
              ]}
              onChange={(val) => setFilter(val as string)}
            />
          </Space>
          <div className="template-selector__scroll">
            {list.map((tpl) => (
              <div
                key={tpl.template_id}
                className={`template-list-item${tpl.template_id === '__blank__' ? ' template-list-item--blank' : ''}${
                  activeId === tpl.template_id ? ' template-list-item--active' : ''
                }`}
                onClick={() => handleSelectTemplate(tpl)}
              >
                <div className="template-list-item__header">
                  <Typography.Text strong ellipsis>
                    {tpl.title}
                  </Typography.Text>
                  {tpl.template_id !== '__blank__' && (
                    <Tag color={tpl.is_system ? 'blue' : 'green'}>{tpl.is_system ? '官方' : '自定义'}</Tag>
                  )}
                </div>
                <Typography.Paragraph type="secondary" ellipsis={{ rows: 1 }}>
                  {tpl.description || '暂无描述'}
                </Typography.Paragraph>
              </div>
            ))}
            {!loading && list.length === 1 && <Typography.Text type="secondary">暂无模板，请稍后重试</Typography.Text>}
          </div>
        </div>

        <div className="template-selector__editor detail">
          {activeTemplate ? (
            <div className="template-editor">
              <Input
                size="large"
                value={editorTitle}
                onChange={(e) => {
                  setEditorTitle(e.target.value)
                  setDirty(true)
                }}
                className="template-editor__title"
                placeholder="请输入模板标题"
              />
              <div className="template-editor__body">
                <textarea
                  className="template-editor__textarea"
                  value={editorBody}
                  onChange={(e) => {
                    setEditorBody(e.target.value)
                    setDirty(true)
                    pushHistory(e.target.value)
                  }}
                  onKeyDown={(e) => {
                    if (e.ctrlKey || e.metaKey) {
                      if (e.key.toLowerCase() === 'z') {
                        e.preventDefault()
                        handleUndo()
                      } else if (e.key.toLowerCase() === 'y') {
                        e.preventDefault()
                        handleRedo()
                      }
                    }
                  }}
                  placeholder="在此编辑提示词内容..."
                />
              </div>
              <div className="template-editor__actions">
                <Space>
                  <Button icon={<RollbackOutlined />} disabled={!dirty} onClick={handleReset}>
                    恢复原始内容
                  </Button>
                </Space>
                <Space>
                  <Popover
                    open={savePopoverOpen}
                    onOpenChange={(visible) => setSavePopoverOpen(visible)}
                    trigger="click"
                    placement="topRight"
                    destroyTooltipOnHide
                    getPopupContainer={(triggerNode) => triggerNode.parentElement || document.body}
                    overlayStyle={{ pointerEvents: 'auto' }}
                    content={
                      <Space direction="vertical" style={{ width: 280 }}>
                        <Typography.Text type="secondary">模板名称</Typography.Text>
                        <Input
                          ref={saveNameInputRef}
                          placeholder="请输入新模板名称"
                          value={saveName}
                          onChange={(e) => setSaveName(e.target.value)}
                        />
                        <Typography.Text type="secondary">模板描述</Typography.Text>
                        <Input.TextArea
                          rows={3}
                          placeholder="请输入模板描述（可选）"
                          value={saveDesc}
                          onChange={(e) => setSaveDesc(e.target.value)}
                        />
                        <Button type="primary" block icon={<SaveOutlined />} onClick={handleSaveAs}>
                          保存
                        </Button>
                      </Space>
                    }
                  >
                    <Button disabled={!hasSelection} icon={<SaveOutlined />} onClick={() => setSavePopoverOpen(true)}>
                      另存为新模板
                    </Button>
                  </Popover>
                  <Button type="primary" disabled={!hasSelection} icon={<CheckOutlined />} onClick={handleConfirm}>
                    确认并应用
                  </Button>
                </Space>
              </div>
            </div>
          ) : (
            <div className="template-editor__empty">
              <Typography.Text type="secondary">请选择左侧模板以开始编辑</Typography.Text>
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}

export default TemplateSelector
