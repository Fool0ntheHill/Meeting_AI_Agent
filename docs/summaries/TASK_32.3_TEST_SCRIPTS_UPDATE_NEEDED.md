# Task 32.3 补充 - 测试脚本 JWT 更新

## 问题描述

Task 32.3 标记为已完成，但实际上只更新了 API 路由文件的认证方式，**遗漏了测试脚本的更新**。

### 当前状态
- ✅ 所有 API 路由已更新为 JWT 认证
- ❌ 测试脚本仍使用旧的 API Key 认证
- ❌ 导致所有测试脚本返回 401 错误

### 错误示例
```
状态码: 401
响应: {"detail": "无效的 Token"}
```

## 需要更新的测试脚本

### 1. 衍生内容相关
- `scripts/test_artifacts_api.py` - 衍生内容管理 API 测试
- `scripts/test_task_confirmation_api.py` - 任务确认 API 测试

### 2. 修正相关
- `scripts/test_corrections_api.py` - 修正 API 测试

### 3. 热词相关
- `scripts/test_hotwords_api.py` - 热词管理 API 测试

### 4. 任务相关
- `scripts/test_task_api_unit.py` - 任务 API 单元测试
- `scripts/test_api_cache.py` - API 缓存测试
- `scripts/test_api_comprehensive.py` - 综合 API 测试

### 5. 其他
- `scripts/task24_checkpoint.py` - Task 24 检查点测试

## 修复方案

### 方案 1: 创建通用认证辅助函数（推荐）

创建 `scripts/auth_helper.py`:
```python
"""
测试脚本认证辅助函数
"""
import requests
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

def get_jwt_token(username: str = "test_user") -> str:
    """
    获取 JWT token
    
    Args:
        username: 用户名
        
    Returns:
        JWT token 字符串
        
    Raises:
        Exception: 登录失败
    """
    response = requests.post(
        f"{BASE_URL}/auth/dev/login",
        json={"username": username}
    )
    
    if response.status_code != 200:
        raise Exception(f"登录失败: {response.status_code} - {response.text}")
    
    data = response.json()
    return data["access_token"]


def get_auth_headers(username: str = "test_user") -> dict:
    """
    获取认证 headers
    
    Args:
        username: 用户名
        
    Returns:
        包含 Authorization header 的字典
    """
    token = get_jwt_token(username)
    return {"Authorization": f"Bearer {token}"}


# 全局 token 缓存（避免每次请求都登录）
_token_cache: Optional[str] = None

def get_cached_token(username: str = "test_user", force_refresh: bool = False) -> str:
    """
    获取缓存的 JWT token（如果不存在则登录）
    
    Args:
        username: 用户名
        force_refresh: 是否强制刷新 token
        
    Returns:
        JWT token 字符串
    """
    global _token_cache
    
    if _token_cache is None or force_refresh:
        _token_cache = get_jwt_token(username)
    
    return _token_cache
```

### 方案 2: 更新每个测试脚本

在每个测试脚本开头添加:
```python
# 旧代码
API_KEY = USER_ID
headers = {"Authorization": f"Bearer {API_KEY}"}

# 新代码
from auth_helper import get_auth_headers
headers = get_auth_headers()
```

## 实施步骤

### Step 1: 创建认证辅助函数
```bash
# 创建 scripts/auth_helper.py
```

### Step 2: 更新所有测试脚本
逐个更新上述 8 个测试脚本，替换认证方式

### Step 3: 验证测试脚本
```bash
# 启动 API 服务器
python main.py

# 在另一个终端运行测试
python scripts/test_artifacts_api.py
python scripts/test_corrections_api.py
python scripts/test_hotwords_api.py
# ... 其他测试脚本
```

### Step 4: 更新文档
- 更新 Task 32.3 完成状态
- 更新 API 使用指南
- 更新快速开始文档

## 预计工作量

- **创建辅助函数**: 30 分钟
- **更新 8 个测试脚本**: 1-2 小时
- **验证和测试**: 30 分钟
- **更新文档**: 30 分钟

**总计**: 2.5-3.5 小时

## 优先级

**建议优先级**: P1 (中等)

**理由**:
- 不影响核心功能（API 本身工作正常）
- 但影响开发体验（无法运行测试脚本）
- 应该在前端集成前完成（前端需要参考测试脚本）

## 建议执行时机

### 选项 1: 立即修复（推荐）
作为 Task 32.3 的补充，立即更新所有测试脚本

### 选项 2: 与 Task 29 合并
在 Phase 1 Task 29 (集成测试) 中统一更新

### 选项 3: 延后到前端集成前
在前端开始集成前必须完成

## 相关任务

- **Task 32.3**: 替换所有接口的认证方式（部分完成）
- **Task 29**: 集成测试（可以合并）
- **Task 25**: API 文档生成（需要更新示例）

## 总结

这是 Task 32.3 的一个遗漏项，需要补充完成。建议创建一个通用的认证辅助函数，然后更新所有测试脚本使用 JWT 认证。这样可以确保所有测试脚本正常工作，为后续的开发和前端集成做好准备。
