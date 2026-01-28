import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { message } from 'antd'
import { API_URL } from '@/config/env'
import { authStorage } from '@/utils/auth-storage'

const instance: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 30000,
})

instance.interceptors.request.use((config) => {
  const { token } = authStorage.load()
  if (token) {
    config.headers = {
      ...(config.headers || {}),
      Authorization: `Bearer ${token}`,
    } as typeof config.headers
  }
  return config
})

instance.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const status = error.response?.status
    if (status === 401 || status === 403) {
      authStorage.clear()
      message.error('认证已失效，请重新登录')
      window.location.href = '/login'
      return Promise.reject(error)
    }
    if (status === 422) {
      message.warning('表单校验失败，请检查输入')
    } else if (status === 429) {
      message.warning('请求过于频繁，请稍后重试')
    } else if (status && status >= 500) {
      message.error('服务开小差了，请稍后再试')
    }
    return Promise.reject(error)
  }
)

export const request = async <T = unknown>(config: AxiosRequestConfig): Promise<T> => {
  const res = await instance.request<T>(config)
  return res.data
}

export default instance
