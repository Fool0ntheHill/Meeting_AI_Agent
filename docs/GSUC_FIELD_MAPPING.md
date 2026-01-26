# GSUC 字段映射说明

## 🔍 问题分析

### 问题 1: 会有重复问题吗？

**答案: ✅ 不会有重复问题**

### 问题 2: 前端显示的中文名是哪个字段？

**答案: `username` 字段 (GSUC 返回的 `username`，不是 `account`)**

---

## 📊 GSUC 返回的字段

当用户扫码登录后，GSUC 返回以下信息：

```json
{
  "rc": 0,
  "msg": "success",
  "appid": "app_meeting_agent",
  "uid": 1231,                    // ✅ 用户唯一 ID (数字)
  "account": "lorenzolin",        // ✅ 账号名 (英文)
  "username": "林晋辉",            // ✅ 用户显示名称 (中文)
  "avatar": "https://...",        // ✅ 头像 URL
  "thumb_avatar": "https://..."   // ✅ 缩略图头像
}
```

**关键区别:**
- `account`: 账号名，通常是英文 (如 "lorenzolin")
- `username`: 显示名称，通常是中文真实姓名 (如 "林晋辉")

---

## 🗄️ 数据库存储

### User 表字段

```python
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(64), primary_key=True)      # "user_gsuc_1231"
    username = Column(String(128), nullable=False)      # "lorenzolin" ⚠️ 存的是 account
    tenant_id = Column(String(64), nullable=False)      # "tenant_gsuc_1231"
    is_active = Column(Boolean, default=True)
    # ...
```

**当前实现:**

```python
# 创建用户时
user = user_repo.create(
    user_id=f"user_gsuc_{user_info['uid']}",     # "user_gsuc_1231"
    username=user_info['account'],                # ⚠️ "lorenzolin" (英文账号)
    tenant_id=f"tenant_gsuc_{user_info['uid']}",  # "tenant_gsuc_1231"
    is_active=True
)
```

**问题:** 数据库的 `username` 字段存储的是 `account` (英文)，不是 `username` (中文)

---

## 🌐 前端接收的数据

### 回调重定向时传递的参数

```python
params = {
    "access_token": access_token,
    "user_id": user.user_id,                    # "user_gsuc_1231"
    "tenant_id": user.tenant_id,                # "tenant_gsuc_1231"
    "username": user_info['username'],          # ✅ "林晋辉" (中文)
    "account": user_info['account'],            # ✅ "lorenzolin" (英文账号)
    "avatar": user_info.get('avatar', ''),      # 头像 URL
    "expires_in": str(config.jwt_expire_hours * 3600)
}

redirect_url = f"{frontend_url}?{urlencode(params)}"
# http://localhost:5173/login?access_token=xxx&user_id=user_gsuc_1231&username=林晋辉&account=lorenzolin&...
```

**前端接收到的字段:**
- `username`: 中文名 "林晋辉" (用于显示用户名)
- `account`: 英文账号 "lorenzolin" (用于显示 ID)

---

## 🔄 完整的字段流转

```
1. GSUC 返回
   {
     "uid": 1231,
     "account": "lorenzolin",      // 英文账号
     "username": "林晋辉"           // 中文名
   }
   ↓
2. 数据库存储 (User 表)
   user_id: "user_gsuc_1231"
   username: "lorenzolin"          // ⚠️ 存的是 account (英文)
   ↓
3. 重定向到前端
   ?user_id=user_gsuc_1231         // ✅ 稳定的主键 ID
   &username=林晋辉                // ✅ 中文名 (用于显示)
   &account=lorenzolin             // ✅ 英文账号 (用于显示 ID)
   ↓
4. 前端显示
   用户名: "林晋辉"                // ✅ 显示中文名
   ID: "lorenzolin"                // ✅ 显示英文账号
```

---

## ❓ 为什么不会有重复问题？

### 1. user_id 的唯一性保证

```python
# user_id 由 GSUC uid 拼接而成
user_id = f"user_gsuc_{user_info['uid']}"  # "user_gsuc_1231"
```

**GSUC uid 的特点:**
- ✅ 全局唯一 (GSUC 系统保证)
- ✅ 永久不变 (不会因为改名而变化)
- ✅ 数字类型 (1231, 1232, ...)

**我们的 user_id:**
- ✅ 基于 GSUC uid，继承其唯一性
- ✅ 添加前缀 `user_gsuc_` 避免与其他登录方式冲突
- ✅ 数据库主键约束保证唯一

### 2. 数据库约束

```python
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(64), primary_key=True, index=True)  # ✅ 主键，唯一
    username = Column(String(128), nullable=False, unique=True, index=True)  # ✅ 唯一约束
```

**双重保证:**
1. `user_id` 是主键，数据库保证唯一
2. `username` 有唯一约束，也保证唯一

### 3. 查找或创建逻辑

```python
# 先查找
user = user_repo.get_by_id(user_id)

if not user:
    # 不存在才创建
    user = user_repo.create(
        user_id=user_id,
        username=user_info['account'],
        tenant_id=tenant_id,
        is_active=True
    )
```

**流程:**
1. 第一次登录: 创建新用户
2. 第二次登录: 找到已存在的用户，不会重复创建

### 4. 实际测试验证

从数据库查询结果看：

```
User ID: user_gsuc_1231
  Username: lorenzolin
  Tenant ID: tenant_gsuc_1231
  Login Type: GSUC (uid=1231)
```

**结论:**
- ✅ 只有一条记录
- ✅ 多次登录不会创建重复记录
- ✅ user_id 唯一

---

## ⚠️ 潜在问题

### 问题 1: 数据库 username 字段存储不一致

**当前情况:**
- 数据库 `username` 字段: "lorenzolin" (英文 account)
- 前端显示: "林晋辉" (中文 username)
- 前端每次都从 URL 参数读取，不从数据库读取

**潜在风险:**
1. 如果前端从数据库读取 username，会显示英文账号
2. 数据库中没有存储中文名，无法通过中文名搜索用户

### 问题 2: 用户改名后的处理

**场景:** 用户在 GSUC 系统中改名

```
第一次登录:
  uid: 1231
  account: "lorenzolin"
  username: "林晋辉"

改名后登录:
  uid: 1231  (不变)
  account: "lorenzolin"  (不变)
  username: "林煜东"  (改了)
```

**当前实现:**
- 数据库 username 不会更新 (仍然是 "lorenzolin")
- 前端每次都从 URL 参数读取最新的中文名
- ✅ 前端显示会自动更新
- ⚠️ 数据库中的名字不会更新

---

## 🔧 改进建议

### 建议 1: 数据库增加 display_name 字段

```python
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(64), primary_key=True)
    username = Column(String(128), nullable=False, unique=True)  # 英文账号 (不变)
    display_name = Column(String(128), nullable=True)            # ✅ 中文名 (可更新)
    tenant_id = Column(String(64), nullable=False)
    # ...
```

**修改创建逻辑:**

```python
user = user_repo.create(
    user_id=f"user_gsuc_{user_info['uid']}",
    username=user_info['account'],          # 英文账号
    display_name=user_info['username'],     # ✅ 中文名
    tenant_id=f"tenant_gsuc_{user_info['uid']}",
    is_active=True
)
```

**修改更新逻辑:**

```python
user = user_repo.get_by_id(user_id)

if user:
    # 更新中文名 (如果改了)
    if user.display_name != user_info['username']:
        user.display_name = user_info['username']
        db.commit()
```

### 建议 2: 传递给前端时使用 display_name

```python
params = {
    "access_token": access_token,
    "user_id": user.user_id,
    "tenant_id": user.tenant_id,
    "username": user.display_name or user.username,  # ✅ 优先使用中文名
    "account": user.username,                        # ✅ 英文账号
    "avatar": user_info.get('avatar', ''),
    "expires_in": str(config.jwt_expire_hours * 3600)
}
```

---

## 📋 当前字段映射总结

| 来源 | 字段名 | 值 | 说明 |
|------|--------|-----|------|
| **GSUC 返回** | `uid` | 1231 | 用户唯一 ID |
| **GSUC 返回** | `account` | "lorenzolin" | 英文账号 |
| **GSUC 返回** | `username` | "林晋辉" | 中文名 |
| **数据库存储** | `user_id` | "user_gsuc_1231" | 我们的用户 ID |
| **数据库存储** | `username` | "lorenzolin" | ⚠️ 存的是 account |
| **前端接收** | `user_id` | "user_gsuc_1231" | ✅ 稳定的主键 ID |
| **前端接收** | `username` | "林晋辉" | ✅ 中文名 (用于显示) |
| **前端接收** | `account` | "lorenzolin" | ✅ 英文账号 (用于显示 ID) |
| **前端显示** | 用户名 | "林晋辉" | ✅ 显示中文名 |
| **前端显示** | ID | "lorenzolin" | ✅ 显示英文账号 |

---

## 🎯 总结

### 重复问题

✅ **不会有重复问题**
- user_id 基于 GSUC uid，全局唯一
- 数据库主键约束保证唯一
- 查找或创建逻辑避免重复

### 前端接收的字段 (已更新)

✅ **回调参数包含完整信息**
- `user_id`: "user_gsuc_1231" (稳定的主键 ID)
- `username`: "林晋辉" (中文名，用于显示用户名)
- `account`: "lorenzolin" (英文账号，用于显示 ID)
- `avatar`: 头像 URL
- `access_token`: JWT Token
- `tenant_id`: 租户 ID
- `expires_in`: Token 过期时间

### 前端使用建议

1. **显示用户名**: 使用 `username` 字段 ("林晋辉")
2. **显示 ID**: 使用 `account` 字段 ("lorenzolin")
3. **用户标识**: 使用 `user_id` 字段 ("user_gsuc_1231")

### 示例重定向 URL

```
http://localhost:5173/login?
  access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...&
  user_id=user_gsuc_1231&
  tenant_id=tenant_gsuc_1231&
  username=林晋辉&
  account=lorenzolin&
  avatar=https://...&
  expires_in=86400
```

---

✅ 后端已更新，前端现在可以拿到 `account` 字段了！
