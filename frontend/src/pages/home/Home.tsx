import { Card, Col, Row, Typography, Tag, Space, Button, List, Skeleton } from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listTasks } from '@/api/tasks'
import { useTemplateStore } from '@/store/template'
import { useAuthStore } from '@/store/auth'
import StatusTag from '@/components/StatusTag'
import type { TaskDetailResponse, PromptTemplate } from '@/types/frontend-types'

const latestNews = [
  { title: 'AI 纪要新版本发布', tag: '更新', time: '5 分钟前' },
  { title: '新增「销售跟进」模板', tag: '模板', time: '30 分钟前' },
  { title: '语音识别模型升级', tag: '系统', time: '1 小时前' },
]

const Home = () => {
  const navigate = useNavigate()
  const { templates, loading: tplLoading, fetchTemplates } = useTemplateStore()
  const { userId, tenantId } = useAuthStore()
  const [tasksLoading, setTasksLoading] = useState(false)
  const [latestTasks, setLatestTasks] = useState<TaskDetailResponse[]>([])
  const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  useEffect(() => {
    const loadTasks = async () => {
      setTasksLoading(true)
      try {
        const res = await listTasks({ limit: 6, offset: 0, include_deleted: false })
        const itemsRaw = Array.isArray((res as { items?: TaskDetailResponse[] })?.items)
          ? (res as { items: TaskDetailResponse[] }).items
          : Array.isArray(res)
            ? (res as TaskDetailResponse[])
            : []
        setLatestTasks(itemsRaw)
      } catch {
        setLatestTasks([])
      } finally {
        setTasksLoading(false)
      }
    }
    void loadTasks()
    fetchTemplates(userId || undefined, tenantId || undefined)
  }, [fetchTemplates, tenantId, userId])

  const taskCards: Array<TaskDetailResponse | undefined> = tasksLoading ? Array.from({ length: 4 }) : latestTasks.slice(0, 4)
  const templateCards: Array<PromptTemplate | undefined> = tplLoading ? Array.from({ length: 4 }) : templates.slice(0, 4)
  const getTaskName = (item?: TaskDetailResponse) =>
    item?.display_name || item?.meeting_type || (item as { name?: string })?.name || item?.task_id || ''
  const formatDate = (value?: string) => {
    if (!value) return '--'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '--'
    return dateFormatter.format(date)
  }

  return (
    <div className="page-container">
      <Typography.Title level={3} style={{ marginBottom: 16 }}>
        欢迎回来
      </Typography.Title>
      <Card
        title={
          <Space>
            <Typography.Text strong>查看会话</Typography.Text>
          </Space>
        }
        extra={
          <Button type="link" onClick={() => navigate('/tasks')}>
            前往任务 <ArrowRightOutlined />
          </Button>
        }
        style={{ borderRadius: 12, marginBottom: 16 }}
      >
        <Row gutter={12}>
          {taskCards.map((item, idx) => (
            <Col span={6} key={item?.task_id || idx}>
              <Card
                hoverable
                onClick={() => (item?.task_id ? navigate(`/workspace/${item.task_id}`) : undefined)}
                style={{ minHeight: 120 }}
              >
                {tasksLoading ? (
                  <Skeleton active paragraph={{ rows: 2 }} />
                ) : (
                  <>
                    <Typography.Text strong>{getTaskName(item)}</Typography.Text>
                    <div style={{ marginTop: 8 }}>
                      {item?.state && <StatusTag state={item.state} />}{' '}
                    </div>
                    <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
                      创建时间：{formatDate(item?.created_at)}
                    </Typography.Text>
                    <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 2 }}>
                      更新时间：{formatDate(item?.updated_at)}
                    </Typography.Text>
                  </>
                )}
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      <Card
        title={<Typography.Text strong>提示词模板</Typography.Text>}
        extra={
          <Button type="link" onClick={() => navigate('/templates')}>
            前往模板 <ArrowRightOutlined />
          </Button>
        }
        style={{ borderRadius: 12, marginBottom: 16 }}
      >
        <Row gutter={12}>
          {templateCards.map((tpl, idx) => (
            <Col span={6} key={tpl?.template_id || idx}>
              <Card
                hoverable
                onClick={() => (tpl?.template_id ? navigate(`/templates?focus=${tpl.template_id}`) : undefined)}
                style={{ minHeight: 120 }}
              >
                {tplLoading ? (
                  <Skeleton active paragraph={{ rows: 2 }} />
                ) : (
                  <>
                    <Typography.Text strong>{tpl?.title}</Typography.Text>
                    <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginTop: 4, marginBottom: 0 }}>
                      {tpl?.description || '暂无描述'}
                    </Typography.Paragraph>
                  </>
                )}
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      <Card title="公告与更新" style={{ borderRadius: 12 }}>
        <List
          grid={{ gutter: 16, column: 3 }}
          dataSource={latestNews}
          renderItem={(item) => (
            <List.Item>
              <Card hoverable>
                <Space>
                  <Tag color="blue">{item.tag}</Tag>
                  <div>
                    <Typography.Text strong>{item.title}</Typography.Text>
                    <div style={{ fontSize: 12, color: '#999' }}>{item.time}</div>
                  </div>
                </Space>
              </Card>
            </List.Item>
          )}
        />
      </Card>
    </div>
  )
}

export default Home
