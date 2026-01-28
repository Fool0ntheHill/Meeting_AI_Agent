/* eslint-disable react-hooks/set-state-in-effect */
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { Button, Dropdown, Popover, Slider, Spin } from 'antd'
import {
  CaretRightFilled,
  PauseOutlined,
  DownOutlined,
  SoundOutlined,
  UndoOutlined,
  RedoOutlined,
} from '@ant-design/icons'

export interface AudioPlayerRef {
  seekTo: (time: number) => void
  play: () => void
  pause: () => void
}

interface AudioPlayerProps {
  url?: string
  onTimeUpdate?: (currentTime: number) => void
  onReady?: () => void
}

const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2]

const JumpIcon = ({ direction }: { direction: 'back' | 'forward' }) => (
  <span className="workspace-audio__jump-icon">
    {direction === 'back' ? <UndoOutlined /> : <RedoOutlined />}
    <span className="workspace-audio__jump-label">15</span>
  </span>
)

const AudioPlayer = forwardRef<AudioPlayerRef, AudioPlayerProps>(({ url, onTimeUpdate, onReady }, ref) => {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [playbackRate, setPlaybackRate] = useState(1)
  const [volume, setVolume] = useState(80)
  const [isLoading, setIsLoading] = useState(true)
  const [isDragging, setIsDragging] = useState(false)
  const [dragTime, setDragTime] = useState(0)

  useEffect(() => {
    const el = audioRef.current
    if (!el || !url) {
      setIsLoading(false)
      setDuration(0)
      setCurrentTime(0)
      return
    }

    setIsLoading(true)
    const onLoaded = () => {
      setDuration(el.duration || 0)
      setIsLoading(false)
      onReady?.()
    }
    const onTime = () => {
      const time = el.currentTime || 0
      if (!isDragging) {
        setCurrentTime(time)
        onTimeUpdate?.(time)
      }
    }
    const onPlay = () => setIsPlaying(true)
    const onPause = () => setIsPlaying(false)
    const onEnded = () => setIsPlaying(false)

    el.addEventListener('loadedmetadata', onLoaded)
    el.addEventListener('timeupdate', onTime)
    el.addEventListener('play', onPlay)
    el.addEventListener('pause', onPause)
    el.addEventListener('ended', onEnded)

    el.volume = volume / 100
    el.playbackRate = playbackRate

    return () => {
      el.removeEventListener('loadedmetadata', onLoaded)
      el.removeEventListener('timeupdate', onTime)
      el.removeEventListener('play', onPlay)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('ended', onEnded)
    }
  }, [url, onReady, onTimeUpdate, volume, playbackRate])

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume / 100
    }
  }, [volume])

  useImperativeHandle(ref, () => ({
    seekTo: (time: number) => {
      if (!audioRef.current) return
      audioRef.current.currentTime = time
      audioRef.current.play()
    },
    play: () => audioRef.current?.play(),
    pause: () => audioRef.current?.pause(),
  }))

  const togglePlay = () => {
    const el = audioRef.current
    if (!el) return
    if (isPlaying) {
      el.pause()
    } else {
      void el.play()
    }
  }

  const handleSpeedChange = (value: number) => {
    setPlaybackRate(value)
    if (audioRef.current) {
      audioRef.current.playbackRate = value
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const displayTime = isDragging ? dragTime : currentTime

  return (
    <div className="workspace-audio">
      <div className="workspace-audio__controls">
        <div className="workspace-audio__time">
          {formatTime(displayTime)} / {formatTime(duration)}
        </div>

        <div className="workspace-audio__center">
          <Button type="text" className="workspace-audio__jump" onClick={() => wavesurfer.current?.skip(-15)}>
            <JumpIcon direction="back" />
          </Button>
          <Button type="text" className="workspace-audio__play" onClick={togglePlay}>
            <span className="workspace-audio__play-icon">
              {isPlaying ? <PauseOutlined /> : <CaretRightFilled />}
            </span>
          </Button>
          <Button
            type="text"
            className="workspace-audio__jump"
            onClick={() => {
              if (!audioRef.current) return
              audioRef.current.currentTime = Math.min(duration, (audioRef.current.currentTime || 0) + 15)
            }}
          >
            <JumpIcon direction="forward" />
          </Button>
        </div>

        <div className="workspace-audio__right">
          <Popover
            trigger="click"
            placement="bottomRight"
            content={
              <div style={{ width: 120, padding: '4px 2px' }}>
                <Slider value={volume} onChange={(value) => setVolume(value)} />
              </div>
            }
          >
            <Button type="text" icon={<SoundOutlined />} className="workspace-audio__volume-btn" />
          </Popover>
          <Dropdown
            trigger={['click']}
            menu={{
              items: speeds.map((s) => ({ key: String(s), label: `${s}x` })),
              onClick: ({ key }) => handleSpeedChange(Number(key)),
            }}
          >
            <Button type="text" className="workspace-audio__rate-btn">
              <span className="workspace-audio__rate-text">{playbackRate}x</span>
              <DownOutlined className="workspace-audio__rate-icon" />
            </Button>
          </Dropdown>
        </div>
      </div>

      <div className="workspace-audio__wave">
        {isLoading ? (
          <div className="workspace-audio__loading">
            <Spin size="small" />
          </div>
        ) : (
          <Slider
            min={0}
            max={Math.max(duration, 0.1)}
            step={0.1}
            value={Math.min(displayTime, duration || 0)}
            onChange={(value) => {
              setIsDragging(true)
              setDragTime(value as number)
            }}
            onAfterChange={(value) => {
              const time = value as number
              setIsDragging(false)
              setCurrentTime(time)
              if (audioRef.current) {
                audioRef.current.currentTime = time
                if (!isPlaying) {
                  void audioRef.current.play()
                }
              }
            }}
            tooltip={{ formatter: (v) => formatTime(v || 0) }}
          />
        )}
      </div>

      <audio ref={audioRef} src={url} preload="metadata" />
    </div>
  )
})

AudioPlayer.displayName = 'AudioPlayer'

export default AudioPlayer
