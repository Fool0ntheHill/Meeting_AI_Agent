# 企业微信通知集成指南

## 概述

在会议纪要生成成功或失败后，系统会自动向用户发送企业微信 Markdown 消息通知。

## 功能特性

### 成功通知
- 会议名称
- 会议时间（日期 + 时间）
- 纪要类型（自定义名称或默认类型）
- Workspace 链接（跳转到具体的 artifact）

### 失败通知
- 会议名称
- 会议时间（日期 + 时间）
- 错误码
- 错误消息
- Workbench 链接（跳转到任务执行页）

## 配置

### 后端配置 (`config/development.yaml`)

```yaml
# 企业微信通知配置
wecom:
  enabled: true
  api_url: "http://gsmsg.gs.com:24905"  # 企微消息 API 地址

# 前端 URL 配置（用于生成通知链接）
frontend:
  base_url: "http://localhost:3000"  # 前端基础 URL
  workspace_path: "/workspace"  # Workspace 路径
  workbench_path: "/workbench"  # Workbench 路径
```

**注意**：
- `frontend.base_url` 需要根据部署环境配置
- 开发环境：`http://localhost:3000`
- 生产环境：实际的域名或 IP 地址

### 配置模型更新

在 `src/config/models.py` 中添加了两个新的配置类：

```python
class WeComConfig(BaseModel):
    """企业微信通知配置"""
    enabled: bool = Field(default=False, description="是否启用企微通知")
    api_url: str = Field(default="http://gsmsg.gs.com:24905", description="企微消息 API 地址")

class FrontendConfig(BaseModel):
    """前端配置"""
    base_url: str = Field(..., description="前端基础 URL")
    workspace_path: str = Field(default="/workspace", description="Workspace 路径")
    workbench_path: str = Field(default="/workbench", description="Workbench 路径")
```

## 实现细节

### 用户标识

系统使用 User 表中的 `username` 字段作为企微英文账号：
- GSUC 登录时，`username` 存储的是企微英文账号（如 `lorenzolin`）
- 开发环境登录时，`username` 是用户自定义的用户名

### 通知流程

1. **Artifact 生成成功**：
   ```
   generate_artifact() 
   → 生成成功 
   → asyncio.create_task(_send_success_notification())
   → 从数据库获取 user.username
   → 调用企微 API 发送通知
   ```

2. **Artifact 生成失败**：
   ```
   generate_artifact() 
   → 捕获异常 
   → asyncio.create_task(_send_failure_notification())
   → 从数据库获取 user.username
   → 调用企微 API 发送通知
   ```

### 异步通知

通知使用 `asyncio.create_task()` 异步发送，不阻塞 API 响应：
- 即使通知发送失败，也不影响 artifact 生成结果
- 通知失败会记录日志，但不会抛出异常

### URL 生成

**成功通知链接**：
```
{frontend.base_url}/tasks/{task_id}/workspace?artifactId={artifact_id}
```

**失败通知链接**：
```
{frontend.base_url}/tasks/{task_id}/workbench
```

## 企微消息格式

### 成功消息示例

```markdown
# ✅ 会议纪要生成成功

**会议名称**: 产品评审会

**会议时间**: 2026-01-26 14:30

**纪要类型**: 产品评审纪要

---

[📄 点击查看会议纪要](http://localhost:3000/tasks/task_abc123/workspace?artifactId=artifact_xyz789)
```

### 失败消息示例

```markdown
# ❌ 会议纪要生成失败

**会议名称**: 产品评审会

**会议时间**: 2026-01-26 14:30

**错误信息**: LLM API 调用超时

**错误码**: ARTIFACT_GENERATION_FAILED

---

[🔧 前往工作台查看详情](http://localhost:3000/tasks/task_abc123/workbench)
```

## 前端配合要点

### 无需额外改动

前端不需要做任何改动，只需要：
1. 确保路由格式符合规范：
   - Workspace: `/tasks/{taskId}/workspace?artifactId={artifactId}`
   - Workbench: `/tasks/{taskId}/workbench`

2. 告知后端 `frontend.base_url` 配置值

### 环境迁移

当从开发环境迁移到生产环境时：
- 只需修改 `config/production.yaml` 中的 `frontend.base_url`
- 不需要修改代码

## 测试

### 测试脚本

使用 `scripts/test_wecom_notification.py` 测试通知功能：

```bash
python scripts/test_wecom_notification.py
```

### 手动测试

1. 启动后端服务
2. 生成一个 artifact
3. 检查企微是否收到通知
4. 点击链接验证跳转是否正确

## 故障排查

### 通知未发送

检查日志中是否有以下信息：
- `WeCom notification disabled, skipping` - 企微通知未启用
- `Frontend config not found` - 前端配置缺失
- `User not found` - 用户不存在
- `Failed to send WeCom notification` - 发送失败

### 链接无法跳转

1. 检查 `frontend.base_url` 配置是否正确
2. 检查前端路由是否匹配
3. 检查 task_id 和 artifact_id 是否正确

## 相关文件

- `src/utils/wecom_notification.py` - 企微通知服务
- `src/api/routes/artifacts.py` - Artifact 生成路由（集成通知）
- `src/config/models.py` - 配置模型
- `config/development.yaml` - 开发环境配置
- `scripts/test_wecom_notification.py` - 测试脚本

## 注意事项

1. **用户账号**：确保 User 表中的 `username` 字段存储的是企微英文账号
2. **异步执行**：通知是异步发送的，不会阻塞 API 响应
3. **错误处理**：通知发送失败不会影响 artifact 生成
4. **配置管理**：不同环境使用不同的配置文件
5. **URL 格式**：前端路由格式需要与后端生成的 URL 一致
