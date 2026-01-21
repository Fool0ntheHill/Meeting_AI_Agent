# 说话人真实姓名映射修复

## 问题描述

用户反馈：新生成的会议纪要中，说话人名称显示的是"林雨东"而不是"林煜东"。

## 问题分析

通过检查发现两个问题：

### 问题 1：双重修正逻辑错误

在 `src/services/pipeline.py` 中，说话人名称替换使用了两次修正：

1. **第一次修正**：`Speaker 1` -> `speaker_linyudong`
2. **第二次修正**：`speaker_linyudong` -> `林煜东`

但是代码中第二次修正的映射 key 使用错误：

```python
# ❌ 错误的代码
real_name_mapping = {}
for speaker_label, speaker_id in speaker_mapping.items():
    display_name = display_names.get(speaker_id)
    if display_name:
        real_name_mapping[speaker_label] = display_name  # speaker_label 是 "Speaker 1"
```

问题：第一次修正后，transcript 中的 speaker 已经是 `speaker_linyudong` 了，但第二次修正的 key 还是用 `speaker_label`（"Speaker 1"），导致无法匹配。

### 问题 2：LLM 识别错误

即使修复了映射逻辑，LLM 仍然可能把"林煜东"识别成"林雨东"（同音字）。这是因为：
- ASR 转写时可能就识别错了
- 或者 LLM 在生成纪要时自己推断错了

## 解决方案

### 修复 1：修正双重映射逻辑

```python
# ✅ 正确的代码
real_name_mapping = {}
for speaker_id, display_name in display_names.items():
    real_name_mapping[speaker_id] = display_name  # speaker_id 是 "speaker_linyudong"
```

**修改文件**：`src/services/pipeline.py`

**修改内容**：
- 第二次修正的映射 key 改为 `speaker_id`（而不是 `speaker_label`）
- 简化逻辑，直接使用 `display_names` 字典

### 修复 2：Azure ASR 音频格式转换

顺便修复了 Azure ASR 的音频格式问题：

**问题**：Azure ASR 不支持 `.ogg` 格式，导致 422 错误

**解决**：在发送给 Azure ASR 之前，先将音频转换为 WAV 格式

**修改文件**：`src/providers/azure_asr.py`

```python
# 下载 OGG 文件
audio_data = await self._download_audio(audio_url)

# 转换为 WAV 格式
temp_wav_path = await self.audio_processor.convert_format(temp_input_path)

# 读取 WAV 数据
with open(temp_wav_path, 'rb') as f:
    audio_data = f.read()
```

## 测试验证

### 测试脚本

创建了 `scripts/test_speaker_name_replacement.py` 来验证双重修正逻辑：

```
1. 原始 transcript:
   Speaker 1: 大家好，我是林煜东
   Speaker 2: 你好，我是蓝为一

2. 第一次修正后 (Speaker -> speaker_id):
   speaker_linyudong: 大家好，我是林煜东
   speaker_lanweiyi: 你好，我是蓝为一

3. 从数据库查询到的真实姓名:
   speaker_lanweiyi -> 蓝为一
   speaker_linyudong -> 林煜东

4. 真实姓名映射 (修正后):
   speaker_lanweiyi -> 蓝为一
   speaker_linyudong -> 林煜东

5. 第二次修正后 (speaker_id -> 真实姓名):
   林煜东: 大家好，我是林煜东
   蓝为一: 你好，我是蓝为一
```

✅ 测试通过！

### 检查现有任务

使用 `scripts/check_artifact_speaker_names.py` 检查了现有任务：

- `task_097021e3d3944092`：包含"林雨东"（错误）
- `task_07cb88970c3848c4`：包含"林雨东"（错误）

这些是旧任务，在修复之前生成的。

## 后续步骤

1. **重启 Worker**：应用修复后的代码
   ```bash
   # 停止当前 worker (Ctrl+C)
   python worker.py
   ```

2. **创建新任务测试**：上传新的音频文件，验证说话人名称是否正确

3. **如果还是显示错误名称**：
   - 检查 ASR 转写结果（可能是 ASR 识别错了）
   - 检查 speakers 表中的 display_name 是否正确
   - 考虑在提示词中明确说明正确的人名

## 文件清单

- ✅ `src/services/pipeline.py` - 修复双重映射逻辑
- ✅ `src/providers/azure_asr.py` - 添加音频格式转换
- ✅ `scripts/test_speaker_name_replacement.py` - 测试脚本
- ✅ `scripts/check_artifact_speaker_names.py` - 检查脚本
- ✅ `scripts/check_transcript_speaker_names.py` - 检查脚本

## 状态

✅ **已修复** - 双重映射逻辑已修正，需要重启 Worker 并创建新任务测试
