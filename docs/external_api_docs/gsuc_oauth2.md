# GSUC OAuth2.0 单点登录 API 文档

## 简介

本文档介绍 GSUC (企业用户中心) OAuth2.0 单点登录的认证流程和 API 接口。

## 认证流程

### 流程图

```
用户 → 第三方应用 → GSUC 用户中心 → 企业微信 → GSUC → 第三方应用
```

### 详细步骤

1. **用户访问第三方应用**
   - 第三方应用检测到用户未登录
   - 携带参数跳转到 GSUC 用户中心

2. **GSUC 用户中心处理**
   - 如果用户已登录 GSUC，直接跳过扫码步骤
   - 如果未登录，显示企业微信扫码页面

3. **企业微信扫码**
   - 用户使用企业微信扫描二维码
   - 确认登录

4. **GSUC 获取用户信息**
   - GSUC 使用 corpid, corpsecret 向企业微信请求 access_token
   - 使用 access_token 和 code 获取用户 userid

5. **重定向到第三方应用**
   - GSUC 生成 code 并拼接到 redirect_uri
   - 用户跳转到第三方应用

6. **第三方应用获取用户信息**
   - 使用 code + appid + appsecret 生成 access_token
   - 调用 GSUC API 获取用户信息
   - 完成登录

## API 接口

### 1. 登录认证

第三方应用检测到未登录后，携带参数让用户跳转到用户中心地址。

**接口地址**

```
GET https://gsuc.gamesci.com.cn/sso/login
```

**请求参数**

| 参数 | 必须 | 说明 |
|------|------|------|
| appid | 是 | 第三方应用 ID，需让运维开通。每个不同的应用都有不同的 ID，如 omp id 为 gs10001，opsite id 为 gs10002 |
| redirect_uri | 是 | 完成认证后重定向的地址，需要进行 urlEncode，如 `http://omp.gs.com:8080/login?test=aaa` (将其使用 urlencode 转义) |
| state | 否 | 说明，接口会将该参数原样返回，用于防止 csrf 攻击（跨站请求伪造攻击） |

**返回参数**

返回时会将下面参数加到 redirect_uri 后，让用户跳转到 redirect_uri

| 参数 | 类型 | 说明 |
|------|------|------|
| code | str | 授权 code，用于获取用户信息，只能使用一次，5分钟未被使用自动过期 |
| state | str | 第三方应用带过来的 state 参数，原样返回 |

**请求样例**

```
https://gsuc.gamesci.com.cn/sso/login?appid=gs10001&redirect_uri=http%3A%2F%2Fomp.gs.com%3A8080%2Flogin%3Ftest%3Daaa&state=ompRamdomAuth
```

### 2. 获取用户信息

第三方 redirect_uri 接口拿到 code 以后，使用下面接口获取用户信息。

**注意：该步骤需在第三方应用服务器端去请求**

**接口地址**

```
GET https://gsuc.gamesci.com.cn/sso/userinfo
```

**请求参数**

| 参数 | 必须 | 说明 |
|------|------|------|
| code | 是 | 上一步获取到的 code，用于获取用户信息 |
| access_token | 是 | 加密认证串，生成方式是将 code, appid, appsecret 字符串拼接起来后，用 encrypt() 函数加密后得到，其中 appid, appsecret 需找运维提供 |

**返回参数**

如果拿到 rc 为 0 时，则表示该用户认证是合法的，可以让用户登录。

| 参数 | 类型 | 说明 |
|------|------|------|
| rc | int | 返回值，如果为 0 表示获取用户信息成功，非 0 则失败 |
| msg | str | 如果 rc 为非 0，该字段会有详细错误说明 |
| appid | str | 应用 id |
| uid | int | 用户的唯一 id，如 1003 |
| account | str | 用户登录名，如 zhangsan |
| username | str | 用户中文名，如 张三 |
| avatar | str | 企业微信头像 url |
| thumb_avatar | str | 企业微信头像缩略图 url |

**请求样例**

```
https://gsuc.gamesci.com.cn/sso/userinfo?code=GY3DMNBUME3DSLJYMRRTMLJUMM4WELJZGACWELKDGVSTMMUDGI2DQMBWHA&access_token=NnRAF2yg3s7ZwV52RvJVJlCLFUMD42w3Zpb3yG7BcWOEp8ksH8n%2FlljF2b4JYKWTf%2B5L3sJSymj8FXoP%2FcB8fGpgdg%2Bu5yrl1QostslKN1m6cgNEPSvWxCvV7WU0bmvkIc7BNBMDeSpoI8CKGEc%2BQxpwtkt32AKdSFqdonWolv8%3D
```

## access_token 生成方法

access_token 的生成需要使用 encrypt() 函数对 `code + appid + appsecret` 字符串进行加密。

**Python 示例**

```python
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

def encrypt(text: str, key: str = "your-encryption-key") -> str:
    """
    加密函数
    
    Args:
        text: 要加密的文本 (code + appid + appsecret)
        key: 加密密钥 (需要向运维获取)
        
    Returns:
        str: Base64 编码的加密结果
    """
    # 使用 AES-256-CBC 加密
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC)
    encrypted = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
    return base64.b64encode(encrypted).decode('utf-8')
```

**注意事项**

1. 加密密钥需要向运维获取
2. 加密算法可能因实际情况而异，需要与 GSUC 团队确认
3. access_token 需要进行 URL 编码后再传递

## 集成清单

### 需要向运维申请的信息

- [ ] appid (应用 ID)
- [ ] appsecret (应用密钥)
- [ ] 加密密钥 (用于生成 access_token)
- [ ] redirect_uri 白名单 (需要将回调地址加入白名单)

### 需要配置的信息

- [ ] GSUC 登录页面 URL
- [ ] GSUC 用户信息 API URL
- [ ] 加密算法和密钥
- [ ] 前端回调地址

## 安全注意事项

1. **appsecret 保密**：appsecret 必须保存在服务器端，不能暴露给前端
2. **state 参数**：使用 state 参数防止 CSRF 攻击，建议使用随机字符串
3. **code 有效期**：code 只能使用一次，5分钟内有效
4. **HTTPS**：生产环境必须使用 HTTPS
5. **redirect_uri 验证**：确保 redirect_uri 在白名单内

## 错误处理

### 常见错误码

| rc | 说明 | 处理方式 |
|----|------|----------|
| 0 | 成功 | 正常处理 |
| 1001 | code 无效或已过期 | 重新发起登录流程 |
| 1002 | access_token 无效 | 检查加密算法和密钥 |
| 1003 | appid 无效 | 检查 appid 配置 |
| 1004 | 用户不存在 | 提示用户联系管理员 |

## 测试流程

1. **开发环境测试**
   - 配置测试 appid 和 appsecret
   - 使用测试账号扫码登录
   - 验证用户信息获取

2. **集成测试**
   - 测试完整登录流程
   - 测试 state 参数防 CSRF
   - 测试 code 过期处理
   - 测试错误场景

3. **生产环境部署**
   - 使用生产 appid 和 appsecret
   - 配置生产 redirect_uri
   - 启用 HTTPS
   - 监控登录成功率

## 参考资料

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [企业微信开发文档](https://work.weixin.qq.com/api/doc)
