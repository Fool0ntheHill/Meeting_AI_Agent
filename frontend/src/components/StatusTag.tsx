import { Tag } from 'antd'
import type { TaskState } from '@/types/frontend-types'

const colors: Record<TaskState, string> = {
  pending: 'default',
  queued: 'blue',
  running: 'processing',
  transcribing: 'geekblue',
  identifying: 'cyan',
  correcting: 'orange',
  summarizing: 'purple',
  success: 'green',
  failed: 'red',
  partial_success: 'gold',
}

const labels: Record<TaskState, string> = {
  pending: '待处理',
  queued: '排队中',
  running: '执行中',
  transcribing: '转写中',
  identifying: '说话人识别',
  correcting: '修正中',
  summarizing: '纪要生成',
  success: '已完成',
  failed: '失败',
  partial_success: '部分成功',
}

export const StatusTag = ({ state }: { state: TaskState }) => <Tag color={colors[state]}>{labels[state]}</Tag>

export default StatusTag
