export const ENV = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  API_PREFIX: import.meta.env.VITE_API_PREFIX || '/api/v1',
  ENABLE_MOCK: import.meta.env.VITE_ENABLE_MOCK === 'true',
  ENABLE_DEVTOOLS: import.meta.env.VITE_ENABLE_DEVTOOLS === 'true',
  LOG_LEVEL: (import.meta.env.VITE_LOG_LEVEL as string) || 'info',
  MODE: import.meta.env.MODE,
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
} as const

export const API_URL = `${ENV.API_BASE_URL}${ENV.API_PREFIX}`
