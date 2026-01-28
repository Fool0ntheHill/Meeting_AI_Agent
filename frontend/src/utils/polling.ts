export interface PollingOptions<T> {
  fetcher: () => Promise<T>
  onUpdate: (data: T) => void
  isDone: (data: T) => boolean
  initialInterval?: number
  maxInterval?: number
  maxAttempts?: number
}

export const createExponentialPoller = <T>({
  fetcher,
  onUpdate,
  isDone,
  initialInterval = 2000,
  maxInterval = 10000,
  maxAttempts = 20,
}: PollingOptions<T>) => {
  let attempts = 0
  let stopped = false
  let timer: number | undefined

  const schedule = (interval: number) => {
    timer = window.setTimeout(async () => {
      if (stopped) return
      attempts += 1
      try {
        const data = await fetcher()
        onUpdate(data)
        if (isDone(data) || attempts >= maxAttempts) {
          stopped = true
          return
        }
      } catch {
        // 静默失败后继续退避
      }
      const nextInterval = Math.min(maxInterval, interval * 1.6)
      schedule(nextInterval)
    }, interval)
  }

  schedule(initialInterval)

  return {
    stop: () => {
      stopped = true
      if (timer) {
        clearTimeout(timer)
      }
    },
  }
}
