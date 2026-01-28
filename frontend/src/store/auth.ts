import { create } from 'zustand'
import { login as loginApi } from '@/api/auth'
import { authStorage } from '@/utils/auth-storage'
import type { LoginResponse } from '@/types/frontend-types'

interface AuthState {
  token: string | null
  userId: string | null
  tenantId: string | null
  username: string | null
  account: string | null
  avatar: string | null
  expiresAt: number | null
  loading: boolean
  login: (username: string) => Promise<LoginResponse>
  logout: () => void
  hydrate: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userId: null,
  tenantId: null,
  username: null,
  account: null,
  avatar: null,
  expiresAt: null,
  loading: false,
  hydrate: () => {
    const { token, userId, tenantId, expiry, username, account, avatar } = authStorage.load()
    if (token && expiry && Date.now() < expiry) {
      set({ token, userId, tenantId, expiresAt: expiry, username, account, avatar })
    } else {
      authStorage.clear()
    }
  },
  login: async (username: string) => {
    set({ loading: true })
    try {
      const res = await loginApi({ username })
      authStorage.save(res.access_token, res.user_id, res.tenant_id, res.expires_in, username)
      set({
        token: res.access_token,
        userId: res.user_id,
        tenantId: res.tenant_id,
        expiresAt: Date.now() + res.expires_in * 1000,
        username,
        account: null,
        avatar: null,
      })
      return res
    } finally {
      set({ loading: false })
    }
  },
  logout: () => {
    authStorage.clear()
    set({ token: null, userId: null, tenantId: null, expiresAt: null, username: null, account: null, avatar: null })
  },
}))
