# 数据库层使用指南

## 快速开始

### 1. 初始化数据库

```python
from src.database.session import init_db

# SQLite (开发环境)
init_db("sqlite:///./meeting_agent.db")

# PostgreSQL (生产环境)
init_db("postgresql://user:password@localhost:5432/meeting_agent")
```

### 2. 使用 Session

#### 方式 A: 上下文管理器(推荐)

```python
from src.database.session import session_scope
from src.database.repositories import TaskRepository

with session_scope() as session:
    task_repo = TaskRepository(session)
    task = task_repo.create(
        task_id="task_001",
        user_id="user_123",
        tenant_id="tenant_456",
        meeting_type="common",
        audio_files=["meeting.ogg"],
        file_order=[0],
    )
    # 自动提交或回滚
```

#### 方式 B: 手动管理

```python
from src.database.session import get_session
from src.database.repositories import TaskRepository

session = get_session()
try:
    task_repo = TaskRepository(session)
    task = task_repo.create(...)
    session.commit()
except Exception as e:
    session.rollback()
    raise
finally:
    session.close()
```

## Repository 使用示例

### TaskRepository (任务管理)

```python
from src.database.session import session_scope
from src.database.repositories import TaskRepository

with session_scope() as session:
    task_repo = TaskRepository(session)
    
    # 创建任务
    task = task_repo.create(
        task_id="task_001",
        user_id="user_123",
        tenant_id="tenant_456",
        meeting_type="common",
        audio_files=["meeting.ogg"],
        file_order=[0],
    )
    
    # 查询任务
    task = task_repo.get_by_id("task_001")
    
    # 更新状态
    task_repo.update_state(
        task_id="task_001",
        state="transcribing",
        progress=50.0,
    )
    
    # 获取用户任务列表
    tasks = task_repo.get_by_user("user_123", limit=10)
```

### TranscriptRepository (转写记录)

```python
from src.database.session import session_scope
from src.database.repositories import TranscriptRepository
from src.core.models import TranscriptionResult, Segment

with session_scope() as session:
    transcript_repo = TranscriptRepository(session)
    
    # 创建转写结果
    transcript_result = TranscriptionResult(
        segments=[
            Segment(
                text="大家好",
                start_time=0.0,
                end_time=1.5,
                speaker="Speaker 0",
                confidence=0.95,
            )
        ],
        full_text="大家好",
        duration=1.5,
        language="zh-CN",
        provider="volcano",
    )
    
    record = transcript_repo.create(
        transcript_id="transcript_001",
        task_id="task_001",
        transcript_result=transcript_result,
    )
    
    # 查询转写记录
    record = transcript_repo.get_by_task_id("task_001")
    
    # 转换为 TranscriptionResult
    result = transcript_repo.to_transcription_result(record)
```

### SpeakerMappingRepository (说话人映射)

```python
from src.database.session import session_scope
from src.database.repositories import SpeakerMappingRepository

with session_scope() as session:
    speaker_repo = SpeakerMappingRepository(session)
    
    # 创建或更新映射
    speaker_repo.create_or_update(
        task_id="task_001",
        speaker_label="Speaker 0",
        speaker_name="张三",
        speaker_id="speaker_linyudong",
        confidence=0.65,
    )
    
    # 获取映射字典
    mapping = speaker_repo.get_mapping_dict("task_001")
    # {"Speaker 0": "张三", "Speaker 1": "李四"}
    
    # 人工修正
    speaker_repo.create_or_update(
        task_id="task_001",
        speaker_label="Speaker 0",
        speaker_name="王五",
        is_corrected=True,
        corrected_by="user_123",
    )
```

### ArtifactRepository (生成内容)

```python
from src.database.session import session_scope
from src.database.repositories import ArtifactRepository
from src.core.models import MeetingMinutes, PromptInstance

with session_scope() as session:
    artifact_repo = ArtifactRepository(session)
    
    # 创建会议纪要
    meeting_minutes = MeetingMinutes(
        title="产品规划会议",
        participants=["张三", "李四"],
        summary="讨论了 Q2 产品路线图",
        key_points=["确定核心功能", "分析用户反馈"],
        action_items=["张三负责整理报告"],
    )
    
    prompt_instance = PromptInstance(
        template_id="tpl_001",
        language="zh-CN",
        parameters={},
    )
    
    record = artifact_repo.create(
        artifact_id="artifact_001",
        task_id="task_001",
        artifact_type="meeting_minutes",
        version=1,
        prompt_instance=prompt_instance,
        content=meeting_minutes.model_dump_json(),
        created_by="user_123",
    )
    
    # 查询最新版本
    latest = artifact_repo.get_latest_by_task("task_001", "meeting_minutes")
    
    # 转换为 GeneratedArtifact
    artifact = artifact_repo.to_generated_artifact(latest)
    minutes = artifact.get_meeting_minutes()
```

### PromptTemplateRepository (提示词模板)

```python
from src.database.session import session_scope
from src.database.repositories import PromptTemplateRepository

with session_scope() as session:
    template_repo = PromptTemplateRepository(session)
    
    # 创建模板
    template = template_repo.create(
        template_id="tpl_001",
        title="标准会议纪要",
        prompt_body="你是一个专业的会议纪要助手...",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN", "en-US"],
        parameter_schema={
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
            }
        },
        description="生成标准会议纪要",
        is_system=True,
    )
    
    # 查询模板
    template = template_repo.get_by_id("tpl_001")
    
    # 按类型查询
    templates = template_repo.get_by_type("meeting_minutes")
    
    # 获取所有系统模板
    system_templates = template_repo.get_all(is_system=True)
```

## 数据模型关系

```
Task (任务)
  ├── TranscriptRecord (转写记录) [1:1]
  ├── SpeakerMapping (说话人映射) [1:N]
  └── GeneratedArtifactRecord (生成内容) [1:N]

PromptTemplateRecord (提示词模板) [独立表]
```

## 事务管理

### 自动事务(推荐)

```python
with session_scope() as session:
    # 所有操作在同一个事务中
    task_repo = TaskRepository(session)
    task = task_repo.create(...)
    
    transcript_repo = TranscriptRepository(session)
    transcript = transcript_repo.create(...)
    
    # 自动提交
```

### 手动事务

```python
session = get_session()
try:
    # 操作 1
    task_repo = TaskRepository(session)
    task = task_repo.create(...)
    
    # 操作 2
    transcript_repo = TranscriptRepository(session)
    transcript = transcript_repo.create(...)
    
    # 手动提交
    session.commit()
except Exception as e:
    # 回滚
    session.rollback()
    raise
finally:
    session.close()
```

## 查询优化

### 预加载关联数据

```python
from sqlalchemy.orm import joinedload

with session_scope() as session:
    # 预加载转写记录和说话人映射
    task = (
        session.query(Task)
        .options(
            joinedload(Task.transcripts),
            joinedload(Task.speaker_mappings),
        )
        .filter(Task.task_id == "task_001")
        .first()
    )
    
    # 访问关联数据不会触发额外查询
    transcripts = task.transcripts
    mappings = task.speaker_mappings
```

### 批量操作

```python
with session_scope() as session:
    # 批量插入
    tasks = [
        Task(task_id=f"task_{i}", user_id="user_123", ...)
        for i in range(100)
    ]
    session.bulk_save_objects(tasks)
```

## 测试

### 使用内存数据库

```python
from src.database.session import init_db, session_scope

# 测试时使用内存数据库
init_db("sqlite:///:memory:")

with session_scope() as session:
    # 测试代码
    pass
```

### 测试隔离

```python
import pytest
from src.database.session import init_db, get_engine
from src.database.models import Base

@pytest.fixture(scope="function")
def db_session():
    """每个测试函数使用独立的数据库"""
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    from src.database.session import get_session
    session = get_session(engine)
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)
```

## 最佳实践

1. **始终使用 Repository 模式**
   - 不要直接操作 SQLAlchemy 模型
   - 通过 Repository 封装所有数据库操作

2. **使用上下文管理器**
   - 优先使用 `session_scope()` 确保事务正确提交/回滚
   - 避免忘记关闭 session

3. **避免 N+1 查询**
   - 使用 `joinedload()` 预加载关联数据
   - 使用 `selectinload()` 处理大量关联数据

4. **合理使用索引**
   - 为常用查询字段创建索引
   - 避免过度索引影响写入性能

5. **数据库连接管理**
   - 开发环境使用 SQLite
   - 生产环境使用 PostgreSQL
   - 通过环境变量配置数据库 URL

## 更多信息

- [数据库迁移指南](../../docs/database_migration_guide.md)
- [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/)
- [PostgreSQL 最佳实践](https://wiki.postgresql.org/wiki/Don%27t_Do_This)
