import { memo, useEffect, useRef, useState } from 'react'
import { Button, Input, Popover, Radio, Tag, Typography } from 'antd'
import type { TranscriptParagraph } from '@/types/frontend-types'

const formatTime = (seconds: number) => {
  const total = Math.max(0, Math.floor(seconds))
  const hrs = Math.floor(total / 3600)
  const mins = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hrs > 0) {
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

interface TranscriptEditorProps {
  paragraphs?: TranscriptParagraph[]
  currentTime: number
  onSeek: (time: number) => void
  onUpdateParagraph: (id: string, text: string) => void
  onRenameSpeaker: (from: string, to: string, scope: 'single' | 'global', pid?: string) => void
  readOnly?: boolean
  onFocusArea?: () => void
}

interface TranscriptItemProps {
  item: TranscriptParagraph
  isActive: boolean
  isRenaming: boolean
  renameValue?: string
  renameScope: 'single' | 'global'
  onSeek: (time: number) => void
  onUpdate: (id: string, text: string) => void
  onRenameSpeaker: (from: string, to: string, scope: 'single' | 'global', pid?: string) => void
  onRenameValueChange: (val: string) => void
  onRenameScopeChange: (val: 'single' | 'global') => void
  onRenameStart: (item: TranscriptParagraph) => void
   onRenameCancel: () => void
  readOnly: boolean
  onFocusArea?: () => void
}

const TranscriptItem = memo(
  ({
    item,
    isActive,
    isRenaming,
    renameValue,
    renameScope,
    onSeek,
    onUpdate,
    onRenameSpeaker,
    onRenameValueChange,
    onRenameScopeChange,
    onRenameStart,
    onRenameCancel,
    readOnly,
    onFocusArea,
  }: TranscriptItemProps) => {

    return (
      <div
        key={item.paragraph_id}
        className={`workspace-transcript__item${isActive ? ' is-active' : ''}`}
      >
        <div className="workspace-transcript__meta">
          <button type="button" className="workspace-transcript__time" onClick={() => onSeek(item.start_time)}>
            [{formatTime(item.start_time)}]
          </button>

          <Popover
            open={isRenaming}
            trigger="click"
            content={
              <div className="workspace-transcript__popover">
                <Input
                  value={renameValue}
                  onChange={(e) => onRenameValueChange(e.target.value)}
                  placeholder="输入新名字"
                  className="workspace-transcript__rename-input"
                />
                <Radio.Group
                  value={renameScope}
                  onChange={(e) => onRenameScopeChange(e.target.value)}
                  className="workspace-transcript__rename-options"
                >
                  <Radio value="single">应用到当前段落</Radio>
                  <Radio value="global">应用到该说话人的所有段落</Radio>
                </Radio.Group>
                <Button
                  type="primary"
                  block
                  className="workspace-transcript__rename-save"
                  disabled={!renameValue?.trim()}
                  onClick={() => {
                    if (!renameValue) return
                    onRenameSpeaker(item.speaker, renameValue, renameScope, item.paragraph_id)
                    onRenameCancel()
                  }}
                >
                  保存
                </Button>
              </div>
            }
            onOpenChange={(open) => {
              if (open) {
                onRenameStart(item)
              } else {
                onRenameCancel()
              }
            }}
          >
            <Tag color="geekblue" className="cursor-pointer m-0 hover:opacity-80">
              {item.speaker}
            </Tag>
          </Popover>
        </div>

        {readOnly ? (
          <Typography.Text className="workspace-transcript__text">{item.text}</Typography.Text>
        ) : (
          <Input.TextArea
            variant="borderless"
            autoSize
            value={item.text}
            onChange={(e) => onUpdate(item.paragraph_id, e.target.value)}
            onFocus={onFocusArea}
            className="workspace-transcript__input"
            style={{ minHeight: 24 }}
          />
        )}
      </div>
    )
  },
  (prev, next) => {
    if (prev.isActive !== next.isActive) return false
    if (prev.isRenaming !== next.isRenaming) return false
    if (prev.renameValue !== next.renameValue && (prev.isRenaming || next.isRenaming)) return false
    if (prev.renameScope !== next.renameScope && (prev.isRenaming || next.isRenaming)) return false
    if (prev.item.text !== next.item.text) return false
    if (prev.item.speaker !== next.item.speaker) return false
    if (prev.item.start_time !== next.item.start_time || prev.item.end_time !== next.item.end_time) return false
    return true
  }
)

const TranscriptEditor = ({
  paragraphs,
  currentTime,
  onSeek,
  onUpdateParagraph,
  onRenameSpeaker,
  readOnly = false,
  onFocusArea,
}: TranscriptEditorProps) => {
  const activeItemRef = useRef<HTMLDivElement | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)
  const lastUserScroll = useRef<number>(0)

  const safeParagraphs = paragraphs ?? []
  const [renameValue, setRenameValue] = useState('')
  const [renameScope, setRenameScope] = useState<'single' | 'global'>('single')
  const [renameFrom, setRenameFrom] = useState('')
  const [renamePid, setRenamePid] = useState<string | undefined>(undefined)

  const handleRenameConfirm = () => {
    const next = renameValue.trim()
    if (!next || next === renameFrom) return
    onRenameSpeaker(renameFrom, next, renameScope, renamePid)
  }

  useEffect(() => {
    const now = Date.now()
    if (now - lastUserScroll.current < 1500) return
    if (activeItemRef.current) {
      activeItemRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [currentTime])

  useEffect(() => {
    const container = listRef.current
    if (!container) return
    const onScroll = () => {
      lastUserScroll.current = Date.now()
    }
    container.addEventListener('wheel', onScroll, { passive: true })
    container.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      container.removeEventListener('wheel', onScroll)
      container.removeEventListener('scroll', onScroll)
    }
  }, [])

  return (
    <>
      <div className="workspace-transcript">
          <div
            className="workspace-transcript__list"
            ref={listRef}
            tabIndex={-1}
            onClick={onFocusArea}
          onFocusCapture={onFocusArea}
        >
          {safeParagraphs.map((item) => {
            const isActive = currentTime >= item.start_time && currentTime < item.end_time
            const isRenaming = renamePid === item.paragraph_id
            return (
              <div
                key={item.paragraph_id}
                ref={(el) => {
                  if (isActive) {
                    activeItemRef.current = el
                  }
                }}
              >
                <TranscriptItem
                  item={item}
                  isActive={isActive}
                  isRenaming={isRenaming}
                  renameValue={isRenaming ? renameValue : undefined}
                  renameScope={renameScope}
                  onSeek={onSeek}
                  onUpdate={onUpdateParagraph}
                  onRenameSpeaker={onRenameSpeaker}
                  onRenameValueChange={setRenameValue}
                  onRenameScopeChange={(val) => setRenameScope(val)}
                  onRenameStart={(target) => {
                    setRenameFrom(target.speaker)
                    setRenamePid(target.paragraph_id)
                    setRenameValue(target.speaker)
                    setRenameScope('single')
                  }}
                  onRenameCancel={() => {
                    setRenamePid(undefined)
                    setRenameValue('')
                    setRenameScope('single')
                  }}
                  readOnly={readOnly}
                  onFocusArea={onFocusArea}
                />
              </div>
            )
          })}
        </div>
      </div>
      
    </>
  )
}

export default TranscriptEditor
