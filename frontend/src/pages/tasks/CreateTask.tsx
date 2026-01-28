import { useMemo, useState } from 'react'
import { Alert, Button, Card, Divider, Space, Typography, Upload, message } from 'antd'
import { ArrowRightOutlined, InboxOutlined, DeleteOutlined, MenuOutlined } from '@ant-design/icons'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { UploadRequestOption as RcCustomRequestOptions } from 'rc-upload/lib/interface'
import { useNavigate } from 'react-router-dom'
import { uploadAudio } from '@/api/tasks'
import { useCreateTaskDraftStore, type UploadedAudio } from '@/store/createTaskDraft'
import { ENV } from '@/config/env'
import CreateTaskSteps from './CreateTaskSteps'
import './create-task.css'

const audioTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg', 'audio/x-m4a', 'audio/webm']
const maxSizeMb = 1024

const readAudioDuration = (file: File) =>
  new Promise<number | null>((resolve) => {
    const audio = document.createElement('audio')
    audio.preload = 'metadata'
    const url = URL.createObjectURL(file)
    const cleanup = () => {
      URL.revokeObjectURL(url)
    }
    audio.onloadedmetadata = () => {
      const value = Number.isFinite(audio.duration) ? audio.duration : null
      cleanup()
      resolve(value)
    }
    audio.onerror = () => {
      cleanup()
      resolve(null)
    }
    audio.src = url
  })

const CreateTask = () => {
  const navigate = useNavigate()
  const [uploading, setUploading] = useState(false)
  const { fileList, uploads, setFileList, addUpload, removeUpload, reorderUploads, setUploadsWithFiles } = useCreateTaskDraftStore()
  const [activeId, setActiveId] = useState<string | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  const beforeUpload = (file: File) => {
    if (!audioTypes.includes(file.type)) {
      message.error('仅支持 wav/mp3/m4a/opus/webm')
      return Upload.LIST_IGNORE
    }
    const sizeMb = file.size / 1024 / 1024
    if (sizeMb > maxSizeMb) {
      message.error(`单文件需小于 ${maxSizeMb}MB`)
      return Upload.LIST_IGNORE
    }
    return true
  }

  const customRequest = async ({ file, onSuccess, onError }: RcCustomRequestOptions) => {
    try {
      setUploading(true)
      const rawFile = file as File
      const [duration, res] = await Promise.all([readAudioDuration(rawFile), uploadAudio(rawFile)])
      const rcFile = file as { uid?: string; name?: string }
      const fallbackId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      addUpload({
        uid: rcFile.uid ?? rcFile.name ?? fallbackId,
        name: rcFile.name ?? '未命名文件',
        original_filename: res.original_filename ?? rcFile.name ?? '未命名文件',
        file_path: res.file_path,
        duration,
      })
      onSuccess?.(res as never)
    } catch (err) {
      onError?.(err as Error)
    } finally {
      setUploading(false)
    }
  }

  const onNext = () => {
    if (uploads.length === 0) {
      message.warning('请先上传音频文件')
      return
    }
    navigate('/tasks/create/config')
  }

  const onSeedMock = () => {
    setUploadsWithFiles([
      {
        uid: `mock-${Date.now()}-1`,
        name: '需求评审-上半场.wav',
        file_path: 'mock/meeting_part1.wav',
        duration: 812,
      },
      {
        uid: `mock-${Date.now()}-2`,
        name: '需求评审-下半场.ogg',
        file_path: 'mock/meeting_part2.ogg',
        duration: 1045,
      },
    ])
    message.success('已注入示例音频，可继续体验后续步骤')
  }

  const formatDuration = (seconds?: number | null) => {
    if (!seconds || Number.isNaN(seconds)) return '--'
    const total = Math.max(0, Math.round(seconds))
    const mins = Math.floor(total / 60)
    const secs = total % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      const oldIndex = uploads.findIndex((item) => item.uid === active.id)
      const newIndex = uploads.findIndex((item) => item.uid === over.id)
      if (oldIndex !== -1 && newIndex !== -1) {
        const next = arrayMove(uploads, oldIndex, newIndex)
        reorderUploads(next)
      }
    }
    setActiveId(null)
  }

  const activeItem = useMemo(() => (activeId ? uploads.find((item) => item.uid === activeId) || null : null), [activeId, uploads])
  const activeIndex = useMemo(
    () => (activeItem ? uploads.findIndex((item) => item.uid === activeItem.uid) : 0),
    [activeItem, uploads]
  )

  const SortableItem = ({ item, index }: { item: UploadedAudio; index: number }) => {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.uid })
    const style = {
      transform: CSS.Transform.toString(transform),
      transition,
    }
    return (
      <div
        ref={setNodeRef}
        style={style}
        className={`sortable-item${isDragging ? ' sortable-item--placeholder' : ''}`}
        {...attributes}
        {...listeners}
      >
        <div className="sortable-item__content">
          <div className="sortable-item__meta">
            <span className="sortable-item__index">{index + 1}</span>
            <div>
              <Typography.Text>{item.name}</Typography.Text>
              <div>
                <Typography.Text type="secondary">时长 {formatDuration(item.duration)}</Typography.Text>
              </div>
            </div>
          </div>
          <Space size={12}>
            <DeleteOutlined onClick={(e) => { e.stopPropagation(); removeUpload(item.uid) }} style={{ color: '#ff4d4f' }} />
            <MenuOutlined className="sortable-item__handle" />
          </Space>
        </div>
      </div>
    )
  }

  const DragOverlayItem = ({ item, index }: { item: UploadedAudio; index: number }) => (
    <div className="sortable-item sortable-item--overlay">
      <div className="sortable-item__content">
        <div className="sortable-item__meta">
          <span className="sortable-item__index">{index + 1}</span>
          <div>
            <Typography.Text>{item.name}</Typography.Text>
            <div>
              <Typography.Text type="secondary">时长 {formatDuration(item.duration)}</Typography.Text>
            </div>
          </div>
        </div>
        <MenuOutlined className="sortable-item__handle" />
      </div>
    </div>
  )

  return (
    <div className="page-container create-task">
      <div className="create-task__center">
        <Typography.Title level={3} className="create-task__title">
          上传并排序音频
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="create-task__subtitle">
          支持多文件上传，上传后可直接拖拽排序；系统会按顺序拼接并标记说话人。
        </Typography.Paragraph>
        <CreateTaskSteps current={0} />
        <Card className="create-task__card" bordered={false}>
          <div className="create-task__upload-row">
            <Upload.Dragger
              multiple
              fileList={fileList}
              beforeUpload={beforeUpload}
            customRequest={customRequest}
            onChange={(info) => {
              setFileList(info.fileList)
              if (info.file.status === 'removed') {
                removeUpload(info.file.uid)
              }
            }}
            accept={audioTypes.join(',')}
            showUploadList={false}
              style={{ minHeight: 300 }}
          >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">拖拽或点击上传</p>
              <p className="ant-upload-hint">支持多文件上传，单文件不超过 {maxSizeMb}MB</p>
            </Upload.Dragger>
            <div className="create-task__tips-card">
              <Typography.Title level={5} style={{ marginBottom: 12 }}>
                上传小贴士
              </Typography.Title>
              <div className="create-task__tips">
                <Typography.Text>• 支持 wav/mp3/m4a/ogg/opus/webm，多个文件可分次上传。</Typography.Text>
                <Typography.Text>• 上传完成后可拖拽调整顺序，顺序即转写顺序。</Typography.Text>
                <Typography.Text>• 系统会按顺序自动拼接音频文件。</Typography.Text>
              </div>
            </div>
          </div>
          {ENV.ENABLE_MOCK && uploads.length === 0 && (
            <div style={{ marginTop: 12 }}>
              <Button onClick={onSeedMock}>使用示例数据体验后续流程</Button>
              <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
                Mock 模式下上传接口不可用时可直接体验后续页面
              </Typography.Text>
            </div>
          )}
          {uploads.length > 0 && (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
              onDragCancel={() => setActiveId(null)}
            >
              <SortableContext items={uploads.map((item) => item.uid)} strategy={verticalListSortingStrategy}>
                <div className="sortable-list">
                  {uploads.map((item, index) => (
                    <SortableItem key={item.uid} item={item} index={index} />
                  ))}
                </div>
              </SortableContext>
              <DragOverlay>{activeItem ? <DragOverlayItem item={activeItem} index={activeIndex} /> : null}</DragOverlay>
            </DndContext>
          )}
          <Space className="create-task__actions">
            <Button type="primary" icon={<ArrowRightOutlined />} onClick={onNext} loading={uploading} disabled={uploads.length === 0}>
              下一步：选择配置
            </Button>
          </Space>
        </Card>
      </div>
    </div>
  )
}

export default CreateTask
