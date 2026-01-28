import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'

const NotFound = () => {
  const navigate = useNavigate()
  return <Result status="404" title="页面不存在" extra={<Button onClick={() => navigate('/tasks')}>返回首页</Button>} />
}

export default NotFound
