import { Spin } from 'antd'

const Loading = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
    <Spin size="large" />
  </div>
)

export default Loading
