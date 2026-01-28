import { Card, Typography, Empty } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'

const Trash = () => {
  return (
    <div className="page-container">
      <Typography.Title level={4}>回收站</Typography.Title>
      <Card>
        <Empty
          description="暂无已删除任务，可在此恢复或彻底清除（占位）"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <DeleteOutlined style={{ fontSize: 16 }} />
        </Empty>
      </Card>
    </div>
  )
}

export default Trash
