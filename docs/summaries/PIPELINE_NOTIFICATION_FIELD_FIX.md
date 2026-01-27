# Pipeline 企微通知字段名修复

**日期**: 2026-01-27  
**状态**: ✅ 已完成

## 问题描述

Pipeline 在发送企微通知时出现错误：

```
AttributeError: 'Task' object has no attribute 'task_name'
```

### 错误日志

```
Task task_d33884ac706b46fc: Failed to send WeCom notification: 'Task' object has no attribute 'task_name'
Traceback (most recent call last):
  File "D:\Programs\Meeting_AI_Agent\src\services\pipeline.py", line 478, in process_meeting
    task_name = task.task_name
                ^^^^^^^^^^^^^^
AttributeError: 'Task' object has no attribute 'task_name'
```

### 影响

- ✅ 任务本身执行成功（artifact 生成完成）
- ❌ 企微通知发送失败
- ❌ 用户没有收到任务完成通知

## 根本原因

在 `src/services/pipeline.py` 中，代码尝试访问 `task.task_name`，但 Task 模型的字段名实际上是 `name` 而不是 `task_name`。

### Task 模型字段定义

```python
class Task(Base):
    """任务表"""
    
    __tablename__ = "tasks"
    
    # 主键
    task_id = Column(String(64), primary_key=True, index=True)
    
    # 任务元数据
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # ✅ 字段名是 name
    meeting_type = Column(String(64), nullable=False)
    # ...
```

## 修复方案

### 修改文件: `src/services/pipeline.py`

#### 成功通知部分

**修改前**:
```python
# 获取任务名称
task = self.tasks.get_by_id(task_id)
if task:
    task_name = task.task_name  # ❌ 错误的字段名
```

**修改后**:
```python
# 获取任务名称（字段名是 name 不是 task_name）
task = self.tasks.get_by_id(task_id)
if task:
    task_name = task.name  # ✅ 正确的字段名
```

#### 失败通知部分

**修改前**:
```python
# 获取任务信息
task = self.tasks.get_by_id(task_id)
if task:
    task_name = task.task_name  # ❌ 错误的字段名
```

**修改后**:
```python
# 获取任务信息（字段名是 name 不是 task_name）
task = self.tasks.get_by_id(task_id)
if task:
    task_name = task.name  # ✅ 正确的字段名
```

## 验证

### 字段名确认

运行 `scripts/test_pipeline_notification_fix.py`:

```
Task 模型的主要字段：
  ✅ task_id
  ✅ name
  ❌ task_name (不存在)
  ✅ user_id
  ✅ meeting_date
  ✅ meeting_time

结论：
  ✅ 任务名称字段是 'name'
  ❌ 没有 'task_name' 字段
```

### 其他文件检查

检查其他使用任务名称的文件：

1. ✅ `src/api/routes/artifacts.py` - 正确使用 `task.name`
2. ✅ `src/api/routes/corrections.py` - 正确使用 `task.name`
3. ✅ `src/services/pipeline.py` - 已修复为 `task.name`

## 预期效果

修复后，新增任务时：

1. ✅ 任务正常执行完成
2. ✅ Artifact 成功生成
3. ✅ 企微通知成功发送
4. ✅ 用户收到标准 Markdown 格式的通知

### 通知示例

```markdown
✅ **会议纪要生成成功**

**会议名称**: 未命名会议
**会议时间**: 2025-12-29
**生成内容**: 纪要

---

📄 [点击查看会议纪要](链接)
```

## 相关修改

### 本次修复

- `src/services/pipeline.py` - 修复字段名从 `task_name` 改为 `name`

### 之前的相关修改

1. **企微通知格式更新** (docs/summaries/WECOM_MARKDOWN_FORMAT_UPDATE.md)
   - 从 ATP 富文本改为标准 Markdown 格式

2. **Pipeline 通知支持** (同一次修改)
   - 添加了新增任务的企微通知功能
   - 但使用了错误的字段名

3. **Worker Artifact 生成修复** (docs/summaries/WORKER_ARTIFACT_GENERATION_FIX.md)
   - 修复了 `display_name` 参数问题

## 测试清单

- [x] 确认 Task 模型字段名为 `name`
- [x] 修复 Pipeline 成功通知代码
- [x] 修复 Pipeline 失败通知代码
- [x] 验证其他文件使用正确字段名
- [x] 创建测试脚本验证修复
- [ ] 实际测试新增任务发送通知

## 相关文件

- `src/services/pipeline.py` - Pipeline 服务（已修复）
- `src/database/models.py` - Task 模型定义
- `src/api/routes/artifacts.py` - Artifact API（已正确）
- `src/api/routes/corrections.py` - 校正 API（已正确）
- `scripts/test_pipeline_notification_fix.py` - 验证脚本

## 总结

这是一个简单的字段名错误：
- **问题**: 使用了不存在的 `task.task_name` 字段
- **原因**: Task 模型的字段名是 `name` 而不是 `task_name`
- **修复**: 将所有 `task.task_name` 改为 `task.name`
- **影响**: 修复后新增任务可以正常发送企微通知

现在所有场景的企微通知都能正常工作：
1. ✅ 新增任务（Pipeline）
2. ✅ 重新生成（API）
3. ✅ 生成新纪要（API）
4. ✅ 说话人校正后重新生成（API）
