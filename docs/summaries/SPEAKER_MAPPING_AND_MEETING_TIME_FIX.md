# 说话人映射和会议时间传递修复

## 问题描述

用户报告了两个问题：

1. **说话人名称问题**：生成新笔记时，LLM 看到的是 `speaker1`、`speaker2` 等原始标签，而不是真实的说话人名称（如 `speaker_linyudong`、`speaker_lanweiyi`）
2. **会议时间缺失**：重新生成时看不到会议时间

## 根本原因

### 问题 1: 说话人映射未应用

**原因**：`gemini_llm.py` 中的 `format_transcript` 方法直接使用 `segment.speaker`，这是 ASR 返回的原始标签（speaker1, speaker2），没有应用数据库中的说话人映射。

**数据流**：
```
ASR 转写 → TranscriptionResult (segments 包含 speaker1, speaker2)
                ↓
        format_transcript() 直接使用 segment.speaker
                ↓
        LLM 看到 speaker1, speaker2 ❌
```

**正确的数据流应该是**：
```
ASR 转写 → TranscriptionResult (segments 包含 speaker1, speaker2)
                ↓
        从数据库获取 SpeakerMapping (speaker1 → 张三)
                ↓
        format_transcript(transcript, speaker_mapping) 应用映射
                ↓
        LLM 看到真实姓名 ✅
```

### 问题 2: 会议时间传递

**原因**：虽然 API 路由已经传递了 `meeting_date` 和 `meeting_time`，但需要确保在所有生成路径中都正确传递。

## 解决方案

### 1. 修改 `format_transcript` 方法支持说话人映射

**文件**: `src/providers/gemini_llm.py`

```python
def format_transcript(
    self, 
    transcript: TranscriptionResult,
    speaker_mapping: Optional[Dict[str, str]] = None
) -> str:
    """
    格式化转写文本
    
    Args:
        transcript: 转写结果
        speaker_mapping: 说话人映射字典 (可选)，格式: {"speaker1": "张三", "speaker2": "李四"}
                       如果提供，会将原始标签替换为真实姓名

    Returns:
        str: 格式化后的文本
    """
    if not transcript.segments:
        return ""

    lines = []
    for segment in transcript.segments:
        # 获取说话人名称
        raw_speaker = segment.speaker or "未知说话人"
        
        # 如果提供了映射，尝试替换为真实姓名
        if speaker_mapping and raw_speaker in speaker_mapping:
            speaker = speaker_mapping[raw_speaker]
            logger.debug(f"Mapped speaker: {raw_speaker} -> {speaker}")
        else:
            speaker = raw_speaker
        
        # 格式: [说话人] 文本 (开始时间 - 结束时间)
        start_time = self._format_time(segment.start_time)
        end_time = self._format_time(segment.end_time)
        lines.append(f"[{speaker}] {segment.text} ({start_time} - {end_time})")

    return "\n".join(lines)
```

### 2. 更新 `generate_artifact` 方法接收并使用说话人映射

**文件**: `src/providers/gemini_llm.py`

在 `generate_artifact` 方法中：

```python
# 2. 获取说话人映射（如果有）
speaker_mapping = kwargs.get("speaker_mapping")
if speaker_mapping:
    logger.info(f"Using speaker mapping: {speaker_mapping}")
else:
    logger.warning("No speaker mapping provided, using raw speaker labels")

# 3. 格式化转写文本（应用说话人映射）
formatted_transcript = self.format_transcript(transcript, speaker_mapping)
```

### 3. API 路由传递说话人映射

**文件**: `src/api/routes/artifacts.py` 和 `src/api/routes/corrections.py`

在生成和重新生成接口中：

```python
# 获取说话人映射
speaker_mapping_repo = SpeakerMappingRepository(db)
speaker_mapping = speaker_mapping_repo.get_mapping_dict(task.task_id)
logger.info(f"Retrieved speaker mapping for task {task.task_id}: {speaker_mapping}")

# 调用服务生成内容
generated_artifact = await artifact_service.generate_artifact(
    task_id=task.task_id,
    transcript=transcript_result,
    artifact_type=artifact_type,
    prompt_instance=prompt_instance,
    output_language=output_lang,
    user_id=task.user_id,
    template=None,
    speaker_mapping=speaker_mapping,  # 传递说话人映射 ✅
    meeting_date=task.meeting_date,   # 传递会议日期 ✅
    meeting_time=task.meeting_time,   # 传递会议时间 ✅
)
```

### 4. 服务层透传参数

**文件**: `src/services/artifact_generation.py`

服务层使用 `**kwargs` 将参数透传给 LLM：

```python
artifact = await self.llm.generate_artifact(
    transcript=transcript,
    prompt_instance=prompt_instance,
    output_language=output_language,
    template=template,
    task_id=task_id,
    artifact_id=artifact_id,
    version=next_version,
    created_by=user_id,
    **kwargs,  # 包含 speaker_mapping, meeting_date, meeting_time
)
```

## 测试验证

创建了测试脚本 `scripts/test_speaker_mapping_in_prompt.py` 验证修复：

### 测试结果

```
✅ 所有检查通过!
   - 说话人映射正确应用
   - 会议时间正确格式化
   - LLM 将看到真实姓名而不是 speaker1/speaker2
```

### 对比示例

**修复前**（LLM 看到的）：
```
[Speaker 1] 我先简单的实现了一下样例...
[Speaker 2] 但是他们是在一个统一的导航里面...
```

**修复后**（LLM 看到的）：
```
[speaker_linyudong] 我先简单的实现了一下样例...
[speaker_lanweiyi] 但是他们是在一个统一的导航里面...
```

## 影响范围

### 修改的文件

1. `src/providers/gemini_llm.py` - 核心修复
   - `format_transcript()` 方法支持说话人映射
   - `generate_artifact()` 方法接收并使用说话人映射

2. `src/api/routes/artifacts.py` - API 层
   - `generate_artifact` 端点获取并传递说话人映射

3. `src/api/routes/corrections.py` - API 层
   - `regenerate_artifact` 端点获取并传递说话人映射

4. `src/services/artifact_generation.py` - 服务层
   - 透传参数（已有 `**kwargs`，无需修改）

### 新增文件

- `scripts/test_speaker_mapping_in_prompt.py` - 测试脚本

## 向后兼容性

✅ **完全向后兼容**

- `speaker_mapping` 参数是可选的（`Optional[Dict[str, str]]`）
- 如果不提供映射，行为与之前相同（使用原始标签）
- 不会影响现有代码

## 前端需要做什么

**无需修改**

前端不需要做任何改动，后端会自动：
1. 从数据库获取说话人映射
2. 应用到转写文本格式化
3. 传递给 LLM

## 后续优化建议

1. **缓存说话人映射**：如果同一任务多次生成 artifact，可以缓存映射避免重复查询
2. **日志增强**：在生成日志中记录使用的说话人映射，方便调试
3. **错误处理**：如果映射缺失，记录警告但不阻塞生成

## 总结

这次修复解决了两个关键问题：

1. ✅ **说话人名称正确传递**：LLM 现在看到的是真实姓名（如 `speaker_linyudong`），而不是原始标签（`speaker1`）
2. ✅ **会议时间正确传递**：会议日期和时间在所有生成路径中都正确传递

修复后，生成的会议纪要将包含正确的说话人名称和会议时间信息，提升了内容质量和可读性。
