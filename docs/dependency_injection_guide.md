# 依赖注入指南

## 概述

本文档说明如何在 API 路由中使用依赖注入，避免硬编码具体的实现类。

## 为什么需要依赖注入？

### 问题：硬编码实现

❌ **不好的做法**：
```python
@router.post("/generate")
async def generate_artifact(...):
    # 硬编码 GeminiLLM
    from src.providers.gemini_llm import GeminiLLM
    from src.config.loader import get_config
    
    config = get_config()
    llm = GeminiLLM(config.gemini)  # 硬编码！
    result = await llm.generate(...)
```

**问题**：
1. 难以测试（无法 mock）
2. 难以切换实现（如果要换成 OpenAI）
3. 违反依赖倒置原则
4. 代码重复

### 解决方案：依赖注入

✅ **好的做法**：
```python
@router.post("/generate")
async def generate_artifact(
    llm: LLMProvider = Depends(get_llm_provider),  # 依赖注入！
    ...
):
    result = await llm.generate(...)
```

**优点**：
1. 易于测试（可以注入 mock）
2. 易于切换实现
3. 符合 SOLID 原则
4. 代码简洁

## 可用的依赖注入

### 1. 数据库会话

```python
from src.api.dependencies import get_db

@router.get("/tasks")
async def list_tasks(db: Session = Depends(get_db)):
    # db 会自动管理事务
    tasks = task_repo.list(db)
    return tasks
```

**特点**：
- 自动提交事务
- 自动回滚（出错时）
- 自动关闭连接

### 2. 用户认证

```python
from src.api.dependencies import verify_api_key

@router.get("/tasks")
async def list_tasks(user_id: str = Depends(verify_api_key)):
    # user_id 已验证
    tasks = get_user_tasks(user_id)
    return tasks
```

**特点**：
- 自动验证 Authorization 头
- 返回 user_id
- 认证失败自动返回 401

### 3. 租户 ID

```python
from src.api.dependencies import get_tenant_id

@router.get("/tasks")
async def list_tasks(tenant_id: str = Depends(get_tenant_id)):
    # tenant_id 已获取
    tasks = get_tenant_tasks(tenant_id)
    return tasks
```

**特点**：
- 自动从 user_id 获取 tenant_id
- 支持多租户隔离

### 4. LLM 提供商（新增）

```python
from src.api.dependencies import get_llm_provider
from src.core.providers import LLMProvider

@router.post("/generate")
async def generate_artifact(
    llm: LLMProvider = Depends(get_llm_provider),
):
    # llm 是 LLMProvider 接口
    result = await llm.generate(...)
    return result
```

**特点**：
- 返回 LLMProvider 接口（不是具体实现）
- 当前实现：GeminiLLM
- 未来可扩展：OpenAI, Claude, etc.

## 实际示例

### 示例 1：生成衍生内容

**文件**：`src/api/routes/artifacts.py`

```python
from fastapi import APIRouter, Depends
from src.api.dependencies import get_db, verify_api_key, get_llm_provider
from src.core.providers import LLMProvider

@router.post("/{task_id}/artifacts/{artifact_type}/generate")
async def generate_artifact(
    task_id: str,
    artifact_type: str,
    request: GenerateArtifactRequest,
    user_id: str = Depends(verify_api_key),      # 认证
    db: Session = Depends(get_db),                # 数据库
    llm: LLMProvider = Depends(get_llm_provider), # LLM
):
    # 验证任务存在
    task = task_repo.get_by_id(db, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(404)
    
    # 使用 LLM 生成内容
    result = await llm.generate(...)
    
    # 保存到数据库
    artifact_repo.create(db, result)
    
    return result
```

### 示例 2：测试时注入 Mock

```python
from fastapi.testclient import TestClient
from unittest.mock import Mock

# 创建 mock LLM
mock_llm = Mock(spec=LLMProvider)
mock_llm.generate.return_value = {"content": "test"}

# 覆盖依赖
app.dependency_overrides[get_llm_provider] = lambda: mock_llm

# 测试
client = TestClient(app)
response = client.post("/api/v1/tasks/123/artifacts/meeting_minutes/generate")
assert response.status_code == 200
```

## 如何添加新的依赖

### 步骤 1：在 dependencies.py 中定义

```python
# src/api/dependencies.py

def get_storage_client() -> StorageClient:
    """获取存储客户端"""
    config = get_config()
    return TOSClient(config.storage)
```

### 步骤 2：在路由中使用

```python
# src/api/routes/files.py

from src.api.dependencies import get_storage_client

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    storage: StorageClient = Depends(get_storage_client),
):
    url = await storage.upload(file)
    return {"url": url}
```

### 步骤 3：测试时 Mock

```python
# tests/test_files.py

mock_storage = Mock(spec=StorageClient)
app.dependency_overrides[get_storage_client] = lambda: mock_storage
```

## 依赖注入的层次

```
┌─────────────────────────────────────────┐
│         API 路由 (routes/)              │
│  - 使用 Depends() 注入依赖               │
│  - 不直接导入具体实现                    │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      依赖函数 (dependencies.py)          │
│  - 创建和配置具体实现                    │
│  - 返回接口类型                          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      具体实现 (providers/, services/)    │
│  - GeminiLLM, TOSClient, etc.           │
│  - 实现接口定义的方法                    │
└─────────────────────────────────────────┘
```

## 最佳实践

### 1. 返回接口而非实现

✅ **好**：
```python
def get_llm_provider() -> LLMProvider:  # 返回接口
    return GeminiLLM(config)
```

❌ **不好**：
```python
def get_llm_provider() -> GeminiLLM:  # 返回具体类
    return GeminiLLM(config)
```

### 2. 使用类型注解

✅ **好**：
```python
async def generate(
    llm: LLMProvider = Depends(get_llm_provider),  # 有类型注解
):
    ...
```

❌ **不好**：
```python
async def generate(
    llm = Depends(get_llm_provider),  # 没有类型注解
):
    ...
```

### 3. 避免在依赖函数中做业务逻辑

✅ **好**：
```python
def get_llm_provider() -> LLMProvider:
    config = get_config()
    return GeminiLLM(config)  # 只创建实例
```

❌ **不好**：
```python
def get_llm_provider() -> LLMProvider:
    config = get_config()
    llm = GeminiLLM(config)
    llm.validate()  # 不要在这里做业务逻辑
    llm.setup()
    return llm
```

### 4. 依赖可以依赖其他依赖

```python
def get_artifact_service(
    llm: LLMProvider = Depends(get_llm_provider),
    db: Session = Depends(get_db),
) -> ArtifactGenerationService:
    return ArtifactGenerationService(llm, db)
```

## 未来扩展

### 支持多 LLM 提供商

```python
def get_llm_provider(
    provider: str = Query("gemini"),  # 从请求参数选择
) -> LLMProvider:
    config = get_config()
    
    if provider == "gemini":
        return GeminiLLM(config.gemini)
    elif provider == "openai":
        return OpenAILLM(config.openai)
    elif provider == "claude":
        return ClaudeLLM(config.claude)
    else:
        raise HTTPException(400, f"Unknown provider: {provider}")
```

### 支持配置化选择

```python
def get_llm_provider() -> LLMProvider:
    config = get_config()
    
    # 从配置读取默认提供商
    provider = config.default_llm_provider
    
    if provider == "gemini":
        return GeminiLLM(config.gemini)
    elif provider == "openai":
        return OpenAILLM(config.openai)
    # ...
```

## 相关文档

- [FastAPI 依赖注入文档](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SOLID 原则](https://en.wikipedia.org/wiki/SOLID)
- [依赖倒置原则](https://en.wikipedia.org/wiki/Dependency_inversion_principle)

## 总结

依赖注入的优点：
- ✅ 代码解耦
- ✅ 易于测试
- ✅ 易于扩展
- ✅ 符合 SOLID 原则

使用方式：
1. 在 `dependencies.py` 中定义依赖函数
2. 在路由中使用 `Depends()` 注入
3. 测试时使用 `app.dependency_overrides` 覆盖

现在 `artifacts.py` 已经使用依赖注入，不再硬编码 `GeminiLLM`！
