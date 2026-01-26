# GSUC 回调问题修复指南

## 🔍 问题诊断

### 当前现象
扫码登录后，浏览器停在：
```
http://localhost:8000/api/v1/auth/callback?appid=app_meeting_agent&code=Io7sRqQjWYnvpty8z1a6BjU1IQlUQftT&gsuc_auth_type=wecom&state=
```

### 问题分析

1. **路径不匹配**
   - GSUC 回调到: `/api/v1/auth/callback`
   - 代码路由是: `/api/v1/auth/gsuc/callback`
   - ❌ 404 Not Found

2. **缺少 frontend_callback 参数**
   - 代码需要 `frontend_callback` 参数来知道重定向到哪里
   - 当前 URL 没有这个参数

3. **state 为空**
   - URL 中 `state=` 后面没有值
   - 可能是 GSUC 配置问题

4. **GSUC 配置未启用**
   - `config/development.yaml` 中 GSUC 配置被注释了

---

## 🛠️ 解决方案

### 方案 1: 修改 GSUC 配置 (推荐)

#### 步骤 1: 启用 GSUC 配置

编辑 `config/development.yaml`，取消注释并填入正确的值：

```yaml
# GSUC OAuth2.0 单点登录
gsuc:
  enabled: true
  appid: "app_meeting_agent"  # 你的 APP ID
  appsecret: "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="  # 你的 APP SECRET
  encryption_key: "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="  # 加密密钥
  login_url: "https://gsuc.gamesci.com.cn/sso/login"
  userinfo_url: "https://gsuc.gamesci.com.cn/sso/userinfo"
  callback_url: "http://localhost:8000/api/v1/auth/gsuc/callback"  # ✅ 正确的回调地址
  timeout: 30
```

#### 步骤 2: 在 GSUC 后台修改回调地址

联系运维，将 GSUC 后台配置的回调地址改为：
```
http://localhost:8000/api/v1/auth/gsuc/callback
```

**注意**: 必须在 GSUC 白名单中添加这个地址！

#### 步骤 3: 前端调用流程

前端需要先调用 `/api/v1/auth/gsuc/login` 获取登录 URL：

```javascript
// 1. 前端请求登录 URL
const response = await fetch('http://localhost:8000/api/v1/auth/gsuc/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    frontend_callback_url: 'http://localhost:5173/login'  // 前端回调地址
  })
});

const { login_url, state } = await response.json();

// 2. 重定向到 GSUC 登录页面
window.location.href = login_url;

// 3. 用户扫码登录后，GSUC 会回调到后端
// 4. 后端处理完成后，会重定向到前端: http://localhost:5173/login?access_token=xxx&user_id=xxx&...

// 5. 前端接收 token
const urlParams = new URLSearchParams(window.location.search);
const accessToken = urlParams.get('access_token');
const userId = urlParams.get('user_id');

// 6. 保存 token
localStorage.setItem('access_token', accessToken);
localStorage.setItem('user_id', userId);
```

---

### 方案 2: 添加兼容路由 (临时方案)

如果无法修改 GSUC 后台配置，可以添加一个兼容路由：

#### 修改 `src/api/routes/auth.py`

在文件末尾添加：

```python
@router.get("/callback")
async def gsuc_callback_compat(
    code: str = Query(..., description="GSUC 返回的授权 code"),
    appid: str = Query(None, description="GSUC 返回的 appid"),
    gsuc_auth_type: str = Query(None, description="认证类型"),
    state: str = Query("", description="状态参数"),
    db: Session = Depends(get_db)
):
    """
    GSUC OAuth2.0 回调 - 兼容路由
    
    兼容 GSUC 直接回调到 /api/v1/auth/callback 的情况
    """
    config = get_config()
    
    # 检查 GSUC 是否启用
    if not config.gsuc or not config.gsuc.enabled:
        raise HTTPException(
            status_code=403,
            detail="GSUC 认证未启用"
        )
    
    # 创建 GSUC 认证提供商
    provider = GSUCAuthProvider(
        appid=config.gsuc.appid,
        appsecret=config.gsuc.appsecret,
        encryption_key=config.gsuc.encryption_key,
        login_url=config.gsuc.login_url,
        userinfo_url=config.gsuc.userinfo_url,
        timeout=config.gsuc.timeout
    )
    
    try:
        # 获取用户信息
        user_info = await provider.verify_and_get_user(code)
        
        logger.info(f"GSUC user info: uid={user_info['uid']}, account={user_info['account']}")
        
        # 查找或创建用户
        user_repo = UserRepository(db)
        user_id = f"user_gsuc_{user_info['uid']}"
        tenant_id = f"tenant_gsuc_{user_info['uid']}"
        
        user = user_repo.get_by_id(user_id)
        
        if not user:
            user = user_repo.create(
                user_id=user_id,
                username=user_info['account'],
                tenant_id=tenant_id,
                is_active=True
            )
            logger.info(f"Created new GSUC user: {user_id}")
        else:
            logger.info(f"GSUC user login: {user_id}")
        
        # 签发 JWT Token
        expires_delta = timedelta(hours=config.jwt_expire_hours)
        access_token = create_access_token(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            expires_delta=expires_delta
        )
        
        # 重定向到前端 (使用默认前端地址)
        from fastapi.responses import RedirectResponse
        from urllib.parse import urlencode
        
        # ⚠️ 这里硬编码前端地址，生产环境应该从配置读取
        frontend_url = "http://localhost:5173/login"
        
        params = {
            "access_token": access_token,
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "username": user_info['username'],
            "avatar": user_info.get('avatar', ''),
            "expires_in": str(config.jwt_expire_hours * 3600)
        }
        
        redirect_url = f"{frontend_url}?{urlencode(params)}"
        
        logger.info(f"Redirecting to frontend: {frontend_url}")
        return RedirectResponse(url=redirect_url)
        
    except GSUCAuthError as e:
        logger.error(f"GSUC auth failed: {e.message}")
        # 重定向到前端错误页面
        error_url = f"http://localhost:5173/login?error=auth_failed&message={e.message}"
        return RedirectResponse(url=error_url)
    except Exception as e:
        logger.error(f"GSUC callback error: {e}")
        error_url = f"http://localhost:5173/login?error=server_error"
        return RedirectResponse(url=error_url)
```

---

### 方案 3: 使用 main.py (最简单)

如果只是测试，可以直接使用 `main.py`:

#### 步骤 1: 修改 main.py 的配置

```python
# main.py 顶部
APP_ID = "app_meeting_agent"
APP_SECRET = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
GSUC_URL = "https://gsuc.gamesci.com.cn/sso/userinfo"
FRONTEND_URL = "http://localhost:5173/login"  # ✅ 改成你的前端登录页
```

#### 步骤 2: 在 GSUC 后台配置回调地址

```
http://localhost:8000/api/v1/auth/callback
```

#### 步骤 3: 启动 main.py

```bash
python main.py
```

#### 步骤 4: 测试

直接访问 GSUC 登录页面：
```
https://gsuc.gamesci.com.cn/sso/login?appid=app_meeting_agent&redirect_uri=http://localhost:8000/api/v1/auth/callback
```

---

## 🔍 调试步骤

### 1. 检查后端日志

启动后端后，查看日志输出：

```bash
# 如果使用 main.py
python main.py

# 如果使用 src/api/app.py
uvicorn src.api.app:app --reload
```

扫码登录后，应该看到类似的日志：

```
============================================================
收到 GSUC 回调请求
============================================================
Code: Io7sRqQjWYnvpty8z1a6BjU1IQlUQftT

生成 access_token...
✓ access_token 生成成功

请求 GSUC 用户信息...
✓ GSUC API 响应成功
✓ GSUC 认证成功
  用户信息:
    UID: 1003
    Account: zhangsan
    Username: 张三

✓ 生成 SessionID: session_zhangsan_1003

重定向到前端:
  URL: http://localhost:5173/login?token=session_zhangsan_1003
============================================================
```

### 2. 检查浏览器网络请求

打开浏览器开发者工具 (F12) -> Network 标签页

扫码登录后，应该看到：

1. **GSUC 回调到后端**
   ```
   GET http://localhost:8000/api/v1/auth/callback?code=xxx
   Status: 307 Temporary Redirect
   Location: http://localhost:5173/login?access_token=xxx
   ```

2. **浏览器重定向到前端**
   ```
   GET http://localhost:5173/login?access_token=xxx
   Status: 200 OK
   ```

如果看不到重定向，说明后端没有返回 `RedirectResponse`。

### 3. 手动测试回调接口

使用真实的 code 测试：

```bash
curl -v "http://localhost:8000/api/v1/auth/callback?code=Io7sRqQjWYnvpty8z1a6BjU1IQlUQftT"
```

应该看到：

```
< HTTP/1.1 307 Temporary Redirect
< location: http://localhost:5173/login?token=xxx
```

---

## 📋 检查清单

- [ ] GSUC 配置已启用 (`config/development.yaml`)
- [ ] 回调地址正确 (`/api/v1/auth/gsuc/callback` 或 `/api/v1/auth/callback`)
- [ ] GSUC 后台白名单已添加回调地址
- [ ] 前端回调地址正确 (`http://localhost:5173/login`)
- [ ] 后端服务已启动
- [ ] 可以看到后端日志输出
- [ ] 浏览器可以看到重定向 (307)

---

## 🎯 推荐方案

**开发环境**: 使用方案 2 (添加兼容路由)
- ✅ 无需修改 GSUC 后台配置
- ✅ 快速测试
- ✅ 保持现有代码结构

**生产环境**: 使用方案 1 (修改 GSUC 配置)
- ✅ 符合标准 OAuth2.0 流程
- ✅ 支持多个前端回调地址
- ✅ 更安全 (有 state 验证)

---

## 💡 前端集成示例

### 完整的前端登录流程

```javascript
// 1. 用户点击"企业微信登录"按钮
async function loginWithGSUC() {
  try {
    // 请求后端获取 GSUC 登录 URL
    const response = await fetch('http://localhost:8000/api/v1/auth/gsuc/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        frontend_callback_url: window.location.origin + '/login'
      })
    });
    
    const { login_url } = await response.json();
    
    // 重定向到 GSUC 登录页面
    window.location.href = login_url;
    
  } catch (error) {
    console.error('获取登录 URL 失败:', error);
  }
}

// 2. 用户扫码登录后，GSUC 回调到后端，后端重定向回前端
// 3. 前端在页面加载时检查 URL 参数
function autoInitLogin() {
  const urlParams = new URLSearchParams(window.location.search);
  const accessToken = urlParams.get('access_token');
  const userId = urlParams.get('user_id');
  const username = urlParams.get('username');
  
  if (accessToken) {
    // 保存 token
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('user_id', userId);
    localStorage.setItem('username', username);
    
    // 清除 URL 参数
    window.history.replaceState({}, document.title, window.location.pathname);
    
    // 跳转到首页
    window.location.href = '/';
  }
  
  // 检查错误
  const error = urlParams.get('error');
  if (error) {
    const message = urlParams.get('message') || '登录失败';
    alert(`登录失败: ${message}`);
  }
}

// 页面加载时自动执行
window.addEventListener('DOMContentLoaded', autoInitLogin);
```

---

## 🚀 快速修复 (5 分钟)

如果你现在就想让它工作，最快的方法：

### 1. 添加兼容路由

在 `src/api/routes/auth.py` 文件末尾添加上面"方案 2"中的代码。

### 2. 重启后端

```bash
uvicorn src.api.app:app --reload
```

### 3. 再次扫码登录

应该就能正常重定向到前端了！

---

需要我帮你实现哪个方案？
