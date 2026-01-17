# Task 27.1 完成总结: 审计日志实现

## 完成时间
2026-01-14

## 任务概述
实现审计日志系统，记录所有关键操作，包括任务创建/更新、API 调用、成本使用、热词管理、提示词模板管理等。

## 实现内容

### 1. 数据库模型

#### AuditLogRecord 表
```python
class AuditLogRecord(Base):
    """审计日志表"""
    
    # 主键
    log_id = Column(String(64), primary_key=True)
    
    # 操作信息
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(64), nullable=False, index=True)
    
    # 用户信息
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    
    # 操作详情 (JSON)
    details = Column(Text, nullable=True)
    
    # 成本信息
    cost_amount = Column(Float, nullable=True)
    cost_currency = Column(String(8), nullable=True, default="USD")
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
```

**索引设计**:
- `idx_audit_user_created`: (user_id, created_at) - 按用户查询
- `idx_audit_tenant_created`: (tenant_id, created_at) - 按租户查询
- `idx_audit_action_created`: (action, created_at) - 按操作类型查询
- `idx_audit_resource`: (resource_type, resource_id) - 按资源查询

### 2. AuditLogger 类

#### 核心方法
1. **任务审计**
   - `log_task_created()` - 记录任务创建
   - `log_task_updated()` - 记录任务更新
   - `log_task_confirmed()` - 记录任务确认

2. **衍生内容审计**
   - `log_artifact_generated()` - 记录衍生内容生成

3. **API 调用审计**
   - `log_api_call()` - 记录 API 调用（成功/失败）

4. **成本审计**
   - `log_cost_usage()` - 记录成本使用

5. **热词管理审计**
   - `log_hotword_created()` - 记录热词集创建
   - `log_hotword_deleted()` - 记录热词集删除

6. **提示词模板审计**
   - `log_template_created()` - 记录模板创建
   - `log_template_updated()` - 记录模板更新
   - `log_template_deleted()` - 记录模板删除

### 3. AuditLogRepository 类

#### 查询方法
1. **按用户查询**
   - `get_by_user()` - 获取用户的审计日志
   - 支持按 action 和 resource_type 过滤
   - 支持分页 (limit, offset)

2. **按租户查询**
   - `get_by_tenant()` - 获取租户的审计日志
   - 支持相同的过滤和分页

3. **按资源查询**
   - `get_by_resource()` - 获取特定资源的审计日志
   - 用于追踪单个资源的操作历史

4. **成本汇总**
   - `get_cost_summary()` - 获取成本汇总
   - 支持按用户或租户汇总
   - 返回总成本和货币单位

## 使用示例

### 1. 记录任务创建
```python
from src.utils.audit import AuditLogger

audit_logger = AuditLogger(session)

log_id = audit_logger.log_task_created(
    task_id="task-123",
    user_id="user-456",
    tenant_id="tenant-789",
    details={
        "meeting_type": "daily_standup",
        "audio_files": ["file1.ogg", "file2.ogg"],
        "asr_language": "zh-CN+en-US",
    }
)
```

### 2. 记录 API 调用
```python
# 成功的 API 调用
audit_logger.log_api_call(
    provider="gemini",
    api_name="generate_content",
    user_id="user-123",
    tenant_id="tenant-456",
    task_id="task-789",
    success=True,
    details={"duration_ms": 1500, "tokens": 1000}
)

# 失败的 API 调用
audit_logger.log_api_call(
    provider="volcano",
    api_name="submit_transcription",
    user_id="user-123",
    tenant_id="tenant-456",
    success=False,
    details={"error": "rate_limit", "retry_after": 60}
)
```

### 3. 记录成本使用
```python
audit_logger.log_cost_usage(
    task_id="task-123",
    user_id="user-456",
    tenant_id="tenant-789",
    cost_amount=0.05,
    cost_currency="USD",
    details={
        "asr_cost": 0.02,
        "llm_cost": 0.03,
        "duration_seconds": 300,
    }
)
```

### 4. 查询审计日志
```python
from src.database.repositories import AuditLogRepository

repo = AuditLogRepository(session)

# 获取用户的所有任务创建日志
logs = repo.get_by_user(
    user_id="user-123",
    action="task_created",
    limit=50
)

# 获取特定任务的所有操作历史
logs = repo.get_by_resource(
    resource_type="task",
    resource_id="task-123"
)

# 获取用户的成本汇总
summary = repo.get_cost_summary(user_id="user-123")
print(f"Total cost: ${summary['total_cost']:.2f}")
```

## 测试覆盖

### 单元测试 (26 个)
✅ 所有测试通过

**测试类别**:

1. **AuditLogger 测试** (20 个)
   - 任务审计 (3 个)
     - 任务创建
     - 任务更新
     - 任务确认
   
   - 衍生内容审计 (1 个)
     - 衍生内容生成
   
   - API 调用审计 (2 个)
     - 成功的 API 调用
     - 失败的 API 调用
   
   - 成本审计 (2 个)
     - 记录成本使用
     - 使用默认货币
   
   - 热词管理审计 (2 个)
     - 热词集创建
     - 热词集删除
   
   - 提示词模板审计 (3 个)
     - 模板创建
     - 模板更新
     - 模板删除
   
   - 边界情况 (7 个)
     - 不带详细信息
     - 带空详细信息
     - 带复杂详细信息
     - 带中文字符
     - 多次记录生成不同 ID
     - 不带任务 ID 的 API 调用

2. **AuditLogRepository 测试** (6 个)
   - 按用户查询 (2 个)
   - 按租户查询 (1 个)
   - 按资源查询 (1 个)
   - 成本汇总 (2 个)

## 文件清单

### 新增文件
1. `src/utils/audit.py` - AuditLogger 实现 (300+ 行)
2. `tests/unit/test_utils_audit.py` - 单元测试 (400+ 行)

### 修改文件
1. `src/database/models.py` - 添加 AuditLogRecord 模型
2. `src/database/repositories.py` - 添加 AuditLogRepository

## 技术亮点

### 1. 灵活的详细信息存储
使用 JSON 字段存储操作详情，支持任意结构的数据：
- 嵌套对象
- 数组
- 中文字符
- 自动序列化/反序列化

### 2. 多维度索引
设计了 4 个复合索引，支持高效查询：
- 按用户 + 时间
- 按租户 + 时间
- 按操作类型 + 时间
- 按资源类型 + 资源 ID

### 3. 成本追踪
内置成本字段，方便统计和分析：
- 单条记录的成本
- 按用户/租户汇总
- 支持多种货币

### 4. 统一的日志接口
所有操作都通过 AuditLogger 记录，保证一致性：
- 自动生成唯一 ID
- 自动记录时间戳
- 统一的日志格式

### 5. 类型安全
使用枚举和常量定义操作类型：
- `task_created`, `task_updated`, `task_confirmed`
- `artifact_generated`
- `api_call`
- `cost_usage`
- `hotword_created`, `hotword_deleted`
- `template_created`, `template_updated`, `template_deleted`

## 集成建议

### 1. 在 API 路由中集成
```python
from src.utils.audit import AuditLogger

@router.post("/api/v1/tasks")
async def create_task(
    request: TaskCreateRequest,
    user_id: str = Depends(verify_jwt_token),
    session: Session = Depends(get_session),
):
    # 创建任务
    task = task_repo.create(...)
    
    # 记录审计日志
    audit_logger = AuditLogger(session)
    audit_logger.log_task_created(
        task_id=task.task_id,
        user_id=user_id,
        tenant_id=task.tenant_id,
        details={
            "meeting_type": request.meeting_type,
            "audio_files": request.audio_files,
        }
    )
    
    session.commit()
    return task
```

### 2. 在 Worker 中集成
```python
# 记录 API 调用
audit_logger.log_api_call(
    provider="volcano",
    api_name="submit_transcription",
    user_id=task.user_id,
    tenant_id=task.tenant_id,
    task_id=task.task_id,
    success=True,
    details={"duration_seconds": audio_duration}
)

# 记录成本
audit_logger.log_cost_usage(
    task_id=task.task_id,
    user_id=task.user_id,
    tenant_id=task.tenant_id,
    cost_amount=total_cost,
    details={
        "asr_cost": asr_cost,
        "llm_cost": llm_cost,
        "voiceprint_cost": voiceprint_cost,
    }
)
```

### 3. 添加审计日志查询 API
```python
@router.get("/api/v1/audit-logs")
async def get_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(verify_jwt_token),
    session: Session = Depends(get_session),
):
    repo = AuditLogRepository(session)
    logs = repo.get_by_user(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )
    return logs

@router.get("/api/v1/cost-summary")
async def get_cost_summary(
    user_id: str = Depends(verify_jwt_token),
    session: Session = Depends(get_session),
):
    repo = AuditLogRepository(session)
    summary = repo.get_cost_summary(user_id=user_id)
    return summary
```

## 下一步建议

### 1. 数据库迁移
创建 Alembic 迁移脚本添加 `audit_logs` 表：
```bash
alembic revision --autogenerate -m "Add audit_logs table"
alembic upgrade head
```

### 2. 集成到现有代码
在以下位置添加审计日志：
- `src/api/routes/tasks.py` - 任务创建/更新/确认
- `src/api/routes/artifacts.py` - 衍生内容生成
- `src/api/routes/hotwords.py` - 热词管理
- `src/api/routes/prompt_templates.py` - 模板管理
- `src/queue/worker.py` - API 调用和成本记录

### 3. 添加日志保留策略
定期清理旧的审计日志：
```python
def cleanup_old_audit_logs(session: Session, days: int = 90):
    """删除 90 天前的审计日志"""
    cutoff_date = datetime.now() - timedelta(days=days)
    session.query(AuditLogRecord).filter(
        AuditLogRecord.created_at < cutoff_date
    ).delete()
    session.commit()
```

### 4. 添加审计日志导出
支持导出审计日志为 CSV 或 JSON：
```python
@router.get("/api/v1/audit-logs/export")
async def export_audit_logs(
    format: str = "csv",  # csv or json
    user_id: str = Depends(verify_jwt_token),
    session: Session = Depends(get_session),
):
    repo = AuditLogRepository(session)
    logs = repo.get_by_user(user_id=user_id, limit=10000)
    
    if format == "csv":
        return generate_csv(logs)
    else:
        return generate_json(logs)
```

### 5. 添加实时审计日志流
使用 WebSocket 推送实时审计日志：
```python
@router.websocket("/ws/audit-logs")
async def audit_logs_stream(
    websocket: WebSocket,
    user_id: str = Depends(verify_jwt_token),
):
    await websocket.accept()
    # 订阅审计日志事件
    # 推送新的审计日志到客户端
```

## 性能考虑

### 1. 异步写入
审计日志写入不应阻塞主流程：
```python
# 使用后台任务异步写入
background_tasks.add_task(
    audit_logger.log_task_created,
    task_id=task_id,
    user_id=user_id,
    tenant_id=tenant_id,
)
```

### 2. 批量写入
高并发场景下使用批量写入：
```python
# 收集多条日志
logs = []
for operation in operations:
    logs.append(create_audit_log(...))

# 批量插入
session.bulk_save_objects(logs)
session.commit()
```

### 3. 分区表
数据量大时考虑按时间分区：
```sql
-- 按月分区
CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

## 总结

Task 27.1 成功实现了完整的审计日志系统：
- ✅ 26 个单元测试全部通过
- ✅ 支持 10+ 种操作类型
- ✅ 灵活的 JSON 详细信息存储
- ✅ 多维度查询支持
- ✅ 成本追踪和汇总
- ✅ 完善的索引设计

这为系统提供了完整的操作审计能力，满足合规性要求和问题追踪需求。

**测试统计**:
- 总测试数: 198 (172 + 26)
- 通过率: 100%
- 新增代码: ~700 行
- 测试代码: ~400 行

**下一步**: Task 27.2 (可选) - 编写属性测试

---

**完成时间**: 2026-01-14  
**实现者**: Kiro AI Assistant  
**状态**: ✅ 完成
