# 生产环境部署与迁移指南

## 概述

本文档详细说明如何将会议纪要 AI Agent 从开发环境迁移到生产环境，包括数据库迁移、存储迁移、API 集成等关键步骤。

---

## 当前架构分析

### 数据存储架构

**元数据（数据库）**：
- 开发环境：SQLite（`meeting_agent.db`）
- 生产环境：PostgreSQL（推荐）或 MySQL
- 存储内容：
  - 用户信息（users）
  - 任务元数据（tasks）
  - 转写记录元数据（transcripts）
  - 说话人映射（speaker_mappings）
  - 生成内容元数据（generated_artifacts）
  - 提示词模板（prompt_templates）
  - 热词集元数据（hotword_sets）
  - 审计日志（audit_logs）

**文件数据（对象存储）**：
- 开发环境：本地文件系统（`uploads/` 目录）
- 生产环境：火山引擎 TOS（或其他 OSS）
- 存储内容：
  - 上传的音频文件
  - 处理后的音频文件
  - 临时文件

**关键特点**：
✅ 元数据和文件数据已分离
✅ 数据库只存储路径/URL，不存储文件内容
✅ 使用 SQLAlchemy ORM，支持多种数据库
✅ 存储客户端已抽象（`StorageClient`），支持切换

---

## 生产环境迁移步骤

### 第一步：数据库迁移

#### 1.1 准备生产数据库

```bash
# 连接到 PostgreSQL
psql -U postgres -h your-db-host

# 创建数据库
CREATE DATABASE meeting_agent_prod 
  WITH ENCODING='UTF8' 
  LC_COLLATE='zh_CN.UTF-8' 
  LC_CTYPE='zh_CN.UTF-8';

# 创建专用用户
CREATE USER meeting_agent WITH PASSWORD 'your_secure_password';

# 授权
GRANT ALL PRIVILEGES ON DATABASE meeting_agent_prod TO meeting_agent;

# 授予 schema 权限
\c meeting_agent_prod
GRANT ALL ON SCHEMA public TO meeting_agent;
```

#### 1.2 初始化表结构

```python
# 方式 1: 使用 Python 脚本
from src.database.session import init_db

# 生产数据库连接字符串
prod_db_url = "postgresql://meeting_agent:password@prod-db-host:5432/meeting_agent_prod"
init_db(prod_db_url)
```

```bash
# 方式 2: 使用 Alembic（推荐）
pip install alembic

# 初始化 Alembic
alembic init alembic

# 生成初始迁移
alembic revision --autogenerate -m "Initial schema"

# 应用到生产数据库
alembic upgrade head
```

#### 1.3 数据迁移（如果需要）

```python
# scripts/migrate_data_to_production.py
"""将开发环境数据迁移到生产环境"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import (
    Base, User, Task, TranscriptRecord, 
    SpeakerMapping, GeneratedArtifactRecord,
    PromptTemplateRecord, HotwordSetRecord
)

# 源数据库（开发）
source_engine = create_engine("sqlite:///./meeting_agent.db")
SourceSession = sessionmaker(bind=source_engine)

# 目标数据库（生产）
target_engine = create_engine("postgresql://meeting_agent:password@prod-host:5432/meeting_agent_prod")
Base.metadata.create_all(target_engine)
TargetSession = sessionmaker(bind=target_engine)

def migrate_table(model_class, source_session, target_session):
    """迁移单个表"""
    records = source_session.query(model_class).all()
    for record in records:
        # 使用 merge 避免主键冲突
        target_session.merge(record)
    target_session.commit()
    print(f"✅ {model_class.__tablename__}: {len(records)} 条记录")

def main():
    source_session = SourceSession()
    target_session = TargetSession()
    
    try:
        # 按依赖顺序迁移
        print("开始数据迁移...")
        
        migrate_table(User, source_session, target_session)
        migrate_table(PromptTemplateRecord, source_session, target_session)
        migrate_table(HotwordSetRecord, source_session, target_session)
        migrate_table(Task, source_session, target_session)
        migrate_table(TranscriptRecord, source_session, target_session)
        migrate_table(SpeakerMapping, source_session, target_session)
        migrate_table(GeneratedArtifactRecord, source_session, target_session)
        
        print("✅ 数据迁移完成！")
        
    except Exception as e:
        target_session.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        source_session.close()
        target_session.close()

if __name__ == "__main__":
    main()
```

---

### 第二步：文件存储迁移

#### 2.1 配置生产 TOS

```yaml
# config/production.yaml
storage:
  provider: tos
  bucket: your-company-meeting-agent-prod  # 公司的 TOS bucket
  region: cn-beijing  # 或其他区域
  access_key: ${STORAGE_ACCESS_KEY}
  secret_key: ${STORAGE_SECRET_KEY}
  endpoint: tos-cn-beijing.volces.com  # 或公司内网地址
  temp_file_ttl: 3600
```

#### 2.2 迁移本地文件到 TOS

```python
# scripts/migrate_files_to_tos.py
"""将本地文件迁移到 TOS"""

import asyncio
from pathlib import Path
from src.utils.storage import StorageClient
from src.config.loader import get_config

async def migrate_files():
    """迁移文件"""
    config = get_config()
    
    # 初始化 TOS 客户端
    storage = StorageClient(
        bucket=config.storage.bucket,
        region=config.storage.region,
        access_key=config.storage.access_key,
        secret_key=config.storage.secret_key,
    )
    
    # 扫描本地文件
    upload_dir = Path("uploads")
    files = list(upload_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    
    print(f"发现 {len(files)} 个文件需要迁移")
    
    # 上传文件
    for i, local_file in enumerate(files, 1):
        # 保持相对路径结构
        relative_path = local_file.relative_to(upload_dir)
        object_key = f"uploads/{relative_path}"
        
        try:
            url = await storage.upload_file(
                local_path=str(local_file),
                object_key=object_key,
            )
            print(f"[{i}/{len(files)}] ✅ {relative_path} -> {url}")
        except Exception as e:
            print(f"[{i}/{len(files)}] ❌ {relative_path}: {e}")
    
    print("✅ 文件迁移完成！")

if __name__ == "__main__":
    asyncio.run(migrate_files())
```

#### 2.3 更新数据库中的文件路径

```python
# scripts/update_file_paths_in_db.py
"""更新数据库中的文件路径为 TOS URL"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Task
import json

def update_paths():
    """更新路径"""
    engine = create_engine("postgresql://meeting_agent:password@prod-host:5432/meeting_agent_prod")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        tasks = session.query(Task).all()
        
        for task in tasks:
            # 解析 audio_files JSON
            audio_files = task.get_audio_files_list()
            
            # 转换路径
            updated_files = []
            for file_path in audio_files:
                if file_path.startswith("uploads/"):
                    # 转换为 TOS URL
                    tos_url = f"https://your-bucket.tos-cn-beijing.volces.com/{file_path}"
                    updated_files.append(tos_url)
                else:
                    updated_files.append(file_path)
            
            # 更新
            task.set_audio_files_list(updated_files)
        
        session.commit()
        print(f"✅ 更新了 {len(tasks)} 个任务的文件路径")
        
    except Exception as e:
        session.rollback()
        print(f"❌ 更新失败: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    update_paths()
```

---

### 第三步：API 服务部署

#### 3.1 配置生产环境变量

```bash
# .env.production
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
JWT_SECRET_KEY=your_very_secure_random_key_here

# Gemini
GEMINI_API_KEY_1=your_gemini_key_1
GEMINI_API_KEY_2=your_gemini_key_2

# Azure
AZURE_KEY_1=your_azure_key_1

# 讯飞
IFLYTEK_APP_ID=your_iflytek_app_id
IFLYTEK_API_KEY=your_iflytek_key
IFLYTEK_API_SECRET=your_iflytek_secret
IFLYTEK_GROUP_ID=your_group_id
```

#### 3.2 部署方式选择

**方式 1: Docker 部署（推荐）**

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  worker:
    build: .
    command: python worker.py
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: meeting_agent_prod
      POSTGRES_USER: meeting_agent
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

**方式 2: Systemd 服务**

```ini
# /etc/systemd/system/meeting-agent-api.service
[Unit]
Description=Meeting Agent API
After=network.target

[Service]
Type=simple
User=meeting-agent
WorkingDirectory=/opt/meeting-agent
Environment="PATH=/opt/meeting-agent/venv/bin"
EnvironmentFile=/opt/meeting-agent/.env.production
ExecStart=/opt/meeting-agent/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/meeting-agent-worker.service
[Unit]
Description=Meeting Agent Worker
After=network.target

[Service]
Type=simple
User=meeting-agent
WorkingDirectory=/opt/meeting-agent
Environment="PATH=/opt/meeting-agent/venv/bin"
EnvironmentFile=/opt/meeting-agent/.env.production
ExecStart=/opt/meeting-agent/venv/bin/python worker.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable meeting-agent-api
sudo systemctl enable meeting-agent-worker
sudo systemctl start meeting-agent-api
sudo systemctl start meeting-agent-worker

# 查看状态
sudo systemctl status meeting-agent-api
sudo systemctl status meeting-agent-worker
```

#### 3.3 Nginx 反向代理

```nginx
# /etc/nginx/sites-available/meeting-agent
upstream meeting_agent_api {
    server 127.0.0.1:8000;
    # 如果有多个实例
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name api.your-company.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-company.com;

    # SSL 证书
    ssl_certificate /etc/nginx/ssl/your-cert.crt;
    ssl_certificate_key /etc/nginx/ssl/your-key.key;

    # 上传文件大小限制
    client_max_body_size 500M;

    # API 路由
    location /api/v1/ {
        proxy_pass http://meeting_agent_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置（处理长时间请求）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 健康检查
    location /health {
        proxy_pass http://meeting_agent_api;
        access_log off;
    }
}
```

---

### 第四步：与公司 Go 服务集成

#### 4.1 影响分析

**好消息**：
✅ 后端是独立的 Python 服务，不需要改写为 Go
✅ 通过 HTTP API 通信，语言无关
✅ 可以作为微服务集成到公司架构

**需要对接的部分**：

1. **认证系统**：
   - 当前：开发环境用户名登录 + JWT
   - 生产：企业微信扫码登录（需要对接公司的认证服务）

2. **用户系统**：
   - 当前：本地 users 表
   - 生产：可能需要同步公司的用户系统

3. **计费系统**：
   - 当前：本地 audit_logs 记录成本
   - 生产：可能需要对接公司的计费平台

#### 4.2 认证集成方案

**方案 A: 网关统一认证（推荐）**

```
前端 -> 公司 API 网关（Go）-> Meeting Agent API（Python）
         ↓
      企业微信认证
      生成 JWT Token
```

```python
# src/api/dependencies.py
# 修改认证依赖，信任网关传递的用户信息

from fastapi import Header, HTTPException

async def get_current_user_id(
    x_user_id: str = Header(..., description="用户 ID（由网关注入）"),
    x_tenant_id: str = Header(..., description="租户 ID（由网关注入）"),
) -> str:
    """
    从网关注入的 Header 中获取用户信息
    
    网关已完成认证，直接信任 Header
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未认证")
    
    return x_user_id

async def get_current_tenant_id(
    x_tenant_id: str = Header(..., description="租户 ID（由网关注入）"),
) -> str:
    """获取租户 ID"""
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="未认证")
    
    return x_tenant_id
```

**方案 B: JWT Token 验证**

```python
# src/api/dependencies.py
# 验证公司统一签发的 JWT Token

import jwt
from fastapi import Header, HTTPException

# 公司的 JWT 公钥（用于验证签名）
COMPANY_JWT_PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----
"""

async def get_current_user_id(
    authorization: str = Header(..., description="Bearer Token"),
) -> str:
    """验证公司签发的 JWT Token"""
    try:
        # 提取 Token
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="无效的认证格式")
        
        token = authorization[7:]
        
        # 验证 Token（使用公司的公钥）
        payload = jwt.decode(
            token,
            COMPANY_JWT_PUBLIC_KEY,
            algorithms=["RS256"],  # 公司使用的算法
        )
        
        # 提取用户信息
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token 缺少用户信息")
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")
```

#### 4.3 API 对接示例

**公司 Go 服务调用 Python API**：

```go
// company-service/internal/meeting/client.go
package meeting

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)

type MeetingAgentClient struct {
    BaseURL    string
    HTTPClient *http.Client
}

func NewMeetingAgentClient(baseURL string) *MeetingAgentClient {
    return &MeetingAgentClient{
        BaseURL: baseURL,
        HTTPClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

// CreateTask 创建会议任务
func (c *MeetingAgentClient) CreateTask(userID, tenantID string, req CreateTaskRequest) (*TaskResponse, error) {
    url := fmt.Sprintf("%s/api/v1/tasks", c.BaseURL)
    
    body, err := json.Marshal(req)
    if err != nil {
        return nil, err
    }
    
    httpReq, err := http.NewRequest("POST", url, bytes.NewBuffer(body))
    if err != nil {
        return nil, err
    }
    
    // 注入用户信息（如果使用网关方案）
    httpReq.Header.Set("Content-Type", "application/json")
    httpReq.Header.Set("X-User-ID", userID)
    httpReq.Header.Set("X-Tenant-ID", tenantID)
    
    resp, err := c.HTTPClient.Do(httpReq)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusCreated {
        body, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("API error: %s", string(body))
    }
    
    var taskResp TaskResponse
    if err := json.NewDecoder(resp.Body).Decode(&taskResp); err != nil {
        return nil, err
    }
    
    return &taskResp, nil
}

// GetTaskStatus 获取任务状态
func (c *MeetingAgentClient) GetTaskStatus(userID, tenantID, taskID string) (*TaskStatusResponse, error) {
    url := fmt.Sprintf("%s/api/v1/tasks/%s", c.BaseURL, taskID)
    
    httpReq, err := http.NewRequest("GET", url, nil)
    if err != nil {
        return nil, err
    }
    
    httpReq.Header.Set("X-User-ID", userID)
    httpReq.Header.Set("X-Tenant-ID", tenantID)
    
    resp, err := c.HTTPClient.Do(httpReq)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("API error: %s", string(body))
    }
    
    var statusResp TaskStatusResponse
    if err := json.NewDecoder(resp.Body).Decode(&statusResp); err != nil {
        return nil, err
    }
    
    return &statusResp, nil
}
```

---

### 第五步：监控与运维

#### 5.1 健康检查

```python
# src/api/routes/health.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    storage: str

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    # TODO: 实际检查各个组件状态
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database="ok",
        redis="ok",
        storage="ok",
    )
```

#### 5.2 日志收集

```yaml
# config/production.yaml
log:
  level: INFO
  format: json  # JSON 格式便于日志收集
  output: file
  file_path: /var/log/meeting-agent/app.log
  max_bytes: 10485760  # 10MB
  backup_count: 10
  filter_sensitive: true  # 过滤敏感信息
```

#### 5.3 性能监控

```python
# 可以集成 Prometheus + Grafana
# pip install prometheus-fastapi-instrumentator

from prometheus_fastapi_instrumentator import Instrumentator

app = create_app()
Instrumentator().instrument(app).expose(app)
```

---

## 迁移检查清单

### 数据库迁移
- [ ] 创建生产数据库
- [ ] 初始化表结构
- [ ] 迁移开发数据（如需要）
- [ ] 验证数据完整性
- [ ] 配置数据库备份

### 文件存储迁移
- [ ] 配置生产 TOS
- [ ] 迁移本地文件到 TOS
- [ ] 更新数据库中的文件路径
- [ ] 验证文件可访问性
- [ ] 配置 TOS 生命周期策略

### API 服务部署
- [ ] 配置生产环境变量
- [ ] 部署 API 服务（Docker/Systemd）
- [ ] 部署 Worker 服务
- [ ] 配置 Nginx 反向代理
- [ ] 配置 SSL 证书
- [ ] 测试 API 可用性

### 认证集成
- [ ] 对接企业微信登录
- [ ] 配置 JWT 验证
- [ ] 测试认证流程
- [ ] 配置权限控制

### 监控运维
- [ ] 配置健康检查
- [ ] 配置日志收集
- [ ] 配置性能监控
- [ ] 配置告警规则
- [ ] 编写运维文档

### 前端对接
- [ ] 更新前端 API 地址
- [ ] 对接企业微信登录
- [ ] 测试端到端流程
- [ ] 性能测试
- [ ] 用户验收测试

---

## 常见问题

### Q1: 公司用 Go，会影响我们的 Python 服务吗？

**不会**。你们的服务是独立的微服务，通过 HTTP API 通信，语言无关。公司的 Go 服务可以直接调用你们的 API。

### Q2: 数据库和文件存储是分开的吗？

**是的**。数据库只存储元数据（任务信息、用户信息等），文件（音频）存储在 TOS。这是标准的架构，便于扩展。

### Q3: 如何处理大文件上传？

当前支持最大 500MB。生产环境建议：
1. 使用 TOS 预签名 URL 直传（前端直接上传到 TOS）
2. 或者使用分片上传
3. 配置 CDN 加速

### Q4: 如何保证服务高可用？

1. 部署多个 API 实例（负载均衡）
2. 部署多个 Worker 实例（队列消费）
3. 数据库主从复制
4. Redis 哨兵/集群
5. TOS 本身高可用

### Q5: 成本如何计算？

当前已实现成本追踪（`audit_logs` 表），记录每次 API 调用的成本。可以：
1. 定期汇总统计
2. 对接公司计费系统
3. 按租户/用户分摊

---

## 下一步行动

1. **立即可做**：
   - 创建生产数据库
   - 配置生产 TOS
   - 准备生产环境变量

2. **前端完成后**：
   - 部署 API 服务
   - 对接企业微信登录
   - 端到端测试

3. **上线前**：
   - 性能测试
   - 安全审计
   - 用户培训

---

## 联系与支持

如有问题，请参考：
- 技术文档：`docs/`
- API 文档：`docs/FRONTEND_DEVELOPMENT_GUIDE.md`
- 配置示例：`config/production.yaml.example`
