import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Flex, Input, Popconfirm, Space, Tag, Typography, message } from 'antd'
import {
  FileTextOutlined,
  PlusOutlined,
  FileSearchOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { useTemplateStore } from '@/store/template'
import { useAuthStore } from '@/store/auth'
import type { PromptTemplate } from '@/types/frontend-types'
import TemplateEditorModal from '@/components/TemplateEditorModal'

const Templates = () => {
  const { fetchTemplates, filtered, setFilter, setKeyword, create, update, remove, defaultTemplateId, setDefaultTemplateId } =
    useTemplateStore()
  const data = filtered()
  const [modalOpen, setModalOpen] = useState(false)
  const [activeTemplate, setActiveTemplate] = useState<PromptTemplate | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const { userId } = useAuthStore()

  useEffect(() => {
    fetchTemplates(userId, useAuthStore.getState().tenantId || undefined)
    setFilter('all')
    setKeyword('')
  }, [fetchTemplates, setFilter, setKeyword, userId])

  const [official, personal] = useMemo(() => {
    const officialList = data.filter((tpl) => tpl.is_system || tpl.scope === 'global')
    const personalList = data.filter((tpl) => !tpl.is_system && tpl.scope !== 'global')
    return [officialList, personalList]
  }, [data])

  const iconByType = (tpl: PromptTemplate) => {
    if (tpl.artifact_type?.includes('meeting')) return <FileTextOutlined />
    if (tpl.artifact_type?.includes('summary')) return <BulbOutlined />
    return <FileSearchOutlined />
  }

  const openCreate = () => {
    setActiveTemplate(null)
    setModalOpen(true)
  }

  const openEdit = (tpl: PromptTemplate) => {
    setActiveTemplate(tpl)
    setModalOpen(true)
  }

  const handleApply = (tpl: PromptTemplate) => {
    setDefaultTemplateId(tpl.template_id)
    message.success(`已设置为默认模板：${tpl.title}`)
  }

  const handleDelete = async (tpl: PromptTemplate) => {
    if (tpl.is_system) return
    setDeletingId(tpl.template_id)
    try {
      await remove(tpl.template_id, userId || undefined)
      message.success('模板已删除')
      fetchTemplates(userId, useAuthStore.getState().tenantId || undefined)
    } catch {
      message.error('删除失败，请稍后重试')
    } finally {
      setDeletingId(null)
    }
  }

  const renderSection = (title: string, list: PromptTemplate[], emptyText: string) => (
    <div style={{ marginTop: 16 }}>
      <Flex align="center" justify="space-between" style={{ marginBottom: 8 }}>
        <Space>
          <Typography.Title level={5} style={{ margin: 0 }}>
            {title}
          </Typography.Title>
          <Tag color={title === '默认模板' ? 'blue' : 'green'}>{list.length}</Tag>
        </Space>
      </Flex>
      <Flex wrap="wrap" gap={12}>
        {list.map((tpl) => (
          <Card
            key={tpl.template_id}
            title={
              <Space>
                {iconByType(tpl)}
                <span>{tpl.title}</span>
              </Space>
            }
            style={{ width: 320 }}
            extra={<Tag color={tpl.is_system ? 'blue' : 'green'}>{tpl.is_system ? '官方' : '私人'}</Tag>}
            actions={[
              <Button type="link" disabled={defaultTemplateId === tpl.template_id} onClick={() => handleApply(tpl)}>
                {defaultTemplateId === tpl.template_id ? '默认使用中' : '应用'}
              </Button>,
              <Button type="link" onClick={() => openEdit(tpl)}>
                预览与修改
              </Button>,
              tpl.is_system ? (
                <Button type="link" disabled>
                  删除
                </Button>
              ) : (
                <Popconfirm
                  title="删除模板"
                  description="删除后不可恢复，确认删除？"
                  onConfirm={() => handleDelete(tpl)}
                  okButtonProps={{ danger: true, loading: deletingId === tpl.template_id }}
                >
                  <Button type="link" danger loading={deletingId === tpl.template_id}>
                    删除
                  </Button>
                </Popconfirm>
              ),
            ]}
          >
            <Typography.Paragraph ellipsis={{ rows: 2 }}>{tpl.description || '暂无描述'}</Typography.Paragraph>
            <Space wrap>
              {tpl.supported_languages?.map((lang) => (
                <Tag key={lang}>{lang}</Tag>
              ))}
            </Space>
          </Card>
        ))}
        {list.length === 0 && <Typography.Text type="secondary">{emptyText}</Typography.Text>}
      </Flex>
    </div>
  )


  return (
    <div className="page-container">
      <Flex align="center" justify="space-between" style={{ marginBottom: 12 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          模板广场
        </Typography.Title>
        <Space size="middle">
          <Input.Search
            placeholder="搜索模板"
            allowClear
            style={{ width: 240 }}
            onChange={(e) => setKeyword(e.target.value)}
          />
          <Button icon={<PlusOutlined />} type="primary" onClick={openCreate}>
            创建模板
          </Button>
        </Space>
      </Flex>
      {renderSection('默认模板', official, '暂无默认模板')}
      {renderSection('私人模板', personal, '暂无私人模板')}
      {data.length === 0 && <Typography.Text type="secondary">暂无数据，请稍后重试。</Typography.Text>}

      <TemplateEditorModal
        open={modalOpen}
        mode="manage"
        template={activeTemplate}
        onClose={() => {
          setModalOpen(false)
          setActiveTemplate(null)
        }}
        onSave={async (payload) => {
          try {
            if (activeTemplate) {
              await update(activeTemplate.template_id, payload, userId || undefined)
              message.success('已更新模板')
            } else {
              await create(payload, userId || undefined)
              message.success('创建成功')
            }
            setModalOpen(false)
            setActiveTemplate(null)
            fetchTemplates(userId, useAuthStore.getState().tenantId || undefined)
          } catch {
            message.error(activeTemplate ? '更新失败，请稍后重试' : '创建失败，请稍后重试')
          }
        }}
      />
    </div>
  )
}

export default Templates
