# 企业微信通知功能实现总结

## 实现日期
2026-01-26

## 功能概述
在会议纪要生成成功或失败后，系统自动向用户发送企业微信 Markdown 消息通知。

## 修改的文件

### 1. 配置模型 (`src/config/models.py`)
- 添加 `WeComConfig` 类：企微通知配置
- 添加 `FrontendConfig` 类：前端 URL 配置
- 在 `AppConfig` 中添加 `wecom` 和 `frontend` 字段

### 2. 配置文件 (`config/development.yaml`)
```yaml
wecom:
  enabled: true
  api_url: "http://gsmsg.gs.com:24905"

frontend:
  base_url: "http://localhost:3000"
  workspace_path: "/workspace"
  workbench_path: "/workbench"
```

### 3. 企微通知服务 (`src/utils/wecom_notification.py`)
- 更新 `WeComNotificationService` 构造函数，接受 `frontend_base_url` 参数
- 更新 `send_artifact_success_notification` 方法，移除 `frontend_base_url` 参数
- 更新 `send_artifact_failure_notification` 方法，移除 `frontend_base_url` 参数
- 更新 `get_wecom_service` 函数，支持传入配置参数

### 4. Artifact 生成路由 (`src/api/routes/artifacts.py`)
- 添加 `asyncio` 导入
- 添加 `get_wecom_service` 和 `get_config` 导入
- 在 `generate_artifact` 成功时调用 `_send_success_notification`
- 在 `generate_artifact` 失败时调用 `_send_failure_notification`
- 添加 `_send_success_notification` helper 函数
- 添加 `_send_failure_notification` helper 函数

### 5. Artifact 重新生成路由 (`src/api/routes/corrections.py`)
- 添加 `asyncio` 导入
- 添加 `get_wecom_service` 和 `get_config` 导入
- 在 `regenerate_artifact` 成功时调用 `_send_success_notification`
- 在 `regenerate_artifact` 失败时调用 `_send_failure_notification`
- 添加 `_send_success_notification` helper 函数
- 添加 `_send_failure_notification` helper 函数

## 关键设计决策

### 1. 异步通知
使用 `asyncio.create_task()` 异步发送通知，不阻塞 API 响应：
- 即使通知发送失败，也不影响 artifact 生成结果
- 通知失败会记录日志，但不会抛出异常

### 2. 独立数据库会话
异步任务中创建新的数据库会话：
```python
db = get_session()
try:
    # 使用 db
finally:
    db.close()
```
**原因**：FastAPI 的依赖注入会在请求结束后关闭 Session，异步任务需要独立的 Session。

### 3. 用户账号获取
通过 `task.user_id` → 查询 User 表 → 获取 `user.username`（企微英文账号）：
- GSUC 登录时，`username` 存储企微英文账号（如 `lorenzolin`）
- 开发环境登录时，`username` 是用户自定义的用户名

### 4. URL 生成
- 成功：`{base_url}/tasks/{task_id}/workspace?artifactId={artifact_id}`
- 失败：`{base_url}/tasks/{task_id}/workbench`

## 通知消息格式

### 成功通知
```markdown
# ✅ 会议纪要生成成功

**会议名称**: {task_name}
**会议时间**: {meeting_date} {meeting_time}

---

[📄 点击查看会议纪要]({workspace_url})
```

### 失败通知
```markdown
# ❌ 会议纪要生成失败

**会议名称**: {task_name}
**会议时间**: {meeting_date} {meeting_time}
**错误信息**: {error_message}
**错误码**: {error_code}

---

[🔧 前往工作台查看详情]({workbench_url})
```

## 测试验证

### 语法检查
```bash
python -m py_compile src/api/routes/artifacts.py src/api/routes/corrections.py src/utils/wecom_notification.py src/config/models.py
```
✅ 通过

### 功能测试
使用 `scripts/test_wecom_notification.py` 测试通知功能。

## 前端配合

### 无需改动
前端不需要做任何代码改动，只需要：
1. 确保路由格式符合规范
2. 告知后端 `frontend.base_url` 配置值

### 环境迁移
修改配置文件中的 `frontend.base_url` 即可，无需修改代码。

## 注意事项

1. **配置检查**：确保 `wecom.enabled` 和 `frontend.base_url` 已配置
2. **用户账号**：确保 User 表的 `username` 字段存储企微英文账号
3. **异步执行**：通知是异步的，不会阻塞 API 响应
4. **错误处理**：通知发送失败不会影响 artifact 生成
5. **数据库会话**：异步任务使用独立的数据库会话

## 相关文档
- [企业微信通知集成指南](../WECOM_NOTIFICATION_INTEGRATION.md)
- [Artifact 显示名称指南](../ARTIFACT_DISPLAY_NAME_GUIDE.md)
