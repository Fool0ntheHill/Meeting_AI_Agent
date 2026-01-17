# 生产环境迁移方案总结

## 📋 问题回答

### Q1: 数据库迁移要怎么做？

**答案**：使用提供的迁移脚本 `scripts/migrate_data_to_production.py`

**当前架构**：
- 开发环境：SQLite（`meeting_agent.db`）
- 生产环境：PostgreSQL（推荐）

**迁移步骤**：
1. 创建生产数据库
2. 初始化表结构（使用 SQLAlchemy 自动创建）
3. 运行迁移脚本（可选，如果需要保留开发数据）

```bash
# 演练模式
python scripts/migrate_data_to_production.py \
  --source sqlite:///./meeting_agent.db \
  --target postgresql://user:pass@host:5432/dbname \
  --dry-run

# 实际迁移
python scripts/migrate_data_to_production.py \
  --source sqlite:///./meeting_agent.db \
  --target postgresql://user:pass@host:5432/dbname
```

---

### Q2: 当前的数据库是分元数据和具体数据的吗？

**答案**：是的，已经分离

**元数据（数据库）**：
- 用户信息（users）
- 任务元数据（tasks）
- 转写记录元数据（transcripts）
- 说话人映射（speaker_mappings）
- 生成内容元数据（generated_artifacts）
- 提示词模板（prompt_templates）
- 热词集元数据（hotword_sets）
- 审计日志（audit_logs）

**具体数据（对象存储）**：
- 开发环境：本地文件系统（`uploads/` 目录）
- 生产环境：火山引擎 TOS（或其他 OSS）
- 存储内容：音频文件、临时文件

**关键特点**：
✅ 数据库只存储文件路径/URL，不存储文件内容
✅ 使用 `StorageClient` 抽象存储操作
✅ 支持切换不同的对象存储服务

---

### Q3: 公司的好像是分开元数据和 OSS 的，还要把服务器地址迁到公司上

**答案**：你们的架构已经符合这个模式，只需要配置公司的 OSS

**迁移步骤**：

1. **配置公司的 TOS/OSS**：
```yaml
# config/production.yaml
storage:
  provider: tos
  bucket: your-company-meeting-agent-prod  # 公司的 bucket
  region: cn-beijing  # 公司的区域
  access_key: ${STORAGE_ACCESS_KEY}
  secret_key: ${STORAGE_SECRET_KEY}
  endpoint: tos-cn-beijing.volces.com  # 或公司内网地址
```

2. **迁移本地文件到公司 OSS**：
```bash
# 使用迁移脚本
python scripts/migrate_files_to_tos.py \
  --config config/production.yaml \
  --source-dir uploads \
  --max-concurrent 10
```

3. **更新数据库中的文件路径**：
```bash
# 将本地路径转换为 OSS URL
python scripts/update_file_paths_in_db.py \
  --db postgresql://user:pass@host:5432/dbname \
  --tos-base https://your-company-bucket.tos-cn-beijing.volces.com
```

**服务器地址迁移**：
- 部署到公司服务器（Docker 或 Systemd）
- 配置 Nginx 反向代理
- 使用公司的域名（如 `api.your-company.com`）

---

### Q4: 此外还有 API 接口也要变一下吧？

**答案**：前端需要更新 API 地址，后端不需要改代码

**前端需要修改**：
```typescript
// .env.production
VITE_API_BASE_URL=https://api.your-company.com
VITE_API_PREFIX=/api/v1
```

**后端不需要改**：
- API 路由保持不变（`/api/v1/*`）
- 只需要配置 Nginx 反向代理
- 通过域名访问即可

**Nginx 配置示例**：
```nginx
server {
    listen 443 ssl http2;
    server_name api.your-company.com;
    
    location /api/v1/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### Q5: 公司好像大部分是用 GO 写的，对我们的影响大吗？

**答案**：影响很小，可以无缝集成

**好消息**：
✅ 后端是独立的 Python 微服务，不需要改写为 Go
✅ 通过 HTTP API 通信，语言无关
✅ 可以作为微服务集成到公司架构

**需要对接的部分**：

1. **认证系统**：
   - 当前：开发环境用户名登录 + JWT
   - 生产：企业微信扫码登录（需要对接公司的认证服务）
   - 方案：网关统一认证 或 JWT Token 验证

2. **用户系统**：
   - 当前：本地 users 表
   - 生产：可能需要同步公司的用户系统
   - 方案：通过 API 同步 或 共享用户数据库

3. **计费系统**：
   - 当前：本地 audit_logs 记录成本
   - 生产：可能需要对接公司的计费平台
   - 方案：通过 API 上报成本数据

**Go 服务调用 Python API 示例**：
```go
// company-service/internal/meeting/client.go
package meeting

import (
    "bytes"
    "encoding/json"
    "net/http"
)

type MeetingAgentClient struct {
    BaseURL string
    HTTPClient *http.Client
}

func (c *MeetingAgentClient) CreateTask(userID, tenantID string, req CreateTaskRequest) (*TaskResponse, error) {
    url := c.BaseURL + "/api/v1/tasks"
    
    body, _ := json.Marshal(req)
    httpReq, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
    
    // 注入用户信息
    httpReq.Header.Set("Content-Type", "application/json")
    httpReq.Header.Set("X-User-ID", userID)
    httpReq.Header.Set("X-Tenant-ID", tenantID)
    
    resp, err := c.HTTPClient.Do(httpReq)
    // ... 处理响应
    
    return &taskResp, nil
}
```

**集成架构**：
```
前端（React）
    ↓
公司 API 网关（Go）
    ↓
Meeting Agent API（Python）
    ↓
数据库（PostgreSQL）+ OSS（TOS）
```

---

## 📦 已创建的文件

### 文档
1. **`docs/production_deployment_guide.md`**
   - 完整的生产环境部署指南
   - 包含数据库迁移、文件迁移、API 部署、监控运维
   - 详细的配置示例和故障排查

2. **`docs/production_migration_checklist.md`**
   - 快速检查清单
   - 分步骤的操作指南
   - 每个步骤的验证点

3. **`docs/summaries/PRODUCTION_MIGRATION_SUMMARY.md`**（本文档）
   - 问题回答总结
   - 关键概念说明

### 迁移脚本
1. **`scripts/migrate_data_to_production.py`**
   - 数据库迁移工具
   - 支持演练模式（`--dry-run`）
   - 自动处理依赖关系

2. **`scripts/migrate_files_to_tos.py`**
   - 文件迁移工具
   - 支持并发上传
   - 保持目录结构

3. **`scripts/update_file_paths_in_db.py`**
   - 路径更新工具
   - 将本地路径转换为 OSS URL
   - 支持演练模式

---

## 🎯 迁移流程总览

### 阶段 1: 准备（1-2 天）
- [ ] 准备生产服务器
- [ ] 申请各种账号（火山引擎、Azure、讯飞、Gemini）
- [ ] 配置企业微信应用
- [ ] 备份开发数据

### 阶段 2: 数据库迁移（半天）
- [ ] 创建生产数据库
- [ ] 初始化表结构
- [ ] 迁移数据（可选）
- [ ] 验证数据完整性

### 阶段 3: 文件迁移（半天-1天）
- [ ] 配置生产 TOS
- [ ] 迁移文件到 TOS
- [ ] 更新数据库路径
- [ ] 验证文件可访问

### 阶段 4: API 部署（1 天）
- [ ] 配置环境变量
- [ ] 部署 API 服务
- [ ] 部署 Worker 服务
- [ ] 配置 Nginx
- [ ] 配置 SSL

### 阶段 5: 认证集成（1-2 天）
- [ ] 对接企业微信登录
- [ ] 配置网关认证
- [ ] 测试认证流程

### 阶段 6: 测试验证（1-2 天）
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 安全测试
- [ ] 用户验收测试

### 阶段 7: 上线（半天）
- [ ] 灰度发布
- [ ] 全量发布
- [ ] 监控告警
- [ ] 文档交付

**总计：5-8 天**

---

## 🔑 关键要点

### 架构优势
✅ 元数据和文件数据已分离
✅ 使用 ORM，支持多种数据库
✅ 存储客户端已抽象，易于切换
✅ 微服务架构，语言无关

### 迁移优势
✅ 提供完整的迁移脚本
✅ 支持演练模式，安全可靠
✅ 自动处理依赖关系
✅ 详细的文档和检查清单

### 集成优势
✅ HTTP API 通信，与 Go 服务无缝集成
✅ 支持网关认证，易于对接
✅ 独立部署，不影响现有系统
✅ 可以逐步迁移，风险可控

---

## 📚 相关文档

- [完整部署指南](../production_deployment_guide.md)
- [快速检查清单](../production_migration_checklist.md)
- [数据库迁移指南](../database_migration_guide.md)
- [前端开发指南](../FRONTEND_DEVELOPMENT_GUIDE.md)
- [后端 API 信息](../BACKEND_API_INFO.md)

---

## 🎉 总结

你们的项目架构设计得很好，已经做到了元数据和文件数据分离，使用了 ORM 和存储抽象，这使得迁移到生产环境非常简单。

**主要工作**：
1. 配置生产数据库（PostgreSQL）
2. 配置公司的 OSS（TOS）
3. 运行迁移脚本
4. 部署服务
5. 对接认证

**与公司 Go 服务的集成**：
- 通过 HTTP API 通信，语言无关
- 可以作为独立微服务运行
- 不需要改写为 Go

**前端完成后**：
- 更新 API 地址
- 对接企业微信登录
- 端到端测试
- 即可上线 MVP

整个迁移过程预计 5-8 天，风险可控，可以逐步进行。
