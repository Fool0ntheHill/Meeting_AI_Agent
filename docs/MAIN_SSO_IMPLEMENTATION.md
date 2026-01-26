# main.py GSUC SSO 实现文档

## 📋 概述

`main.py` 是一个独立的 FastAPI 应用，实现了 GSUC 单点登录 (SSO) 的回调接口逻辑。

### 核心功能

1. **加密算法迁移**: 将 Python 2 的 AES 加密代码完美迁移到 Python 3
2. **回调接口**: 处理 GSUC OAuth2.0 回调，验证用户身份
3. **SessionID 生成**: 生成会话标识并重定向到前端

---

## 🔐 加密算法详解

### Python 2 -> Python 3 迁移要点

#### 1. 字符串常量变化
```python
# Python 2
string.letters  # 所有字母 (大小写)

# Python 3
string.ascii_letters  # ASCII 字母 (大小写)
```

#### 2. 随机采样方法
```python
# Python 2
random.sample(string.letters + string.digits, 16)  # 不允许重复

# Python 3
random.choices(string.ascii_letters + string.digits, k=16)  # 允许重复
```

#### 3. 异常处理语法
```python
# Python 2
except Exception, e:

# Python 3
except Exception as e:
```

#### 4. 字节与字符串转换
```python
# Python 3 需要显式处理 bytes/str 转换
text_all.encode('utf-8')  # str -> bytes
base64.b64encode(ciphertext).decode('utf-8')  # bytes -> str
```

### 加密算法流程

```
输入: text (待加密文本), key (Base64 编码的 32 字节密钥)

1. 解码密钥
   key_bytes = base64.b64decode(key)
   验证: len(key_bytes) == 32

2. 添加随机前缀 (16 字符)
   random_prefix = random.choices(ascii_letters + digits, k=16)
   text_random = random_prefix + text

3. 补齐长度为 32 的倍数
   add_num = 32 - (len(text_random) % 32)
   if add_num == 0: add_num = 32
   text_all = text_random + chr(add_num) * add_num

4. AES-256-CBC 加密
   iv = key_bytes[:16]  # 使用密钥前 16 字节作为 IV
   cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
   ciphertext = cipher.encrypt(text_all.encode('utf-8'))

5. Base64 编码
   return base64.b64encode(ciphertext).decode('utf-8')
```

---

## 🚀 使用方式

### 1. 安装依赖

```bash
pip install fastapi uvicorn httpx pycryptodome
```

### 2. 启动服务

```bash
# 方式 1: 直接运行
python main.py

# 方式 2: 使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 测试加密
curl "http://localhost:8000/api/v1/auth/test-encrypt?text=hello"
```

---

## 📡 API 端点

### 1. 根路径
```
GET /
```

**响应:**
```json
{
  "service": "GSUC SSO Service",
  "status": "running",
  "endpoints": {
    "callback": "/api/v1/auth/callback",
    "health": "/health"
  }
}
```

### 2. 健康检查
```
GET /health
```

**响应:**
```json
{
  "status": "healthy"
}
```

### 3. 回调接口 (核心)
```
GET /api/v1/auth/callback?code={code}
```

**参数:**
- `code` (必需): GSUC 返回的授权 code

**流程:**
1. 接收 code
2. 生成 access_token = encrypt(code + APP_ID + APP_SECRET, APP_SECRET)
3. 请求 GSUC 用户信息 API
4. 验证返回结果 (rc == 0)
5. 生成 SessionID: `session_{account}_{uid}`
6. 重定向到前端: `{FRONTEND_URL}?token={session_id}`

**成功响应:**
```
HTTP 307 Temporary Redirect
Location: http://localhost:5173?token=session_zhangsan_1003
```

**错误响应:**
```json
{
  "detail": "GSUC 认证失败: 错误信息"
}
```

### 4. 加密测试端点
```
GET /api/v1/auth/test-encrypt?text={text}&key={key}
```

**参数:**
- `text` (必需): 待加密的文本
- `key` (可选): Base64 编码的密钥 (默认使用 APP_SECRET)

**响应:**
```json
{
  "success": true,
  "input_text": "hello",
  "input_length": 5,
  "encrypted": "chB0O4HYUITFHlTAnBjKohQgVBieJSp/17Xg5OWr9I0=",
  "encrypted_length": 44
}
```

---

## 🔄 完整 SSO 流程

```
┌─────────┐         ┌─────────┐         ┌──────────┐         ┌─────────┐
│  前端   │         │  GSUC   │         │  后端    │         │  前端   │
│  应用   │         │  登录   │         │  回调    │         │  回调   │
└────┬────┘         └────┬────┘         └────┬─────┘         └────┬────┘
     │                   │                   │                    │
     │ 1. 重定向到 GSUC  │                   │                    │
     ├──────────────────>│                   │                    │
     │                   │                   │                    │
     │ 2. 用户扫码登录   │                   │                    │
     │                   │                   │                    │
     │                   │ 3. 重定向到后端   │                    │
     │                   │   (携带 code)     │                    │
     │                   ├──────────────────>│                    │
     │                   │                   │                    │
     │                   │                   │ 4. 生成 access_token
     │                   │                   │    (加密算法)      │
     │                   │                   │                    │
     │                   │ 5. 请求用户信息   │                    │
     │                   │<──────────────────┤                    │
     │                   │                   │                    │
     │                   │ 6. 返回用户信息   │                    │
     │                   ├──────────────────>│                    │
     │                   │                   │                    │
     │                   │                   │ 7. 生成 SessionID  │
     │                   │                   │                    │
     │                   │                   │ 8. 重定向到前端    │
     │                   │                   │    (携带 token)    │
     │                   │                   ├───────────────────>│
     │                   │                   │                    │
     │                   │                   │                    │ 9. 保存 token
     │                   │                   │                    │    完成登录
     │                   │                   │                    │
```

### 详细步骤

1. **前端重定向到 GSUC**
   ```
   https://gsuc.gamesci.com.cn/sso/login?appid=app_meeting_agent&redirect_uri=http://localhost:8000/api/v1/auth/callback
   ```

2. **用户扫码登录**
   - 用户使用企业微信/钉钉等扫码
   - GSUC 验证用户身份

3. **GSUC 重定向到后端**
   ```
   http://localhost:8000/api/v1/auth/callback?code=abc123xyz
   ```

4. **后端生成 access_token**
   ```python
   text = code + APP_ID + APP_SECRET
   access_token = encrypt(text, APP_SECRET)
   ```

5. **后端请求用户信息**
   ```
   GET https://gsuc.gamesci.com.cn/sso/userinfo?code=abc123xyz&access_token=xxx
   ```

6. **GSUC 返回用户信息**
   ```json
   {
     "rc": 0,
     "msg": "success",
     "uid": 1003,
     "account": "zhangsan",
     "username": "张三",
     "avatar": "https://..."
   }
   ```

7. **后端生成 SessionID**
   ```python
   session_id = f"session_{account}_{uid}"
   # 例如: session_zhangsan_1003
   ```

8. **后端重定向到前端**
   ```
   HTTP 307 Temporary Redirect
   Location: http://localhost:5173?token=session_zhangsan_1003
   ```

9. **前端保存 token，完成登录**
   ```javascript
   const params = new URLSearchParams(window.location.search);
   const token = params.get('token');
   localStorage.setItem('session_token', token);
   ```

---

## 🧪 测试

### 1. 运行完整测试

```bash
# 先启动服务
python main.py

# 在另一个终端运行测试
python scripts/test_main_sso.py
```

### 2. 测试加密算法

```bash
python scripts/test_gsuc_sso_complete.py
```

### 3. 手动测试

```bash
# 测试加密
curl "http://localhost:8000/api/v1/auth/test-encrypt?text=hello"

# 测试回调 (需要真实 code)
curl "http://localhost:8000/api/v1/auth/callback?code=YOUR_REAL_CODE"
```

---

## ⚙️ 配置参数

### 必需配置

```python
APP_ID = "app_meeting_agent"
APP_SECRET = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
GSUC_URL = "https://gsuc.gamesci.com.cn/sso/userinfo"
FRONTEND_URL = "http://localhost:5173"
```

### 配置说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `APP_ID` | GSUC 应用 ID (向运维申请) | `app_meeting_agent` |
| `APP_SECRET` | GSUC 应用密钥 (Base64 编码的 32 字节) | `G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw=` |
| `GSUC_URL` | GSUC 用户信息 API 地址 | `https://gsuc.gamesci.com.cn/sso/userinfo` |
| `FRONTEND_URL` | 前端回调地址 | `http://localhost:5173` |

---

## 🔍 调试

### 查看详细日志

服务启动后，每次回调都会打印详细日志:

```
============================================================
收到 GSUC 回调请求
============================================================
Code: abc123xyz...

生成 access_token...
  待加密文本长度: 85 字符
✓ access_token 生成成功
  Token (前50字符): chB0O4HYUITFHlTAnBjKohQgVBieJSp/17Xg5OWr9I0xARv9Gq...

请求 GSUC 用户信息...
  URL: https://gsuc.gamesci.com.cn/sso/userinfo
  参数: code=abc123xyz..., access_token=chB0O4HYUITFHlTAnBjKohQgVBieJSp...
✓ GSUC API 响应成功
  响应数据: {'rc': 0, 'msg': 'success', 'uid': 1003, ...}
✓ GSUC 认证成功
  用户信息:
    UID: 1003
    Account: zhangsan
    Username: 张三

✓ 生成 SessionID: session_zhangsan_1003

重定向到前端:
  URL: http://localhost:5173?token=session_zhangsan_1003
============================================================
```

### 常见问题

#### 1. 加密失败
```
错误: 密钥长度为 X 字节，期望 32 字节
```
**解决**: 确保 `APP_SECRET` 是 Base64 编码的 32 字节密钥

#### 2. GSUC API 请求失败
```
✗ GSUC API 请求失败: HTTPError
```
**解决**: 
- 检查网络连接
- 确认 GSUC_URL 正确
- 验证 code 是否有效 (code 只能使用一次)

#### 3. 认证失败
```
✗ GSUC 认证失败: rc=1001, msg=invalid code
```
**解决**:
- code 已过期或已使用
- access_token 计算错误
- APP_ID 或 APP_SECRET 不正确

---

## 📦 依赖

```txt
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pycryptodome>=3.19.0
```

---

## 🔒 安全注意事项

1. **密钥保护**: `APP_SECRET` 应该存储在环境变量或配置文件中，不要硬编码
2. **HTTPS**: 生产环境必须使用 HTTPS
3. **State 验证**: 生产环境应该验证 state 参数防止 CSRF 攻击
4. **Code 有效期**: code 只能使用一次，使用后立即失效
5. **SessionID 管理**: 应该使用更安全的 session 管理机制 (如 JWT)

---

## 📝 与现有系统集成

如果要将此实现集成到现有的 FastAPI 应用中:

1. **复制加密函数**
   ```python
   # 从 main.py 复制 encrypt() 函数到你的项目
   ```

2. **添加路由**
   ```python
   # 从 main.py 复制 gsuc_callback() 函数
   # 添加到你的路由文件中
   ```

3. **更新配置**
   ```python
   # 使用你的配置系统替换硬编码的配置
   ```

4. **集成用户系统**
   ```python
   # 将 SessionID 替换为你的 JWT Token 或 Session 管理
   ```

---

## ✅ 验证清单

部署前请确认:

- [ ] APP_ID 和 APP_SECRET 正确
- [ ] 回调地址在 GSUC 白名单中
- [ ] 加密算法测试通过
- [ ] 端点可访问
- [ ] 日志正常输出
- [ ] 前端能正确接收 token
- [ ] 使用 HTTPS (生产环境)
- [ ] 密钥存储安全

---

## 📚 相关文档

- [GSUC OAuth2.0 文档](../docs/external_api_docs/gsuc_oauth2.md)
- [现有 auth.py 实现](../src/api/routes/auth.py)
- [GSUC Auth Provider](../src/providers/gsuc_auth.py)
- [测试脚本](../scripts/test_gsuc_sso_complete.py)

---

## 🎯 总结

`main.py` 提供了一个完整、独立的 GSUC SSO 实现:

✅ **加密算法**: 完美迁移 Python 2 -> Python 3  
✅ **回调处理**: 完整的 OAuth2.0 流程  
✅ **错误处理**: 详细的日志和错误信息  
✅ **测试覆盖**: 完整的测试套件  
✅ **文档完善**: 详细的使用说明  

可以直接使用，也可以作为参考集成到现有系统中。
