import { Navigate, useParams } from 'react-router-dom'

const TaskDetailRedirect = () => {
  const { id } = useParams<{ id: string }>()
  return <Navigate to={id ? `/workspace/${id}` : '/tasks'} replace />
}

export default TaskDetailRedirect
