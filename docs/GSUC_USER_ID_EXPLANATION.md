# GSUC 用户 ID 生成逻辑说明

## 📋 核心问题

1. **扫码登录和数据库联系起来了吗？** ✅ 是的
2. **user_id 是企微返回的还是我们自己拼接的？** ⚠️ 是我们拼接的

---

## 🔍 详细说明

### 1. GSUC 返回的用户信息

当用户扫码登录后，GSUC 返回以下信息：

```json
{
  "rc": 0,
  "msg": "success",
  "appid": "app_meeting_agent",
  "uid": 1003,                    // ✅ GSUC 用户 ID (数字)
  "account": "zhangsan",          // ✅ 账号名
  "username": "张三",              // ✅ 用户名
  "avatar": "https://...",        // ✅ 头像 URL
  "thumb_avatar": "https://..."   // ✅ 缩略图头像
}
```

**关键字段:**
- `uid`: GSUC 系统中的用户唯一标识 (数字类型，如 1003)
- `account`: 用户账号 (字符串，如 "zhangsan")
- `username`: 用户显示名称 (字符串，如 "张三")

### 2. 我们的 user_id 生成逻辑

在 `src/api/routes/auth.py` 中：

```python
# 获取 GSUC 用户信息
user_info = await provider.verify_and_get_user(code)
# user_info['uid'] = 1003
# user_info['account'] = "zhangsan"
# user_info['username'] = "张三"

# 生成我们系统的 user_id (拼接)
user_id = f"user_gsuc_{user_info['uid']}"      # ✅ 拼接: "user_gsuc_1003"
tenant_id = f"tenant_gsuc_{user_info['uid']}"  # ✅ 拼接: "tenant_gsuc_1003"
```

**为什么要拼接？**

1. **区分登录方式**
   - GSUC 登录: `user_gsuc_1003`
   - 开发登录: `user_test_user`
   - 未来可能的其他登录方式: `user_wechat_xxx`, `user_dingtalk_xxx`

2. **保证唯一性**
   - GSUC 的 uid 是数字 (1003)
   - 我们的 user_id 是字符串 (`user_gsuc_1003`)
   - 避免与其他登录方式的 ID 冲突

3. **便于识别**
   - 从 user_id 就能看出是哪种登录方式
   - 便于日志追踪和问题排查

### 3. 数据库存储

用户信息会存储到 `users` 表：

```sql
CREATE TABLE users (
    user_id VARCHAR(64) PRIMARY KEY,      -- "user_gsuc_1003"
    username VARCHAR(128) NOT NULL,       -- "zhangsan"
    tenant_id VARCHAR(64) NOT NULL,       -- "tenant_gsuc_1003"
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    updated_at DATETIME,
    last_login_at DATETIME
);
```

**实际存储的数据:**

| user_id | username | tenant_id | is_active |
|---------|----------|-----------|-----------|
| user_gsuc_1003 | zhangsan | tenant_gsuc_1003 | true |

### 4. 完整流程

```
1. 用户扫码登录
   ↓
2. GSUC 返回用户信息
   {
     "uid": 1003,
     "account": "zhangsan",
     "username": "张三"
   }
   ↓
3. 后端拼接 user_id
   user_id = "user_gsuc_1003"
   tenant_id = "tenant_gsuc_1003"
   ↓
4. 查找数据库
   SELECT * FROM users WHERE user_id = 'user_gsuc_1003'
   ↓
5a. 如果用户存在
    - 更新 last_login_at
    - 签发 JWT Token
   ↓
5b. 如果用户不存在
    - 创建新用户记录
    INSERT INTO users (user_id, username, tenant_id, is_active)
    VALUES ('user_gsuc_1003', 'zhangsan', 'tenant_gsuc_1003', true)
    - 签发 JWT Token
   ↓
6. 返回 JWT Token 给前端
   {
     "access_token": "eyJ...",
     "user_id": "user_gsuc_1003",
     "tenant_id": "tenant_gsuc_1003",
     "username": "张三"
   }
```

---

## 🔗 数据库关系

### 1. 用户表 (users)

```python
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(64), primary_key=True)      # "user_gsuc_1003"
    username = Column(String(128), nullable=False)      # "zhangsan"
    tenant_id = Column(String(64), nullable=False)      # "tenant_gsuc_1003"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    last_login_at = Column(DateTime, nullable=True)
```

### 2. 任务表 (tasks)

任务通过 `user_id` 关联到用户：

```python
class Task(Base):
    __tablename__ = "tasks"
    
    task_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False)        # "user_gsuc_1003"
    tenant_id = Column(String(64), nullable=False)      # "tenant_gsuc_1003"
    # ... 其他字段
```

**查询示例:**

```python
# 查询某个用户的所有任务
tasks = db.query(Task).filter(Task.user_id == "user_gsuc_1003").all()

# 查询某个租户的所有任务
tasks = db.query(Task).filter(Task.tenant_id == "tenant_gsuc_1003").all()
```

### 3. 文件夹表 (folders)

```python
class Folder(Base):
    __tablename__ = "folders"
    
    folder_id = Column(String(64), primary_key=True)
    owner_user_id = Column(String(64), nullable=False)  # "user_gsuc_1003"
    owner_tenant_id = Column(String(64), nullable=False) # "tenant_gsuc_1003"
    # ... 其他字段
```

---

## 🆚 不同登录方式的 user_id 对比

| 登录方式 | GSUC uid | 我们的 user_id | tenant_id |
|---------|----------|---------------|-----------|
| **GSUC 登录** | 1003 | `user_gsuc_1003` | `tenant_gsuc_1003` |
| **开发登录** | - | `user_test_user` | `tenant_test_user` |
| **未来: 微信** | wx_12345 | `user_wechat_wx_12345` | `tenant_wechat_wx_12345` |
| **未来: 钉钉** | dd_67890 | `user_dingtalk_dd_67890` | `tenant_dingtalk_dd_67890` |

---

## ❓ 常见问题

### Q1: 为什么不直接用 GSUC 的 uid 作为 user_id？

**A:** 有几个原因：

1. **类型不匹配**: GSUC uid 是数字 (1003)，我们的 user_id 是字符串
2. **冲突风险**: 如果有多种登录方式，不同系统的 ID 可能重复
3. **可读性**: `user_gsuc_1003` 比 `1003` 更容易识别来源

### Q2: 如果同一个人用不同方式登录，会创建多个账号吗？

**A:** 是的，当前实现会创建不同的账号：

- GSUC 登录: `user_gsuc_1003`
- 开发登录: `user_test_user`

**未来改进方案:**
- 添加用户绑定功能
- 通过手机号或邮箱关联不同登录方式
- 实现账号合并功能

### Q3: tenant_id 有什么用？

**A:** tenant_id 用于多租户隔离：

1. **数据隔离**: 不同租户的数据互不可见
2. **权限控制**: 用户只能访问自己租户的数据
3. **未来扩展**: 支持企业级多租户部署

**当前实现:**
- 每个用户都有独立的 tenant_id
- 未来可以支持多个用户共享同一个 tenant_id (企业账号)

### Q4: 如何查询某个 GSUC 用户的所有数据？

**A:** 使用拼接后的 user_id：

```python
# 已知 GSUC uid = 1003
user_id = f"user_gsuc_1003"

# 查询用户信息
user = db.query(User).filter(User.user_id == user_id).first()

# 查询用户的所有任务
tasks = db.query(Task).filter(Task.user_id == user_id).all()

# 查询用户的所有文件夹
folders = db.query(Folder).filter(Folder.owner_user_id == user_id).all()
```

### Q5: 如何从 user_id 反推 GSUC uid？

**A:** 解析字符串：

```python
user_id = "user_gsuc_1003"

# 方法 1: 字符串分割
if user_id.startswith("user_gsuc_"):
    gsuc_uid = user_id.replace("user_gsuc_", "")  # "1003"
    gsuc_uid_int = int(gsuc_uid)  # 1003

# 方法 2: 正则表达式
import re
match = re.match(r"user_gsuc_(\d+)", user_id)
if match:
    gsuc_uid = match.group(1)  # "1003"
    gsuc_uid_int = int(gsuc_uid)  # 1003
```

---

## 🔄 JWT Token 内容

签发的 JWT Token 包含以下信息：

```json
{
  "sub": "user_gsuc_1003",           // user_id
  "tenant_id": "tenant_gsuc_1003",   // tenant_id
  "exp": 1706342400,                 // 过期时间
  "iat": 1706256000                  // 签发时间
}
```

**前端使用:**

```javascript
// 解析 JWT Token (不验证签名)
function parseJwt(token) {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(
    atob(base64).split('').map(c => 
      '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    ).join('')
  );
  return JSON.parse(jsonPayload);
}

const token = localStorage.getItem('access_token');
const payload = parseJwt(token);
console.log(payload.sub);        // "user_gsuc_1003"
console.log(payload.tenant_id);  // "tenant_gsuc_1003"
```

---

## 📊 数据库示例

### 用户表数据

| user_id | username | tenant_id | is_active | created_at |
|---------|----------|-----------|-----------|------------|
| user_gsuc_1003 | zhangsan | tenant_gsuc_1003 | true | 2026-01-26 10:00:00 |
| user_gsuc_1004 | lisi | tenant_gsuc_1004 | true | 2026-01-26 11:00:00 |
| user_test_user | test_user | tenant_test_user | true | 2026-01-20 09:00:00 |

### 任务表数据

| task_id | user_id | tenant_id | name | status |
|---------|---------|-----------|------|--------|
| task_abc123 | user_gsuc_1003 | tenant_gsuc_1003 | 会议纪要 | SUCCESS |
| task_def456 | user_gsuc_1003 | tenant_gsuc_1003 | 项目讨论 | PROCESSING |
| task_ghi789 | user_test_user | tenant_test_user | 测试任务 | SUCCESS |

---

## 🎯 总结

### 当前实现

1. ✅ **已联系数据库**: 用户信息存储在 `users` 表
2. ✅ **user_id 是拼接的**: `user_gsuc_{gsuc_uid}`
3. ✅ **自动创建用户**: 首次登录自动创建数据库记录
4. ✅ **数据隔离**: 通过 user_id 和 tenant_id 实现

### 优点

- ✅ 支持多种登录方式
- ✅ 避免 ID 冲突
- ✅ 便于识别和追踪
- ✅ 数据隔离清晰

### 缺点

- ⚠️ 同一个人不同登录方式会创建多个账号
- ⚠️ 需要额外的账号绑定功能
- ⚠️ user_id 较长 (但可读性好)

### 未来改进

1. **账号绑定**: 支持多种登录方式绑定到同一账号
2. **统一 ID**: 引入全局唯一的 `global_user_id`
3. **用户合并**: 支持合并重复账号
4. **企业租户**: 支持多用户共享 tenant_id

---

## 📚 相关代码

- **用户模型**: `src/database/models.py` (User 类)
- **认证路由**: `src/api/routes/auth.py` (gsuc_callback 函数)
- **GSUC 提供商**: `src/providers/gsuc_auth.py`
- **用户仓库**: `src/database/repositories.py` (UserRepository 类)

---

需要修改 user_id 生成逻辑吗？或者有其他问题？
