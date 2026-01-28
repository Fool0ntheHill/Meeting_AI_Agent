import { useState } from 'react'
import { Button, Card, Typography, message } from 'antd'
import { ArrowLeftOutlined, ArrowRightOutlined, MenuOutlined } from '@ant-design/icons'
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
import { useNavigate } from 'react-router-dom'
import { useCreateTaskDraftStore, type UploadedAudio } from '@/store/createTaskDraft'
import CreateTaskSteps from './CreateTaskSteps'
import './create-task.css'

const formatDuration = (seconds?: number | null) => {
  if (!seconds || Number.isNaN(seconds)) return '--'
  const total = Math.max(0, Math.round(seconds))
  const hrs = Math.floor(total / 3600)
  const mins = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hrs > 0) {
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

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
        <MenuOutlined className="sortable-item__handle" />
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

const CreateTaskSort = () => {
  const navigate = useNavigate()
  const { uploads, reorderUploads } = useCreateTaskDraftStore()
  const [activeId, setActiveId] = useState<string | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

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

  const handleNext = () => {
    if (uploads.length === 0) {
      message.warning('请先上传音频文件')
      navigate('/tasks/create')
      return
    }
    navigate('/tasks/create/config')
  }

  const activeItem = activeId ? uploads.find((item) => item.uid === activeId) || null : null
  const activeIndex = activeItem ? uploads.findIndex((item) => item.uid === activeItem.uid) : 0

  return (
    <div className="page-container create-task">
      <div className="create-task__center">
        <Typography.Title level={3} className="create-task__title">
          拖拽排序音频
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="create-task__subtitle">
          轻轻拖拽即可调整顺序，松手即生效。系统会根据顺序生成说话人编号，体验更丝滑。
        </Typography.Paragraph>
        <CreateTaskSteps current={1} />
        <Card className="create-task__step-card" bordered={false}>
          {uploads.length === 0 ? (
            <Typography.Text type="secondary">暂无已上传文件，请先返回上传。</Typography.Text>
          ) : (
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
              <DragOverlay>
                {activeItem ? <DragOverlayItem item={activeItem} index={activeIndex} /> : null}
              </DragOverlay>
            </DndContext>
          )}
          <div className="create-task__step-actions">
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks/create')}>
              上一步：上传
            </Button>
            <Button type="primary" icon={<ArrowRightOutlined />} onClick={handleNext} disabled={uploads.length === 0}>
              下一步：选择配置
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default CreateTaskSort
