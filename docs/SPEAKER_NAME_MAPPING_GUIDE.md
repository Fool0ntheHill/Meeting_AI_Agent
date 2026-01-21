# 说话人姓名映射功能指南

## 问题描述

**现状**：逐字稿显示的是 `Speaker 1`、`Speaker 2` 这样的标签，而不是真实姓名。

**期望**：显示真实姓名，如 `林煜东`、`蓝为一`。

## 解决方案

### 架构设计

```
声纹识别 -> speaker_mappings 表 -> speakers 表 -> API 返回真实姓名 -> 前端显示
```

1. **声纹识别**：识别出声纹 ID（如 `speaker_linyudong`）
2. **speaker_mappings 表**：存储任务级别的映射（`Speaker 1` -> `speaker_linyudong`）
3. **speakers 表**：存储声纹 ID 到真实姓名的映射（`speaker_linyudong` -> `林煜东`）
4. **API 返回**：自动关联并返回真实姓名
5. **前端显示**：使用 `speaker_mapping` 替换显示

### 数据库结构

#### speakers 表（新增）

存储声纹 ID 到真实姓名的全局映射：

```sql
CREATE TABLE speakers (
    speaker_id VARCHAR(64) PRIMARY KEY,      -- 声纹 ID，如 speaker_linyudong
    display_name VARCHAR(128) NOT NULL,      -- 真实姓名，如 "林煜东"
    tenant_id VARCHAR(64) NOT NULL,          -- 租户 ID
    created_by VARCHAR(64) NOT NULL,         -- 创建者
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

#### speaker_mappings 表（已存在，现在会被使用）

存储任务级别的说话人映射：

```sql
CREATE TABLE speaker_mappings (
    mapping_id INTEGER PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,            -- 任务 ID
    speaker_label VARCHAR(64) NOT NULL,      -- "Speaker 1", "Speaker 2"
    speaker_name VARCHAR(128) NOT NULL,      -- 声纹 ID（如 speaker_linyudong）
    speaker_id VARCHAR(64),                  -- 声纹 ID（冗余字段）
    confidence FLOAT,                        -- 识别置信度
    is_corrected BOOLEAN DEFAULT FALSE,
    ...
);
```

### 后端实现

#### 1. Pipeline 保存 speaker mapping

修改 `src/services/pipeline.py`：

```python
# 声纹识别后保存映射
if self.speaker_mappings is not None and speaker_mapping:
    for speaker_label, speaker_id in speaker_mapping.items():
        self.speaker_mappings.create_or_update(
            task_id=task_id,
            speaker_label=speaker_label,  # "Speaker 1"
            speaker_name=speaker_id,      # "speaker_linyudong"
            speaker_id=speaker_id,
        )
```

#### 2. API 返回真实姓名

修改 `src/api/routes/tasks.py` 的 `get_transcript` 端点：

```python
# 获取 speaker mapping
speaker_mapping_repo = SpeakerMappingRepository(db)
speaker_repo = SpeakerRepository(db)

task_mappings = speaker_mapping_repo.get_by_task_id(task.task_id)

speaker_mapping = {}
for mapping in task_mappings:
    # 查询真实姓名
    display_name = speaker_repo.get_display_name(mapping.speaker_id)
    if display_name:
        speaker_mapping[mapping.speaker_label] = display_name
    else:
        speaker_mapping[mapping.speaker_label] = mapping.speaker_id

return TranscriptResponse(
    ...
    speaker_mapping=speaker_mapping  # {"Speaker 1": "林煜东", "Speaker 2": "蓝为一"}
)
```

#### 3. API 响应格式

`GET /api/v1/tasks/{task_id}/transcript` 现在返回：

```json
{
  "task_id": "task_xxx",
  "segments": [
    {
      "text": "大家好",
      "start_time": 0.0,
      "end_time": 1.5,
      "speaker": "Speaker 1",  // 原始标签
      "confidence": null
    }
  ],
  "speaker_mapping": {
    "Speaker 1": "林煜东",  // 真实姓名
    "Speaker 2": "蓝为一"
  },
  "full_text": "...",
  "duration": 479.09,
  "language": "zh-CN",
  "provider": "volcano"
}
```

### 前端实现

前端已经实现了自动替换逻辑（在 `task.ts` 中）：

```typescript
const rawSpeakerMap = asRecord.speaker_mapping ?? 
                      asRecord.speaker_map ?? 
                      asRecord.speakerMap ?? 
                      undefined

const speakerMap = rawSpeakerMap && typeof rawSpeakerMap === 'object'
  ? Object.fromEntries(
      Object.entries(rawSpeakerMap).map(([key, value]) => 
        [key, typeof value === 'string' ? value : key]
      )
    )
  : null

// 在构建 segments 时使用映射
speaker: speakerMap
  ? String(speakerMap[String(seg.speaker ?? '')] ?? seg.speaker ?? 'Speaker')
  : String(seg.speaker ?? 'Speaker')
```

**前端无需修改**，只要后端返回 `speaker_mapping` 字段，前端会自动使用。

### 部署步骤

#### 1. 运行数据库迁移

```bash
python scripts/migrate_add_speakers_table.py
```

这会：
- 创建 `speakers` 表
- 插入测试数据（`speaker_linyudong` -> `林煜东`，`speaker_lanweiyi` -> `蓝为一`）

#### 2. 重启 Worker

```bash
# 停止旧 worker
Ctrl+C

# 启动新 worker
python worker.py
```

新 worker 会使用更新后的代码，保存 speaker mapping 到数据库。

#### 3. 重启 Backend API（可选）

如果后端已经在运行，需要重启以加载新的 API 代码：

```bash
# 停止旧 backend
Ctrl+C

# 启动新 backend
python main.py
```

#### 4. 运行新任务

旧任务没有 speaker mapping 数据，需要运行新任务来测试：

```bash
# 上传音频并创建任务
# Worker 会自动处理并保存 speaker mapping
```

### 测试验证

#### 1. 检查数据库

```bash
python scripts/test_speaker_mapping.py
```

预期输出：
```
找到 2 个说话人：
  - speaker_linyudong -> 林煜东
  - speaker_lanweiyi -> 蓝为一

任务 task_xxx 的 speaker mappings：
  - Speaker 1 -> speaker_linyudong (ID: speaker_linyudong)
  - Speaker 2 -> speaker_lanweiyi (ID: speaker_lanweiyi)

speaker_mapping 字段：
  类型: <class 'dict'>
  内容:
    - Speaker 1 -> 林煜东
    - Speaker 2 -> 蓝为一
```

#### 2. 测试 API

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/tasks/{task_id}/transcript
```

检查响应中的 `speaker_mapping` 字段。

### 管理说话人姓名

#### 添加新说话人

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

#### 更新说话人姓名

```python
with session_scope() as session:
    speaker_repo = SpeakerRepository(session)
    speaker_repo.create_or_update(
        speaker_id="speaker_linyudong",
        display_name="林煜东（更新后）",
        tenant_id="default",
        created_by="admin"
    )
```

### 常见问题

#### Q: 旧任务能显示真实姓名吗？

A: 不能。旧任务没有保存 speaker mapping 数据。需要重新运行任务。

#### Q: 如何批量更新旧任务？

A: 可以编写脚本从 transcript 的 segments 中提取 speaker 信息，然后创建 speaker_mappings 记录。但这只能恢复声纹 ID，无法恢复真实姓名（除非有其他数据源）。

#### Q: 前端需要修改吗？

A: 不需要。前端已经实现了自动替换逻辑，只要后端返回 `speaker_mapping` 字段即可。

#### Q: 如果 speakers 表中没有某个声纹 ID 怎么办？

A: API 会返回声纹 ID 本身（如 `speaker_linyudong`），前端会显示这个 ID。

#### Q: 如何支持用户自定义说话人姓名？

A: 可以通过以下方式：
1. **方案 A**：提供 API 让用户创建/更新 speakers 表中的记录
2. **方案 B**：在 speaker_mappings 表中添加 `is_corrected` 标记，允许用户手动修正
3. **方案 C**：在前端维护本地映射表（不推荐，数据不持久化）

推荐使用方案 A + B 的组合。

### 未来改进

1. **说话人管理 API**：提供 CRUD 接口管理 speakers 表
2. **手动修正功能**：允许用户在前端修正说话人姓名
3. **说话人库导入**：支持批量导入说话人数据
4. **多租户隔离**：确保不同租户的说话人数据隔离
5. **说话人头像**：在 speakers 表中添加头像字段

## 总结

- ✅ 后端已实现完整的说话人姓名映射功能
- ✅ 前端已实现自动替换逻辑
- ✅ 数据库迁移脚本已准备好
- ⚠️ 需要重启 worker 和 backend
- ⚠️ 旧任务无法显示真实姓名（需要重新运行）
- 📝 新任务会自动保存并返回真实姓名

**下一步**：运行迁移脚本，重启服务，创建新任务测试。
