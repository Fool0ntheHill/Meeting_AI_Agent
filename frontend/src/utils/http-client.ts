import axios from 'axios'
import type { AxiosProgressEvent, AxiosRequestConfig } from 'axios'
// 注意：如果你的项目里 router 路径不一样，请大模型自动调整

/** 跳转 GSUC SSO 登录 */
export function jumpToLogin() {
  const APP_ID = 'app_meeting_agent'
  const redirectUri = encodeURIComponent('http://localhost:8000/api/v1/auth/callback')
  const state = crypto?.randomUUID?.() ?? `${Date.now()}`
  window.location.href = `https://gsuc.gamesci.com.cn/sso/login?appid=${APP_ID}&redirect_uri=${redirectUri}&state=${encodeURIComponent(
    state
  )}`
}

/** 初始化登录：解析 URL token 或本地 token */
export function autoInitLogin(): boolean {
  const url = new URL(window.location.href)
  const token = url.searchParams.get('token')
  if (token) {
    localStorage.setItem('SESSIONID', token)
    window.history.replaceState({}, document.title, window.location.pathname + window.location.hash)
    return true
  }
  const saved = localStorage.getItem('SESSIONID')
  return Boolean(saved)
}

export interface DownloadParams {
  responseType?: 'arraybuffer' | 'blob' | 'document' | 'json' | 'text' | 'stream'
  method?: 'get' | 'post' | 'put' | 'delete'
  onComplete?: (data: any) => void
  onProgress?: (e: AxiosProgressEvent) => void
}

export interface HttpSsoOpts {
  disableWxworkBrowser?: boolean
  withToken?: boolean
  authTokenName?: string
  getAuthToken?: () => string
  server401Callback?: (data: any, disableWxworkBrowser: boolean) => void
}

export interface HttpOpts extends HttpSsoOpts {
  headers?: Record<string, any>
  meth?: 'get' | 'post' | 'put' | 'delete'
  timeout?: number
  withCredentials?: boolean
  getServerUrl?: () => string
  serverKey?: string
  errorAlert?: boolean

  /** response hooks */
  onSuccess?: (data: any) => void
  onError?: (rc: number, msg: any) => void
  onFinish?: (rc: number, msg: any, data: any) => void

  /** response transform */
  transformToCamelCase?: boolean
}

function defaultOptions(): HttpOpts {
  return {
    headers: {},
    meth: 'post',
    timeout: 10000,
    serverKey: '',
    withCredentials: false,
    disableWxworkBrowser: true,
    withToken: true,
    getAuthToken: () => localStorage.getItem('SESSIONID') || '',
    authTokenName: 'SESSIONID',
    getServerUrl: undefined,
    transformToCamelCase: false
  }
}

function serializeParams(params: any): string {
  if (!params || typeof params !== 'object') return ''
  const search = new URLSearchParams()
  const append = (key: string, value: any) => {
    if (value === undefined || value === null) return
    if (Array.isArray(value)) {
      value.forEach((v) => append(key, v))
      return
    }
    if (typeof value === 'object') {
      search.append(key, JSON.stringify(value))
      return
    }
    search.append(key, String(value))
  }
  Object.entries(params).forEach(([k, v]) => append(k, v))
  return search.toString()
}

/** Utils: snake/camel 转换 */
export function convertKeysToCamelCase(obj: any): any {
  if (typeof obj !== 'object' || obj === null) return obj
  if (Array.isArray(obj)) return obj.map(convertKeysToCamelCase)

  const camelCaseObj: any = {}
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const camelCaseKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
      camelCaseObj[camelCaseKey] = convertKeysToCamelCase(obj[key])
    }
  }
  return camelCaseObj
}

export function convertKeysToSnakeCase(obj: any): any {
  if (typeof obj !== 'object' || obj === null) return obj
  if (Array.isArray(obj)) return obj.map(convertKeysToSnakeCase)

  const snakeCaseObj: any = {}
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const snakeCaseKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
      snakeCaseObj[snakeCaseKey] = convertKeysToSnakeCase(obj[key])
    }
  }
  return snakeCaseObj
}

/**
 * 纯 HTTP 客户端
 */
export class HttpClient {
  private opt: HttpOpts

  constructor(opts?: HttpOpts) {
    this.opt = { ...defaultOptions(), ...(opts ?? {}) }
  }

  setSso(s: HttpSsoOpts) {
    this.opt = { ...this.opt, ...s }
  }

  setTimeout(n: number) {
    this.opt.timeout = n
  }

  setGetTokenKey(n: string) {
    this.opt.authTokenName = n
  }

  setWithCredentials(n: boolean) {
    this.opt.withCredentials = n
  }

  setDisableWxworkBrowser(n: boolean) {
    this.opt.disableWxworkBrowser = n
  }

  setWithToken(n: boolean) {
    this.opt.withToken = n
  }

  get(url: string, params?: any, opts?: HttpOpts) {
    return this.request(url, { params }, { ...opts, meth: 'get' })
  }

  post(url: string, data?: any, opts?: HttpOpts) {
    return this.request(url, { data }, { ...opts, meth: 'post' })
  }

  put(url: string, data?: any, opts?: HttpOpts) {
    return this.request(url, { data }, { ...opts, meth: 'put' })
  }

  delete(url: string, params?: any, opts?: HttpOpts) {
    return this.request(url, { params }, { ...opts, meth: 'delete' })
  }

  /**
   * 核心请求
   */
  async request(
    url: string,
    payload: { params?: any; data?: any },
    opts?: HttpOpts
  ) {
    const merged = { ...this.opt, ...(opts ?? {}) }
    const method = merged.meth ?? 'post'

    const token = merged.getAuthToken?.() ?? ''
    const headers = merged.withToken
      ? { Token: token, ...(merged.headers ?? {}), ...(opts?.headers ?? {}) }
      : { ...(merged.headers ?? {}), ...(opts?.headers ?? {}) }

    const config: AxiosRequestConfig = {
      method,
      url,
      baseURL: url.startsWith('http') ? undefined : (merged.getServerUrl?.() ?? ''),
      headers,
      params: payload.params ?? (method === 'get' || method === 'delete' ? payload.data : undefined),
      data: payload.data ?? (method === 'get' || method === 'delete' ? undefined : payload.params),
      timeout: merged.timeout,
      withCredentials: merged.withCredentials,
      paramsSerializer: (p) => serializeParams(p)
    }

    try {
      const resp = await axios(config)
      const raw = resp.data
      const data = merged.transformToCamelCase ? convertKeysToCamelCase(raw) : raw

      merged.onSuccess?.(data)
      merged.onFinish?.(0, '', data)
      return data
    } catch (error: any) {
      let rc = 1
      let msg: any = error

      if (error?.response) {
        rc = error.response.status
        msg = error.response.data

        if (rc === 401) {
          merged.server401Callback?.(msg, merged.disableWxworkBrowser ?? true)
        }
      }

      merged.onError?.(rc, msg)
      merged.onFinish?.(rc, msg, {})
      throw error
    }
  }

  download(url: string, params: DownloadParams = {}) {
    const method = params.method ?? 'get'
    return axios({
      method,
      responseType: params.responseType ?? 'blob',
      url,
      onDownloadProgress: e => params.onProgress?.(e)
    }).then(({ data }) => {
      params.onComplete?.(data)
      return data
    })
  }
}

/**
 * WebClient (包含上传和重定向下载功能)
 */
export class WebClient {
  private opt: HttpOpts

  constructor(opts?: HttpOpts) {
    this.opt = { ...defaultOptions(), ...(opts ?? {}) }
  }

  setSso(s: HttpSsoOpts) {
    this.opt = { ...this.opt, ...s }
  }

  doRawCall(opts: { url: string; reqParam?: any } & HttpOpts) {
    const merged = { ...this.opt, ...opts }
    const http = new HttpClient(merged)
    return http.request(opts.url, { data: opts.reqParam }, merged)
  }

  doCallWithUpload(opts: {
    url: string
    reqParam?: any
    upFiles: Array<{ file: File; name: string }>
  } & HttpOpts) {
    const merged = { ...this.opt, ...opts }
    const formData = new FormData()
    formData.append('exdata', JSON.stringify(opts.reqParam ?? {}))
    for (const f of opts.upFiles ?? []) {
      formData.append('file', f.file, f.name)
    }

    const http = new HttpClient({
      ...merged,
      headers: { ...(merged.headers ?? {}), 'Content-Type': 'multipart/form-data' },
      meth: 'post'
    })

    return http.request(opts.url, { data: formData }, http['opt'])
  }

  doGetDownloadRawUrl(url: string, opts: { reqParam?: any } & HttpOpts) {
    const merged = { ...this.opt, ...opts }
    const base = merged.getServerUrl?.() ?? ''
    const token = merged.getAuthToken?.() ?? ''

    const q = serializeParams(opts.reqParam ?? {})
    const full =
      base +
      url +
      `?Token=${encodeURIComponent(token)}` +
      (q ? `&${q}` : '') +
      `&ts=${Date.now()}`

    window.location.href = full
  }
}

export default {
  HttpClient,
  WebClient,
  jumpToLogin,
  autoInitLogin
}
