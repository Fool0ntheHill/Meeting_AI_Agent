/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useRef, useState, useCallback } from 'react'
import { Button, Card, Descriptions, Flex, Progress, Space, Typography, Alert } from 'antd'
import { ReloadOutlined, PlayCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { useTaskStore } from '@/store/task'
import StatusTag from '@/components/StatusTag'
import { createExponentialPoller } from '@/utils/polling'

const TaskDetail = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentTask, status, fetchDetail, fetchStatus } = useTaskStore()
  const pollerRef = useRef<{ stop: () => void } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setError(null)
    try {
      await fetchDetail(id)
    } catch (err) {
      setError((err as Error)?.message || '获取详情失败')
    }
  }, [id, fetchDetail])

  const startPolling = useCallback(() => {
    if (!id) return
    pollerRef.current?.stop()
    pollerRef.current = createExponentialPoller({
      fetcher: () => fetchStatus(id),
      onUpdate: () => {},
      isDone: (data) => data.state === 'success' || data.state === 'failed',
      initialInterval: 2000,
      maxInterval: 10000,
    })
  }, [id, fetchStatus])

  // 轮询与详情加载
  useEffect(() => {
    void load()
    startPolling()
    return () => {
      pollerRef.current?.stop()
    }
  }, [id, fetchDetail, fetchStatus, load, startPolling])

  if (!id) return null

  return (
    <div className="page-container">
      <Flex align="center" justify="space-between" style={{ marginBottom: 12 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          任务详情
        </Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => fetchStatus(id)}>
            手动刷新状态
          </Button>
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => navigate(`/workspace/${id}`)}>
            进入工作台
          </Button>
        </Space>
      </Flex>
      {error && <Alert type="error" message={error} style={{ marginBottom: 12 }} />}
      <Card>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="任务 ID">{id}</Descriptions.Item>
          <Descriptions.Item label="会议类型">{currentTask?.meeting_type || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {status?.state ? <StatusTag state={status.state} /> : currentTask?.state && <StatusTag state={currentTask.state} />}
          </Descriptions.Item>
          <Descriptions.Item label="进度">{status?.progress ?? currentTask?.progress ?? 0}%</Descriptions.Item>
          <Descriptions.Item label="创建时间">{currentTask?.created_at || '-'}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{currentTask?.updated_at || '-'}</Descriptions.Item>
        </Descriptions>
        <div style={{ marginTop: 16 }}>
          <Progress percent={status?.progress ?? currentTask?.progress ?? 0} status={status?.state === 'failed' ? 'exception' : 'active'} />
          {status?.estimated_time && status.estimated_time > 0 && (
            <Typography.Text type="secondary">预计剩余时间：{status.estimated_time}s</Typography.Text>
          )}
          {(status?.state === 'failed' || currentTask?.state === 'failed') && (
            <Alert
              style={{ marginTop: 12 }}
              type="error"
              message="处理失败"
              description={status?.error_details || currentTask?.error_details || '请重试或联系支持'}
              showIcon
              icon={<ExclamationCircleOutlined />}
            />
          )}
        </div>
      </Card>
    </div>
  )
}

export default TaskDetail
