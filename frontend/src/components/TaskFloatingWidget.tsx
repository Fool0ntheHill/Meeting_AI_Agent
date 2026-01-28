import { Tooltip, Progress } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTaskRunnerStore } from '@/store/task-runner'
import './TaskFloatingWidget.css'

const TaskFloatingWidget = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { tasks } = useTaskRunnerStore()
  const isWorkbench = location.pathname.includes('/workbench')

  if (isWorkbench) return null

  const running = Object.values(tasks).filter((task) => task.status === 'PROCESSING')
  if (running.length === 0) return null

  const active = running.sort((a, b) => b.updatedAt - a.updatedAt)[0]
  const percent = Math.round(active.progress)

  return (
    <div className="task-floating-widget" onClick={() => navigate(`/tasks/${active.taskId}/workbench`)}>
      <Tooltip title={active.title}>
        <div className="task-floating-widget__inner">
          <Progress type="circle" width={56} percent={percent} strokeColor="#1677ff" />
        </div>
      </Tooltip>
    </div>
  )
}

export default TaskFloatingWidget
