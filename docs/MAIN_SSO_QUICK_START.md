# main.py GSUC SSO 快速开始

## 🚀 5 分钟快速上手

### 1. 安装依赖 (30 秒)

```bash
pip install fastapi uvicorn httpx pycryptodome
```

### 2. 启动服务 (10 秒)

```bash
python main.py
```

看到以下输出表示成功:
```
============================================================
GSUC SSO 服务启动
============================================================
配置:
  APP_ID: app_meeting_agent
  GSUC_URL: https://gsuc.gamesci.com.cn/sso/userinfo
  FRONTEND_URL: http://localhost:5173

启动命令:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. 测试服务 (1 分钟)

```bash
# 健康检查
curl http://localhost:8000/health

# 测试加密
curl "http://localhost:8000/api/v1/auth/test-encrypt?text=hello"
```

### 4. 运行测试 (2 分钟)

```bash
# 测试加密算法
python scripts/test_gsuc_sso_complete.py

# 测试服务端点
python scripts/test_main_sso.py
```

### 5. 查看文档 (1 分钟)

```bash
# 打开浏览器访问
http://localhost:8000/docs
```

---

## 📋 核心概念

### 加密算法 (Python 2 -> Python 3)

```python
def encrypt(text: str, key: str) -> str:
    """
    1. 解码 Base64 密钥 (32 字节)
    2. 添加 16 位随机前缀
    3. 补齐长度为 32 的倍数
    4. AES-256-CBC 加密
    5. Base64 编码返回
    """
```

### 回调流程

```
1. 接收 code
2. 生成 access_token = encrypt(code + APP_ID + APP_SECRET, APP_SECRET)
3. 请求 GSUC 用户信息
4. 验证 rc == 0
5. 生成 SessionID
6. 重定向到前端
```

---

## 🔧 配置

### 必需参数

```python
APP_ID = "app_meeting_agent"              # GSUC 应用 ID
APP_SECRET = "G22PT4zLJZRgf6WXWF8V5yXr..."  # Base64 编码的 32 字节密钥
GSUC_URL = "https://gsuc.gamesci.com.cn/sso/userinfo"
FRONTEND_URL = "http://localhost:5173"     # 前端回调地址
```

### 修改配置

编辑 `main.py` 文件顶部的配置参数即可。

---

## 📡 API 端点

### 回调接口 (核心)
```
GET /api/v1/auth/callback?code={code}
```

### 加密测试
```
GET /api/v1/auth/test-encrypt?text={text}
```

### 健康检查
```
GET /health
```

---

## 🧪 测试命令

```bash
# 测试 1: 加密算法
python scripts/test_gsuc_sso_complete.py

# 测试 2: 服务端点
python scripts/test_main_sso.py

# 测试 3: 手动测试加密
curl "http://localhost:8000/api/v1/auth/test-encrypt?text=hello"

# 测试 4: 手动测试回调 (需要真实 code)
curl "http://localhost:8000/api/v1/auth/callback?code=YOUR_CODE"
```

---

## 🔍 调试

### 查看日志

服务启动后会打印详细日志:

```
============================================================
收到 GSUC 回调请求
============================================================
Code: abc123xyz...

生成 access_token...
✓ access_token 生成成功

请求 GSUC 用户信息...
✓ GSUC API 响应成功
✓ GSUC 认证成功

✓ 生成 SessionID: session_zhangsan_1003

重定向到前端:
  URL: http://localhost:5173?token=session_zhangsan_1003
============================================================
```

### 常见问题

#### 问题 1: 加密失败
```
错误: 密钥长度为 X 字节，期望 32 字节
```
**解决**: 确保 APP_SECRET 是 Base64 编码的 32 字节密钥

#### 问题 2: GSUC API 请求失败
```
✗ GSUC API 请求失败
```
**解决**: 
- 检查网络连接
- 确认 GSUC_URL 正确
- 验证 code 是否有效

#### 问题 3: 认证失败
```
✗ GSUC 认证失败: rc=1001
```
**解决**:
- code 已过期或已使用
- APP_ID 或 APP_SECRET 不正确

---

## 📚 完整文档

详细文档请查看:
- [完整实现文档](./MAIN_SSO_IMPLEMENTATION.md)
- [实现总结](./summaries/MAIN_SSO_IMPLEMENTATION_COMPLETE.md)

---

## ✅ 验证清单

部署前确认:

- [ ] 依赖已安装
- [ ] 服务可以启动
- [ ] 健康检查通过
- [ ] 加密测试通过
- [ ] APP_ID 和 APP_SECRET 正确
- [ ] 回调地址在 GSUC 白名单中

---

## 🎯 下一步

1. **开发环境**: 使用 `python main.py` 测试
2. **生产环境**: 使用 `uvicorn main:app --host 0.0.0.0 --port 8000`
3. **集成现有系统**: 参考 `src/api/routes/auth.py`
4. **使用 JWT**: 替换 SessionID 为 JWT Token

---

## 💡 提示

- 每次加密结果不同 (因为有随机前缀)
- code 只能使用一次
- 生产环境必须使用 HTTPS
- 建议使用环境变量存储密钥

---

## 🆘 获取帮助

如果遇到问题:

1. 查看服务日志
2. 运行测试脚本
3. 查看完整文档
4. 检查配置参数

---

**就这么简单！5 分钟即可完成 GSUC SSO 集成。** 🎉
