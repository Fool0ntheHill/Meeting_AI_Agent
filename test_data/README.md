# 测试音频文件目录

此目录用于存放测试音频文件。

## 准备测试音频

### 方法 1: 使用自己的会议录音

将你的会议录音文件放到此目录:

```bash
# 复制音频文件
cp /path/to/your/meeting.wav test_data/
```

### 方法 2: 录制测试音频

使用任何录音软件录制一段简短的对话(1-3分钟):

- **格式**: WAV, MP3, M4A 等常见格式
- **内容**: 包含多人对话的会议场景
- **时长**: 建议 1-5 分钟(首次测试)
- **质量**: 16kHz 采样率,单声道或立体声

### 方法 3: 下载示例音频

可以从以下来源下载测试音频:
- 公开的会议录音数据集
- 自己录制的测试对话

## 音频格式要求

支持的音频格式:
- WAV (推荐)
- MP3
- M4A
- FLAC
- OGG

推荐参数:
- 采样率: 16000 Hz
- 声道: 单声道(mono)
- 比特率: 128 kbps 以上

## 格式转换

如果需要转换音频格式,可以使用 ffmpeg:

```bash
# 转换为 WAV 格式
ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav

# 转换为单声道
ffmpeg -i input.wav -ac 1 output_mono.wav

# 调整采样率
ffmpeg -i input.wav -ar 16000 output_16k.wav
```

## 运行测试

准备好音频文件后,运行端到端测试:

```bash
# 基础测试
python scripts/test_e2e.py --audio test_data/meeting.wav

# 跳过说话人识别(如果没有配置科大讯飞 API)
python scripts/test_e2e.py --audio test_data/meeting.wav --skip-speaker-recognition

# 测试多文件拼接
python scripts/test_e2e.py --audio test_data/part1.wav test_data/part2.wav --file-order 0 1
```

## 注意事项

1. **音频质量**: 音频质量越好,ASR 识别准确率越高
2. **文件大小**: 首次测试建议使用较小的文件(< 10MB)
3. **网络连接**: 确保网络连接稳定,ASR 和 LLM 都需要调用远程 API
4. **API 配额**: 注意 API 调用配额,避免超限

## 示例文件结构

```
test_data/
├── README.md
├── meeting_sample.wav          # 示例会议录音
├── meeting_part1.wav           # 多文件测试 - 第1部分
├── meeting_part2.wav           # 多文件测试 - 第2部分
└── short_conversation.mp3      # 短对话测试
```
