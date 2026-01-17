# 数据库迁移指南

## 概述

本项目使用 SQLAlchemy ORM，支持从 SQLite 轻松迁移到 PostgreSQL、MySQL 等生产级数据库。

## 当前架构

### 技术栈

- **ORM**: SQLAlchemy 2.0+
- **开发数据库**: SQLite (文件数据库，无需安装)
- **生产数据库**: PostgreSQL (推荐) / MySQL

### 数据库表结构

#### 1. tasks (任务表)

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | String(64) PK | 任务唯一标识 |
| user_id | String(64) | 用户 ID |
| tenant_id | String(64) | 租户 ID |
| meeting_type | String(64) | 会议类型 |
| audio_files | Text (JSON) | 音频文件列表 |
| file_order | Text (JSON) | 文件排序 |
| asr_language | String(32) | ASR 识别语言 |
| output_language | String(32) | 输出语言 |
| skip_speaker_recognition | Boolean | 是否跳过声纹识别 |
| hotword_set_id | String(64) | 热词集 ID |
| preferred_asr_provider | String(32) | 首选 ASR 提供商 |
| state | String(32) | 任务状态 |
| progress | Float | 进度百分比 |
| estimated_time | Integer | 预计剩余时间(秒) |
| error_details | Text | 错误详情 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| completed_at | DateTime | 完成时间 |

**索引**:
- `idx_task_user_created`: (user_id, created_at)
- `idx_task_tenant_created`: (tenant_id, created_at)
- `idx_task_state_created`: (state, created_at)

#### 2. transcripts (转写记录表)

| 字段 | 类型 | 说明 |
|------|------|------|
| transcript_id | String(64) PK | 转写记录 ID |
| task_id | String(64) FK | 关联任务 ID |
| segments | Text (JSON) | 转写片段列表 |
| full_text | Text | 完整文本 |
| duration | Float | 音频时长(秒) |
| language | String(32) | 语言 |
| provider | String(32) | ASR 提供商 |
| created_at | DateTime | 创建时间 |

**外键**: task_id → tasks.task_id (CASCADE DELETE)

#### 3. speaker_mappings (说话人映射表)

| 字段 | 类型 | 说明 |
|------|------|------|
| mapping_id | Integer PK | 自增主键 |
| task_id | String(64) FK | 关联任务 ID |
| speaker_label | String(64) | 说话人标签 |
| speaker_name | String(128) | 说话人姓名 |
| speaker_id | String(64) | 声纹特征 ID |
| confidence | Float | 识别置信度 |
| is_corrected | Boolean | 是否人工修正 |
| corrected_by | String(64) | 修正人 |
| corrected_at | DateTime | 修正时间 |
| created_at | DateTime | 创建时间 |

**外键**: task_id → tasks.task_id (CASCADE DELETE)
**唯一约束**: (task_id, speaker_label)

#### 4. generated_artifacts (生成内容表)

| 字段 | 类型 | 说明 |
|------|------|------|
| artifact_id | String(64) PK | 内容 ID |
| task_id | String(64) FK | 关联任务 ID |
| artifact_type | String(64) | 内容类型 |
| version | Integer | 版本号 |
| prompt_instance | Text (JSON) | 提示词实例 |
| content | Text (JSON) | 生成内容 |
| created_by | String(64) | 创建者 |
| created_at | DateTime | 创建时间 |

**外键**: task_id → tasks.task_id (CASCADE DELETE)
**索引**:
- `idx_artifact_task_type`: (task_id, artifact_type)
- `idx_artifact_task_version`: (task_id, version)

#### 5. prompt_templates (提示词模板表)

| 字段 | 类型 | 说明 |
|------|------|------|
| template_id | String(64) PK | 模板 ID |
| title | String(256) | 模板标题 |
| description | Text | 模板描述 |
| prompt_body | Text | 提示词正文 |
| artifact_type | String(64) | 内容类型 |
| supported_languages | Text (JSON) | 支持的语言列表 |
| parameter_schema | Text (JSON) | 参数定义 |
| is_system | Boolean | 是否系统模板 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 迁移到 PostgreSQL

### 1. 安装 PostgreSQL 驱动

```bash
pip install psycopg2-binary
# 或者使用纯 Python 实现
pip install psycopg2
```

### 2. 创建 PostgreSQL 数据库

```sql
-- 连接到 PostgreSQL
psql -U postgres

-- 创建数据库
CREATE DATABASE meeting_agent;

-- 创建用户(可选)
CREATE USER meeting_user WITH PASSWORD 'your_password';

-- 授权
GRANT ALL PRIVILEGES ON DATABASE meeting_agent TO meeting_user;
```

### 3. 修改数据库连接

```python
from src.database.session import init_db, get_engine

# PostgreSQL 连接字符串
database_url = "postgresql://meeting_user:your_password@localhost:5432/meeting_agent"

# 初始化数据库
init_db(database_url)
```

### 4. 数据迁移(可选)

如果需要从 SQLite 迁移数据到 PostgreSQL:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Task, TranscriptRecord, etc.

# 源数据库 (SQLite)
source_engine = create_engine("sqlite:///./meeting_agent.db")
SourceSession = sessionmaker(bind=source_engine)

# 目标数据库 (PostgreSQL)
target_engine = create_engine("postgresql://user:pass@localhost/meeting_agent")
Base.metadata.create_all(target_engine)
TargetSession = sessionmaker(bind=target_engine)

# 迁移数据
source_session = SourceSession()
target_session = TargetSession()

try:
    # 迁移任务
    tasks = source_session.query(Task).all()
    for task in tasks:
        target_session.merge(task)
    
    # 迁移其他表...
    
    target_session.commit()
    print("数据迁移成功!")
except Exception as e:
    target_session.rollback()
    print(f"迁移失败: {e}")
finally:
    source_session.close()
    target_session.close()
```

## 迁移到 MySQL

### 1. 安装 MySQL 驱动

```bash
pip install pymysql
# 或者
pip install mysqlclient
```

### 2. 创建 MySQL 数据库

```sql
-- 连接到 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE meeting_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'meeting_user'@'localhost' IDENTIFIED BY 'your_password';

-- 授权
GRANT ALL PRIVILEGES ON meeting_agent.* TO 'meeting_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 修改数据库连接

```python
# MySQL 连接字符串
database_url = "mysql+pymysql://meeting_user:your_password@localhost:3306/meeting_agent?charset=utf8mb4"

# 初始化数据库
init_db(database_url)
```

## 配置管理

### 环境变量配置

```bash
# .env 文件
DATABASE_URL=postgresql://user:pass@localhost:5432/meeting_agent

# 或者 SQLite (开发环境)
DATABASE_URL=sqlite:///./meeting_agent.db
```

### 代码中使用

```python
import os
from src.database.session import init_db

# 从环境变量读取
database_url = os.getenv("DATABASE_URL", "sqlite:///./meeting_agent.db")
init_db(database_url)
```

## 性能优化建议

### PostgreSQL 优化

```sql
-- 创建额外索引(根据查询模式)
CREATE INDEX idx_tasks_user_state ON tasks(user_id, state);
CREATE INDEX idx_artifacts_created ON generated_artifacts(created_at);

-- 启用查询计划分析
EXPLAIN ANALYZE SELECT * FROM tasks WHERE user_id = 'user_123';
```

### 连接池配置

```python
from src.database.session import get_engine

# 生产环境连接池配置
engine = get_engine(
    database_url="postgresql://...",
    echo=False,  # 关闭 SQL 日志
)

# 连接池参数已在 session.py 中配置:
# - pool_size=10
# - max_overflow=20
# - pool_pre_ping=True
# - pool_recycle=3600
```

## 数据库备份

### SQLite 备份

```bash
# 简单复制文件
cp meeting_agent.db meeting_agent_backup.db

# 或使用 SQLite 命令
sqlite3 meeting_agent.db ".backup meeting_agent_backup.db"
```

### PostgreSQL 备份

```bash
# 备份
pg_dump -U meeting_user -d meeting_agent -F c -f meeting_agent_backup.dump

# 恢复
pg_restore -U meeting_user -d meeting_agent -c meeting_agent_backup.dump
```

## 常见问题

### Q: 如何查看当前使用的数据库?

```python
from src.database.session import get_engine

engine = get_engine()
print(f"Database URL: {engine.url}")
```

### Q: 如何重置数据库?

```python
from src.database.session import get_engine
from src.database.models import Base

engine = get_engine()

# 删除所有表
Base.metadata.drop_all(engine)

# 重新创建所有表
Base.metadata.create_all(engine)
```

### Q: 如何处理数据库迁移(Schema 变更)?

推荐使用 Alembic 进行数据库版本管理:

```bash
# 安装 Alembic
pip install alembic

# 初始化 Alembic
alembic init alembic

# 生成迁移脚本
alembic revision --autogenerate -m "Add new column"

# 应用迁移
alembic upgrade head
```

## 总结

- ✅ 使用 SQLAlchemy ORM 确保数据库无关性
- ✅ SQLite 适合开发和测试
- ✅ PostgreSQL 推荐用于生产环境
- ✅ 通过环境变量管理数据库连接
- ✅ 使用 Repository 模式封装数据访问
- ✅ 支持连接池和性能优化
