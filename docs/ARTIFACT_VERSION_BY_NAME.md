# Artifact 版本号按名称累计 - 实现文档

## 背景

之前的版本号是按 `artifact_type` 累计的，导致：
- 用户创建不同名称的笔记时，版本号会继续累加（如"纪要 v2", "纪要 v3"）
- 前端需要硬编码 `artifact_type`，不够灵活
- 用户无法创建多个独立的笔记系列

## 新设计

**版本号按 `display_name` 累计**，而不是 `artifact_type`

### 核心逻辑

1. **版本号计算**：
   - 主键：`(task_id, display_name)`
   - 查询同一 task 下相同 `display_name` 的最大版本号，然后 +1
   - 不同名称的笔记有独立的版本序列

2. **字段说明**：
   - `display_name`：必填，用户输入的笔记名称
   - `artifact_type`：保留，用于模板选择和分类，但不影响版本号
   - `version`：版本号，按 `display_name` 累计

### 示例

```
Task: task_123

Artifacts:
1. display_name="会议纪要", artifact_type="meeting_minutes", version=1
2. display_name="会议纪要", artifact_type="meeting_minutes", version=2  ← 同名，版本+1
3. display_name="行动项", artifact_type="action_items", version=1      ← 不同名，新序列
4. display_name="行动项", artifact_type="action_items", version=2      ← 同名，版本+1
5. display_name="技术讨论", artifact_type="meeting_minutes", version=1  ← 不同名，新序列
```

## API 变更

### 生成 Artifact

**请求**：
```json
POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate

{
  "name": "会议纪要",  // 必填！
  "prompt_instance": {
    "template_id": "meeting_minutes_v1",
    "language": "zh-CN",
    "prompt_text": "..."
  }
}
```

**响应**：
```json
{
  "success": true,
  "artifact_id": "artifact_xxx",
  "version": 1,
  "display_name": "会议纪要",
  "content": {...}
}
```

### 重新生成 Artifact

**请求**：
```json
POST /api/v1/tasks/{task_id}/corrections/regenerate/{artifact_type}

{
  "name": "会议纪要",  // 必填！
  "prompt_instance": {
    "template_id": "meeting_minutes_v1",
    "language": "zh-CN",
    "prompt_text": "..."
  }
}
```

### 校验规则

- `name` 字段必填，不能为空或纯空格
- 前端需要在提交前校验
- 后端也会校验，返回 400 错误

## 前端改动

### 1. 生成/重新生成时传递 name

```typescript
// 生成新笔记
const response = await generateArtifact({
  taskId,
  artifactType,  // 仍然需要，用于模板选择
  name: values.meeting_type?.trim(),  // 必填！
  promptInstance: {...}
});

// 重新生成
const response = await regenerateArtifact({
  taskId,
  artifactType,
  name: currentArtifact.display_name,  // 使用当前名称
  promptInstance: {...}
});
```

### 2. Tab 标签显示

```typescript
// 使用 display_name + version
const tabLabel = `${artifact.display_name} v${artifact.version}`;

// 例如：
// "会议纪要 v1"
// "会议纪要 v2"
// "行动项 v1"
// "技术讨论 v1"
```

### 3. 重命名行为

**重要**：重命名后再生成会创建新的版本序列！

```typescript
// 原来：display_name="会议纪要", version=2
// 用户重命名为："技术讨论"
// 再生成时：display_name="技术讨论", version=1  ← 新序列！
```

需要在 UI 上给用户提示：
> "重命名后再生成会创建新的版本序列，是否继续？"

## 后端改动

### 1. API 路由

**文件**：`src/api/routes/artifacts.py`, `src/api/routes/corrections.py`

```python
# 校验 display_name 必填
if not request.name or not request.name.strip():
    raise HTTPException(
        status_code=400,
        detail="display_name (name) is required"
    )

display_name = request.name.strip()

# 获取当前最大版本号（按 display_name）
artifact_repo = ArtifactRepository(db)
existing_artifacts = artifact_repo.get_by_task_and_name(task.task_id, display_name)
max_version = max([a.version for a in existing_artifacts], default=0)
new_version = max_version + 1
```

### 2. Repository 新方法

**文件**：`src/database/repositories.py`

```python
def get_by_task_and_name(
    self,
    task_id: str,
    display_name: str,
) -> List[GeneratedArtifactRecord]:
    """获取任务指定名称的所有版本（用于版本号计算）"""
    return (
        self.session.query(GeneratedArtifactRecord)
        .filter(
            GeneratedArtifactRecord.task_id == task_id,
            GeneratedArtifactRecord.display_name == display_name,
        )
        .order_by(desc(GeneratedArtifactRecord.version))
        .all()
    )
```

## 数据迁移

### 运行迁移脚本

为旧数据添加默认的 `display_name`：

```bash
python scripts/migrate_add_default_display_names.py
```

### 迁移规则

- `meeting_minutes` → "会议纪要"
- `action_items` → "行动项"
- `summary_notes` → "摘要笔记"

### 兼容性

- 旧数据迁移后，版本号保持不变
- 新生成的 artifact 按新规则计算版本号
- 列表/详情接口返回 `display_name`，前端优先使用

## 测试要点

### 1. 基本功能

- [ ] 创建新笔记，指定名称 "会议纪要"，版本号为 1
- [ ] 再次生成同名笔记，版本号为 2
- [ ] 创建不同名称 "行动项"，版本号为 1（新序列）

### 2. 校验

- [ ] 不传 `name` 字段，返回 400 错误
- [ ] 传空字符串 `name: ""`，返回 400 错误
- [ ] 传纯空格 `name: "   "`，返回 400 错误

### 3. 重命名

- [ ] 重命名后再生成，创建新的版本序列
- [ ] 原名称的版本序列不受影响

### 4. 兼容性

- [ ] 旧数据迁移后，能正常显示和生成
- [ ] 列表接口返回 `display_name`
- [ ] 详情接口返回 `display_name`

## 注意事项

1. **前端必须传 name**：
   - 生成/重新生成时都要传
   - 不能为空或纯空格

2. **重命名影响**：
   - 重命名后再生成会创建新序列
   - 需要给用户明确提示

3. **artifact_type 保留**：
   - 仍然用于模板选择
   - 仍然用于分类和筛选
   - 只是不再影响版本号

4. **旧数据兼容**：
   - 运行迁移脚本补充默认名称
   - 或者在显示时回退到 artifact_type

## 相关文件

- `src/api/routes/artifacts.py` - 生成接口
- `src/api/routes/corrections.py` - 重新生成接口
- `src/database/repositories.py` - Repository 新方法
- `scripts/migrate_add_default_display_names.py` - 数据迁移脚本
- `docs/ARTIFACT_DISPLAY_NAME_GUIDE.md` - Display name 功能文档
