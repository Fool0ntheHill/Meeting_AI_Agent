# GSUC 自动重试机制

## 概述

当 GSUC 认证失败（如 code 过期、服务器错误等）时，系统会自动重定向到登录页并触发重新登录，无需用户手动清理。

## 后端实现

### 自动兜底逻辑

当 GSUC 回调处理失败时，后端会：

1. **捕获所有认证错误**（GSUCAuthError 和其他异常）
2. **重定向到前端登录页**，携带 `gsuc_retry=1` 参数
3. **附加失败原因**：`reason=auth_failed` 或 `reason=server_error`

```python
# src/api/routes/auth.py - gsuc_callback_compat 函数

except GSUCAuthError as e:
    logger.error(f"GSUC auth failed: {e.message}")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    retry_url = f"{frontend_url}/login?gsuc_retry=1&reason=auth_failed"
    return RedirectResponse(url=retry_url, status_code=302)

except Exception as e:
    logger.error(f"GSUC callback error: {e}")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    retry_url = f"{frontend_url}/login?gsuc_retry=1&reason=server_error"
    return RedirectResponse(url=retry_url, status_code=302)
```

### 重定向 URL 格式

```
http://localhost:5173/login?gsuc_retry=1&reason=auth_failed
http://localhost:5173/login?gsuc_retry=1&reason=server_error
```

**参数说明**：
- `gsuc_retry=1`: 标识需要自动重试
- `reason`: 失败原因（`auth_failed` 或 `server_error`）

---

## 前端实现

### React/TypeScript 示例

```typescript
// Login.tsx 或登录页面组件

import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

function LoginPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    // 检查是否需要自动重试
    const gsucRetry = searchParams.get('gsuc_retry');
    const reason = searchParams.get('reason');

    if (gsucRetry === '1') {
      console.log(`GSUC 登录失败，原因: ${reason}，正在自动重试...`);

      // 1. 清理本地存储
      localStorage.removeItem('SESSIONID');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_id');
      localStorage.removeItem('tenant_id');
      // 清理其他相关的 token/session

      // 2. 显示提示信息（可选）
      showToast('上次登录已过期，正在重新获取扫码页...', 'info');

      // 3. 清理 URL 参数
      searchParams.delete('gsuc_retry');
      searchParams.delete('reason');
      navigate({ search: searchParams.toString() }, { replace: true });

      // 4. 自动触发重新登录
      setTimeout(() => {
        jumpToGSUCLogin();
      }, 500); // 短暂延迟，让用户看到提示
    }
  }, [searchParams, navigate]);

  // 跳转到 GSUC 登录
  const jumpToGSUCLogin = async () => {
    try {
      // 调用后端接口获取 GSUC 登录 URL
      const response = await fetch('/api/v1/auth/gsuc/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          frontend_callback_url: `${window.location.origin}/login`
        })
      });

      const data = await response.json();

      // 跳转到 GSUC 登录页面
      window.location.href = data.login_url;
    } catch (error) {
      console.error('获取 GSUC 登录 URL 失败:', error);
      showToast('登录失败，请稍后重试', 'error');
    }
  };

  return (
    <div>
      <h1>登录</h1>
      <button onClick={jumpToGSUCLogin}>
        使用企业微信登录
      </button>
    </div>
  );
}
```

### Vue 3 示例

```vue
<template>
  <div>
    <h1>登录</h1>
    <button @click="jumpToGSUCLogin">使用企业微信登录</button>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

onMounted(() => {
  // 检查是否需要自动重试
  const gsucRetry = route.query.gsuc_retry;
  const reason = route.query.reason;

  if (gsucRetry === '1') {
    console.log(`GSUC 登录失败，原因: ${reason}，正在自动重试...`);

    // 1. 清理本地存储
    localStorage.removeItem('SESSIONID');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('tenant_id');

    // 2. 显示提示信息
    showToast('上次登录已过期，正在重新获取扫码页...', 'info');

    // 3. 清理 URL 参数
    router.replace({ query: {} });

    // 4. 自动触发重新登录
    setTimeout(() => {
      jumpToGSUCLogin();
    }, 500);
  }
});

const jumpToGSUCLogin = async () => {
  try {
    const response = await fetch('/api/v1/auth/gsuc/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        frontend_callback_url: `${window.location.origin}/login`
      })
    });

    const data = await response.json();
    window.location.href = data.login_url;
  } catch (error) {
    console.error('获取 GSUC 登录 URL 失败:', error);
    showToast('登录失败，请稍后重试', 'error');
  }
};
</script>
```

---

## 用户体验流程

### 正常流程

1. 用户点击"使用企业微信登录"
2. 跳转到 GSUC 扫码页面
3. 扫码成功，GSUC 回调到后端
4. 后端验证成功，重定向到前端并携带 JWT
5. 前端保存 token，跳转到主页

### 自动重试流程（code 过期/服务器错误）

1. GSUC 回调到后端，但验证失败（code 过期或服务器错误）
2. **后端自动重定向**到 `/login?gsuc_retry=1&reason=xxx`
3. **前端检测到 `gsuc_retry=1`**
4. **自动清理本地存储**（token、session 等）
5. **显示提示信息**："上次登录已过期，正在重新获取扫码页..."
6. **自动调用登录接口**，获取新的 GSUC 登录 URL
7. **自动跳转到新的扫码页面**
8. 用户重新扫码，完成登录

**用户感知**：只看到一次短暂的页面跳转和提示信息，无需手动操作。

---

## 配置

### 环境变量

后端需要配置前端 URL：

```bash
# .env 或环境变量
FRONTEND_URL=http://localhost:5173
```

或在代码中使用默认值：

```python
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
```

### 生产环境

生产环境需要修改为实际的前端域名：

```bash
FRONTEND_URL=https://your-domain.com
```

---

## 错误原因说明

### `reason=auth_failed`

- **含义**: GSUC 认证失败（如 code 无效、已使用、权限不足等）
- **常见原因**:
  - OAuth2 code 已被使用（重复访问回调 URL）
  - Code 已过期（超过有效期）
  - GSUC 服务返回认证错误

### `reason=server_error`

- **含义**: 服务器内部错误
- **常见原因**:
  - GSUC API 返回 500 错误
  - 网络连接失败
  - 数据库错误
  - 其他未预期的异常

---

## 第一次就失败（500 错误）排查指南

### 问题特征

- 刚扫完码，第一次回调就报 500 错误
- 不是 code 重复导致的（因为是第一次使用）
- 后续刷新页面会因为 code 重复继续失败

### 可能原因

#### 1. 加密密钥配置错误（最常见）

**症状**：
```
GSUC API request failed: Server error '500 Internal Server Error'
```

**原因**：
- `config/development.yaml` 中的 `encryption_key` 与 GSUC 服务器配置不匹配
- 加密密钥长度不正确（必须是 32 字节）
- Base64 解码失败

**排查步骤**：

1. 检查后端日志中的加密密钥信息：
   ```
   [debug] Encryption key length: XX bytes (expected 32)
   ```

2. 验证配置文件：
   ```yaml
   # config/development.yaml
   gsuc:
     enabled: true
     appid: "app_meeting_agent"
     appsecret: "your_appsecret"
     encryption_key: "your_base64_encoded_key"  # 必须是 Base64 编码的 32 字节密钥
   ```

3. 测试密钥解码：
   ```python
   import base64
   key = base64.b64decode("your_encryption_key")
   print(f"Key length: {len(key)} bytes")  # 应该是 32
   ```

4. **联系 GSUC 运维**确认：
   - `appid` 是否正确
   - `appsecret` 是否正确
   - `encryption_key` 是否正确
   - 回调地址是否在白名单中

#### 2. 浏览器预取导致 code 被提前消耗

**症状**：
- 第一次就失败，但配置确认无误
- 浏览器 Network 面板显示同一个 URL 被请求了两次

**原因**：
- 某些浏览器（如 Chrome）或浏览器插件会预加载链接
- 安全软件在后台检查 URL
- 第一次预取消耗了 code，第二次真正访问时 code 已失效

**解决方案**：

1. **添加随机 state 参数**（防止缓存）：
   ```typescript
   const state = crypto.randomUUID();
   const loginUrl = `${data.login_url}&state=${state}`;
   window.location.href = loginUrl;
   ```

2. **禁用浏览器预取**（临时测试）：
   - Chrome: `chrome://flags/#prefetch-privacy-changes` 设为 Disabled
   - 或使用隐私模式测试

3. **检查浏览器插件**：
   - 临时禁用所有插件测试
   - 特别是安全类、广告拦截类插件

#### 3. GSUC 服务器问题

**症状**：
- 后端日志显示请求发送成功
- GSUC 直接返回 500 错误
- 响应体为空或包含 GSUC 内部错误信息

**排查步骤**：

1. 检查后端日志中的详细响应：
   ```
   [error] GSUC returned 500 error
   [error] Response body: ...
   ```

2. **联系 GSUC 运维**：
   - 提供完整的错误日志
   - 提供请求时间戳
   - 询问 GSUC 服务器状态

### 调试日志

后端已添加详细的调试日志，重启后端后查看：

```bash
# 启动后端
python main.py

# 或使用脚本
.\scripts\start_backend.ps1
```

**关键日志**：
```
[debug] Encryption key length: 32 bytes (expected 32)
[debug] Generated access_token: 2qUyYNOknTt6evAQh3...
[debug] Request URL: https://gsuc.gamesci.com.cn/sso/userinfo
[debug] GSUC response status: 500
[error] GSUC returned 500 error
[error] Response body: ...
```

### 临时解决方案

如果 GSUC 登录暂时无法使用，可以使用开发登录：

```bash
# 调用开发登录接口
curl -X POST http://localhost:8000/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser"}'
```

或在前端添加开发登录按钮（仅开发环境）。

---

## 测试

### 测试自动重试

1. **模拟 code 过期**：
   ```bash
   # 直接访问旧的回调 URL（带过期的 code）
   http://localhost:8000/api/v1/auth/callback?code=expired_code&appid=xxx
   ```

2. **预期行为**：
   - 后端捕获错误
   - 重定向到 `/login?gsuc_retry=1&reason=auth_failed`
   - 前端自动清理存储
   - 自动跳转到新的扫码页面

3. **验证**：
   - 检查浏览器 Network 面板，确认重定向链
   - 检查 localStorage 是否被清理
   - 确认自动跳转到 GSUC 登录页

---

## 注意事项

1. **避免无限循环**：确保前端只在检测到 `gsuc_retry=1` 时触发一次重试，清理 URL 参数后不再重复
2. **用户体验**：提示信息应简洁明了，避免技术术语
3. **日志记录**：后端和前端都应记录重试事件，便于排查问题
4. **超时处理**：如果多次重试失败，应提供手动重试按钮或联系管理员的提示

---

## 相关文档

- [GSUC SSO 快速开始](./MAIN_SSO_QUICK_START.md)
- [GSUC SSO 实现指南](./MAIN_SSO_IMPLEMENTATION.md)
- [GSUC SSO FAQ](./GSUC_SSO_FAQ.md)
