# Worker Artifact 生成错误修复

**日期**: 2026-01-27  
**状态**: ✅ 已完成

## 问题描述

Worker 在执行任务时，artifact 生成阶段失败，错误信息：

```
ArtifactRepository.create() got an unexpected keyword argument 'display_name'
```

### 失败任务示例

- **task_dfe2e046652246ef**: 转写、声纹识别、校正都成功，但在 summarizing 阶段失败
- 音频时长: 479.09s
- Segments: 122 个
- 识别出 2 个说话人: 林煜东、蓝为一

## 根本原因

在 `src/services/artifact_generation.py` 第 196 行调用 `ArtifactRepository.create()` 时传入了 `display_name` 参数：

```python
self.artifacts.create(
    artifact_id=artifact.artifact_id,
    task_id=artifact.task_id,
    artifact_type=artifact.artifact_type,
    version=artifact.version,
    prompt_instance=...,
    content=artifact.content,
    created_by=artifact.created_by,
    metadata=artifact.metadata,
    display_name=display_name,  # ❌ 这个参数不被接受
    state="success",
)
```

但 `ArtifactRepository.create()` 方法的签名中没有 `display_name` 参数：

```python
def create(
    self,
    artifact_id: str,
    task_id: str,
    artifact_type: str,
    version: int,
    prompt_instance: Dict,
    content: Dict,
    created_by: str,
    metadata: Optional[Dict] = None,
    state: str = "success",
) -> GeneratedArtifactRecord:
```

### 为什么会出现这个问题？

1. **数据库模型支持 display_name**: `GeneratedArtifactRecord` 模型确实有 `display_name` 字段
2. **Repository 方法未更新**: 但 `create()` 方法的参数列表没有包含这个字段
3. **调用方已经在使用**: `artifact_generation.py` 已经在传递这个参数

## 修复方案

### 修改文件: `src/database/repositories.py`

在 `ArtifactRepository.create()` 方法中添加 `display_name` 参数：

```python
def create(
    self,
    artifact_id: str,
    task_id: str,
    artifact_type: str,
    version: int,
    prompt_instance: Dict,
    content: Dict,
    created_by: str,
    metadata: Optional[Dict] = None,
    display_name: Optional[str] = None,  # ✅ 新增参数
    state: str = "success",
) -> GeneratedArtifactRecord:
    """创建生成内容记录"""
    record = GeneratedArtifactRecord(
        artifact_id=artifact_id,
        task_id=task_id,
        artifact_type=artifact_type,
        version=version,
        prompt_instance=json.dumps(prompt_instance, ensure_ascii=False),
        content=json.dumps(content, ensure_ascii=False),
        artifact_metadata=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        created_by=created_by,
        display_name=display_name,  # ✅ 传递给模型
        state=state,
    )
    self.session.add(record)
    self.session.flush()
    logger.info(f"Artifact created: {artifact_id} for task {task_id} with state={state}, display_name={display_name}")
    return record
```

### 关键改动

1. **添加参数**: `display_name: Optional[str] = None`
2. **传递给模型**: `display_name=display_name`
3. **更新日志**: 记录 display_name 信息

## 验证

### 检查最近任务

运行 `scripts/verify_artifact_generation_fix.py` 查看任务状态：

```
Task ID: task_dfe2e046652246ef
  State: failed
  Error: ArtifactRepository.create() got an unexpected keyword argument 'display_name'
  Artifacts: None

Task ID: task_dadac03a8f3048ef
  State: success
  Artifacts: 3
    - artifact_8a01d23267d14ca2: meeting_minutes v1 (success)
      Display Name: 测试
    - artifact_f81daa89cf3f4848: meeting_minutes v1 (success)
      Display Name: 纪要
```

### 预期效果

修复后，新任务应该能够：
1. ✅ 成功传递 `display_name` 参数
2. ✅ 在数据库中正确保存 display_name
3. ✅ 完成 artifact 生成流程
4. ✅ 任务状态更新为 `success`

## 影响范围

### 受影响的功能

1. **同步 artifact 生成**: Pipeline 生成第一版纪要时会传递 `display_name="纪要"`
2. **异步 artifact 生成**: 用户手动生成新 artifact 时可以指定 display_name
3. **版本号计算**: 基于 display_name 计算版本号（同名 artifact 递增）

### 向后兼容性

- ✅ `display_name` 是可选参数（默认 None）
- ✅ 不影响现有代码（没有传递 display_name 的调用仍然有效）
- ✅ 数据库字段已存在（不需要迁移）

## 相关文件

- `src/database/repositories.py` - 修复 create() 方法签名
- `src/services/artifact_generation.py` - 调用方（已经在使用 display_name）
- `src/database/models.py` - 数据库模型（已有 display_name 字段）
- `scripts/verify_artifact_generation_fix.py` - 验证脚本

## 后续步骤

1. ✅ 修复已完成
2. ⏳ 等待新任务测试（用户上传音频后自动测试）
3. ⏳ 监控 worker 日志确认无错误
4. ⏳ 验证 display_name 正确保存到数据库

## 总结

这是一个简单的参数不匹配问题：
- **原因**: Repository 方法签名缺少 `display_name` 参数
- **修复**: 添加参数并传递给模型
- **影响**: 修复后 artifact 生成流程可以正常完成
- **风险**: 低（向后兼容，只是添加可选参数）
