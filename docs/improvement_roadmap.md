# 项目改进路线图

## 文档版本
- 创建时间: 2026-01-14
- 基于用户建议整理

---

## 一、核心调整策略分析

### 1. 多租户 (Tenant) 配置化降级

**当前状态**: ✅ 已实现
- 代码层面: `tenant_id` 字段已在所有表中保留
- 数据库模型: `Task`, `HotwordSetRecord` 等都有 `tenant_id`
- Repository: 支持按 `tenant_id` 过滤

**实现建议**: 
```yaml
# config/development.yaml
app:
  default_tenant_id: "corp_default"
  multi_tenant_enabled: false  # Phase 1 关闭,Phase 2 开启
```

**行动计划**: 
- ⏳ **P1 优先级** - 在配置文件中添加 `DEFAULT_TENANT_ID`
- ⏳ **P1 优先级** - 在 API 依赖注入中自动填充 `tenant_id`
- ⏳ **P2 优先级** - 添加租户隔离中间件(当 `multi_tenant_enabled=true` 时启用)

**位置**: 
- 配置: `src/config/models.py` 添加 `default_tenant_id` 字段
- 中间件: `src/api/middleware.py` 添加 `TenantContextMiddleware`
- 依赖注入: `src/api/dependencies.py` 修改 `verify_api_key` 返回 `(user_id, tenant_id)`

---

### 2. 热词库 (Hotwords) 作用域简化

**当前状态**: ✅ 已实现多作用域
- 数据库: `scope` 字段支持 `global/tenant/user`
- API: 支持按 `scope` 过滤
- 代码: 保留了合并逻辑的能力

**实现建议**: 
```python
# src/services/transcription.py
def _get_hotwords(self, task: Task) -> List[str]:
    """获取热词列表 (优先级: User > Tenant > Global)"""
    # Phase 1: 只使用 Global
    global_hotwords = self.hotword_repo.get_by_scope("global")
    
    # Phase 2: 添加 User 级热词
    # user_hotwords = self.hotword_repo.get_by_scope("user", task.user_id)
    # return merge_hotwords(global_hotwords, user_hotwords)
    
    return global_hotwords
```

**行动计划**: 
- ✅ **已完成** - 数据库模型支持多作用域
- ✅ **已完成** - API 支持 CRUD
- ⏳ **P0 优先级** - 在 Task 18 中连接热词到 ASR (见下文)

---

### 3. 鉴权体系 (JWT Authentication)

**当前状态**: ⚠️ 部分实现
- 已有: `verify_api_key` 依赖注入
- 缺失: JWT 签发和验证逻辑
- 风险: 当前是简单的 API Key 验证,不包含用户信息

**实现建议**: 
```python
# src/api/routes/auth.py (新文件)
@router.post("/dev/login")
async def dev_login(username: str):
    """开发环境登录接口"""
    # 1. 查找或创建用户
    user = get_or_create_user(username)
    
    # 2. 签发 JWT
    payload = {
        "uid": user.user_id,
        "tenant_id": user.tenant_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    
    return {"access_token": token, "token_type": "bearer"}

# src/api/dependencies.py (修改)
def verify_jwt_token(token: str = Depends(oauth2_scheme)):
    """验证 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["uid"], payload["tenant_id"]
    except JWTError:
        raise HTTPException(401, "Invalid token")
```

**行动计划**: 
- 🟢 **P0 优先级** - 实现 JWT 签发接口 (`POST /api/v1/auth/dev/login`)
- 🟢 **P0 优先级** - 实现 JWT 验证中间件
- 🟢 **P0 优先级** - 替换所有 `verify_api_key` 为 `verify_jwt_token`
- ⏳ **P2 优先级** - 预留企微接口对接点

**位置**: 
- 新文件: `src/api/routes/auth.py`
- 修改: `src/api/dependencies.py`
- 配置: `src/config/models.py` 添加 `jwt_secret_key`

---

## 二、潜在风险与核心问题

### 1. 功能"空心化"风险 ⚠️

#### 问题 1.1: LLM 生成逻辑是占位符

**当前状态**: ⚠️ 确认存在
- Task 19: `regenerate_artifact` 返回 `{"placeholder": "Content generation not yet implemented"}`
- Task 22: `generate_artifact` 同样返回占位符
- 原因: 标记为 Phase 2,避免阻塞 MVP

**影响**: 
- 🔴 **严重** - 无法交付核心价值(会议摘要生成)
- 🔴 **严重** - 前端无法进行真实的集成测试

**解决方案**: 
```python
# src/services/artifact_generation.py (已存在,需要调用)
class ArtifactGenerationService:
    def generate(self, transcript: TranscriptionResult, prompt_instance: PromptInstance):
        # 1. 格式化转写文本
        formatted_text = self._format_transcript(transcript)
        
        # 2. 构建完整 Prompt
        full_prompt = self._build_prompt(prompt_instance, formatted_text)
        
        # 3. 调用 LLM (已实现但未连接)
        content = self.llm_provider.generate(full_prompt)
        
        return content
```

**行动计划**: 
- 🟢 **P0 优先级** - 在 Task 19/22 的端点中调用 `ArtifactGenerationService`
- 🟢 **P0 优先级** - 移除占位符逻辑
- 🟢 **P0 优先级** - 配置 Gemini API Key (已有 `GeminiLLM` 实现)

**位置**: 
- 修改: `src/api/routes/corrections.py` (regenerate_artifact 函数)
- 修改: `src/api/routes/artifacts.py` (generate_artifact 函数)
- 已有: `src/services/artifact_generation.py` (服务已实现)
- 已有: `src/providers/gemini_llm.py` (提供商已实现)

---

#### 问题 1.2: 热词未连接到 ASR

**当前状态**: ⚠️ 确认存在
- Task 20: 热词 CRUD API 已实现
- Task 18: 任务创建时未读取热词
- 原因: 两个任务独立开发,未连接

**影响**: 
- 🟡 **中等** - 热词功能无法生效
- 🟡 **中等** - ASR 准确率无法提升

**解决方案**: 
```python
# src/api/routes/tasks.py (修改 create_task)
@router.post("", response_model=CreateTaskResponse)
async def create_task(request: CreateTaskRequest, db: Session = Depends(get_db)):
    # ... 现有逻辑 ...
    
    # 🆕 读取热词
    hotword_repo = HotwordSetRepository(db)
    hotwords = []
    
    # 1. 读取全局热词
    global_sets = hotword_repo.get_by_scope("global", provider="volcano")
    for hs in global_sets:
        if hs.asr_language == task.asr_language:
            hotwords.append(hs.provider_resource_id)  # Volcano BoostingTableID
    
    # 2. 推送到队列时携带热词
    queue_manager.push_task({
        "task_id": task_id,
        "hotword_ids": hotwords,  # 🆕 添加热词 ID
        # ... 其他参数 ...
    })
```

**行动计划**: 
- 🟢 **P0 优先级** - 在 `create_task` 中读取热词
- 🟢 **P0 优先级** - 在 Worker 中将热词传递给 ASR 服务
- 🟢 **P0 优先级** - 在 `TranscriptionService` 中使用热词

**位置**: 
- 修改: `src/api/routes/tasks.py` (create_task 函数)
- 修改: `src/queue/worker.py` (process_task 函数)
- 修改: `src/services/transcription.py` (transcribe 方法)

---

#### 问题 1.3: 成本预估未适配不同模型

**当前状态**: ⚠️ 确认存在
- 当前: 硬编码价格 (ASR: 0.30, LLM: 0.40)
- 问题: 不同 LLM 模型价格差异大

**解决方案**: 
```python
# src/utils/cost.py (修改)
PRICING = {
    "asr": {
        "volcano": 0.0016,  # 元/分钟
        "azure": 0.0024,
    },
    "llm": {
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},  # 元/1K tokens
        "gpt-4": {"input": 0.21, "output": 0.42},
    },
    "voiceprint": {
        "iflytek": 0.002,  # 元/次
    }
}

def estimate_llm_cost(model: str, input_tokens: int, output_tokens: int):
    pricing = PRICING["llm"][model]
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000
```

**行动计划**: 
- 🟡 **P1 优先级** - 将价格配置化
- 🟡 **P1 优先级** - 根据实际使用的模型计算成本
- 🟡 **P1 优先级** - 在任务完成后记录实际成本

**位置**: 
- 修改: `src/utils/cost.py`
- 修改: `src/api/routes/tasks.py` (estimate_cost 端点)

---

### 2. 安全与架构规范风险 🔴

#### 问题 2.1: 身份传递不规范 (最大隐患)

**当前状态**: 🔴 **严重风险**
- 当前: `verify_api_key` 返回固定的 `user_id = "test_user"`
- 风险: 容易退化为 URL 参数传递 `?uid=admin`
- 后果: 未来接入企微时需要重构所有接口

**解决方案**: 见上文 "鉴权体系 (JWT Authentication)"

**行动计划**: 
- 🟢 **P0 优先级** - 立即实现 JWT 鉴权
- 🟢 **P0 优先级** - 禁止 URL 参数传递用户信息
- 🟢 **P0 优先级** - 所有接口统一使用 `Depends(verify_jwt_token)`

---

#### 问题 2.2: 越权访问 (IDOR)

**当前状态**: ⚠️ 部分实现
- 已有: 部分接口检查 `task.user_id != user_id`
- 缺失: 不是所有接口都有检查

**解决方案**: 
```python
# src/api/dependencies.py (新增)
def verify_task_ownership(
    task_id: str,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
) -> Task:
    """验证任务所有权"""
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(404, "任务不存在")
    
    if task.user_id != user_id:
        raise HTTPException(403, "无权访问此任务")
    
    return task

# 使用示例
@router.get("/{task_id}/status")
async def get_task_status(task: Task = Depends(verify_task_ownership)):
    return {"task_id": task.task_id, "state": task.state}
```

**行动计划**: 
- 🟡 **P1 优先级** - 创建 `verify_task_ownership` 依赖注入
- 🟡 **P1 优先级** - 在所有任务相关接口中使用
- 🟡 **P1 优先级** - 审计所有 GET/UPDATE 接口

**位置**: 
- 修改: `src/api/dependencies.py`
- 修改: `src/api/routes/tasks.py`
- 修改: `src/api/routes/corrections.py`
- 修改: `src/api/routes/artifacts.py`

---

### 3. 运维与架构风险

#### 问题 3.1: 数据库变更不可控

**当前状态**: ⚠️ 缺失
- 已有: SQLAlchemy ORM 模型
- 缺失: Alembic 迁移脚本
- 风险: 手动维护表结构,容易出错

**解决方案**: 
```bash
# 初始化 Alembic
alembic init alembic

# 生成初始迁移
alembic revision --autogenerate -m "Initial schema"

# 应用迁移
alembic upgrade head
```

**行动计划**: 
- 🟡 **P1 优先级** - 初始化 Alembic
- 🟡 **P1 优先级** - 生成当前数据库的基线迁移
- 🟡 **P1 优先级** - 为 Task 19.4 的新字段创建迁移脚本

**位置**: 
- 新目录: `alembic/` (迁移脚本)
- 新文件: `alembic.ini` (配置文件)
- 文档: `docs/database_migration_guide.md` (已存在,需更新)

---

#### 问题 3.2: 逻辑重叠

**当前状态**: ⚠️ 确认存在
- Task 19: 修正后可选重新生成
- Task 22: 直接生成新版本
- 问题: 两者都调用生成逻辑,但入口不同

**解决方案**: 
```python
# 统一的生成逻辑
class ArtifactGenerationService:
    def regenerate_for_task(
        self, 
        task_id: str, 
        artifact_type: str,
        prompt_instance: PromptInstance,
        reason: str = "manual"  # "correction" | "manual"
    ):
        """统一的重新生成入口"""
        # 1. 获取最新转写
        # 2. 调用 LLM
        # 3. 创建新版本
        # 4. 记录原因到 metadata
        pass

# Task 19 调用
service.regenerate_for_task(task_id, "meeting_minutes", prompt, reason="correction")

# Task 22 调用
service.regenerate_for_task(task_id, artifact_type, prompt, reason="manual")
```

**行动计划**: 
- 🟡 **P1 优先级** - 重构为统一的生成入口
- 🟡 **P1 优先级** - 在 metadata 中记录生成原因

**位置**: 
- 修改: `src/services/artifact_generation.py`

---

## 三、改进建议与行动计划

### 🟢 P0: 核心闭环与本地鉴权 (立即执行)

#### 1. 实现本地开发鉴权

**任务**: 
- [ ] 创建 `src/api/routes/auth.py`
- [ ] 实现 `POST /api/v1/auth/dev/login` 接口
- [ ] 实现 JWT 签发逻辑
- [ ] 修改 `src/api/dependencies.py` 添加 `verify_jwt_token`
- [ ] 替换所有 `verify_api_key` 为 `verify_jwt_token`
- [ ] 添加 JWT 配置到 `config/*.yaml`

**预计工作量**: 4-6 小时

**文件清单**: 
- 新增: `src/api/routes/auth.py`
- 修改: `src/api/dependencies.py`
- 修改: `src/config/models.py`
- 修改: 所有 API 路由文件

---

#### 2. 打通 LLM 真实调用

**任务**: 
- [ ] 在 `src/api/routes/corrections.py` 中调用 `ArtifactGenerationService`
- [ ] 在 `src/api/routes/artifacts.py` 中调用 `ArtifactGenerationService`
- [ ] 移除所有占位符逻辑
- [ ] 配置 Gemini API Key
- [ ] 测试端到端生成流程

**预计工作量**: 2-3 小时

**文件清单**: 
- 修改: `src/api/routes/corrections.py`
- 修改: `src/api/routes/artifacts.py`
- 修改: `config/test.yaml` (添加 Gemini API Key)

---

#### 3. 连接热词与 ASR

**任务**: 
- [ ] 在 `src/api/routes/tasks.py` 的 `create_task` 中读取热词
- [ ] 修改队列消息格式,添加 `hotword_ids` 字段
- [ ] 在 `src/queue/worker.py` 中传递热词到服务层
- [ ] 在 `src/services/transcription.py` 中使用热词调用 ASR
- [ ] 测试热词生效

**预计工作量**: 3-4 小时

**文件清单**: 
- 修改: `src/api/routes/tasks.py`
- 修改: `src/queue/worker.py`
- 修改: `src/services/transcription.py`

---

### 🟡 P1: 鲁棒性与数据安全 (下个迭代)

#### 1. 补全数据库迁移

**任务**: 
- [ ] 初始化 Alembic (`alembic init alembic`)
- [ ] 生成基线迁移 (`alembic revision --autogenerate -m "Initial schema"`)
- [ ] 为 Task 19.4 新字段创建迁移
- [ ] 更新 `docs/database_migration_guide.md`
- [ ] 添加迁移到 CI/CD 流程

**预计工作量**: 2-3 小时

---

#### 2. 完善所有权检查

**任务**: 
- [ ] 创建 `verify_task_ownership` 依赖注入
- [ ] 审计所有任务相关接口
- [ ] 替换手动检查为依赖注入
- [ ] 添加单元测试

**预计工作量**: 3-4 小时

---

#### 3. 实现速率限制

**任务**: 
- [ ] 集成 Redis 计数器
- [ ] 实现速率限制中间件
- [ ] 配置限流策略 (60 req/min per user)
- [ ] 添加限流响应 (429 Too Many Requests)

**预计工作量**: 2-3 小时

---

### ⚪ P2: 可观测性与体验 (上线前完成)

#### 1. 热词库治理

**任务**: 
- [ ] 添加热词数量上限校验 (1000 个)
- [ ] 添加热词去重逻辑
- [ ] 添加热词长度校验
- [ ] 添加热词格式校验

**预计工作量**: 2 小时

---

#### 2. 文档与 Swagger

**任务**: 
- [ ] 集成 Swagger UI (`/docs`)
- [ ] 添加所有接口的示例
- [ ] 添加认证说明
- [ ] 添加错误码文档

**预计工作量**: 2-3 小时

---

#### 3. 监控埋点

**任务**: 
- [ ] 记录 LLM 响应时间
- [ ] 记录 API 错误率
- [ ] 集成 Prometheus 指标
- [ ] 添加告警规则

**预计工作量**: 4-5 小时

---

## 四、总体时间估算

| 优先级 | 任务数 | 预计工作量 | 建议完成时间 |
|--------|--------|------------|--------------|
| P0 | 3 | 9-13 小时 | 本周内 |
| P1 | 3 | 7-10 小时 | 下周内 |
| P2 | 3 | 8-10 小时 | 上线前 |
| **总计** | **9** | **24-33 小时** | **2-3 周** |

---

## 五、风险评估

| 风险 | 严重程度 | 当前状态 | 缓解措施 |
|------|----------|----------|----------|
| 身份传递不规范 | 🔴 严重 | 未实现 JWT | P0 立即实现 |
| LLM 生成是占位符 | 🔴 严重 | 未连接服务 | P0 立即连接 |
| 热词未生效 | 🟡 中等 | 未连接 ASR | P0 立即连接 |
| 越权访问 | 🟡 中等 | 部分检查 | P1 完善检查 |
| 数据库迁移缺失 | 🟡 中等 | 无迁移脚本 | P1 初始化 Alembic |
| 成本预估不准 | 🟢 较低 | 硬编码价格 | P1 配置化 |

---

## 六、建议的实施顺序

### 第 1 周 (P0 任务)

**Day 1-2**: JWT 鉴权
- 实现 `/auth/dev/login` 接口
- 实现 JWT 验证中间件
- 替换所有接口的认证方式

**Day 3**: LLM 真实调用
- 连接 `ArtifactGenerationService`
- 移除占位符
- 端到端测试

**Day 4-5**: 热词连接
- 任务创建时读取热词
- Worker 传递热词
- ASR 使用热词

### 第 2 周 (P1 任务)

**Day 1-2**: 数据库迁移
- 初始化 Alembic
- 生成迁移脚本

**Day 3**: 所有权检查
- 创建依赖注入
- 审计所有接口

**Day 4-5**: 速率限制
- 实现限流中间件
- 测试限流效果

### 第 3 周 (P2 任务)

**Day 1**: 热词治理
**Day 2**: Swagger 文档
**Day 3-4**: 监控埋点
**Day 5**: 集成测试与上线准备

---

## 七、总结

用户的建议非常专业且切中要害。主要问题集中在:

1. **🔴 P0 核心功能缺失**: LLM 生成、热词连接、JWT 鉴权
2. **🟡 P1 安全隐患**: 越权访问、数据库迁移
3. **🟢 P2 体验优化**: 文档、监控、治理

建议按照 P0 → P1 → P2 的顺序逐步实施,预计 2-3 周可以完成所有改进。

**关键里程碑**:
- ✅ 第 1 周结束: 核心功能闭环,可以生成真实的会议摘要
- ✅ 第 2 周结束: 安全加固,可以进入测试环境
- ✅ 第 3 周结束: 生产就绪,可以上线

---

## 附录: 快速参考

### 当前已完成的任务
- ✅ Task 18: 任务创建 API
- ✅ Task 19: 修正与重新生成 API (含 19.4 确认)
- ✅ Task 20: 热词管理 API
- ✅ Task 21: 提示词模板管理 API
- ✅ Task 22: 衍生内容管理 API
- ✅ Task 23: 鉴权与中间件 (基础版)

### 需要立即实施的任务 (P0)
1. JWT 鉴权 (4-6h)
2. LLM 真实调用 (2-3h)
3. 热词连接 ASR (3-4h)

### 相关文档
- [数据库迁移指南](./database_migration_guide.md)
- [API 实现总结](../API_IMPLEMENTATION_SUMMARY.md)
- [任务列表](.kiro/specs/meeting-minutes-agent/tasks.md)
