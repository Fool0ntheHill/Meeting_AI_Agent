import { useEffect, useMemo } from 'react'
import { FileTextOutlined } from '@ant-design/icons'
import { Typography, Spin } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useTaskStore } from '@/store/task'
import { useFolderStore } from '@/store/folder'
import type { TaskDetailResponse } from '@/types/frontend-types'

interface FileSidebarProps {
  listFilter?: string | null
}

type TaskListItem = TaskDetailResponse & {
  folder_id?: string | null
  folder_path?: string
  display_name?: string
  name?: string
}

const FileSidebar = ({ listFilter }: FileSidebarProps) => {
  const navigate = useNavigate()
  const { id: currentTaskId } = useParams<{ id: string }>()
  const { list, fetchList, loading } = useTaskStore()
  const { fetch: fetchFolders } = useFolderStore()

  // Fetch tasks for the current folder (or root if null)
  useEffect(() => {
    const folderParam = listFilter === 'uncategorized' ? null : listFilter || undefined
    fetchList({
      folder_id: folderParam,
      limit: 100,
      offset: 0,
    })
  }, [fetchList, listFilter])

  useEffect(() => {
    fetchFolders()
  }, [fetchFolders])

  const filteredList = useMemo(() => {
    const items = list as TaskListItem[]
    const completed = items.filter((task) => task.state === 'success' || task.state === 'partial_success')
    if (!listFilter) return completed
    if (listFilter === 'uncategorized') return completed.filter((task) => !task.folder_id)
    return completed.filter((task) => task.folder_id === listFilter)
  }, [list, listFilter])

  const listSearch = listFilter === 'uncategorized'
    ? '?folder=uncategorized'
    : listFilter
      ? `?folder=${encodeURIComponent(listFilter)}`
      : ''

  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }),
    []
  )

  return (
    <div className="workspace-filelist">
      <div className="workspace-filelist__header">
        <Typography.Text strong>文件列表</Typography.Text>
      </div>

      <div className="workspace-filelist__body">
        {loading && list.length === 0 ? (
          <div className="workspace-filelist__loading">
            <Spin size="small" />
          </div>
        ) : filteredList.length === 0 ? (
          <div className="workspace-filelist__empty">暂无任务</div>
        ) : (
          <div className="workspace-filelist__items">
            {filteredList.map((item) => {
              const isActive = item.task_id === currentTaskId
              return (
                <button
                  type="button"
                  key={item.task_id}
                  onClick={() => navigate(`/workspace/${item.task_id}${listSearch}`)}
                  className={`workspace-filelist__item${isActive ? ' is-active' : ''}`}
                >
                  <FileTextOutlined />
                  <div className="workspace-filelist__item-body">
                    <div className="workspace-filelist__item-title">
                      {item.display_name || item.meeting_type || item.name || item.task_id || '未命名任务'}
                    </div>
                    <div className="workspace-filelist__item-time">
                      {item.created_at ? dateFormatter.format(new Date(item.created_at)) : '--'}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default FileSidebar
