# 数据库设计改进建议

## 概述

本文档记录了数据库设计的已知问题和改进建议，用于指导未来的优化工作。

## 已识别的问题

### 1. 数据冗余问题

**问题**: `transcripts` 表中 `full_text` 是 `segments` 的聚合，可能导致更新不一致。

**当前设计**:
```python
class TranscriptRecord(Base):
    segments = Column(Text)  # JSON: List[Segment]
    full_text = Column(Text)  # 冗余存储
```

**改进方案**:

**方案 A: 计算属性 (推荐用于读多写少场景)**
```python
class TranscriptRecord(Base):
    segments = Column(Text)  # JSON: List[Segment]
    # 移除 full_text 列
    
    @property
    def full_text(self) -> str:
        """动态计算完整文本"""
        segments_data = self.get_segments_list()
        return " ".join(seg["text"] for seg in segments_data)
```

**方案 B: 数据库视图 (PostgreSQL)**
```sql
CREATE VIEW transcript_with_text AS
SELECT 
    transcript_id,
    task_id,
    segments,
    -- 从 JSONB 提取并聚合文本
    string_agg(
        segment->>'text', 
        ' ' 
        ORDER BY (segment->>'start_time')::float
    ) as full_text,
    duration,
    language,
    provider,
    created_at
FROM transcripts,
     jsonb_array_elements(segments::jsonb) as segment
GROUP BY transcript_id, task_id, segments, duration, language, provider, created_at;
```

**方案 C: 触发器保证一致性 (PostgreSQL)**
```sql
CREATE OR REPLACE FUNCTION update_transcript_full_text()
RETURNS TRIGGER AS $$
BEGIN
    NEW.full_text := (
        SELECT string_agg(segment->>'text', ' ')
        FROM jsonb_array_elements(NEW.segments::jsonb) as segment
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER transcript_full_text_trigger
BEFORE INSERT OR UPDATE ON transcripts
FOR EACH ROW
EXECUTE FUNCTION update_transcript_full_text();
```

**权衡**:
- 方案 A: 简单，但每次读取都需计算（适合读少场景）
- 方案 B: 查询性能好，但视图不能直接更新
- 方案 C: 自动保证一致性，但增加写入开销

**建议**: 
- MVP 阶段保持当前设计（简单）
- 生产环境迁移到 PostgreSQL 后使用方案 C（触发器）

---

### 2. ID 类型不一致

**问题**: 大多数表使用 `String(64)` 存储 UUID，但 `speaker_mappings` 使用 `Integer` 自增 ID。

**当前设计**:
```python
class Task(Base):
    task_id = Column(String(64), primary_key=True)  # UUID

class SpeakerMapping(Base):
    mapping_id = Column(Integer, primary_key=True, autoincrement=True)  # 自增
```

**问题**:
- 分布式环境下自增 ID 可能冲突
- ID 类型不统一，增加维护成本
- Integer 在极大规模下可能溢出（虽然 BigInt 可解决）

**改进方案**:

```python
class SpeakerMapping(Base):
    __tablename__ = "speaker_mappings"
    
    # 改用 UUID
    mapping_id = Column(String(64), primary_key=True, default=lambda: f"map_{uuid.uuid4().hex[:16]}")
    task_id = Column(String(64), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)
    speaker_label = Column(String(64), nullable=False)
    speaker_name = Column(String(128), nullable=False)
    # ...
    
    # 唯一约束保持不变
    __table_args__ = (
        UniqueConstraint("task_id", "speaker_label", name="uq_task_speaker"),
        Index("idx_speaker_task", "task_id"),
    )
```

**PostgreSQL 原生 UUID 类型**:
```python
from sqlalchemy.dialects.postgresql import UUID
import uuid

class SpeakerMapping(Base):
    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.task_id"))
```

**建议**: 
- 短期: 保持当前设计（避免破坏性变更）
- 长期: 迁移到 PostgreSQL 后统一使用 UUID 类型

---

### 3. 安全性考虑不足

**问题 A: 密码明文存储在文档中**

**当前文档**:
```python
database_url = "postgresql://meeting_user:your_password@localhost:5432/meeting_agent"
```

**改进方案**:
```python
import os
from urllib.parse import quote_plus

# 从环境变量读取
db_password = os.getenv("DB_PASSWORD")
if not db_password:
    raise ValueError("DB_PASSWORD environment variable not set")

# URL 编码密码（处理特殊字符）
encoded_password = quote_plus(db_password)

database_url = f"postgresql://meeting_user:{encoded_password}@localhost:5432/meeting_agent"
```

**使用 Secrets Manager (生产环境)**:
```python
import boto3

def get_db_credentials():
    """从 AWS Secrets Manager 获取数据库凭证"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='prod/meeting-agent/db')
    secret = json.loads(response['SecretString'])
    return secret['username'], secret['password']

username, password = get_db_credentials()
database_url = f"postgresql://{username}:{password}@db.internal/meeting_agent"
```

**问题 B: 敏感数据未加密**

**当前设计**:
```python
class SpeakerMapping(Base):
    speaker_id = Column(String(64))  # 声纹特征 ID，明文存储
```

**改进方案 - 字段级加密**:
```python
from cryptography.fernet import Fernet
import base64

class EncryptedString(TypeDecorator):
    """加密字符串类型"""
    impl = String
    cache_ok = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 从环境变量读取加密密钥
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")
        self.cipher = Fernet(key.encode())
    
    def process_bind_param(self, value, dialect):
        """写入数据库前加密"""
        if value is not None:
            return self.cipher.encrypt(value.encode()).decode()
        return value
    
    def process_result_value(self, value, dialect):
        """从数据库读取后解密"""
        if value is not None:
            return self.cipher.decrypt(value.encode()).decode()
        return value

class SpeakerMapping(Base):
    speaker_id = Column(EncryptedString(256))  # 加密存储
```

**PostgreSQL 透明数据加密 (TDE)**:
```sql
-- 启用 pgcrypto 扩展
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 使用加密函数
INSERT INTO speaker_mappings (speaker_id, ...)
VALUES (pgp_sym_encrypt('sensitive_data', 'encryption_key'), ...);

-- 查询时解密
SELECT pgp_sym_decrypt(speaker_id::bytea, 'encryption_key') as speaker_id
FROM speaker_mappings;
```

**建议**:
- 短期: 使用环境变量管理密码
- 中期: 实现字段级加密（speaker_id）
- 长期: 使用 Secrets Manager + TDE

---

### 4. 迁移脚本效率问题

**问题**: 循环查询和 `merge()` 适合小数据集，大表会超时。

**当前实现**:
```python
# ❌ 低效：逐条查询和插入
tasks = source_session.query(Task).all()
for task in tasks:
    target_session.merge(task)
target_session.commit()
```

**改进方案 A: 批量插入**:
```python
# ✅ 高效：批量插入
from sqlalchemy import insert

BATCH_SIZE = 1000

# 读取源数据
tasks = source_session.query(Task).yield_per(BATCH_SIZE)

# 批量插入
for batch in chunked(tasks, BATCH_SIZE):
    task_dicts = [task.__dict__ for task in batch]
    # 移除 SQLAlchemy 内部字段
    for d in task_dicts:
        d.pop('_sa_instance_state', None)
    
    target_session.execute(
        insert(Task),
        task_dicts
    )
    target_session.commit()
```

**改进方案 B: 使用 pandas (大数据集)**:
```python
import pandas as pd

# 从 SQLite 读取
df = pd.read_sql_table('tasks', source_engine)

# 写入 PostgreSQL (批量)
df.to_sql(
    'tasks',
    target_engine,
    if_exists='append',
    index=False,
    method='multi',  # 批量插入
    chunksize=1000
)
```

**改进方案 C: 专用工具 (推荐生产环境)**:
```bash
# PostgreSQL: 使用 pg_dump 和 pg_restore
pg_dump -h source_host -U user -d source_db -F c -f backup.dump
pg_restore -h target_host -U user -d target_db -c backup.dump

# 或使用 pgloader (SQLite → PostgreSQL)
pgloader sqlite:///meeting_agent.db postgresql://user:pass@localhost/meeting_agent
```

**性能对比**:
| 方法 | 10万条记录 | 100万条记录 |
|------|-----------|------------|
| 循环 merge | ~30分钟 | 超时 |
| 批量插入 | ~2分钟 | ~20分钟 |
| pandas | ~1分钟 | ~10分钟 |
| pgloader | ~30秒 | ~5分钟 |

**建议**: 更新迁移文档，添加批量迁移方案

---

### 5. Schema 差异处理

**问题**: SQLite 宽松类型 vs PostgreSQL 严格类型。

**常见问题**:

**A. DateTime 格式**:
```python
# SQLite: 存储为字符串
created_at = "2026-01-14 10:30:00"

# PostgreSQL: 严格的 TIMESTAMP 类型
# 需要确保格式正确
```

**解决方案**:
```python
from datetime import datetime

# 统一使用 datetime 对象
task.created_at = datetime.now()  # ✅
task.created_at = "2026-01-14"    # ❌ 避免字符串
```

**B. JSON vs JSONB**:
```python
# SQLite: 存储为 TEXT
segments = Column(Text)  # JSON 字符串

# PostgreSQL: 使用 JSONB
from sqlalchemy.dialects.postgresql import JSONB
segments = Column(JSONB)  # 原生 JSON 类型
```

**C. Boolean 类型**:
```python
# SQLite: 存储为 0/1
is_corrected = Column(Boolean)  # 实际存储为 INTEGER

# PostgreSQL: 原生 BOOLEAN
is_corrected = Column(Boolean)  # 真正的 BOOLEAN 类型
```

**迁移时的类型转换**:
```python
def migrate_with_type_conversion():
    """迁移时处理类型差异"""
    tasks = source_session.query(Task).all()
    
    for task in tasks:
        # 确保 datetime 类型正确
        if isinstance(task.created_at, str):
            task.created_at = datetime.fromisoformat(task.created_at)
        
        # 确保 JSON 格式正确
        if isinstance(task.audio_files, str):
            task.audio_files = json.loads(task.audio_files)
        
        target_session.merge(task)
```

---

### 6. MySQL 特定问题

**问题**: MySQL 不支持原生 JSON 索引（不像 PostgreSQL 的 JSONB）。

**PostgreSQL JSONB 优势**:
```sql
-- PostgreSQL: 可以对 JSONB 字段创建索引
CREATE INDEX idx_artifact_type ON generated_artifacts 
USING GIN ((content->>'artifact_type'));

-- 高效查询
SELECT * FROM generated_artifacts 
WHERE content->>'artifact_type' = 'meeting_minutes';
```

**MySQL 限制**:
```sql
-- MySQL: JSON 字段不能直接索引
-- 需要使用虚拟列
ALTER TABLE generated_artifacts 
ADD COLUMN artifact_type_extracted VARCHAR(64) 
AS (JSON_UNQUOTE(JSON_EXTRACT(content, '$.artifact_type'))) STORED;

CREATE INDEX idx_artifact_type ON generated_artifacts(artifact_type_extracted);
```

**建议**: 
- 如果需要频繁查询 JSON 字段，优先选择 PostgreSQL
- 如果必须使用 MySQL，考虑将常查询的 JSON 字段提取为独立列

---

### 7. 缺少约束

**问题**: `state`、`artifact_type` 等字段是 String，易输入无效值。

**当前设计**:
```python
class Task(Base):
    state = Column(String(32))  # 可以是任意字符串
```

**改进方案 A: PostgreSQL ENUM**:
```python
from sqlalchemy import Enum as SQLEnum

class Task(Base):
    state = Column(
        SQLEnum(
            'pending', 'queued', 'running', 'transcribing',
            'identifying', 'correcting', 'summarizing',
            'success', 'failed', 'partial_success',
            name='task_state_enum'
        ),
        nullable=False,
        default='pending'
    )
```

**改进方案 B: CHECK 约束**:
```python
from sqlalchemy import CheckConstraint

class Task(Base):
    state = Column(String(32), nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'queued', 'running', 'transcribing', "
            "'identifying', 'correcting', 'summarizing', 'success', 'failed', 'partial_success')",
            name='check_task_state'
        ),
    )
```

**改进方案 C: 应用层验证 (当前方案)**:
```python
from pydantic import validator

class TaskCreate(BaseModel):
    state: str
    
    @validator('state')
    def validate_state(cls, v):
        allowed = ['pending', 'queued', 'running', ...]
        if v not in allowed:
            raise ValueError(f"Invalid state: {v}")
        return v
```

**建议**: 
- 短期: 保持应用层验证（已实现）
- 长期: 迁移到 PostgreSQL 后添加 ENUM 类型

---

### 8. 备份策略不完整

**问题**: 未提及自动化备份。

**改进方案**:

**A. 自动化 SQLite 备份 (cron)**:
```bash
#!/bin/bash
# backup_sqlite.sh

BACKUP_DIR="/backups/meeting-agent"
DB_FILE="meeting_agent.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份
sqlite3 $DB_FILE ".backup $BACKUP_DIR/meeting_agent_$TIMESTAMP.db"

# 压缩
gzip $BACKUP_DIR/meeting_agent_$TIMESTAMP.db

# 删除 7 天前的备份
find $BACKUP_DIR -name "*.db.gz" -mtime +7 -delete
```

**Crontab 配置**:
```cron
# 每天凌晨 2 点备份
0 2 * * * /path/to/backup_sqlite.sh
```

**B. PostgreSQL 自动备份**:
```bash
#!/bin/bash
# backup_postgres.sh

BACKUP_DIR="/backups/meeting-agent"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份 (添加 --no-owner 避免权限问题)
pg_dump -h localhost -U meeting_user -d meeting_agent \
    --no-owner --no-acl \
    -F c -f $BACKUP_DIR/meeting_agent_$TIMESTAMP.dump

# 删除 30 天前的备份
find $BACKUP_DIR -name "*.dump" -mtime +30 -delete
```

**C. 云备份 (AWS RDS)**:
```python
import boto3

def create_rds_snapshot():
    """创建 RDS 快照"""
    client = boto3.client('rds')
    
    snapshot_id = f"meeting-agent-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    response = client.create_db_snapshot(
        DBSnapshotIdentifier=snapshot_id,
        DBInstanceIdentifier='meeting-agent-prod'
    )
    
    return response['DBSnapshot']['DBSnapshotIdentifier']
```

---

## 其他最佳实践

### 9. 软删除

**当前设计**: 硬删除（CASCADE DELETE）

**改进方案**:
```python
class Task(Base):
    __tablename__ = "tasks"
    
    task_id = Column(String(64), primary_key=True)
    # ... 其他字段
    
    # 添加软删除字段
    deleted_at = Column(DateTime, nullable=True, default=None)
    deleted_by = Column(String(64), nullable=True)
    
    # 查询时自动过滤已删除记录
    @classmethod
    def active_query(cls, session):
        return session.query(cls).filter(cls.deleted_at.is_(None))

# Repository 中使用
class TaskRepository:
    def get_by_id(self, task_id: str) -> Optional[Task]:
        return Task.active_query(self.session).filter(
            Task.task_id == task_id
        ).first()
    
    def soft_delete(self, task_id: str, user_id: str):
        task = self.get_by_id(task_id)
        if task:
            task.deleted_at = datetime.now()
            task.deleted_by = user_id
            self.session.commit()
```

---

### 10. 多租户行级安全 (PostgreSQL)

**当前设计**: 应用层过滤 `tenant_id`

**改进方案 - Row Level Security**:
```sql
-- 启用 RLS
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- 创建策略：用户只能看到自己租户的数据
CREATE POLICY tenant_isolation ON tasks
FOR ALL
TO authenticated_user
USING (tenant_id = current_setting('app.current_tenant_id')::text);

-- 应用层设置租户上下文
SET app.current_tenant_id = 'tenant_123';

-- 查询自动过滤
SELECT * FROM tasks;  -- 只返回 tenant_123 的数据
```

---

## 实施优先级

### 高优先级 (MVP 后立即实施)
1. ✅ 环境变量管理密码
2. ✅ 批量迁移脚本
3. ✅ 自动化备份

### 中优先级 (生产环境前)
4. ⏳ 统一 ID 类型为 UUID
5. ⏳ 添加 ENUM/CHECK 约束
6. ⏳ 实现软删除
7. ⏳ full_text 触发器

### 低优先级 (优化阶段)
8. ⏳ 字段级加密
9. ⏳ Row Level Security
10. ⏳ JSONB 索引优化

---

## 总结

当前数据库设计适合 MVP 阶段，但在生产环境需要以下改进：

1. **安全性**: 环境变量 + Secrets Manager + 字段加密
2. **性能**: 批量迁移 + JSONB 索引 + 分区表
3. **可靠性**: 自动备份 + 软删除 + 约束
4. **一致性**: 触发器 + 事务 + 类型统一

建议在迁移到 PostgreSQL 时一并实施这些改进。
