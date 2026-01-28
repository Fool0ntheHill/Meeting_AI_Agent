import { useEffect, useState } from 'react'

import { Button, Collapse, Form, Input, Select, Space, Switch, Typography, message } from 'antd'

import { CheckOutlined, PlusOutlined } from '@ant-design/icons'

import TemplateSelector from '@/components/TemplateSelector'

import type { Template } from '@/store/template'

import { useTemplateStore } from '@/store/template'



export interface CreateTaskFormValues {

  meeting_type: string

  output_language: string

  asr_languages?: string[]

  meeting_attendees?: string

  description?: string

  template_id?: string

  prompt_text?: string

}



const outputLanguageOptions = [

  { label: '中文', value: 'zh-CN' },

  { label: '英文', value: 'en-US' },

  { label: '日文', value: 'ja-JP' },

  { label: '韩文', value: 'ko-KR' },

]



const asrLanguageOptions = [

  { label: '中文', value: 'zh-CN' },

  { label: '英文', value: 'en-US' },

  { label: '日文', value: 'ja-JP' },

  { label: '韩文', value: 'ko-KR' },

]



interface TaskConfigFormProps {
  meetingTypeLabel?: string
  meetingTypePlaceholder?: string
  initialValues?: Partial<CreateTaskFormValues>
  onFinish: (values: CreateTaskFormValues) => void
  onValuesChange?: (changed: Partial<CreateTaskFormValues>, all: CreateTaskFormValues) => void
  submitText?: string
  renderExtraActions?: () => React.ReactNode
  templateOverride?: Template | null
  onTemplateChange?: (tpl: Template | null) => void
  disableDefaultTemplate?: boolean
}

const TaskConfigForm = ({
  meetingTypeLabel = '任务名称',
  meetingTypePlaceholder = '默认使用首个录音文件名',
  initialValues,
  onFinish,
  onValuesChange,
  submitText = '确认并创建任务',
  renderExtraActions,
  templateOverride,
  onTemplateChange,
  disableDefaultTemplate = false,
}: TaskConfigFormProps) => {
  const [form] = Form.useForm<CreateTaskFormValues>()

  const [templateModal, setTemplateModal] = useState(false)

  const [defaultApplied, setDefaultApplied] = useState(false)

  const { defaultTemplateId, getDetail } = useTemplateStore()

  const [customPrompt, setCustomPrompt] = useState<string | null>(null)

  const [templateOriginalBody, setTemplateOriginalBody] = useState<string | null>(null)

  

  // Use local state for template if not controlled/overridden

  const [localTemplate, setLocalTemplate] = useState<Template | null>(null)

  const activeTemplate = templateOverride !== undefined ? templateOverride : localTemplate



  const handleFinish = (values: CreateTaskFormValues) => {

    const cleanedPrompt = (customPrompt ?? values.prompt_text ?? '').trim()

    onFinish({ ...values, prompt_text: cleanedPrompt || undefined })

  }



  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue(initialValues)
      if (initialValues.prompt_text) {
        setCustomPrompt(initialValues.prompt_text)
        setTemplateOriginalBody(initialValues.prompt_text)
      }
    }
  }, [initialValues, form])

  useEffect(() => {
    if (!templateOverride) return
    setCustomPrompt(templateOverride.prompt_body || null)
    setTemplateOriginalBody(templateOverride.prompt_body || null)
    form.setFieldsValue({
      template_id: templateOverride.template_id,
      prompt_text: templateOverride.prompt_body || '',
    })
  }, [templateOverride, form])


  const handleTemplateApply = (tpl: Template, originalBody?: string | null) => {

    if (onTemplateChange) {

      onTemplateChange(tpl)

    } else {

      setLocalTemplate(tpl)

    }

    setTemplateOriginalBody(originalBody ?? tpl.prompt_body ?? null)

    setCustomPrompt(tpl.prompt_body || null)

    form.setFieldsValue({ template_id: tpl.template_id, prompt_text: tpl.prompt_body || '' })

    setTemplateModal(false)

    message.success(`已选择模板：${tpl.title}`)

  }



  useEffect(() => {
    if (disableDefaultTemplate) return
    if (defaultApplied) return
    if (!defaultTemplateId) return
    if (activeTemplate) {
      setDefaultApplied(true)
      return
    }
    let cancelled = false
    const applyDefault = async () => {
      const tpl = await getDetail(defaultTemplateId)
      if (!tpl || cancelled) return
      if (onTemplateChange) {
        onTemplateChange(tpl)
      } else {
        setLocalTemplate(tpl)
      }
      setTemplateOriginalBody(tpl.prompt_body || null)
      setCustomPrompt(tpl.prompt_body || null)
      form.setFieldsValue({ template_id: tpl.template_id, prompt_text: tpl.prompt_body || '' })
      setDefaultApplied(true)
    }
    void applyDefault()
    return () => {
      cancelled = true
    }
  }, [activeTemplate, defaultApplied, defaultTemplateId, form, getDetail, onTemplateChange, disableDefaultTemplate])


  return (

    <>

      <Form

        form={form}

        layout="vertical"

        onFinish={handleFinish}

        onValuesChange={onValuesChange}

        initialValues={initialValues}

      >

        <div className="create-task__config-grid">

          <Form.Item name="meeting_type" label={meetingTypeLabel} rules={[{ required: true, message: '请输入任务名称' }]}>

            <Input placeholder={meetingTypePlaceholder} maxLength={60} />

          </Form.Item>

          <Form.Item name="output_language" label="输出语言" rules={[{ required: true, message: '请选择输出语言' }]}>

            <Select options={outputLanguageOptions} />

          </Form.Item>

        </div>

        <Form.Item label="提示词模板" required>

          <Space align="start" direction="vertical">

            <Button onClick={() => setTemplateModal(true)} icon={<PlusOutlined />}>

              选择模板

            </Button>

            {activeTemplate && (() => {

              const isBlank = activeTemplate.template_id === '__blank__'

              const hasEditedContent =

                customPrompt && templateOriginalBody !== null && customPrompt !== templateOriginalBody

              const displayName =
                activeTemplate.title || (isBlank ? '临时空白模板' : activeTemplate.template_id)
              const displayLabel = hasEditedContent && isBlank ? `${displayName}（修改版）` : displayName



              return (

                <div className="template-selected">
                  <Typography.Text>已选：</Typography.Text>
                  <Typography.Text strong title={displayLabel}>
                    {displayLabel}
                    {hasEditedContent && !isBlank ? '（已修改）' : ''}
                  </Typography.Text>
                  {hasEditedContent && (
                    <Button
                      size="small"
                      type="link"
                      onClick={() => {
                        setCustomPrompt(templateOriginalBody)

                        form.setFieldsValue({ prompt_text: templateOriginalBody ?? '' })

                        message.success('已恢复模板默认内容')

                      }}

                    >

                      恢复默认

                    </Button>

                  )}

                </div>

              )

            })()}

          </Space>

          <Form.Item name="template_id" rules={[{ required: true, message: '请选择提示词模板' }]} hidden>

            <Input />

          </Form.Item>

          <Form.Item name="prompt_text" hidden>

            <Input />

          </Form.Item>

          <Form.Item shouldUpdate noStyle>

            {() => {

              const errors = form.getFieldError('template_id')

              return errors.length ? <Typography.Text type="danger">{errors[0]}</Typography.Text> : null

            }}

          </Form.Item>

        </Form.Item>

        <Collapse

          items={[

            {

              key: 'advanced',

              label: '高级设置',

              children: (

                <Space direction="vertical" style={{ width: '100%' }}>

                  <Form.Item name="asr_languages" label="会议转写语言">

                    <Select

                      mode="multiple"

                      allowClear

                      maxTagCount={3}

                      placeholder="选择 1-2 种语言，自动拼接为识别语言"

                      options={asrLanguageOptions}

                    />

                  </Form.Item>

                  <Form.Item name="meeting_attendees" label="会议人数（可选）">

                    <Input placeholder="例如 3 人，或直接填写人数" />

                  </Form.Item>

                  <Form.Item label="会议描述（可选）" name="description">

                    <Input.TextArea placeholder="将作为补充上下文传给模型" rows={3} />

                  </Form.Item>

                </Space>

              ),

            },

          ]}

        />

        <div className="create-task__step-actions" style={{ marginTop: 24 }}>

          {renderExtraActions && renderExtraActions()}

          <Button type="primary" htmlType="submit" icon={<CheckOutlined />}>

            {submitText}

          </Button>

        </div>

      </Form>

      <TemplateSelector
        open={templateModal}
        initialTemplate={activeTemplate ?? undefined}
        initialContent={customPrompt ?? activeTemplate?.prompt_body ?? undefined}
        onClose={() => setTemplateModal(false)}
        onApply={({ template, prompt, description, originalPrompt }) => {
          handleTemplateApply({ ...template, prompt_body: prompt, description }, originalPrompt ?? template.prompt_body ?? null)
          setTemplateOriginalBody(originalPrompt ?? template.prompt_body ?? null)
          setCustomPrompt(prompt)
        }}

      />

    </>

  )

}



export default TaskConfigForm
