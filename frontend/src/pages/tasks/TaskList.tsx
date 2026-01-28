import { useEffect, useState, useMemo } from 'react'
import { Button, Card, Dropdown, Flex, Modal, Typography, message, Input, Select, Pagination } from 'antd'
import type { MenuProps } from 'antd'
import { EllipsisOutlined, DeleteOutlined, EditOutlined, FolderOpenOutlined, DownOutlined, UpOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTaskStore } from '@/store/task'
import { useFolderStore } from '@/store/folder'
import {
  renameTask,
  batchMoveTasks,
  batchDeleteTasks,
  batchRestoreTasks,
  deleteTaskPermanent,
} from '@/api/tasks'
import StatusTag from '@/components/StatusTag'
import type { TaskDetailResponse } from '@/types/frontend-types'

type TimeField = 'created_at' | 'updated_at'
type SortOrder = 'asc' | 'desc'

const formatDuration = (seconds?: number | null) => {
  if (seconds == null || Number.isNaN(seconds)) return '--:--'
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const getDisplayTime = (task: TaskDetailResponse & { last_content_modified_at?: string }) => {
  const display = task.last_content_modified_at || task.completed_at || task.created_at
  return display ? new Date(display).toLocaleString() : '--'
}

const getSortValue = (task: TaskDetailResponse & { last_content_modified_at?: string }, field: TimeField) => {
  if (field === 'created_at') return task.created_at || ''
  // updated_at 列使用内容修改时间优先
  return task.last_content_modified_at || task.updated_at || task.completed_at || task.created_at || ''
}

const TaskList = () => {
  const { list, trash, fetchList, fetchTrash } = useTaskStore()
  const { folders, fetch: fetchFolders } = useFolderStore()
  const location = useLocation()
  const [hoverId, setHoverId] = useState<string | null>(null)
  const [selectedByKey, setSelectedByKey] = useState<Record<string, Set<string>>>({})
  const [timeField, setTimeField] = useState<TimeField>('created_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [headerHover, setHeaderHover] = useState(false)
  const [pageSize, setPageSize] = useState(20)
  const [pageByKey, setPageByKey] = useState<Record<string, number>>({})
  const navigate = useNavigate()

  const folderFilter = useMemo(() => new URLSearchParams(location.search).get('folder'), [location.search])
  const isTrash = useMemo(() => location.pathname.startsWith('/tasks/trash'), [location.pathname])
  const listKey = useMemo(() => `${isTrash ? 'trash' : 'list'}:${folderFilter ?? 'all'}`, [isTrash, folderFilter])
  const workspaceSearch = useMemo(() => (isTrash ? '' : location.search), [isTrash, location.search])

  const selected = selectedByKey[listKey] ?? new Set<string>()
  const page = pageByKey[listKey] ?? 1

  const toggleSelect = (id: string) => {
    setSelectedByKey((prev) => {
      const next = new Set(prev[listKey] ?? new Set())
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return { ...prev, [listKey]: next }
    })
  }

  const clearSelection = () =>
    setSelectedByKey((prev) => ({
      ...prev,
      [listKey]: new Set(),
    }))

  useEffect(() => {
    fetchFolders()
  }, [fetchFolders])

  useEffect(() => {
    // 保持全量列表用于排序与全选，再做前端分页
    fetchList({ limit: 200, offset: 0, include_deleted: false })
    if (isTrash) {
      fetchTrash({ limit: 200, offset: 0 })
    }
  }, [fetchList, fetchTrash, isTrash])

  const effectiveList = useMemo(() => (isTrash ? trash : list), [isTrash, list, trash])

  const filteredList = useMemo(() => {
    if (isTrash) return effectiveList
    if (!folderFilter) return effectiveList
    if (folderFilter === 'uncategorized') return effectiveList.filter((item) => !(item as { folder_id?: string }).folder_id)
    return effectiveList.filter((item) => (item as { folder_id?: string }).folder_id === folderFilter)
  }, [effectiveList, folderFilter, isTrash])

  const sortedList = useMemo(() => {
    const arr = [...filteredList]
    arr.sort((a, b) => {
      const ta = new Date(getSortValue(a as TaskDetailResponse, timeField)).getTime()
      const tb = new Date(getSortValue(b as TaskDetailResponse, timeField)).getTime()
      return sortOrder === 'desc' ? tb - ta : ta - tb
    })
    return arr
  }, [filteredList, timeField, sortOrder])
  const displayTotal = sortedList.length
  const totalPages = Math.max(1, Math.ceil(sortedList.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const pagedList = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return sortedList.slice(start, start + pageSize)
  }, [currentPage, pageSize, sortedList])

  const folderMap = useMemo(() => {
    const map = new Map<string, string>()
    if (Array.isArray(folders)) {
      folders.forEach((f) => map.set(f.id, f.name))
    }
    return map
  }, [folders])

  const getFolderLabel = (item: TaskDetailResponse) => {
    const folderId = (item as { folder_id?: string | null }).folder_id || null
    if (!folderId) return '未分类'
    const folderPath = (item as { folder_path?: string }).folder_path
    return folderPath || folderMap.get(folderId) || folderId
  }

  const folderOptions = useMemo(() => {
    const opts = [{ value: 'uncategorized', label: '未分类' }]
    folders?.forEach((f) => opts.push({ value: f.id, label: f.name }))
    return opts
  }, [folders])

  const handleRename = (ids: string[]) => {
    const firstId = ids[0]
    const current = effectiveList.find((t) => t.task_id === firstId)
    const currentName =
      (current as { name?: string } | undefined)?.name ||
      (current as { display_name?: string } | undefined)?.display_name ||
      (current as { meeting_type?: string } | undefined)?.meeting_type ||
      current?.task_id ||
      ''
    let value = currentName
    Modal.confirm({
      title: ids.length > 1 ? '重命名（仅首个）' : '重命名',
      content: <Input defaultValue={value} onChange={(e) => (value = e.target.value)} />,
      onOk: async () => {
        if (!value) {
          message.warning('名称不能为空')
          return Promise.reject()
        }
        try {
          await renameTask(firstId, value)
          message.success('重命名成功')
          void fetchList({ limit: 200, offset: 0, include_deleted: false })
        } catch {
          message.error('重命名失败，请稍后重试')
        }
      },
    })
  }

  const handleMove = (ids: string[]) => {
    let target = folderOptions[0]?.value ?? 'uncategorized'
    Modal.confirm({
      title: '移至文件夹',
      content: (
        <Select
          style={{ width: '100%' }}
          defaultValue={target}
          onChange={(v) => {
            target = v
          }}
          options={folderOptions}
        />
      ),
      onOk: async () => {
        const folderId = target === 'uncategorized' ? null : target
        try {
          await batchMoveTasks(ids, folderId)
          message.success('已移动')
          await Promise.all([
            fetchList({ limit: 200, offset: 0, include_deleted: false }),
            fetchFolders(),
          ])
        } catch {
          message.error('移动失败，请稍后重试')
        }
      },
    })
  }

  const handleTrash = (ids: string[]) => {
    Modal.confirm({
      title: '移至回收站',
      content: `确定将${ids.length}条任务移至回收站？`,
      onOk: async () => {
        try {
          await batchDeleteTasks(ids)
          message.success('已移至回收站')
          clearSelection()
          const idSet = new Set(ids)
          useTaskStore.setState((state) => {
            const nextList = state.list.filter((t) => !idSet.has(t.task_id))
            return {
              list: nextList,
              total: Math.max(0, state.total - ids.length),
              trashTotal: state.trashTotal + ids.length,
            }
          })
          await Promise.all([
            fetchList({ limit: 200, offset: 0, include_deleted: false }),
            fetchTrash({ limit: 200, offset: 0 }),
          ])
        } catch {
          clearSelection()
          message.error('移至回收站失败，请稍后重试')
        }
      },
    })
  }

  const handleRestore = (ids: string[]) => {
    Modal.confirm({
      title: '恢复任务',
      content: `确定恢复${ids.length}条任务到原文件夹？`,
      onOk: async () => {
        try {
          await batchRestoreTasks(ids)
          message.success('已恢复')
          clearSelection()
          await Promise.all([
            fetchList({ limit: 200, offset: 0, include_deleted: false }),
            fetchTrash({ limit: 200, offset: 0 }),
          ])
        } catch {
          message.error('恢复失败，请稍后重试')
        }
      },
    })
  }

  const handlePermanentDelete = (ids: string[]) => {
    Modal.confirm({
      title: '永久删除',
      content: `确定彻底删除${ids.length}条任务？该操作不可撤销。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await Promise.all(ids.map((id) => deleteTaskPermanent(id)))
          message.success('已删除')
          clearSelection()
          // 乐观更新侧边栏计数与本地列表
          const idSet = new Set(ids)
          useTaskStore.setState((state) => ({
            trash: state.trash.filter((t) => !idSet.has(t.task_id)),
            trashTotal: Math.max(0, state.trashTotal - ids.length),
          }))
          await Promise.all([
            fetchTrash({ limit: 200, offset: 0 }),
            fetchList({ limit: 200, offset: 0, include_deleted: false }),
          ])
        } catch {
          message.error('删除失败，请稍后重试')
        }
      },
    })
  }

  const rowMenu = (id: string): MenuProps => ({
    items: isTrash
      ? [
          { key: 'restore', icon: <FolderOpenOutlined />, label: '恢复' },
          { key: 'delete', icon: <DeleteOutlined />, label: '删除', danger: true },
        ]
      : [
          { key: 'rename', icon: <EditOutlined />, label: '重命名' },
          { key: 'move', icon: <FolderOpenOutlined />, label: '移动到' },
          { key: 'delete', icon: <DeleteOutlined />, label: '移至回收站', danger: true },
        ],
    onClick: ({ key, domEvent }) => {
      domEvent?.stopPropagation()
      if (isTrash) {
        if (key === 'restore') handleRestore([id])
        if (key === 'delete') handlePermanentDelete([id])
        return
      }
      if (key === 'rename') handleRename([id])
      if (key === 'move') handleMove([id])
      if (key === 'delete') {
        handleTrash([id])
      }
    },
  })

  const toggleSort = (field: TimeField) => {
    if (timeField === field) {
      setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))
    } else {
      setTimeField(field)
      setSortOrder('desc')
    }
  }

  const renderSortLabel = (label: string, field: TimeField) => {
    const isActive = timeField === field
    const icon = sortOrder === 'desc' ? <DownOutlined /> : <UpOutlined />
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          cursor: 'pointer',
          userSelect: 'none',
          opacity: selected.size > 0 ? 0.3 : 1,
          fontWeight: selected.size > 0 ? 400 : 600,
        }}
        onClick={() => toggleSort(field)}
      >
        <span>{label}</span>
        {isActive ? icon : <DownOutlined style={{ opacity: 0.4 }} />}
      </div>
    )
  }

  const pageTitle = useMemo(() => {
    if (isTrash) return '回收站'
    if (folderFilter === 'uncategorized') return '未分类'
    if (folderFilter && folderMap.get(folderFilter)) return folderMap.get(folderFilter) as string
    if (folderFilter) return folderFilter
    return '全部任务'
  }, [folderFilter, folderMap, isTrash])

  return (
    <div className="page-container">
      <Typography.Title level={3} style={{ marginBottom: 12 }}>
        {pageTitle}
      </Typography.Title>

      <Card bodyStyle={{ padding: 0 }}>
        <div
          style={{
            display: selected.size > 0 ? 'none' : 'grid',
            gridTemplateColumns: '64px 2fr 1fr 1.1fr 1.1fr 1fr 0.5fr',
            padding: '14px 20px',
            color: '#666',
            fontSize: 14,
            minHeight: 48,
          }}
          onMouseEnter={() => setHeaderHover(true)}
          onMouseLeave={() => setHeaderHover(false)}
        >
          <div>
            <input
              type="checkbox"
              style={{ visibility: headerHover ? 'visible' : 'hidden' }}
              checked={selected.size > 0 && selected.size === filteredList.length}
              onChange={(e) => {
                if (e.target.checked) {
                  setSelectedByKey((prev) => ({ ...prev, [listKey]: new Set(filteredList.map((i) => i.task_id)) }))
                } else {
                  clearSelection()
                }
              }}
            />
          </div>
          <div style={{ fontWeight: 600 }}>名称</div>
          <div style={{ fontWeight: 600 }}>时长</div>
          {renderSortLabel('创建时间', 'created_at')}
          {renderSortLabel('修改时间', 'updated_at')}
          <div style={{ fontWeight: 600 }}>文件夹</div>
          <div style={{ textAlign: 'right' }} />
        </div>
        {selected.size > 0 && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '64px 2fr 1fr 1.1fr 1.1fr 1fr 0.5fr',
              padding: '14px 20px',
              alignItems: 'center',
              borderBottom: '1px solid #f0f0f0',
              minHeight: 48,
            }}
          >
            <div>
              <input
                type="checkbox"
                checked={selected.size === filteredList.length}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedByKey((prev) => ({ ...prev, [listKey]: new Set(filteredList.map((i) => i.task_id)) }))
                  } else {
                    clearSelection()
                  }
                }}
              />
            </div>
            <div style={{ gridColumn: '2 / span 1', color: '#666', fontSize: 14, fontWeight: 600 }}>
              <Typography.Text strong>已选（{selected.size}）</Typography.Text>
            </div>
            <div style={{ gridColumn: '3 / span 4', textAlign: 'left' }}>
              <Flex align="center" gap={12} justify="flex-start" wrap={false}>
                {isTrash ? (
                  <>
                    <Button
                      icon={<FolderOpenOutlined />}
                      size="small"
                      style={{ height: 30, paddingInline: 16 }}
                      onClick={() => handleRestore(Array.from(selected))}
                    >
                      恢复
                    </Button>
                    <Button
                      icon={<DeleteOutlined />}
                      size="small"
                      style={{ height: 30, paddingInline: 16 }}
                      danger
                      onClick={() => handlePermanentDelete(Array.from(selected))}
                    >
                      彻底删除
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      icon={<FolderOpenOutlined />}
                      size="small"
                      style={{ height: 30, paddingInline: 16 }}
                      onClick={() => handleMove(Array.from(selected))}
                    >
                      移至文件夹
                    </Button>
                    <Button
                      icon={<EditOutlined />}
                      size="small"
                      style={{ height: 30, paddingInline: 16 }}
                      disabled={selected.size !== 1}
                      onClick={() => handleRename(Array.from(selected))}
                    >
                      重命名
                    </Button>
                    <Button
                      icon={<DeleteOutlined />}
                      size="small"
                      style={{ height: 30, paddingInline: 16 }}
                      danger
                      onClick={() => handleTrash(Array.from(selected))}
                    >
                      回收站
                    </Button>
                  </>
                )}
                <div style={{ flex: 1 }} />
                <Flex align="center" justify="flex-end" style={{ minWidth: 80 }}>
                  <Button type="link" size="small" style={{ height: 30, paddingInline: 6 }} onClick={clearSelection}>
                    取消
                  </Button>
                </Flex>
              </Flex>
            </div>
          </div>
        )}
        {pagedList.map((item) => {
          const checked = selected.has(item.task_id)
          const showCheckbox = checked || hoverId === item.task_id
          return (
            <div
              key={item.task_id}
              onMouseEnter={() => setHoverId(item.task_id)}
              onMouseLeave={() => setHoverId(null)}
              style={{
                display: 'grid',
                gridTemplateColumns: '64px 2fr 1fr 1.1fr 1.1fr 1fr 0.5fr',
                alignItems: 'center',
                padding: '16px 20px',
                borderTop: '1px solid #f0f0f0',
                background: checked ? '#f7f7f9' : 'white',
                cursor: 'pointer',
              }}
              onClick={() => {
                if (isTrash) {
                  toggleSelect(item.task_id)
                  return
                }
                if (item.state === 'success' || item.state === 'partial_success') {
                  navigate(`/workspace/${item.task_id}${workspaceSearch}`)
                } else {
                  navigate(`/tasks/${item.task_id}/workbench`)
                }
              }}
            >
              <div>
                <input
                  type="checkbox"
                  style={{ visibility: showCheckbox ? 'visible' : 'hidden' }}
                  checked={checked}
                  onChange={(e) => {
                    e.stopPropagation()
                    toggleSelect(item.task_id)
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
              <div>
                <Typography.Text strong style={{ fontSize: 16 }}>
                  {(item as { display_name?: string }).display_name || item.meeting_type || item.task_id}
                </Typography.Text>
                <div style={{ marginTop: 4 }}>
                  <StatusTag state={item.state} /> <Typography.Text type="secondary">{item.task_id}</Typography.Text>
                </div>
              </div>
              <div>
                <Typography.Text>
                  {formatDuration((item as { duration?: number | null }).duration)}
                </Typography.Text>
              </div>
              <div>
                <Typography.Text>{item.created_at ? new Date(item.created_at).toLocaleString() : '--'}</Typography.Text>
              </div>
              <div>
                <Typography.Text>{getDisplayTime(item as TaskDetailResponse)}</Typography.Text>
              </div>
              <div>
                <Typography.Text type="secondary">
                  {getFolderLabel(item as TaskDetailResponse)}
                </Typography.Text>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Dropdown menu={rowMenu(item.task_id)} trigger={['click']}>
                  <Button type="text" icon={<EllipsisOutlined />} onClick={(e) => e.stopPropagation()} />
                </Dropdown>
              </div>
            </div>
          )
        })}
        {!sortedList.length && (
          <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>暂无任务</div>
        )}
        <div style={{ padding: '16px 20px', borderTop: '1px solid #f0f0f0' }}>
          <Pagination
            current={currentPage}
            pageSize={pageSize}
            total={displayTotal}
            showSizeChanger
            showQuickJumper
            showTotal={(value) => `共 ${value} 条`}
            onChange={(nextPage, nextSize) => {
              if (nextSize && nextSize !== pageSize) {
                setPageSize(nextSize)
                setPageByKey((prev) => ({ ...prev, [listKey]: 1 }))
              } else {
                setPageByKey((prev) => ({ ...prev, [listKey]: nextPage }))
              }
              // 移除 clearSelection()，保持选中状态跨页
            }}
          />
        </div>
      </Card>
    </div>
  )
}

export default TaskList
