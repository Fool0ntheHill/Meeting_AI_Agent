# 前端开发补充说明

**日期**: 2026-01-16  
**目的**: 提供核心文档之外的补充细节和最佳实践

> **注意**: 本文档是 `FRONTEND_DEVELOPMENT_GUIDE.md` 的补充，不是替代。
> 核心 API 接口、错误处理、权限说明等已在开发指南中完整说明。

---

## 📖 文档定位

### 核心文档（必读）
- `FRONTEND_DEVELOPMENT_GUIDE.md` - 完整的 API 接口、错误处理、权限说明
- `frontend-types.ts` - 完整的类型定义
- `FRONTEND_QUICK_REFERENCE.md` - 快速查找

### 本文档（按需参考）
- 企业微信登录流程（Phase 2，待实现）
- Markdown 编辑器配置（Vditor）
- 安全策略和最佳实践
- 技术栈推荐

---

## 1. 企业微信登录说明 ⏳ Phase 2

> **状态**: 后端接口待实现  
> **开发环境**: 使用 `POST /api/v1/auth/dev/login`（已实现）

### 1.1 认证方式对比

| 环境 | 认证方式 | 接口 | 状态 |
|------|---------|------|------|
| 开发环境 | 用户名登录 | POST /api/v1/auth/dev/login | ✅ 已实现 |
| 生产环境 | 企业微信扫码 | POST /api/v1/auth/wechat/login | ⏳ 待实现 |

### 1.2 企业微信登录流程（待实现）

```typescript
// 1. 前端显示二维码
GET /api/v1/auth/wechat/qrcode

Response:
{
  "qrcode_url": "https://open.work.weixin.qq.com/...",
  "qrcode_image": "data:image/png;base64,...",
  "state": "random_state_string",
  "expires_in": 300  // 5分钟
}

// 2. 用户扫码后，企业微信回调后端
// 后端接收: GET /api/v1/auth/wechat/callback?code=xxx&state=xxx

// 3. 前端轮询检查登录状态
GET /api/v1/auth/wechat/status?state={state}

Response (success):
{
  "status": "success",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": "user_123",
  "tenant_id": "tenant_456",
  "user_name": "张三",
  "department": "研发部",
  "expires_in": 86400
}
```

### 1.3 前端实现示例

```typescript
class WeChatAuth {
  private pollInterval = 2000;  // 2秒轮询一次
  private maxPollTime = 300000;  // 最多轮询5分钟

  async login(): Promise<WeChatLoginResponse> {
    // 1. 获取二维码
    const qrcode = await api.get('/auth/wechat/qrcode');
    
    // 2. 显示二维码
    this.showQRCode(qrcode.qrcode_image);
    
    // 3. 轮询登录状态
    const startTime = Date.now();
    
    while (Date.now() - startTime < this.maxPollTime) {
      const status = await api.get(`/auth/wechat/status?state=${qrcode.state}`);
      
      if (status.status === 'success') {
        this.saveToken(status.access_token);
        return status;
      } else if (status.status === 'expired') {
        return this.login();  // 重新获取二维码
      }
      
      await this.sleep(this.pollInterval);
    }
    
    throw new Error('登录超时');
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

### 1.4 环境切换策略

```typescript
// config.ts
const AUTH_CONFIG = {
  development: {
    type: 'dev',
    endpoint: '/api/v1/auth/dev/login',
  },
  production: {
    type: 'wechat',
    endpoint: '/api/v1/auth/wechat/login',
  },
};

const authConfig = AUTH_CONFIG[process.env.NODE_ENV || 'development'];

// 统一的登录接口
async function login(credentials?: { username?: string }): Promise<LoginResponse> {
  if (authConfig.type === 'dev') {
    return await api.post(authConfig.endpoint, {
      username: credentials?.username || 'test_user',
    });
  } else {
    const wechatAuth = new WeChatAuth();
    return await wechatAuth.login();
  }
}
```

---

## 2. Markdown 编辑器配置

### 2.1 推荐：Vditor

**为什么选择 Vditor**:
- ✅ 支持所见即所得和源码模式切换
- ✅ 内置图片上传
- ✅ 支持数学公式、流程图、甘特图
- ✅ 移动端友好
- ✅ 主题可定制
- ✅ 中文文档完善

**安装**:
```bash
npm install vditor
# or
yarn add vditor
```

### 2.2 基础配置

```typescript
import Vditor from 'vditor';
import 'vditor/dist/index.css';

const vditor = new Vditor('editor-container', {
  height: 600,
  mode: 'wysiwyg',  // 所见即所得模式
  placeholder: '请输入内容...',
  
  // 安全配置
  preview: {
    markdown: {
      sanitize: true,  // ✅ 启用 sanitize
    },
  },
  
  // 工具栏
  toolbar: [
    'emoji',
    'headings',
    'bold',
    'italic',
    'strike',
    '|',
    'line',
    'quote',
    'list',
    'ordered-list',
    'check',
    '|',
    'code',
    'inline-code',
    'link',
    'table',
    '|',
    'undo',
    'redo',
    '|',
    'edit-mode',
    'preview',
    'fullscreen',
  ],
  
  // 上传配置
  upload: {
    url: '/api/v1/upload/image',
    max: 10 * 1024 * 1024,  // 10MB
    accept: 'image/*',
    handler(files) {
      return uploadImages(files);
    },
  },
  
  // 主题
  theme: 'classic',
  
  // 回调
  after() {
    console.log('Vditor initialized');
  },
});

// 获取内容
const markdown = vditor.getValue();

// 设置内容
vditor.setValue('# Hello World');

// 切换模式
vditor.setMode('ir');  // 即时渲染模式
vditor.setMode('wysiwyg');  // 所见即所得模式
vditor.setMode('sv');  // 源码模式
```

---

## 3. Markdown 安全策略

### 3.1 XSS 防护

**问题**: 用户可能在 Markdown 中注入恶意脚本

**解决方案**: 使用 DOMPurify 清理 HTML

```typescript
import DOMPurify from 'dompurify';
import { marked } from 'marked';

function renderMarkdown(markdown: string): string {
  // 1. Markdown 转 HTML
  const html = marked(markdown);
  
  // 2. 清理 HTML
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'strong', 'em', 'u', 's', 'code', 'pre',
      'ul', 'ol', 'li',
      'blockquote',
      'a', 'img',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
    ],
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title',
      'class', 'id',
    ],
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|data):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  });
  
  return clean;
}
```

### 3.2 图片处理

```typescript
// 图片上传
async function uploadImages(files: File[]): Promise<string[]> {
  const urls = [];
  
  for (const file of files) {
    // 1. 验证文件类型
    if (!file.type.startsWith('image/')) {
      throw new Error('只支持图片文件');
    }
    
    // 2. 验证文件大小
    if (file.size > 10 * 1024 * 1024) {
      throw new Error('图片大小不能超过 10MB');
    }
    
    // 3. 上传
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/v1/upload/image', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
      body: formData,
    });
    
    const data = await response.json();
    urls.push(data.url);
  }
  
  return urls;
}

// 图片转 Base64（用于复制）
async function imageToBase64(url: string): Promise<string> {
  const response = await fetch(url);
  const blob = await response.blob();
  
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
```

---

## 4. 技术栈推荐

### 4.1 核心库

```json
{
  "dependencies": {
    // 前端框架
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    
    // UI 组件库
    "antd": "^5.0.0",
    
    // 状态管理
    "zustand": "^4.0.0",
    
    // HTTP 客户端
    "axios": "^1.0.0",
    
    // Markdown 编辑器
    "vditor": "^3.9.0",
    
    // 安全处理
    "dompurify": "^3.0.0",
    
    // 音频处理
    "wavesurfer.js": "^7.0.0",
    "howler": "^2.2.0",
    
    // 拖拽排序
    "@dnd-kit/core": "^6.0.0",
    "@dnd-kit/sortable": "^7.0.0",
    
    // 文件上传
    "react-dropzone": "^14.0.0",
    
    // Diff 对比
    "diff-match-patch": "^1.0.5"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/react": "^18.0.0",
    "@types/dompurify": "^3.0.0"
  }
}
```

### 4.2 项目结构建议

```
src/
├── api/
│   ├── client.ts          # API 客户端封装
│   └── endpoints/         # API 端点定义
├── components/
│   ├── AudioPlayer/       # 音频播放器
│   ├── MarkdownEditor/    # Markdown 编辑器
│   ├── FileUpload/        # 文件上传
│   └── ...
├── pages/
│   ├── Login/             # 登录页
│   ├── TaskList/          # 任务列表
│   ├── Workbench/         # 工作台
│   └── ...
├── stores/
│   ├── authStore.ts       # 认证状态
│   ├── taskStore.ts       # 任务状态
│   └── ...
├── types/
│   └── api.ts             # 从 frontend-types.ts 复制
├── utils/
│   ├── markdown.ts        # Markdown 处理
│   ├── upload.ts          # 上传工具
│   └── ...
└── App.tsx
```

---

## 5. 最佳实践

### 5.1 Token 管理

```typescript
class TokenManager {
  private static TOKEN_KEY = 'access_token';
  private static EXPIRY_KEY = 'token_expiry';

  static saveToken(token: string, expiresIn: number): void {
    localStorage.setItem(this.TOKEN_KEY, token);
    const expiry = Date.now() + expiresIn * 1000;
    localStorage.setItem(this.EXPIRY_KEY, expiry.toString());
  }

  static getToken(): string | null {
    const token = localStorage.getItem(this.TOKEN_KEY);
    const expiry = localStorage.getItem(this.EXPIRY_KEY);

    if (!token || !expiry) return null;

    if (Date.now() > parseInt(expiry)) {
      this.clearToken();
      return null;
    }

    return token;
  }

  static clearToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.EXPIRY_KEY);
  }
}
```

### 5.2 轮询优化

```typescript
// 使用指数退避减少服务器压力
async function smartPoll(taskId: string, onUpdate: (status: TaskStatus) => void) {
  let interval = 2000;  // 初始 2 秒
  const maxInterval = 10000;  // 最大 10 秒

  while (true) {
    const status = await api.getTaskStatus(taskId);
    onUpdate(status);
    
    if (status.state === 'success' || status.state === 'failed') {
      break;
    }

    await new Promise(r => setTimeout(r, interval));
    interval = Math.min(interval * 1.5, maxInterval);
  }
}
```

### 5.3 请求重试

```typescript
async function retryRequest<T>(
  fn: () => Promise<T>,
  maxRetries = 3
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
  throw new Error('Max retries exceeded');
}
```

---

## 6. 常见问题

### Q: 如何处理大文件上传？
**A**: 当前实现支持最大 500MB 直接上传。未来可以考虑：
- 使用 TOS 直传（需要后端提供签名接口）
- 分片上传（需要后端支持）

### Q: 如何实现版本对比？
**A**: 使用 `diff-match-patch` 库，参考 `FRONTEND_DEVELOPMENT_GUIDE.md` §功能 3.1

### Q: 如何配置 Vditor 主题？
**A**: 参考本文档 §2.2，可以设置 `theme: 'classic' | 'dark'`

### Q: 生产环境认证会变吗？
**A**: 会，生产环境将使用企业微信扫码登录（Phase 2），但 Token 使用方式相同

---

## 📚 相关文档

- **核心开发指南**: `FRONTEND_DEVELOPMENT_GUIDE.md`
- **类型定义**: `frontend-types.ts`
- **快速参考**: `FRONTEND_QUICK_REFERENCE.md`
- **用户工作流程**: `FRONTEND_USER_WORKFLOW.md`
- **功能清单**: `FRONTEND_FEATURE_CHECKLIST.md`

---

**维护者**: 后端开发团队  
**最后更新**: 2026-01-16
