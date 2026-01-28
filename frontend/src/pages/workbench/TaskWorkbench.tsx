import { useEffect, useMemo, useState } from "react"
import { Button, Card, Col, Drawer, Modal, Progress, Row, Space, Tag, Typography, message } from "antd"
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  CloseCircleFilled,
  InfoCircleOutlined,
  LoadingOutlined,
  StopOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons"
import { useNavigate, useParams } from "react-router-dom"
import { useTaskRunnerStore, type TaskStep, type TaskRunStatus } from "@/store/task-runner"
import { useTaskStore } from "@/store/task"
import type { TaskState } from "@/types/frontend-types"
import { ENV, API_URL } from "@/config/env"
import TaskConfigForm, { type CreateTaskFormValues } from "@/components/TaskConfigForm"
import { deleteTaskSoft, cancelTask } from "@/api/tasks"
import { authStorage } from "@/utils/auth-storage"
import "./task-workbench.css"

const defaultTip = "正在准备模型资源..."

const getStepIcon = (status: TaskStep["status"]) => {
  if (status === "success") return <CheckCircleFilled style={{ color: "#52c41a" }} />
  if (status === "processing") return <LoadingOutlined style={{ color: "#1677ff" }} />
  if (status === "paused") return <ClockCircleOutlined style={{ color: "#8c8c8c" }} />
  if (status === "failed") return <CloseCircleFilled style={{ color: "#ff4d4f" }} />
  return <ClockCircleOutlined style={{ color: "#bfbfbf" }} />
}

const TaskWorkbench = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { tasks, ensureTask, abortTask, deleteTask, updateFromServer } = useTaskRunnerStore()
  const { fetchStatus, fetchDetail, fetchList, fetchTrash, currentTask, status: latestStatus } = useTaskStore()
  const task = id ? tasks[id] : undefined
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false)
  const [nowTs, setNowTs] = useState(() => Date.now())
  const pollTimerRef = useState<{ timer: number | null }>({ timer: null })[0]
  const [etaSnapshot, setEtaSnapshot] = useState<{ value: number; ts: number }>({ value: 0, ts: Date.now() })
  const [sseActive, setSseActive] = useState(false)

  useEffect(() => {
    if (!id) return
    ensureTask(id)
  }, [id, ensureTask])

  useEffect(() => {
    if (!id) return
    fetchDetail(id)
  }, [id, fetchDetail])

  const stageProgress = (state?: TaskState) => {
    const normalized = (state ?? "").toLowerCase()
    if (normalized === "transcribing") return 40
    if (normalized === "identifying") return 60
    if (normalized === "correcting") return 70
    if (normalized === "summarizing") return 70
    if (normalized === "success" || normalized === "partial_success") return 100
    if (normalized === "running") return 0
    return 0
  }

  const mapBackendStatus = (state?: TaskState, progress?: number): TaskRunStatus => {
    if (!state) return "PENDING"
    if (state === "success" || state === "partial_success") return "SUCCESS"
    if (state === "failed") return "FAILED"
    if (state === "cancelled") return "CANCELLED"
    if (state === "pending" || state === "queued") {
      return progress && progress > 0 ? "PROCESSING" : "PENDING"
    }
    return "PROCESSING"
  }

  const audioDurationSec = useMemo(() => {
    const detail = currentTask as (typeof currentTask & { duration?: number | string; audio_duration?: number | string }) | null
    const parseNum = (v: unknown) => {
      const n = typeof v === "string" ? parseFloat(v) : typeof v === "number" ? v : NaN
      return Number.isFinite(n) ? n : undefined
    }
    const statusDuration = parseNum(latestStatus?.audio_duration)
    const raw = statusDuration ?? parseNum(detail?.duration) ?? parseNum(detail?.audio_duration) ?? 0
    return Number.isFinite(raw) ? raw : 0
  }, [currentTask, latestStatus?.audio_duration])

  const taskStartAt = useMemo(() => {
    const createdAt = currentTask?.created_at
    if (!createdAt) return null
    const ts = Date.parse(createdAt)
    return Number.isNaN(ts) ? null : ts
  }, [currentTask?.created_at])

  const expectedSeconds = useMemo(() => Math.max(0, Math.round(audioDurationSec * 0.25)), [audioDurationSec])

  const statusProgress = typeof latestStatus?.progress === "number" ? latestStatus.progress : task?.progress ?? 0
  const completedAtTs = useMemo(() => {
    const endTime =
      (latestStatus?.updated_at ? Date.parse(latestStatus.updated_at) : NaN) ||
      (currentTask?.completed_at ? Date.parse(currentTask.completed_at) : NaN)
    return Number.isNaN(endTime) ? null : endTime
  }, [latestStatus?.updated_at, currentTask?.completed_at])

  const normalizePhase = (state?: TaskState, progress?: number): TaskState => {
    const normalized = (state ?? "").trim().toLowerCase() as TaskState | ""
    // 后端明确阶段优先
    if (normalized === "identifying" || normalized === "correcting" || normalized === "summarizing") return normalized
    if (normalized === "success" || normalized === "failed" || normalized === "partial_success" || normalized === "cancelled")
      return normalized
    if (normalized === "transcribing" || normalized === "running") {
      if (progress !== undefined) {
        if (progress >= 70) return "summarizing"
        if (progress >= 60) return "correcting"
        if (progress >= 40) return "identifying"
        if (progress > 0) return "transcribing"
      }
      return normalized === "running" ? "running" : "transcribing"
    }
    if (normalized === "pending" || normalized === "queued") return normalized
    // 无状态时，根据进度推测
    if (progress !== undefined) {
      if (progress >= 70) return "summarizing"
      if (progress >= 60) return "correcting"
      if (progress >= 40) return "identifying"
      if (progress > 0) return "transcribing"
    }
    return "pending"
  }

  // 暂时禁用 SSE，避免鉴权失败导致回退；仅保留轮询
  useEffect(() => {
    setSseActive(false)
  }, [id])

  useEffect(() => {
    if (!id || ENV.ENABLE_MOCK || sseActive) return
    let cancelled = false
    const poll = async () => {
      try {
        const res = await fetchStatus(id)
        if (cancelled) return
        const phase = normalizePhase(res.state as TaskState | undefined, res.progress)
        const mapped = stageProgress(phase)
        const serverProgress = typeof res.progress === "number" ? res.progress : undefined
        const elapsedSec = taskStartAt && !Number.isNaN(taskStartAt) ? Math.max(0, (Date.now() - taskStartAt) / 1000) : 0
        const expected = typeof res.estimated_time === "number" && res.estimated_time > 0 ? res.estimated_time : expectedSeconds
        let fallback = mapped
        if (serverProgress === undefined && (phase === "running" || phase === "transcribing") && expected > 0) {
          const ratio = Math.min(1, elapsedSec / expected)
          fallback = Math.max(mapped, Math.round(ratio * 70))
        }
        const nextProgress =
          res.state === "success" || res.state === "partial_success"
            ? 100
            : serverProgress !== undefined
              ? Math.max(serverProgress, task?.progress ?? 0)
              : Math.max(fallback, task?.progress ?? 0)
        updateFromServer(id, {
          status: mapBackendStatus(res.state as TaskState, res.progress),
          phase,
          progress: nextProgress,
          etaSeconds: res.estimated_time ?? task?.etaSeconds ?? 0,
        })
        const baseEta =
          typeof res.estimated_time === "number"
            ? res.estimated_time
            : audioDurationSec > 0
              ? Math.max(0, Math.round(audioDurationSec * 0.25 * (1 - (res.progress ?? 0) / 100)))
              : 0
        setEtaSnapshot((prev) => {
          if (prev && prev.value === baseEta) {
            return prev
          }
          return { value: baseEta, ts: Date.now() }
        })
      } catch {
        // keep last state on polling errors
      }
    }
    poll()
    if (pollTimerRef.timer) {
      window.clearInterval(pollTimerRef.timer)
    }
    pollTimerRef.timer = window.setInterval(poll, 2000)
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        void poll()
      }
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      cancelled = true
      if (pollTimerRef.timer) {
        window.clearInterval(pollTimerRef.timer)
        pollTimerRef.timer = null
      }
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [id, fetchStatus, updateFromServer, pollTimerRef, task?.progress, taskStartAt, expectedSeconds, sseActive])

  useEffect(() => {
    const terminal = task?.status === "SUCCESS" || task?.status === "FAILED"
    if (terminal) return
    const timer = window.setInterval(() => {
      setNowTs(Date.now())
    }, 1000)
    return () => window.clearInterval(timer)
  }, [task?.status])

  const remainingSeconds = useMemo(() => {
    if (task?.status === "SUCCESS" || task?.status === "FAILED") return 0
    const backendEta = typeof latestStatus?.estimated_time === "number" ? latestStatus.estimated_time : undefined
    const baseEta =
      backendEta !== undefined
        ? backendEta
        : audioDurationSec > 0
          ? Math.max(0, Math.round(audioDurationSec * 0.25 * (1 - statusProgress / 100)))
          : task?.etaSeconds ?? 0
    if (baseEta > 0) {
      const elapsed = Math.max(0, (nowTs - etaSnapshot.ts) / 1000)
      return Math.max(0, Math.round(baseEta - elapsed))
    }
    if (taskStartAt && expectedSeconds > 0) {
      const elapsed = Math.max(0, Math.floor((nowTs - taskStartAt) / 1000))
      return Math.max(0, expectedSeconds - elapsed)
    }
    return expectedSeconds
  }, [task?.status, latestStatus?.estimated_time, audioDurationSec, statusProgress, task?.etaSeconds, nowTs, etaSnapshot.ts, taskStartAt, expectedSeconds])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.max(0, seconds % 60)
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
  }

  const formatTime = (timestamp: number) =>
    new Date(timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })

  const expectedFinishTime =
    task?.status === "SUCCESS"
      ? completedAtTs
        ? formatTime(completedAtTs)
        : "--:--"
      : task?.status === "FAILED"
        ? "--:--"
        : remainingSeconds > 0
          ? formatTime(Date.now() + remainingSeconds * 1000)
          : taskStartAt && expectedSeconds > 0
            ? formatTime(taskStartAt + expectedSeconds * 1000)
            : "--:--"

  const currentStep = useMemo(() => {
    if (!task) return null
    return (
      task.steps.find((step) => step.status === "processing" || step.status === "paused" || step.status === "failed") ||
      task.steps.find((step) => step.status === "pending") ||
      null
    )
  }, [task])

  const hintText = useMemo(() => {
    if (!task) return defaultTip
    if (task.status === "SUCCESS") return "处理完成"
    if (task.status === "FAILED") return ""
    const phase = (task.phase ?? "").toLowerCase()
    if (phase === "transcribing") return "正在会议录音转写..."
    if (phase === "identifying") return "正在识别说话人..."
    if (phase === "correcting") return "正在进行声纹修正..."
    if (phase === "summarizing") return "正在生成纪要..."
    if (phase === "running") return "正在处理中..."
    if (task.status === "PROCESSING" && currentStep) return `正在${currentStep.title}...`
    if (task.status === "PENDING") return "等待开始..."
    return defaultTip
  }, [task, currentStep])

  const getStepDetail = (step: TaskStep, index: number) => {
    const fileName = task?.fileNames?.[index] || task?.fileNames?.[0]
    const details = [
      "进入队列，等待调度",
      fileName ? `转写录音：${fileName}` : "正在转写录音",
      "区分不同的说话人",
      "根据声纹进行校正",
      "整理并生成会议纪要",
    ]
    const detail = details[index] || details[details.length - 1]
    if (step.status === "success") return `${detail} · 已完成`
    if (step.status === "failed") return `${detail} · 处理中止`
    if (step.status === "paused") return `${detail} · 已暂停`
    return detail
  }

  const showAbort = task?.status === "PROCESSING" || task?.status === "PAUSED" || task?.status === "PENDING"
  const showResult = task?.status === "SUCCESS"
  const showDelete = !!task?.status && task.status !== "SUCCESS"

  const translateLang = (lang?: string) => {
    if (!lang) return "--"
    const lower = lang.toLowerCase()
    if (lower.startsWith("zh")) return "中文"
    if (lower.startsWith("en")) return "英文"
    return lang
  }

  const getErrorSuggestion = (code?: string, retryable?: boolean) => {
    const normalized = (code || "").toUpperCase()
    if (["NETWORK_TIMEOUT", "NETWORK_DNS", "STORAGE_UNAVAILABLE", "ASR_SERVICE_ERROR", "ASR_TIMEOUT", "LLM_SERVICE_ERROR", "LLM_TIMEOUT", "VOICEPRINT_SERVICE_ERROR", "CACHE_ERROR"].includes(normalized)) {
      return "服务暂不可用，请稍后重试或重新提交任务。"
    }
    if (["AUTH_FAILED", "PERMISSION_DENIED", "ASR_AUTH_ERROR", "LLM_AUTH_ERROR", "VOICEPRINT_AUTH_ERROR"].includes(normalized)) {
      return "鉴权或权限失败，请检查密钥/账号配置后再试。"
    }
    if (["RATE_LIMITED", "BILLING_EXCEEDED"].includes(normalized)) {
      return "触发频率或配额限制，请稍后重试或联系管理员。"
    }
    if (
      ["INPUT_MISSING_FILE", "INPUT_UNSUPPORTED_FORMAT", "INPUT_TOO_LARGE", "INPUT_CORRUPTED", "INPUT_INVALID"].includes(normalized)
    ) {
      return "输入文件存在问题，请重新上传正确格式的音频后重试。"
    }
    if (["LLM_CONTENT_BLOCKED"].includes(normalized)) {
      return "内容被拦截，请调整提示词或内容后重试。"
    }
    if (["SPEAKER_RECOGNITION_FAILED", "CORRECTION_FAILED", "SUMMARY_FAILED", "TRANSCRIPTION_EMPTY"].includes(normalized)) {
      return "处理未完成，请检查音频质量或稍后重试。"
    }
    if (["INTERNAL_ERROR", "DB_ERROR", "QUEUE_ERROR"].includes(normalized)) {
      return "系统内部错误，请联系管理员处理。"
    }
    if (retryable) return "可重试错误，请稍后再试。"
    return "请检查配置或联系管理员。"
  }

  const getAsrLangs = () => {
    const langsFromTask = task?.config.asrLanguages
    const detail = currentTask as unknown as { asr_languages?: string[] | string; asr_language?: string }
    const statusLang = latestStatus?.asr_language
    const merge = statusLang ?? langsFromTask ?? detail?.asr_languages ?? detail?.asr_language ?? []
    const arr =
      typeof merge === "string"
        ? merge
            .split(/[+/,]/)
            .map((s) => s.trim())
            .filter(Boolean)
        : Array.isArray(merge)
          ? merge
          : []
    return arr.length ? arr.map((l) => translateLang(l)).join(" / ") : "--"
  }

  const handleAbort = () => {
    if (!id) return
    Modal.confirm({
      title: "确认中止任务？",
      content: "将请求后端取消任务，处理中断后状态会变为取消。",
      okText: "确认取消",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: () =>
        cancelTask(id)
          .then(() => {
            abortTask(id)
            message.success("已提交取消请求")
          })
          .catch((err) => {
            message.error((err as Error)?.message || "取消任务失败")
            return Promise.reject(err)
          }),
    })
  }

  const handleDelete = () => {
    if (!id) return
    Modal.confirm({
      title: "确认删除任务？",
      content: "任务将被移入回收站，可在任务列表的回收站查看或恢复。",
      okText: "移至回收站",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteTaskSoft(id)
          deleteTask(id)
          await Promise.all([
            fetchList({ limit: 200, offset: 0, include_deleted: false }),
            fetchTrash({ limit: 200, offset: 0 }),
          ])
          message.success("已移至回收站")
          navigate("/tasks")
        } catch (err) {
          message.error((err as Error)?.message || "移至回收站失败")
          return Promise.reject()
        }
      },
    })
  }

  const initialConfigValues: Partial<CreateTaskFormValues> = useMemo(() => {
    if (!task) return {}
    return {
      meeting_type: task.config.meetingType,
      output_language: task.config.outputLanguage,
      asr_languages: task.config.asrLanguages,
      skip_speaker_recognition: false,
      description: "",
    }
  }, [task])

  return (
    <div className="workbench">
      <div className="workbench__container">
        <div className="workbench__header">
          <div>
            <Typography.Title level={3} style={{ marginBottom: 4 }}>
              任务进度
            </Typography.Title>
            <Typography.Text type="secondary">{task?.title || "正在加载任务信息..."}</Typography.Text>
          </div>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tasks")}>
              返回列表 / 后台运行
            </Button>
          </Space>
        </div>

        <Card className="workbench__progress" bordered={false}>
          <Progress percent={Math.round(task?.progress || 0)} status={task?.status === "FAILED" ? "exception" : "active"} />
          {hintText && (
            <Typography.Text className="workbench__hint" type="secondary">
              {hintText}
            </Typography.Text>
          )}
          {task?.status === "FAILED" && (
            <div className="workbench__error" style={{ marginTop: 8 }}>
              <Typography.Text type="danger" style={{ display: "block" }}>
                处理失败，请稍后重试
              </Typography.Text>
              <div style={{ borderBottom: "1px solid #eee", margin: "8px 0" }} />
              <Typography.Text strong style={{ display: "block", marginBottom: 6 }}>
                错误报告
              </Typography.Text>
              <Typography.Paragraph style={{ margin: "4px 0" }}>
                <Typography.Text type="secondary">错误类型：</Typography.Text>
                <Typography.Text>
                  {(() => {
                    const code = (latestStatus?.error_code || "").toUpperCase()
                    const labelMap: Record<string, string> = {
                      NETWORK_TIMEOUT: "网络超时",
                      NETWORK_DNS: "网络连接失败",
                      STORAGE_UNAVAILABLE: "存储不可用",
                      AUTH_FAILED: "鉴权失败",
                      PERMISSION_DENIED: "权限不足",
                      RATE_LIMITED: "请求过于频繁",
                      BILLING_EXCEEDED: "配额不足",
                      INPUT_MISSING_FILE: "音频文件缺失",
                      INPUT_UNSUPPORTED_FORMAT: "不支持的音频格式",
                      INPUT_TOO_LARGE: "音频文件过大",
                      INPUT_CORRUPTED: "音频文件损坏",
                      INPUT_INVALID: "输入参数无效",
                      ASR_SERVICE_ERROR: "语音识别服务异常",
                      ASR_AUTH_ERROR: "语音识别鉴权失败",
                      ASR_TIMEOUT: "语音识别超时",
                      LLM_SERVICE_ERROR: "生成服务异常",
                      LLM_AUTH_ERROR: "生成服务鉴权失败",
                      LLM_TIMEOUT: "生成服务超时",
                      LLM_CONTENT_BLOCKED: "内容被拦截",
                      VOICEPRINT_SERVICE_ERROR: "声纹服务异常",
                      VOICEPRINT_AUTH_ERROR: "声纹鉴权失败",
                      SPEAKER_RECOGNITION_FAILED: "说话人识别失败",
                      CORRECTION_FAILED: "校正失败",
                      SUMMARY_FAILED: "生成纪要失败",
                      TRANSCRIPTION_EMPTY: "转写结果为空",
                      INTERNAL_ERROR: "系统内部错误",
                      DB_ERROR: "数据库错误",
                      CACHE_ERROR: "缓存服务异常",
                      QUEUE_ERROR: "任务队列异常",
                    }
                    return labelMap[code] || "未知错误"
                  })()}
                </Typography.Text>
              </Typography.Paragraph>
              <Typography.Paragraph style={{ margin: "4px 0" }}>
                <Typography.Text type="secondary">调整建议：</Typography.Text>
                <Typography.Text>
                  {getErrorSuggestion(latestStatus?.error_code, latestStatus?.retryable) || "请检查配置或联系管理员。"}
                </Typography.Text>
              </Typography.Paragraph>
              <Typography.Paragraph style={{ margin: "4px 0", whiteSpace: "pre-wrap" }}>
                <Typography.Text type="secondary">错误信息：</Typography.Text>
                <Typography.Text>{latestStatus?.error_message || latestStatus?.error_details || "未知错误"}</Typography.Text>
              </Typography.Paragraph>
            </div>
          )}
          <div className="workbench__control">
            <Space>
              {showAbort && (
                <Button danger icon={<StopOutlined />} onClick={handleAbort}>
                  中止
                </Button>
              )}
              {showResult ? (
                <Button type="primary" icon={<ArrowRightOutlined />} iconPosition="end" onClick={() => id && navigate(`/workspace/${id}`)}>
                  查看结果
                </Button>
              ) : (
                showDelete && (
                  <Button icon={<DeleteOutlined />} onClick={handleDelete}>
                    删除
                  </Button>
                )
              )}
            </Space>
            <Tag color={task?.status === "SUCCESS" ? "green" : task?.status === "FAILED" ? "red" : "blue"}>
              {task?.status || "PENDING"}
            </Tag>
          </div>
        </Card>

        <Row gutter={[16, 16]} align="stretch">
          <Col xs={24} md={16} className="workbench__col">
            <Card title="执行环节" className="workbench__steps workbench__card" bordered={false}>
              <Space direction="vertical" style={{ width: "100%" }}>
                {task?.steps.map((step, index) => (
                  <div key={step.id} className={`workbench__step workbench__step--${step.status}`}>
                    <div className="workbench__step-icon">{getStepIcon(step.status)}</div>
                    <div className="workbench__step-content">
                      <Typography.Text strong={step.status === "processing"}>
                        {index + 1}. {step.title}
                      </Typography.Text>
                      <Typography.Text type="secondary" className="workbench__step-sub">
                        {step.status === "success"
                          ? "已完成"
                          : step.status === "processing"
                            ? "执行中..."
                            : step.status === "paused"
                              ? "已暂停"
                              : step.status === "failed"
                                ? "已中止"
                                : "待开始"}
                      </Typography.Text>
                      <Typography.Text type="secondary" className="workbench__step-detail">
                        {getStepDetail(step, index)}
                      </Typography.Text>
                    </div>
                  </div>
                ))}
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={8} className="workbench__col">
            <Card
              title={
                <Space>
                  <InfoCircleOutlined />
                  实时情报
                </Space>
              }
              className="workbench__info workbench__card"
              bordered={false}
            >
              <div className="workbench__info-section">
                <Typography.Text type="secondary">进度预估</Typography.Text>
                <div className="workbench__info-item">
                  <Typography.Text type="secondary">预期完成时间</Typography.Text>
                  <Typography.Text>{expectedFinishTime}</Typography.Text>
                </div>
                <div className="workbench__info-item">
                  <Typography.Text type="secondary">剩余时间</Typography.Text>
                  <Typography.Text>
                    {task?.status === "FAILED" ? "--:--" : formatDuration(Math.max(0, remainingSeconds ?? 0))}
                  </Typography.Text>
                </div>
              </div>
              <div className="workbench__info-section">
                <Typography.Text type="secondary">任务配置快照</Typography.Text>
                <div className="workbench__info-item">
                  <Typography.Text type="secondary">模板</Typography.Text>
                  <Typography.Text>{task?.config.templateName || "未指定"}</Typography.Text>
                </div>
                <div className="workbench__info-item">
                  <Typography.Text type="secondary">输出语言</Typography.Text>
                  <Typography.Text>{translateLang(task?.config.outputLanguage)}</Typography.Text>
                </div>
                <div className="workbench__info-item">
                  <Typography.Text type="secondary">识别语言</Typography.Text>
                  <Typography.Text>{getAsrLangs()}</Typography.Text>
                </div>
              </div>
            </Card>
          </Col>
        </Row>

        <Drawer
          title="重新生成任务配置"
          width={600}
          onClose={() => setConfigDrawerOpen(false)}
          open={configDrawerOpen}
          styles={{ body: { paddingBottom: 80 } }}
        >
          <TaskConfigForm initialValues={initialConfigValues} onFinish={() => {}} submitText="确认并重新生成" />
        </Drawer>
      </div>
    </div>
  )
}

export default TaskWorkbench
