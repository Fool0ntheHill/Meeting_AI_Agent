# 说话人姓名显示功能完成总结

## 用户需求

**问题**：逐字稿显示 `Speaker 1`、`Speaker 2`，期望显示真实姓名 `林煜东`、`蓝为一`。

**解决方案**：后端返回 `speaker_mapping` 字段，前端自动替换显示。

## 实现方案

### 数据流

```
声纹识别 -> speaker_mappings 表 -> speakers 表 -> API 返回 -> 前端显示
```

1. **声纹识别**：识别出 `speaker_linyudong`、`speaker_lanweiyi`
2. **保存映射**：`Speaker 1` -> `speaker_linyudong`
3. **关联姓名**：`speaker_linyudong` -> `林煜东`
4. **API 返回**：`{"Speaker 1": "林煜东"}`
5. **前端显示**：自动替换为真实姓名

### 后端实现

#### 1. 新增 speakers 表

```sql
CREATE TABLE speakers (
    speaker_id VARCHAR(64) PRIMARY KEY,      -- speaker_linyudong
    display_name VARCHAR(128) NOT NULL,      -- 林煜东
    tenant_id VARCHAR(64) NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### 2. Pipeline 保存 speaker mapping

`src/services/pipeline.py`：
```python
# 声纹识别后保存到数据库
if self.speaker_mappings is not None and speaker_mapping:
    for speaker_label, speaker_id in speaker_mapping.items():
        self.speaker_mappings.create_or_update(
            task_id=task_id,
            speaker_label=speaker_label,  # "Speaker 1"
            speaker_name=speaker_id,      # "speaker_linyudong"
            speaker_id=speaker_id,
        )
```

#### 3. API 返回真实姓名

`src/api/routes/tasks.py` - `get_transcript`：
```python
# 获取 speaker mapping
speaker_mapping_repo = SpeakerMappingRepository(db)
speaker_repo = SpeakerRepository(db)

task_mappings = speaker_mapping_repo.get_by_task_id(task.task_id)

speaker_mapping = {}
for mapping in task_mappings:
    display_name = speaker_repo.get_display_name(mapping.speaker_id)
    if display_name:
        speaker_mapping[mapping.speaker_label] = display_name

return TranscriptResponse(
    ...
    speaker_mapping=speaker_mapping  # {"Speaker 1": "林煜东"}
)
```

### 前端适配

**前端已完成适配，无需修改！**

`task.ts` 中已实现：
```typescript
const speakerMap = rawSpeakerMap && typeof rawSpeakerMap === 'object'
  ? Object.fromEntries(
      Object.entries(rawSpeakerMap).map(([key, value]) => 
        [key, typeof value === 'string' ? value : key]
      )
    )
  : null

// 自动替换 speaker 显示
speaker: speakerMap
  ? String(speakerMap[String(seg.speaker ?? '')] ?? seg.speaker ?? 'Speaker')
  : String(seg.speaker ?? 'Speaker')
```

### API 响应格式

```json
{
  "task_id": "task_xxx",
  "segments": [
    {
      "text": "大家好",
      "speaker": "Speaker 1",
      ...
    }
  ],
  "speaker_mapping": {
    "Speaker 1": "林煜东",
    "Speaker 2": "蓝为一"
  },
  ...
}
```

## 部署清单

### 1. 数据库迁移

```bash
python scripts/migrate_add_speakers_table.py
```

**结果**：
- ✅ 创建 speakers 表
- ✅ 插入测试数据（林煜东、蓝为一）

### 2. 重启服务

```bash
# 重启 Worker
python worker.py

# 重启 Backend（如果已运行）
python main.py
```

### 3. 测试验证

```bash
python scripts/test_speaker_mapping.py
```

**预期结果**：
- ✅ speakers 表包含 2 个说话人
- ✅ API 返回 `speaker_mapping` 字段
- ✅ 前端自动显示真实姓名

## 文件修改清单

### 新增文件
- `src/database/models.py` - Speaker 模型
- `src/database/repositories.py` - SpeakerRepository
- `scripts/migrate_add_speakers_table.py` - 迁移脚本
- `scripts/test_speaker_mapping.py` - 测试脚本
- `scripts/fix_task_user_id.py` - 修复旧任务 user_id
- `scripts/check_task_user.py` - 检查任务 user_id
- `docs/SPEAKER_NAME_MAPPING_GUIDE.md` - 完整指南
- `docs/summaries/SPEAKER_NAME_MAPPING_IMPLEMENTATION.md` - 实现总结

### 修改文件
- `src/services/pipeline.py` - 保存 speaker mapping
- `src/queue/worker.py` - 传递 speaker_mapping_repo
- `src/api/routes/tasks.py` - 返回 speaker_mapping
- `src/api/schemas.py` - 添加 speaker_mapping 字段
- `docs/WORKSPACE_API_INTEGRATION.md` - 更新文档

## 测试结果

### 数据库测试

```
找到 2 个说话人：
  - speaker_linyudong -> 林煜东
  - speaker_lanweiyi -> 蓝为一

批量获取结果：
  - speaker_lanweiyi -> 蓝为一
  - speaker_linyudong -> 林煜东
```

### API 测试

```
GET /api/v1/tasks/{task_id}/transcript
Status: 200

speaker_mapping 字段：
  类型: <class 'dict'>
  内容:
    - Speaker 1 -> 林煜东
    - Speaker 2 -> 蓝为一
```

## 注意事项

### 1. 旧任务无法显示真实姓名

**原因**：旧任务没有 speaker mapping 数据。

**解决方案**：
- 方案 A：重新运行任务
- 方案 B：编写脚本从 transcript 恢复映射（但无法恢复真实姓名）

### 2. speakers 表需要预先配置

**当前状态**：迁移脚本已插入测试数据。

**生产环境**：需要导入真实的说话人数据。

**管理方式**：
```python
from src.database.session import session_scope
from src.database.repositories import SpeakerRepository

with session_scope() as session:
    speaker_repo = SpeakerRepository(session)
    speaker_repo.create_or_update(
        speaker_id="speaker_zhangsan",
        display_name="张三",
        tenant_id="default",
        created_by="admin"
    )
```

### 3. 前端无需修改

前端已在 `task.ts` 中实现自动替换逻辑，支持：
- `speaker_mapping`
- `speaker_map`
- `speakerMap`

只要后端返回任一字段，前端会自动使用。

## 未来改进

1. **说话人管理 API**
   - 提供 CRUD 接口管理 speakers 表
   - 支持用户自定义说话人姓名

2. **手动修正功能**
   - 允许用户在前端修正说话人姓名
   - 更新 speaker_mappings 表的 `is_corrected` 标记

3. **说话人库导入**
   - 支持批量导入说话人数据
   - 支持从 CSV/Excel 导入

4. **多租户隔离**
   - 确保不同租户的说话人数据隔离
   - 支持租户级别的说话人管理

5. **说话人头像**
   - 在 speakers 表中添加头像字段
   - 前端显示说话人头像

## 总结

### 完成状态

- ✅ 后端实现完成
- ✅ 前端已适配（无需修改）
- ✅ 数据库迁移脚本已准备
- ✅ 测试脚本已验证
- ✅ 文档已更新

### 部署状态

- ⚠️ 需要运行数据库迁移
- ⚠️ 需要重启 Worker
- ⚠️ 需要重启 Backend
- ⚠️ 旧任务无法显示真实姓名

### 前端状态

- ✅ 无需任何修改
- ✅ 自动适配新 API 格式
- ✅ 支持多种字段名

### 下一步

1. 运行迁移脚本：`python scripts/migrate_add_speakers_table.py`
2. 重启 Worker：`python worker.py`
3. 重启 Backend：`python main.py`
4. 创建新任务测试
5. 验证前端显示真实姓名

**前端开发者无需任何操作**，只要后端部署完成，新任务会自动显示真实姓名。
