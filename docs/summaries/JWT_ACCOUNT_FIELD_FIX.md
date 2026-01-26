# JWT Account Field Fix - 修复完成

## 问题描述

用户在尝试登录时遇到错误：
```
NameError: name 'account' is not defined
```

错误发生在 `src/api/routes/auth.py` 的 `create_access_token` 函数中。

## 根本原因

之前的代码尝试在 JWT payload 中添加 `account` 字段，但是：
1. `create_access_token` 函数签名中没有 `account` 参数
2. 调用该函数时也没有传递 `account` 参数
3. 根据之前的决策，JWT payload 不需要存储 `account` 字段（应该从数据库 User 表获取）

## 修复方案

**已完成**: JWT payload 已经是正确的，不包含 `account` 字段：

```python
payload = {
    "sub": user_id,  # Subject (用户 ID)
    "tenant_id": tenant_id,
    "exp": expire,  # Expiration time
    "iat": datetime.now(),  # Issued at
}
```

## 需要的操作

**重启后端服务器**以加载修复后的代码：

### 方法 1: 使用 PowerShell 脚本
```powershell
# 停止所有服务
.\scripts\stop_all.ps1

# 启动后端
.\scripts\start_backend.ps1
```

### 方法 2: 手动重启
```bash
# 停止当前运行的后端进程 (Ctrl+C)

# 重新启动
python main.py
```

## 验证步骤

重启后端后，测试登录功能：

```bash
# 测试开发环境登录
python scripts/test_login.py

# 或者通过 API 测试
curl -X POST http://localhost:8000/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}'
```

## 相关文件

- `src/api/routes/auth.py` - JWT 创建函数（已修复）
- `docs/GSUC_FIELD_MAPPING.md` - GSUC 字段映射说明
- `docs/summaries/GSUC_ACCOUNT_FIELD_ADDED.md` - GSUC 回调添加 account 字段

## 技术说明

### JWT Payload 设计

JWT Token 中只存储必要的身份信息：
- `sub`: 用户 ID (user_id)
- `tenant_id`: 租户 ID
- `exp`: 过期时间
- `iat`: 签发时间

### 获取用户详细信息

当需要用户的 `account`（企微英文账号）时：
1. 从 JWT 中提取 `user_id`
2. 查询数据库 User 表获取 `username` 字段（即 account）
3. 例如在企微通知中：`task.user_id` → 查询 User 表 → `user.username`

### GSUC 回调参数

GSUC 回调 URL 中包含的参数（用于前端）：
- `access_token`: JWT Token
- `user_id`: 用户 ID
- `tenant_id`: 租户 ID
- `username`: 中文名（用于前端显示）
- `account`: 英文账号（用于前端显示用户 ID）
- `avatar`: 头像 URL
- `expires_in`: Token 过期时间（秒）

## 状态

✅ **已修复** - 代码已更新，需要重启后端服务器

## 代码验证

### JWT Token 创建 ✅
`src/api/routes/auth.py` 中的 `create_access_token` 函数已正确，不包含 `account` 字段。

### 企微通知 ✅
`src/api/routes/artifacts.py` 和 `src/api/routes/corrections.py` 中的通知函数正确实现：
1. 接收 `user_id` 参数
2. 创建独立的数据库 Session
3. 通过 `UserRepository.get_by_id(user_id)` 查询用户
4. 使用 `user.username` 作为企微英文账号
5. 调用 `wecom_service.send_artifact_success_notification()` 或 `send_artifact_failure_notification()`

### 配置文件 ✅
`config/development.yaml` 中已添加：
- `wecom.enabled`: 是否启用企微通知
- `wecom.api_url`: 企微消息 API 地址
- `frontend.base_url`: 前端基础 URL（用于生成链接）

## 下一步

1. **重启后端服务器**（必须）
2. 测试登录功能
3. 测试 artifact 生成时的企微通知功能
