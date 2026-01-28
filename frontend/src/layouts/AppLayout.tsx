import { Layout, Button, Space, Typography, Dropdown, Avatar, Modal, Form, Input, message } from 'antd'
import {
  AppstoreOutlined,
  FileTextOutlined,
  FolderOutlined,
  HomeOutlined,
  LogoutOutlined,
  PlusOutlined,
  ProfileOutlined,
  DeleteOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  EditOutlined,
  EllipsisOutlined,
  DownOutlined,
  RightOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { useTaskStore } from '@/store/task'
import { useFolderStore } from '@/store/folder'
import { useEffect, useMemo, useState, type CSSProperties } from 'react'
// logo 暂时隐藏

const { Sider, Content } = Layout

const navButtonStyle: CSSProperties = {
  justifyContent: 'flex-start',
  width: '100%',
  border: 'none',
  height: 40,
  paddingInline: 12,
}

type FlatFolder = {
  id: string
  name: string
  count: number
}

type StoredFolder = {
  id: string
  folder_id?: string
  name: string
}

const AppLayout = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout, username, account, hydrate } = useAuthStore()
  const { list: taskList, fetchList, trashTotal, fetchTrash } = useTaskStore()
  const { folders, fetch: fetchFolders, add, rename, remove } = useFolderStore()
  const [collapsed, setCollapsed] = useState(false)
  const [foldersOpen, setFoldersOpen] = useState(true)
  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [editingFolder, setEditingFolder] = useState<FlatFolder | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<FlatFolder | null>(null)
  const [hoveredFolder, setHoveredFolder] = useState<string | null>(null)
  const [plusHover, setPlusHover] = useState(false)
  const [form] = Form.useForm<Pick<FlatFolder, 'name'>>()

  useEffect(() => {
    hydrate()
  }, [hydrate])

  useEffect(() => {
    void fetchList({ limit: 200, offset: 0, include_deleted: false })
    void fetchFolders()
    void fetchTrash({ limit: 200, offset: 0 })
  }, [fetchList, fetchFolders, fetchTrash])

  const active = useMemo(() => {
    const path = location.pathname
    const search = new URLSearchParams(location.search)
    if (path.startsWith('/home')) return 'home'
    if (path.startsWith('/templates')) return 'templates'
    if (path.startsWith('/tasks/trash')) return 'tasks-trash'
    if (path.startsWith('/tasks/folders')) return 'tasks-folders'
    if (path.startsWith('/tasks') && search.get('folder') === 'uncategorized') return 'tasks-uncat'
    if (path.startsWith('/tasks') && search.get('folder')) return 'tasks-folder'
    if (path.startsWith('/tasks')) return 'tasks-all'
    return ''
  }, [location.pathname, location.search])

  const activeFolderId = useMemo(() => {
    const search = new URLSearchParams(location.search)
    const folder = search.get('folder')
    if (folder && folder !== 'uncategorized') return folder
    return null
  }, [location.search])

  const { totalCount, uncatCount, folderTags } = useMemo(() => {
    const folderList: StoredFolder[] = Array.isArray(folders) ? folders : []
    const total = taskList.length
    const uncat = taskList.filter((t) => {
      const folderId = (t as { folder_id?: string }).folder_id
      return !folderId
    }).length
    const map = new Map<string, FlatFolder>()
    folderList.forEach((folder) => {
      const folderId = folder.folder_id ?? folder.id ?? ''
      if (!folderId) return
      map.set(folderId, { id: folderId, name: folder.name, count: 0 })
    })
    taskList.forEach((t) => {
      const folderId = (t as { folder_id?: string }).folder_id
      if (!folderId) return
      const prev = map.get(folderId)
      if (prev) {
        prev.count += 1
      }
    })
    return { totalCount: total, uncatCount: uncat, folderTags: Array.from(map.values()) }
  }, [taskList, folders])

  const openCreate = () => {
    setFoldersOpen(true)
    setEditingFolder(null)
    form.setFieldsValue({ name: '' })
    setFolderModalOpen(true)
  }

  const openEdit = (folder: FlatFolder) => {
    setEditingFolder(folder)
    form.setFieldsValue({ name: folder.name })
    setFolderModalOpen(true)
  }

  const onSubmitFolder = async () => {
    try {
      const values = await form.validateFields()
      if (editingFolder) {
        await rename(editingFolder.id, values.name)
      } else {
        await add(values.name)
        setFoldersOpen(true)
      }
      message.success(editingFolder ? '已更新文件夹' : '已创建文件夹')
      setFolderModalOpen(false)
      setEditingFolder(null)
    } catch {
      // ignore
    }
  }

  return (
    <>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider
          width={252}
          collapsedWidth={56}
          collapsible
          collapsed={collapsed}
          trigger={null}
          style={{
            background: '#fff',
            borderRight: '1px solid #f0f0f0',
            padding: collapsed ? 8 : 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            transition: 'none',
            transform: 'translateZ(0)',
          }}
        >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            paddingInline: 8,
            marginBottom: 6,
            height: 40,
            transform: 'translateZ(0)',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            onClick={() => setCollapsed((v) => !v)}
          />
        </div>

        {!collapsed && (
        <>
        <div
          className="user-card"
          style={{
            borderRadius: 8,
            padding: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            minHeight: 48,
          }}
        >
          <Dropdown
            trigger={['click']}
            menu={{
              items: [
                { key: 'profile', label: '个人中心', icon: <ProfileOutlined />, onClick: () => navigate('/profile') },
                { key: 'logout', label: '退出登录', icon: <LogoutOutlined />, onClick: logout },
              ],
            }}
          >
            <Space style={{ cursor: 'pointer' }}>
              <Avatar size={34} style={{ backgroundColor: '#d1cfd4' }}>
                {(username || 'U').slice(0, 1).toUpperCase()}
              </Avatar>
              {!collapsed && (
                <div style={{ lineHeight: 1.2 }}>
                  <Typography.Text strong style={{ fontSize: 14, color: '#2e2e2e' }}>
                    {username || '未登录'}
                  </Typography.Text>
                  <div style={{ fontSize: 12, color: '#7a7a7a' }}>
                    ID: {account || '待登录'}
                  </div>
                </div>
              )}
            </Space>
          </Dropdown>
        </div>

        <Button
          type="default"
          icon={<PlusOutlined />}
          block
          style={{
            height: 44,
            borderRadius: 10,
            fontSize: 15,
            marginTop: 16,
            marginBottom: 16,
            background: collapsed ? '#fff' : '#f7f5f7',
            border: collapsed ? 'none' : '1px solid #d8d4d8',
            color: '#1f1f1f',
            transform: 'translateZ(0)',
          }}
          onClick={() => navigate('/tasks/create')}
        >
          {!collapsed && '新增任务'}
        </Button>

        <div style={{ marginTop: 6, paddingTop: 12, borderTop: '1px solid #ebe7ec' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type={active === 'home' ? 'default' : 'text'}
              icon={<HomeOutlined />}
              style={{
                ...navButtonStyle,
                paddingInline: collapsed ? 0 : 12,
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active === 'home' ? 'rgba(31,35,41,0.08)' : undefined,
              }}
              onClick={() => navigate('/home')}
            >
              {!collapsed && '主页'}
            </Button>
            <Button
              type={active === 'templates' ? 'default' : 'text'}
              icon={<FileTextOutlined />}
              style={{
                ...navButtonStyle,
                paddingInline: collapsed ? 0 : 12,
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active === 'templates' ? 'rgba(31,35,41,0.08)' : undefined,
              }}
              onClick={() => navigate('/templates')}
            >
              {!collapsed && '模板广场'}
            </Button>
          </Space>
        </div>

        <div style={{ paddingTop: 12, borderTop: '1px solid #ebe7ec' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type={active === 'tasks-all' ? 'default' : 'text'}
              icon={<AppstoreOutlined />}
              style={{
                ...navButtonStyle,
                paddingInline: collapsed ? 0 : 12,
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active === 'tasks-all' ? 'rgba(31,35,41,0.08)' : undefined,
              }}
              onClick={() => navigate('/tasks')}
            >
              {!collapsed && (
                <Space size={6}>
                  <Typography.Text>全部任务</Typography.Text>
                  <Typography.Text type="secondary">({totalCount})</Typography.Text>
                </Space>
              )}
            </Button>
            <Button
              type={active === 'tasks-uncat' ? 'default' : 'text'}
              icon={<FileTextOutlined />}
              style={{
                ...navButtonStyle,
                paddingInline: collapsed ? 0 : 12,
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active === 'tasks-uncat' ? 'rgba(31,35,41,0.08)' : undefined,
              }}
              onClick={() => navigate('/tasks?folder=uncategorized')}
            >
              {!collapsed && (
                <Space size={6}>
                  <Typography.Text>未分类</Typography.Text>
                  <Typography.Text type="secondary">({uncatCount})</Typography.Text>
                </Space>
              )}
            </Button>
            <Button
              type={active === 'tasks-trash' ? 'default' : 'text'}
              icon={<DeleteOutlined />}
              style={{
                ...navButtonStyle,
                paddingInline: collapsed ? 0 : 12,
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active === 'tasks-trash' ? 'rgba(31,35,41,0.08)' : undefined,
                transform: 'translateZ(0)',
              }}
              onClick={() => navigate('/tasks/trash')}
            >
              {!collapsed && (
                <Space size={6}>
                  <Typography.Text>回收站</Typography.Text>
                  <Typography.Text type="secondary">({trashTotal})</Typography.Text>
                </Space>
              )}
            </Button>
            <div style={{ borderTop: '1px solid #f0f0f0', marginTop: 8, marginBottom: 8 }} />
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                paddingInline: collapsed ? 0 : 6,
                borderRadius: 10,
                background: 'transparent',
                gap: 6,
                height: 44,
              }}
            >
              <Button
                type="text"
                icon={<FolderOutlined />}
                style={{
                  ...navButtonStyle,
                  paddingInline: collapsed ? 0 : 10,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  background: 'transparent',
                  flex: 1,
                  height: 32,
                }}
                onClick={() => setFoldersOpen((v) => !v)}
              >
                {!collapsed && (
                  <Space size={8}>
                    <Typography.Text>文件夹</Typography.Text>
                    {foldersOpen ? (
                      <DownOutlined style={{ fontSize: 13, color: '#8c8c8c' }} />
                    ) : (
                      <RightOutlined style={{ fontSize: 13, color: '#8c8c8c' }} />
                    )}
                  </Space>
                )}
              </Button>
              {!collapsed && (
                <Button
                  size="small"
                  type="text"
                  icon={<PlusOutlined />}
                  style={{
                    width: 32,
                    height: 32,
                    border: 'none',
                    boxShadow: 'none',
                    background: plusHover ? '#e1e1e5' : 'transparent',
                  }}
                  onMouseEnter={() => setPlusHover(true)}
                  onMouseLeave={() => setPlusHover(false)}
                  onClick={(e) => {
                    e.stopPropagation()
                    openCreate()
                  }}
                />
              )}
            </div>
            {!collapsed && (
              <div
                style={{
                  overflow: 'hidden',
                  transition: 'max-height 0.25s ease, opacity 0.2s ease',
                  maxHeight: foldersOpen ? Math.max(0, folderTags.length * 48 + 8) : 0,
                  opacity: foldersOpen ? 1 : 0,
                }}
              >
                {folderTags.map((tag) => (
                  <div
                    key={tag.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      paddingInline: 12,
                      borderRadius: 8,
                      gap: 6,
                      background: hoveredFolder === tag.id || activeFolderId === tag.id ? '#e1e1e5' : 'transparent',
                      transition: 'background 0.15s',
                      marginBottom: 4,
                      paddingBlock: 2,
                    }}
                    onMouseEnter={() => setHoveredFolder(tag.id)}
                    onMouseLeave={() => setHoveredFolder(null)}
                  >
                    <Button
                      type="text"
                      icon={<FolderOutlined />}
                      style={{
                        ...navButtonStyle,
                        paddingInline: 8,
                        justifyContent: 'flex-start',
                        background: 'transparent',
                        flex: 1,
                        height: 32,
                      }}
                      onClick={() => navigate(`/tasks?folder=${encodeURIComponent(tag.id)}`)}
                    >
                      <Space size={6}>
                        <Typography.Text>{tag.name}</Typography.Text>
                        <Typography.Text type="secondary">({tag.count})</Typography.Text>
                      </Space>
                    </Button>
                    <Dropdown
                      menu={{
                        items: [
                          { key: 'rename', label: '重命名', icon: <EditOutlined />, onClick: () => openEdit(tag) },
                          { key: 'delete', label: '删除', icon: <DeleteOutlined />, onClick: () => setConfirmDelete(tag) },
                        ],
                      }}
                    >
                      <Button
                        type="text"
                        style={{
                          width: 26,
                          minWidth: 26,
                          height: 28,
                          padding: 0,
                          background:
                            hoveredFolder === tag.id || activeFolderId === tag.id ? '#e1e1e5' : 'transparent',
                          borderRadius: 6,
                          opacity: hoveredFolder === tag.id || activeFolderId === tag.id ? 1 : 0,
                          transition: 'opacity 0.15s, background 0.15s',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = '#d8d8dd'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = hoveredFolder === tag.id ? '#e1e1e5' : 'transparent'
                        }}
                        icon={<EllipsisOutlined />}
                      />
                    </Dropdown>
                  </div>
                ))}
              </div>
            )}
          </Space>
        </div>
        </>
        )}

        </Sider>
        <Layout>
          <Content style={{ padding: 16 }}>
            <Outlet />
          </Content>
        </Layout>
      </Layout>

      <Modal
        title={editingFolder ? '重命名文件夹' : '新建文件夹'}
        open={folderModalOpen}
        onOk={onSubmitFolder}
        onCancel={() => {
          setFolderModalOpen(false)
          setEditingFolder(null)
        }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="文件夹名称"
            name="name"
            rules={[{ required: true, message: '请输入文件夹名称' }]}
          >
            <Input placeholder="例如：产品会议" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="删除文件夹"
        open={!!confirmDelete}
        centered
        onOk={() => {
          // TODO: 接入后端删除文件夹并刷新列表
      message.success('已删除文件夹')
      if (confirmDelete) {
        void remove(confirmDelete.id)
      }
      setConfirmDelete(null)
        }}
        onCancel={() => setConfirmDelete(null)}
        okText="删除"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          此文件夹将被永久删除，无法恢复。文件夹中的任务会移至未分类，请在任务列表中查看。
        </Typography.Paragraph>
      </Modal>
    </>
  )
}

export default AppLayout
