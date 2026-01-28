import { request } from './request'
import type { LoginRequest, LoginResponse } from '@/types/frontend-types'

export const login = (payload: LoginRequest) =>
  request<LoginResponse>({
    url: '/auth/dev/login',
    method: 'POST',
    data: payload,
  })
