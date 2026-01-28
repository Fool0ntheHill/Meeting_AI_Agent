import { Card, Typography, Empty, Button } from 'antd'
import { FolderAddOutlined } from '@ant-design/icons'

const Folders = () => {
  return (
    <div className="page-container">
      <Typography.Title level={4}>文件夹</Typography.Title>
      <Card>
        <Empty
          description="还没有文件夹，您可以创建并整理会议记录"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" icon={<FolderAddOutlined />}>
            新建文件夹（占位）
          </Button>
        </Empty>
      </Card>
    </div>
  )
}

export default Folders
