# 生产环境迁移快速检查清单

## 📋 迁移前准备

### 1. 环境准备
- [ ] 准备生产服务器（推荐配置：4核8G+）
- [ ] 安装 Python 3.12
- [ ] 安装 PostgreSQL 15+
- [ ] 安装 Redis 7+
- [ ] 配置防火墙规则
- [ ] 准备域名和 SSL 证书

### 2. 账号准备
- [ ] 火山引擎账号（ASR + TOS）
- [ ] Azure 账号（备用 ASR）
- [ ] 科大讯飞账号（声纹识别）
- [ ] Google Gemini API Key
- [ ] 企业微信应用配置

### 3. 数据备份
- [ ] 备份开发数据库：`cp meeting_agent.db meeting_agent_backup.db`
- [ ] 备份本地文件：`tar -czf uploads_backup.tar.gz uploads/`
- [ ] 导出配置文件：`cp config/development.yaml config/development_backup.yaml`

---

## 🗄️ 数据库迁移

### 步骤 1: 创建生产数据库

```bash
# 连接 PostgreSQL
psql -U postgres -h your-prod-db-host

# 创建数据库
CREATE DATABASE meeting_agent_prod 
  WITH ENCODING='UTF8' 
  LC_COLLATE='zh_CN.UTF-8' 
  LC_CTYPE='zh_CN.UTF-8';

# 创建用户
CREATE USER meeting_agent WITH PASSWORD 'your_secure_password';

# 授权
GRANT ALL PRIVILEGES ON DATABASE meeting_agent_prod TO meeting_agent;

# 授予 schema 权限
\c meeting_agent_prod
GRANT ALL ON SCHEMA public TO meeting_agent;
```

### 步骤 2: 初始化表结构

```bash
# 方式 1: 使用 Python 脚本
python -c "
from src.database.session import init_db
init_db('postgresql://meeting_agent:password@host:5432/meeting_agent_prod')
print('✅ 表结构初始化完成')
"

# 方式 2: 使用 Alembic（推荐）
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 步骤 3: 迁移数据（可选）

```bash
# 演练模式（不实际迁移）
python scripts/migrate_data_to_production.py \
  --source sqlite:///./meeting_agent.db \
  --target postgresql://meeting_agent:password@host:5432/meeting_agent_prod \
  --dry-run

# 实际迁移
python scripts/migrate_data_to_production.py \
  --source sqlite:///./meeting_agent.db \
  --target postgresql://meeting_agent:password@host:5432/meeting_agent_prod

# 验证数据
psql -U meeting_agent -h host -d meeting_agent_prod -c "
SELECT 
  (SELECT COUNT(*) FROM users) as users,
  (SELECT COUNT(*) FROM tasks) as tasks,
  (SELECT COUNT(*) FROM transcripts) as transcripts,
  (SELECT COUNT(*) FROM generated_artifacts) as artifacts;
"
```

**检查点**：
- [ ] 表结构创建成功
- [ ] 数据迁移完成（如需要）
- [ ] 数据完整性验证通过
- [ ] 索引创建成功

---

## 📦 文件存储迁移

### 步骤 1: 配置生产 TOS

```yaml
# config/production.yaml
storage:
  provider: tos
  bucket: your-company-meeting-agent-prod
  region: cn-beijing
  access_key: ${STORAGE_ACCESS_KEY}
  secret_key: ${STORAGE_SECRET_KEY}
  endpoint: tos-cn-beijing.volces.com  # 或公司内网地址
  temp_file_ttl: 3600
```

### 步骤 2: 迁移文件到 TOS

```bash
# 演练模式
python scripts/migrate_files_to_tos.py \
  --config config/production.yaml \
  --source-dir uploads \
  --dry-run

# 实际迁移（10 个并发）
python scripts/migrate_files_to_tos.py \
  --config config/production.yaml \
  --source-dir uploads \
  --max-concurrent 10

# 验证文件
# 登录火山引擎控制台 -> TOS -> 查看 bucket 文件列表
```

### 步骤 3: 更新数据库路径

```bash
# 演练模式
python scripts/update_file_paths_in_db.py \
  --db postgresql://meeting_agent:password@host:5432/meeting_agent_prod \
  --tos-base https://your-bucket.tos-cn-beijing.volces.com \
  --dry-run

# 实际更新
python scripts/update_file_paths_in_db.py \
  --db postgresql://meeting_agent:password@host:5432/meeting_agent_prod \
  --tos-base https://your-bucket.tos-cn-beijing.volces.com

# 验证路径
psql -U meeting_agent -h host -d meeting_agent_prod -c "
SELECT task_id, audio_files 
FROM tasks 
LIMIT 5;
"
```

**检查点**：
- [ ] TOS bucket 创建成功
- [ ] 文件上传完成
- [ ] 数据库路径更新完成
- [ ] 文件可访问性验证通过

---

## 🚀 API 服务部署

### 步骤 1: 配置环境变量

```bash
# 创建 .env.production
cat > .env.production << 'EOF'
ENV=production
DEBUG=false

# 数据库
DB_HOST=your-prod-db-host
DB_PORT=5432
DB_NAME=meeting_agent_prod
DB_USER=meeting_agent
DB_PASSWORD=your_secure_password

# Redis
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# 火山引擎
VOLCANO_ACCESS_KEY=your_volcano_key
VOLCANO_SECRET_KEY=your_volcano_secret
VOLCANO_APP_ID=your_app_id
VOLCANO_CLUSTER_ID=your_cluster_id
VOLCANO_TOS_BUCKET=your-company-bucket
VOLCANO_TOS_REGION=cn-beijing

# 存储
STORAGE_BUCKET=your-company-bucket
STORAGE_REGION=cn-beijing
STORAGE_ACCESS_KEY=your_storage_key
STORAGE_SECRET_KEY=your_storage_secret

# JWT
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Gemini
GEMINI_API_KEY_1=your_gemini_key_1

# Azure
AZURE_KEY_1=your_azure_key_1

# 讯飞
IFLYTEK_APP_ID=your_iflytek_app_id
IFLYTEK_API_KEY=your_iflytek_key
IFLYTEK_API_SECRET=your_iflytek_secret
IFLYTEK_GROUP_ID=your_group_id
EOF

# 设置权限
chmod 600 .env.production
```

### 步骤 2: Docker 部署（推荐）

```bash
# 构建镜像
docker build -t meeting-agent:latest .

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 健康检查
curl http://localhost:8000/health
```

### 步骤 3: Systemd 部署（备选）

```bash
# 复制服务文件
sudo cp deploy/meeting-agent-api.service /etc/systemd/system/
sudo cp deploy/meeting-agent-worker.service /etc/systemd/system/

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable meeting-agent-api
sudo systemctl enable meeting-agent-worker
sudo systemctl start meeting-agent-api
sudo systemctl start meeting-agent-worker

# 查看状态
sudo systemctl status meeting-agent-api
sudo systemctl status meeting-agent-worker

# 查看日志
sudo journalctl -u meeting-agent-api -f
```

### 步骤 4: 配置 Nginx

```bash
# 复制配置
sudo cp deploy/nginx.conf /etc/nginx/sites-available/meeting-agent
sudo ln -s /etc/nginx/sites-available/meeting-agent /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx

# 测试 API
curl https://api.your-company.com/api/v1/health
```

**检查点**：
- [ ] API 服务启动成功
- [ ] Worker 服务启动成功
- [ ] 健康检查通过
- [ ] Nginx 反向代理配置成功
- [ ] SSL 证书配置成功

---

## 🔐 认证集成

### 步骤 1: 企业微信配置

```python
# src/api/routes/auth.py
# 添加企业微信登录路由

@router.post("/wework/login")
async def wework_login(code: str):
    """企业微信扫码登录"""
    # 1. 使用 code 换取 access_token
    # 2. 获取用户信息
    # 3. 创建/更新用户
    # 4. 生成 JWT token
    pass
```

### 步骤 2: 网关集成（如果使用）

```python
# src/api/dependencies.py
# 修改认证依赖，信任网关注入的 Header

async def get_current_user_id(
    x_user_id: str = Header(...),
    x_tenant_id: str = Header(...),
) -> str:
    """从网关 Header 获取用户信息"""
    return x_user_id
```

**检查点**：
- [ ] 企业微信应用创建成功
- [ ] 回调 URL 配置正确
- [ ] 登录流程测试通过
- [ ] Token 验证正常

---

## 🔗 与公司 Go 服务集成

### 示例：Go 服务调用 Python API

```go
// company-service/internal/meeting/client.go
package meeting

import (
    "bytes"
    "encoding/json"
    "net/http"
)

type Client struct {
    BaseURL string
    HTTPClient *http.Client
}

func (c *Client) CreateTask(userID, tenantID string, req CreateTaskRequest) (*TaskResponse, error) {
    url := c.BaseURL + "/api/v1/tasks"
    
    body, _ := json.Marshal(req)
    httpReq, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
    
    // 注入用户信息
    httpReq.Header.Set("Content-Type", "application/json")
    httpReq.Header.Set("X-User-ID", userID)
    httpReq.Header.Set("X-Tenant-ID", tenantID)
    
    resp, err := c.HTTPClient.Do(httpReq)
    // ... 处理响应
}
```

**检查点**：
- [ ] Go 服务可以调用 Python API
- [ ] 认证流程正常
- [ ] 错误处理完善
- [ ] 超时配置合理

---

## 📊 监控与运维

### 步骤 1: 配置日志

```yaml
# config/production.yaml
log:
  level: INFO
  format: json
  output: file
  file_path: /var/log/meeting-agent/app.log
  max_bytes: 10485760
  backup_count: 10
  filter_sensitive: true
```

### 步骤 2: 配置监控

```bash
# 安装 Prometheus 客户端
pip install prometheus-fastapi-instrumentator

# 暴露 metrics 端点
# 访问 http://localhost:8000/metrics
```

### 步骤 3: 配置告警

```yaml
# prometheus/alerts.yml
groups:
  - name: meeting-agent
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        annotations:
          summary: "高错误率告警"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 5
        annotations:
          summary: "高延迟告警"
```

**检查点**：
- [ ] 日志收集正常
- [ ] 监控指标暴露
- [ ] 告警规则配置
- [ ] 健康检查正常

---

## 🧪 测试验证

### 端到端测试

```bash
# 1. 登录测试
curl -X POST https://api.your-company.com/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}'

# 2. 上传文件测试
curl -X POST https://api.your-company.com/api/v1/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.wav"

# 3. 创建任务测试
curl -X POST https://api.your-company.com/api/v1/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_files": ["uploads/xxx/xxx.wav"],
    "meeting_type": "internal"
  }'

# 4. 查询任务测试
curl https://api.your-company.com/api/v1/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**检查点**：
- [ ] 登录功能正常
- [ ] 文件上传正常
- [ ] 任务创建正常
- [ ] 任务查询正常
- [ ] Worker 处理正常
- [ ] 结果生成正常

---

## 📝 上线前最终检查

### 安全检查
- [ ] 所有密钥使用环境变量
- [ ] 数据库密码强度足够
- [ ] JWT 密钥随机生成
- [ ] HTTPS 强制启用
- [ ] CORS 配置正确
- [ ] 敏感信息过滤

### 性能检查
- [ ] 数据库连接池配置
- [ ] Redis 连接池配置
- [ ] Worker 数量合理
- [ ] 文件上传大小限制
- [ ] API 超时配置
- [ ] 并发限制配置

### 备份检查
- [ ] 数据库自动备份
- [ ] TOS 生命周期策略
- [ ] 日志轮转配置
- [ ] 配置文件备份

### 文档检查
- [ ] API 文档更新
- [ ] 运维文档完善
- [ ] 故障处理手册
- [ ] 联系人信息

---

## 🎉 上线

### 上线步骤

1. **灰度发布**（推荐）
   - 先部署到测试环境
   - 小范围用户测试
   - 逐步扩大范围

2. **全量发布**
   - 停止旧服务
   - 启动新服务
   - 验证功能
   - 监控指标

3. **回滚准备**
   - 保留旧版本
   - 准备回滚脚本
   - 监控告警

### 上线后监控

```bash
# 实时日志
tail -f /var/log/meeting-agent/app.log

# 系统资源
htop

# 数据库连接
psql -U meeting_agent -h host -d meeting_agent_prod -c "
SELECT count(*) FROM pg_stat_activity WHERE datname='meeting_agent_prod';
"

# Redis 状态
redis-cli -h host -a password INFO
```

---

## 📞 问题排查

### 常见问题

**Q: 数据库连接失败**
```bash
# 检查网络
ping your-db-host

# 检查端口
telnet your-db-host 5432

# 检查密码
psql -U meeting_agent -h host -d meeting_agent_prod
```

**Q: TOS 上传失败**
```bash
# 检查配置
python -c "
from src.config.loader import get_config
config = get_config()
print(f'Bucket: {config.storage.bucket}')
print(f'Region: {config.storage.region}')
"

# 测试上传
python scripts/test_tos_upload.py
```

**Q: Worker 不工作**
```bash
# 检查 Redis 连接
redis-cli -h host -a password PING

# 检查队列
redis-cli -h host -a password LLEN meeting_tasks

# 查看 Worker 日志
sudo journalctl -u meeting-agent-worker -f
```

---

## 📚 相关文档

- [完整部署指南](./production_deployment_guide.md)
- [前端开发指南](./FRONTEND_DEVELOPMENT_GUIDE.md)
- [后端 API 信息](./BACKEND_API_INFO.md)
- [数据库迁移指南](./database_migration_guide.md)

---

**祝部署顺利！🎉**
