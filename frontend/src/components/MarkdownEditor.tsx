import { useEffect, useRef, useState } from 'react'
import type VditorType from 'vditor'
import 'vditor/dist/js/i18n/zh_CN.js'
import 'vditor/dist/index.css'

interface Props {
  value: string
  onChange?: (val: string) => void
  readonly?: boolean
  height?: number | string
  outline?: boolean
  mode?: 'wysiwyg' | 'sv' | 'ir'
  hideToolbar?: boolean
  hidePreviewActions?: boolean
  toolbarItems?: Array<string | { name: string; toolbar?: Array<string | { name: string }> }>
  previewMode?: 'both' | 'editor' | 'preview'
  onInstance?: (instance: VditorType | null) => void
}

const MarkdownEditor = ({
  value,
  onChange,
  readonly = false,
  height = 320,
  outline = false,
  mode = 'ir',
  hideToolbar = false,
  hidePreviewActions = false,
  toolbarItems,
  previewMode = 'editor',
  onInstance,
}: Props) => {
  const elRef = useRef<HTMLDivElement>(null)
  const instance = useRef<VditorType | null>(null)
  const [ready, setReady] = useState(false)
  const onChangeRef = useRef<typeof onChange>(onChange)
  const onInstanceRef = useRef<typeof onInstance>(onInstance)
  const lastValueRef = useRef<string>(value)
  const initialValueRef = useRef<string>(value)
  const headingsHandlerRef = useRef<((event: Event) => void) | null>(null)

  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    onInstanceRef.current = onInstance
  }, [onInstance])

  // 初始化或依赖变化时重建编辑器
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      const Vditor = (await import('vditor')).default
      if (cancelled || !elRef.current) return
      instance.current = new Vditor(elRef.current as HTMLDivElement, {
        height,
        value: initialValueRef.current,
        cache: { enable: false },
        lang: 'zh_CN',
        toolbarConfig: { hide: readonly || hideToolbar },
        toolbar: toolbarItems,
        after: () => {
          setReady(true)
        },
        input: (val) => {
          lastValueRef.current = val
          onChangeRef.current?.(val)
        },
        mode,
        preview: {
          hljs: { lineNumber: true },
          actions: hidePreviewActions ? [] : undefined,
          mode: previewMode,
        },
        upload: {
          accept: 'image/*',
          // 占位校验，实际上传需接后端
          filename: () => 'image',
        },
        readOnly: readonly,
        outline: {
          enable: outline,
          position: 'right',
        },
      })
      onInstanceRef.current?.(instance.current)
    }
    load()
    return () => {
      cancelled = true
      instance.current?.destroy()
      instance.current = null
      setReady(false)
      onInstanceRef.current?.(null)
    }
  }, [height, outline, readonly, mode, hideToolbar, hidePreviewActions, toolbarItems, previewMode])

  useEffect(() => {
    if (!ready || !instance.current) return
    if (lastValueRef.current === value) return
    if (instance.current.getValue() !== value) {
      instance.current.setValue(value)
    }
    lastValueRef.current = value
  }, [value, ready])

  useEffect(() => {
    if (!instance.current) return
    if (previewMode === 'preview') return
    instance.current.setPreviewMode(previewMode)
  }, [previewMode])

  useEffect(() => {
    if (!ready || !instance.current) return
    if (previewMode !== 'both') return
    instance.current.renderPreview(value)
  }, [ready, previewMode, value])

  useEffect(() => {
    if (!ready || !instance.current) return
    const vditor = instance.current as unknown as {
      toolbar?: { elements?: Record<string, HTMLElement> }
    }
    const headingsButton = vditor.toolbar?.elements?.headings?.firstElementChild as HTMLElement | null
    if (!headingsButton) return

    const handler = (event: Event) => {
      const panel = headingsButton.parentElement?.querySelector('.vditor-panel') as HTMLElement | null
      if (!panel) return
      if (panel.style.display === 'block') {
        panel.style.display = 'none'
        event.preventDefault()
        event.stopPropagation()
      }
    }
    headingsHandlerRef.current = handler
    headingsButton.addEventListener('click', handler, true)
    return () => {
      headingsButton.removeEventListener('click', handler, true)
      headingsHandlerRef.current = null
    }
  }, [ready])

  return <div ref={elRef} />
}

export default MarkdownEditor
