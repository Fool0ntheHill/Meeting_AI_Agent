# GSUC Session 认证实现总结

## 任务概述

实现 GSUC 基于 Session 的认证方案，支持企业微信扫码登录。

## 关键澄清

### 之前的误解

1. **误解**: `convertKeysToCamelCase` 和 `convertKeysToSnakeCase` 用于生成 SESSIONID
2. **误解**: 后端从 Cookie 中提取 SESSIONID
3. **误解**: 使用 Authorization header 传递 SESSIONID

### 正确理解

1. **SESSIONID 由 GSUC 服务器生成**，不是我们自己生成的
2. **数据格式转换工具**用于在前端 camelCase 和后端 snake_case 之间转换，与 SESSIONID 无关
3. **前端从 Cookie 读取 SESSIONID**，然后放入 `Token` header（不是 `Authorization` header）
4. **后端从 `Token` header 提取 SESSIONID** 进行验证

## 认证流程

```
1. 用户访问 GSUC 登录页面
   https://gsuc.gamesci.com.cn/sso/login?time=xxx&redirect_uri=xxx
   ↓
2. 用户扫码登录
   ↓
3. GSUC 设置 SESSIONID Cookie
   Set-Cookie: SESSIONID=OP0s4dCO5Cln6-BRRXl9PshQnIx29NZE...
   ↓
4. GSUC 重定向到 redirect_uri
   ↓
5. 前端从 Cookie 读取 SESSIONID
   const sessionId = getCookie('SESSIONID')
   ↓
6. 前端将 SESSIONID 放入 Token header 发送请求
   headers: { Token: sessionId }
   ↓
7. 后端从 Token header 提取 SESSIONID
   token = request.headers.get('Token')
   ↓
8. 后端验证 SESSIONID（调用 GSUC API 或查询 Redis 缓存）
   ↓
9. 后端返回数据
```

## 实现内容

### 1. 数据格式转换工具

**文件**: `src/utils/case_converter.py`

**功能**:
- `to_camel_case()`: snake_case → camelCase
- `to_snake_case()`: camelCase → snake_case
- `convert_keys_to_camel_case()`: 递归转换对象键（后端 → 前端）
- `convert_keys_to_snake_case()`: 递归转换对象键（前端 → 后端）

**测试结果**: ✓ 所有测试通过

### 2. GSUC Session 管理器

**文件**: `src/providers/gsuc_session.py`

**功能**:
- 验证 SESSIONID 有效性
- 调用 GSUC API 获取用户信息
- 使用 Redis 缓存减少 API 调用（可选）
- 支持缓存失效

**关键方法**:
```python
async def verify_session(session_id: str) -> Optional[Dict]:
    """
    验证 SESSIONID 并获取用户信息
    
    流程:
    1. 先从 Redis 缓存中查找
    2. 如果缓存未命中，调用 GSUC API 验证
    3. 将用户信息缓存到 Redis
    
    Returns:
        {
            "user_id": "user_gsuc_1003",
            "tenant_id": "tenant_gsuc_1003",
            "username": "张三",
            "account": "zhangsan",
            "uid": "1003"
        }
    """
```

**注意**: 当前 GSUC API 端点为示例，需要向 GSUC 团队确认实际接口

### 3. API 依赖更新

**文件**: `src/api/dependencies.py`

**新增函数**:
```python
async def verify_gsuc_session(
    token: str = Header(None, alias="Token"),  # 从 Token header 提取
    db: Session = Depends(get_db)
) -> Tuple[str, str]:
    """
    验证 GSUC SESSIONID
    
    注意:
    - 从 Token header 提取 SESSIONID（不是 Authorization header）
    - 前端需要从 Cookie 读取 SESSIONID 并放入 Token header
    """
```

**保留函数**:
- `verify_jwt_token()`: 开发环境使用（JWT Token）
- `get_current_user_id()`: 获取当前用户 ID
- `get_current_tenant_id()`: 获取当前租户 ID

### 4. 文档

**已创建**:
1. `docs/GSUC_SESSION_BASED_AUTH_GUIDE.md` - 后端实现指南
2. `docs/GSUC_FRONTEND_INTEGRATION.md` - 前端集成指南
3. `docs/summaries/GSUC_SESSION_IMPLEMENTATION.md` - 实现总结（本文档）

**已更新**:
- `docs/GSUC_INTEGRATION_GUIDE.md` - 更新为正确的理解

### 5. 测试脚本

**文件**: `scripts/test_gsuc_session.py`

**测试内容**:
1. 数据格式转换工具 - ✓ 通过
2. GSUC Session 管理器 - ✓ 通过（Mock）
3. API 依赖导入 - ✓ 通过

## 前端集成要点

### 1. 从 Cookie 读取 SESSIONID

```typescript
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}

const sessionId = getCookie('SESSIONID');
```

### 2. 放入 Token header

```typescript
// 注意：是 Token header，不是 Authorization header
apiClient.interceptors.request.use((config) => {
  const sessionId = getCookie('SESSIONID');
  if (sessionId) {
    config.headers['Token'] = sessionId;  // 不是 Authorization
  }
  return config;
});
```

### 3. 数据格式转换

```typescript
// 请求拦截器：camelCase → snake_case
config.data = convertKeysToSnakeCase(config.data);

// 响应拦截器：snake_case → camelCase
response.data = convertKeysToCamelCase(response.data);
```

### 4. 错误处理

```typescript
// 401 错误：Session 过期
if (error.response?.status === 401) {
  deleteCookie('SESSIONID');
  window.location.href = '/login';
}
```

## 下一步工作

### 1. 向 GSUC 团队确认

- [ ] Session 验证 API 端点
- [ ] Session 过期时间
- [ ] 用户信息获取方式
- [ ] 退出登录流程

### 2. 后端配置

- [ ] 配置 Redis 连接
- [ ] 实现真实的 GSUC API 调用
- [ ] 测试 Session 验证流程
- [ ] 配置 CORS 和 Cookie 安全设置

### 3. 前端实现

- [ ] 实现 Cookie 读取工具
- [ ] 实现 Token header 传递
- [ ] 实现数据格式转换拦截器
- [ ] 实现登录页面
- [ ] 实现回调页面
- [ ] 测试完整登录流程

### 4. 测试验证

- [ ] 登录流程测试
- [ ] Session 验证测试
- [ ] 缓存功能测试
- [ ] 退出登录测试
- [ ] 多用户隔离测试

## 技术细节

### 参考代码分析

从 `AI参考文件夹/参考.txt` 中的关键代码：

```typescript
// 1. 获取 SESSIONID
getAuthToken: () => {
  return ''  // 实际应该从 Cookie 读取
}

// 2. 将 SESSIONID 放入 Token header
if (tmpOpt.withToken) {
  header2 = Object.assign({ Token: token }, opts?.headers)
  // 注意：是 Token header，不是 Authorization header
}

// 3. 数据格式转换（与 SESSIONID 无关）
if (opts.withProto) {
  const tmpRetData = utils.convertKeysToCamelCase(response.data)
  opts?.onSuccess?.(tmpRetData)
}

httpInst.do(
  `/${tmpGroup}/` + tmpApiName,
  utils.convertKeysToSnakeCase(reqFormData),
  tmpOpt
)
```

### 关键区别

| 特性 | 误解 | 正确理解 |
|------|------|----------|
| SESSIONID 生成 | 我们用 utils 函数生成 | GSUC 服务器生成 |
| utils 函数作用 | 生成 SESSIONID | 数据格式转换 |
| SESSIONID 传递 | Cookie Header (自动) | Token Header (手动) |
| 后端提取方式 | 从 Cookie 提取 | 从 Token header 提取 |

## 文件清单

### 新增文件

1. `src/utils/case_converter.py` - 数据格式转换工具
2. `src/providers/gsuc_session.py` - GSUC Session 管理器
3. `docs/GSUC_FRONTEND_INTEGRATION.md` - 前端集成指南
4. `scripts/test_gsuc_session.py` - 测试脚本
5. `docs/summaries/GSUC_SESSION_IMPLEMENTATION.md` - 实现总结

### 修改文件

1. `src/api/dependencies.py` - 添加 `verify_gsuc_session()`
2. `docs/GSUC_SESSION_BASED_AUTH_GUIDE.md` - 更新为正确理解

## 总结

1. ✅ 澄清了 SESSIONID 生成和传递方式
2. ✅ 实现了数据格式转换工具
3. ✅ 实现了 GSUC Session 管理器
4. ✅ 更新了 API 依赖
5. ✅ 创建了完整的文档
6. ✅ 创建了测试脚本

**核心要点**:
- SESSIONID 由 GSUC 生成，不是我们生成
- 前端从 Cookie 读取后放入 Token header
- 后端从 Token header 提取并验证
- 数据格式转换工具用于 camelCase ↔ snake_case

**待完成**:
- 向 GSUC 团队确认 API 接口
- 配置 Redis 缓存
- 前端实现 Token header 传递
- 测试完整登录流程
