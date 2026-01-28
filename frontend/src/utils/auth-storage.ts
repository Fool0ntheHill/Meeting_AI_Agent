const TOKEN_KEY = 'access_token'
const USER_ID_KEY = 'user_id'
const TENANT_ID_KEY = 'tenant_id'
const TOKEN_EXPIRY_KEY = 'token_expiry'
const USERNAME_KEY = 'username'
const ACCOUNT_KEY = 'account'
const AVATAR_KEY = 'avatar'

export const authStorage = {
  save: (token: string, userId: string, tenantId: string, expiresInSeconds: number, username: string, account?: string, avatar?: string) => {
    const expiry = Date.now() + expiresInSeconds * 1000
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_ID_KEY, userId)
    localStorage.setItem(TENANT_ID_KEY, tenantId)
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString())
    localStorage.setItem(USERNAME_KEY, username)
    if (account !== undefined) localStorage.setItem(ACCOUNT_KEY, account)
    if (avatar !== undefined) localStorage.setItem(AVATAR_KEY, avatar)
  },
  load: () => {
    const token = localStorage.getItem(TOKEN_KEY)
    const userId = localStorage.getItem(USER_ID_KEY)
    const tenantId = localStorage.getItem(TENANT_ID_KEY)
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY)
    const username = localStorage.getItem(USERNAME_KEY)
    const account = localStorage.getItem(ACCOUNT_KEY)
    const avatar = localStorage.getItem(AVATAR_KEY)
    return { token, userId, tenantId, expiry: expiry ? Number(expiry) : null, username, account, avatar }
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_ID_KEY)
    localStorage.removeItem(TENANT_ID_KEY)
    localStorage.removeItem(TOKEN_EXPIRY_KEY)
    localStorage.removeItem(USERNAME_KEY)
    localStorage.removeItem(ACCOUNT_KEY)
    localStorage.removeItem(AVATAR_KEY)
  },
  shouldRefresh: () => {
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY)
    if (!expiry) return false
    const expiryTime = Number(expiry)
    const fiveMinutes = 5 * 60 * 1000
    return expiryTime - Date.now() < fiveMinutes
  },
}
