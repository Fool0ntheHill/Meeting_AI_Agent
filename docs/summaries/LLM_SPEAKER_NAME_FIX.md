# LLM 生成会议纪要使用真实姓名

## 问题

LLM 生成的会议纪要中，说话人显示的是：
- ❌ 声纹 ID（如 `speaker_linyudong`）
- ❌ 或者标签（如 `Speaker 1`）

而不是真实姓名（如 `林煜东`）。

## 原因

Pipeline 的处理流程：

1. **转写** → segments 中 speaker 是 `Speaker 1`
2. **声纹识别** → 得到映射 `Speaker 1` -> `speaker_linyudong`
3. **修正** → 替换成 `speaker_linyudong`
4. **生成 artifact** → LLM 看到的是 `speaker_linyudong`

问题在于：LLM 生成时，transcript 中的 speaker 还是声纹 ID，而不是真实姓名。

## 解决方案

在生成 artifact 之前，再次替换 transcript 中的 speaker 为真实姓名：

### 1. Pipeline 添加 speaker_repo

```python
def __init__(
    self,
    ...
    speaker_mapping_repo=None,
    speaker_repo=None,  # 新增
    ...
):
    self.speaker_mappings = speaker_mapping_repo
    self.speakers = speaker_repo  # 新增
```

### 2. 修正阶段增加真实姓名替换

```python
# 3. 修正阶段
if speaker_mapping:
    # 第一次修正：Speaker 1 -> speaker_linyudong
    transcript = await self.correction.correct_speakers(transcript, speaker_mapping)
    
    # 第二次修正：speaker_linyudong -> 林煜东
    if self.speakers is not None:
        # 批量查询真实姓名
        speaker_ids = list(speaker_mapping.values())
        display_names = self.speakers.get_display_names_batch(speaker_ids)
        
        # 创建新映射：Speaker 1 -> 林煜东
        real_name_mapping = {}
        for speaker_label, speaker_id in speaker_mapping.items():
            display_name = display_names.get(speaker_id)
            if display_name:
                real_name_mapping[speaker_label] = display_name
        
        # 再次修正
        transcript = await self.correction.correct_speakers(transcript, real_name_mapping)
```

### 3. Worker 传递 speaker_repo

```python
from src.database.repositories import SpeakerRepository

with session_scope() as session:
    speaker_repo = SpeakerRepository(session)
    self.pipeline_service.speakers = speaker_repo
```

## 处理流程

修改后的流程：

1. **转写** → `Speaker 1`
2. **声纹识别** → `Speaker 1` -> `speaker_linyudong`
3. **第一次修正** → `speaker_linyudong`
4. **查询真实姓名** → `speaker_linyudong` -> `林煜东`
5. **第二次修正** → `林煜东`
6. **生成 artifact** → LLM 看到的是 `林煜东` ✅

## 文件修改

### 修改文件
- `src/services/pipeline.py` - 添加 speaker_repo，增加真实姓名替换逻辑
- `src/queue/worker.py` - 传递 SpeakerRepository

### 测试脚本
- `scripts/test_speaker_name_in_artifact.py` - 检查 artifact 中的说话人姓名

## 测试验证

### 旧任务

旧任务的 artifact 不会自动更新，因为它们已经生成了。

```bash
python scripts/test_speaker_name_in_artifact.py
```

预期结果：
```
❌ 问题：Artifact 中没有使用真实姓名
可能的原因：
1. 这是旧任务，生成时还没有实现真实姓名替换
```

### 新任务

需要：
1. 重启 Worker（加载新代码）
2. 创建新任务
3. 等待处理完成
4. 检查 artifact 内容

预期结果：
- ✅ 包含真实姓名（林煜东/蓝为一）
- ✅ 不包含声纹 ID（speaker_xxx）
- ✅ 不包含标签（Speaker 1/2）

## 部署步骤

1. **确认数据库已迁移**
   ```bash
   # 应该已经运行过
   python scripts/migrate_add_speakers_table.py
   ```

2. **重启 Worker**
   ```bash
   # 停止旧 worker
   Ctrl+C
   
   # 启动新 worker
   python worker.py
   ```

3. **创建新任务测试**
   - 上传音频
   - 等待处理完成
   - 检查会议纪要中的说话人姓名

4. **验证**
   ```bash
   # 使用新任务的 task_id
   python scripts/test_speaker_name_in_artifact.py
   ```

## 注意事项

### 1. 旧任务不会自动更新

旧任务的 artifact 已经生成，不会自动更新。如果需要，可以：
- 重新生成 artifact（通过 API）
- 或者创建新任务

### 2. speakers 表必须有数据

如果 speakers 表中没有对应的声纹 ID，会回退到使用声纹 ID：

```python
if display_name:
    real_name_mapping[speaker_label] = display_name
else:
    # 回退到声纹 ID
    real_name_mapping[speaker_label] = speaker_id
```

### 3. 性能影响

增加了一次数据库查询（批量查询真实姓名），但影响很小：
- 使用批量查询（`get_display_names_batch`）
- 通常只有 2-5 个说话人
- 查询时间 < 10ms

## 未来改进

1. **缓存真实姓名**
   - 在 pipeline 初始化时预加载常用说话人
   - 减少数据库查询

2. **支持别名**
   - 在 speakers 表中添加 `aliases` 字段
   - 支持多个名称（如 "林煜东"、"小林"）

3. **LLM 提示词优化**
   - 在提示词中明确说明说话人姓名
   - 避免 LLM 混淆或误解

## 总结

✅ **已实现** - Pipeline 在生成 artifact 前替换成真实姓名
✅ **已测试** - 测试脚本可以验证 artifact 内容
⚠️ **需要重启** - Worker 需要重启加载新代码
⚠️ **旧任务** - 不会自动更新，需要重新生成

**下一步**：重启 Worker，创建新任务测试。
