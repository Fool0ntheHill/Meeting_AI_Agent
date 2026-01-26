# GSUC 回调添加 account 字段 - 完成总结

## 📋 任务概述

**需求**: 前端需要在 GSUC 登录回调中获取英文账号 (account) 字段，用于显示用户 ID

**问题**: 
- 之前回调只返回 `username` (中文名 "林晋辉")
- 前端无法获取英文账号 "lorenzolin"
- 导致前端只能显示 `user_id` ("user_gsuc_1231") 作为 ID

## ✅ 实现内容

### 1. 修改回调参数

在两个 GSUC 回调路由中都添加了 `account` 字段：

#### 兼容路由: `/api/v1/auth/callback`

```python
params = {
    "access_token": access_token,
    "user_id": user.user_id,                    # "user_gsuc_1231"
    "tenant_id": user.tenant_id,                # "tenant_gsuc_1231"
    "username": user_info['username'],          # "林晋辉" (中文名)
    "account": user_info['account'],            # "lorenzolin" (英文账号) ✅ 新增
    "avatar": user_info.get('avatar', ''),      # 头像 URL
    "expires_in": str(config.jwt_expire_hours * 3600)
}
```

#### 标准路由: `/api/v1/auth/gsuc/callback`

```python
params = {
    "access_token": access_token,
    "user_id": user.user_id,                    # "user_gsuc_1231"
    "tenant_id": user.tenant_id,                # "tenant_gsuc_1231"
    "username": user_info['username'],          # "林晋辉" (中文名)
    "account": user_info['account'],            # "lorenzolin" (英文账号) ✅ 新增
    "avatar": user_info.get('avatar', ''),      # 头像 URL
    "expires_in": str(config.jwt_expire_hours * 3600)
}
```

### 2. 更新文档

更新了 `docs/GSUC_FIELD_MAPPING.md`，说明：
- 回调参数的完整格式
- 各字段的用途和建议使用方式
- 前端如何使用这些字段

### 3. 创建验证脚本

创建了 `scripts/verify_account_field_in_callback.py`，用于验证代码修改

## 📊 字段映射总结

| 字段 | 值示例 | 来源 | 用途 |
|------|--------|------|------|
| `user_id` | "user_gsuc_1231" | 后端生成 | 稳定的用户主键 ID |
| `tenant_id` | "tenant_gsuc_1231" | 后端生成 | 租户 ID |
| `username` | "林晋辉" | GSUC 返回 | 显示用户名 (中文) |
| `account` | "lorenzolin" | GSUC 返回 | 显示用户 ID (英文) ✅ |
| `avatar` | "https://..." | GSUC 返回 | 用户头像 URL |
| `access_token` | "eyJhbGci..." | 后端生成 | JWT Token |
| `expires_in` | "86400" | 后端生成 | Token 过期时间 (秒) |

## 🌐 前端集成

### 回调 URL 示例

```
http://localhost:5173/login?
  access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...&
  user_id=user_gsuc_1231&
  tenant_id=tenant_gsuc_1231&
  username=林晋辉&
  account=lorenzolin&
  avatar=https://example.com/avatar.jpg&
  expires_in=86400
```

### 前端使用建议

```typescript
// 从 URL 参数读取
const params = new URLSearchParams(window.location.search);

// 存储到 localStorage
localStorage.setItem('access_token', params.get('access_token'));
localStorage.setItem('user_id', params.get('user_id'));
localStorage.setItem('tenant_id', params.get('tenant_id'));
localStorage.setItem('username', params.get('username'));  // "林晋辉"
localStorage.setItem('account', params.get('account'));    // "lorenzolin" ✅
localStorage.setItem('avatar', params.get('avatar'));
localStorage.setItem('token_expiry', Date.now() + parseInt(params.get('expires_in')) * 1000);

// 显示用户信息
const displayName = params.get('username');  // "林晋辉" (显示名称)
const displayId = params.get('account');     // "lorenzolin" (显示 ID) ✅
```

## 🔄 完整流程

```
1. 用户扫码登录
   ↓
2. GSUC 返回用户信息
   {
     "uid": 1231,
     "account": "lorenzolin",      // 英文账号
     "username": "林晋辉"           // 中文名
   }
   ↓
3. 后端创建/查找用户
   user_id: "user_gsuc_1231"
   username: "lorenzolin" (数据库存储)
   ↓
4. 后端重定向到前端
   ?user_id=user_gsuc_1231
   &username=林晋辉
   &account=lorenzolin ✅
   &...
   ↓
5. 前端接收并存储
   localStorage.username = "林晋辉"
   localStorage.account = "lorenzolin" ✅
   ↓
6. 前端显示
   用户名: "林晋辉"
   ID: "lorenzolin" ✅
```

## 📁 修改的文件

1. **src/api/routes/auth.py**
   - 在 `gsuc_callback()` 函数中添加 `account` 字段
   - 在 `gsuc_callback_compat()` 函数中添加 `account` 字段

2. **docs/GSUC_FIELD_MAPPING.md**
   - 更新字段映射说明
   - 添加前端使用建议
   - 更新示例 URL

3. **scripts/verify_account_field_in_callback.py** (新建)
   - 验证代码修改的脚本

4. **docs/summaries/GSUC_ACCOUNT_FIELD_ADDED.md** (本文件)
   - 完成总结文档

## ✅ 验证结果

运行验证脚本:
```bash
python scripts/verify_account_field_in_callback.py
```

结果:
```
✅ 兼容路由 /api/v1/auth/callback - account 字段已添加
✅ 标准路由 /api/v1/auth/gsuc/callback - account 字段已添加
✅ 所有必需字段验证通过
```

## 🎯 总结

✅ **已完成**:
1. 在两个 GSUC 回调路由中添加 `account` 字段
2. 更新文档说明字段用途
3. 创建验证脚本确认修改正确

✅ **前端可以**:
1. 从回调 URL 获取 `account` 参数 ("lorenzolin")
2. 使用 `account` 显示用户 ID
3. 使用 `username` 显示用户名 ("林晋辉")

✅ **不会有重复问题**:
- `user_id` 基于 GSUC uid，全局唯一
- 数据库主键约束保证唯一
- 查找或创建逻辑避免重复

---

**日期**: 2026-01-26  
**状态**: ✅ 完成
