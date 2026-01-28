import { Button, Card, Descriptions, Space, Typography } from 'antd'
import { useAuthStore } from '@/store/auth'

const Profile = () => {
  const { userId, tenantId, username, account, logout } = useAuthStore()

  return (
    <div className="page-container">
      <Typography.Title level={4}>个人中心</Typography.Title>
      <Card>
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="用户名">{username}</Descriptions.Item>
          <Descriptions.Item label="用户 ID">{account || userId}</Descriptions.Item>
          <Descriptions.Item label="租户 ID">{tenantId}</Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 12 }}>
          <Button type="primary">获取 Token</Button>
          <Button onClick={logout}>退出登录</Button>
        </Space>
      </Card>
    </div>
  )
}

export default Profile
