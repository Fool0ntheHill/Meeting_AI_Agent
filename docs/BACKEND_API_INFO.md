# 后端 API 实际配置信息

**日期**: 2026-01-16  
**用途**: 前端开发时的实际后端配置

---

## 🌐 后端服务地址

### 开发环境
```
Base URL: http://localhost:8000
API 前缀: /api/v1
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
```

### 启动后端服务
```bash
# 启动 API 服务器
python main.py

# 启动 Worker (另一个终端)
python worker.py
```

---

## 🔐 认证详细信息

### JWT Token 认证

**认证方式**: JWT (JSON Web Token)  
**算法**: HS256  
**Token 有效期**: 24 小时 (86400 秒)

### 开发环境登录

#### 接口
```
POST http://localhost:8000/api/v1/auth/dev/login
Content-Type: application/json
```

#### 请求示例
```json
{
  "username": "test_user"
}
```

**说明**:
- `username` 可以是任意字符串
- 如果用户不存在，会自动创建
- 自动生成 `user_id` 和 `tenant_id`

#### 响应示例
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyX3Rlc3RfdXNlciIsInRlbmFudF9pZCI6InRlbmFudF90ZXN0X3VzZXIiLCJleHAiOjE3MDU0ODMyMDAsImlhdCI6MTcwNTM5NjgwMH0.xxxxx",
  "token_type": "bearer",
  "user_id": "user_test_user",
  "tenant_id": "tenant_test_user",
  "expires_in": 86400
}
```

**响应字段说明**:
- `access_token`: JWT Token，用于后续请求认证
- `token_type`: 固定为 "bearer"
- `user_id`: 用户 ID (格式: `user_{username}`)
- `tenant_id`: 租户 ID (格式: `tenant_{username}`)
- `expires_in`: Token 有效期（秒），24小时 = 86400秒

---

## 🔑 使用 Token

### HTTP Header 格式

**Header 名称**: `Authorization`  
**Header 值**: `Bearer {access_token}`

### 示例

```http
GET http://localhost:8000/api/v1/tasks
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyX3Rlc3RfdXNlciIsInRlbmFudF9pZCI6InRlbmFudF90ZXN0X3VzZXIiLCJleHAiOjE3MDU0ODMyMDAsImlhdCI6MTcwNTM5NjgwMH0.xxxxx
```

### JavaScript/TypeScript 示例

```typescript
// 1. 登录获取 Token
async function login(username: string): Promise<string> {
  const response = await fetch('http://localhost:8000/api/v1/auth/dev/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username }),
  });
  
  const data = await response.json();
  
  // 保存 Token
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user_id', data.user_id);
  localStorage.setItem('tenant_id', data.tenant_id);
  
  // 计算过期时间
  const expiryTime = Date.now() + data.expires_in * 1000;
  localStorage.setItem('token_expiry', expiryTime.toString());
  
  return data.access_token;
}

// 2. 使用 Token 调用 API
async function callAPI(endpoint: string, options: RequestInit = {}): Promise<any> {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    throw new Error('未登录');
  }
  
  const response = await fetch(`http://localhost:8000/api/v1${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });
  
  if (response.status === 401) {
    // Token 过期，清除并跳转登录
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('tenant_id');
    localStorage.removeItem('token_expiry');
    throw new Error('Token 已过期，请重新登录');
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '请求失败');
  }
  
  return response.json();
}

// 3. 使用示例
async function example() {
  // 登录
  await login('test_user');
  
  // 调用 API
  const tasks = await callAPI('/tasks');
  console.log(tasks);
}
```

---

## 📝 完整的 API 客户端封装

```typescript
class MeetingAgentAPI {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = null;

  // 登录
  async login(username: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/auth/dev/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    });
    
    if (!response.ok) {
      throw new Error('登录失败');
    }
    
    const data = await response.json();
    this.token = data.access_token;
    
    // 保存到 localStorage
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user_id', data.user_id);
    localStorage.setItem('tenant_id', data.tenant_id);
    
    const expiryTime = Date.now() + data.expires_in * 1000;
    localStorage.setItem('token_expiry', expiryTime.toString());
  }

  // 检查 Token 是否有效
  isTokenValid(): boolean {
    const token = localStorage.getItem('access_token');
    const expiry = localStorage.getItem('token_expiry');
    
    if (!token || !expiry) return false;
    
    return Date.now() < parseInt(expiry);
  }

  // 获取当前 Token
  getToken(): string | null {
    if (this.isTokenValid()) {
      return localStorage.getItem('access_token');
    }
    return null;
  }

  // 通用请求方法
  private async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<any> {
    // 确保有 Token
    if (!this.token) {
      this.token = this.getToken();
    }
    
    if (!this.token) {
      throw new Error('未登录，请先调用 login()');
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
        ...options.headers,
      },
    });

    // 处理 401 错误
    if (response.status === 401) {
      this.token = null;
      localStorage.clear();
      throw new Error('Token 已过期，请重新登录');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '请求失败');
    }

    return response.json();
  }

  // API 方法示例
  async getTasks(params?: { state?: string; limit?: number; offset?: number }) {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/tasks${query ? '?' + query : ''}`);
  }

  async createTask(data: any) {
    return this.request('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async uploadAudio(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const token = this.getToken();
    if (!token) throw new Error('未登录');

    const response = await fetch(`${this.baseURL}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '上传失败');
    }

    return response.json();
  }
}

// 使用示例
const api = new MeetingAgentAPI();

async function main() {
  // 1. 登录
  await api.login('test_user');
  
  // 2. 上传音频
  const file = document.querySelector('input[type="file"]').files[0];
  const uploadResult = await api.uploadAudio(file);
  
  // 3. 创建任务
  const task = await api.createTask({
    audio_files: [
      {
        file_path: uploadResult.file_path,
        speaker_id: 'speaker_001',
      }
    ],
    meeting_type: 'general',
  });
  
  // 4. 获取任务列表
  const tasks = await api.getTasks({ state: 'success' });
  console.log(tasks);
}
```

---

## 🧪 测试账号

### 开发环境测试账号

由于是开发环境，任意用户名都可以登录：

```typescript
// 示例 1
await api.login('test_user');
// 生成: user_id = "user_test_user", tenant_id = "tenant_test_user"

// 示例 2
await api.login('alice');
// 生成: user_id = "user_alice", tenant_id = "tenant_alice"

// 示例 3
await api.login('bob');
// 生成: user_id = "user_bob", tenant_id = "tenant_bob"
```

**注意**:
- 每个用户名会自动创建独立的用户和租户
- 不同用户的数据是隔离的
- 用户名可以是任意字符串（建议使用英文）

---

## ⚠️ 注意事项

### 1. CORS 配置

后端已配置 CORS，允许前端跨域访问：

```python
# 允许的源
origins = [
    "http://localhost:3000",  # React 默认端口
    "http://localhost:5173",  # Vite 默认端口
    "http://localhost:8080",  # Vue 默认端口
]
```

如果你的前端运行在其他端口，需要修改后端 CORS 配置。

### 2. Token 过期处理

Token 有效期为 24 小时，过期后需要重新登录：

```typescript
// 检查 Token 是否即将过期（提前 5 分钟刷新）
function shouldRefreshToken(): boolean {
  const expiry = localStorage.getItem('token_expiry');
  if (!expiry) return false;
  
  const expiryTime = parseInt(expiry);
  const now = Date.now();
  const fiveMinutes = 5 * 60 * 1000;
  
  return (expiryTime - now) < fiveMinutes;
}

// 自动刷新 Token（定时检查）
setInterval(() => {
  if (shouldRefreshToken()) {
    const username = localStorage.getItem('username');
    if (username) {
      api.login(username);  // 重新登录
    }
  }
}, 60000);  // 每分钟检查一次
```

### 3. 生产环境

生产环境将使用企业微信登录，开发登录接口会被禁用：

```typescript
// 生产环境会返回 403 错误
{
  "detail": "开发登录接口在生产环境不可用"
}
```

---

## 📊 JWT Token 结构

### Token Payload

```json
{
  "sub": "user_test_user",        // Subject: 用户 ID
  "tenant_id": "tenant_test_user", // 租户 ID
  "exp": 1705483200,               // Expiration: 过期时间戳
  "iat": 1705396800                // Issued At: 签发时间戳
}
```

### 解析 Token (可选)

```typescript
// 解析 JWT Token (不验证签名)
function parseJWT(token: string): any {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(
    atob(base64)
      .split('')
      .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join('')
  );
  return JSON.parse(jsonPayload);
}

// 使用
const token = localStorage.getItem('access_token');
const payload = parseJWT(token);
console.log('User ID:', payload.sub);
console.log('Tenant ID:', payload.tenant_id);
console.log('Expires:', new Date(payload.exp * 1000));
```

---

## 🔗 相关文档

- **API 开发指南**: `FRONTEND_DEVELOPMENT_GUIDE.md`
- **类型定义**: `frontend-types.ts`
- **快速参考**: `FRONTEND_QUICK_REFERENCE.md`
- **Swagger UI**: http://localhost:8000/docs

---

**维护者**: 后端开发团队  
**最后更新**: 2026-01-16
