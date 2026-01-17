# 新项目 AI 参考文件夹

## 📁 目录结构

```
新项目AI参考文件夹/
├── 1_ASR转写/                    # ASR 语音转写模块
│   ├── volcano_transcriber_v3.py  # 火山引擎（主力）
│   ├── azure_transcriber.py       # Azure（备用）
│   └── transcription_tester.py    # 测试框架（含评估逻辑）
│
├── 2_声纹识别/                    # 声纹识别模块
│   ├── iflytek_voiceprint.py      # 讯飞客户端
│   ├── audio_processor.py         # 音频处理
│   └── asr_cluster_corrector.py   # 聚类修正
│
├── 3_主流程/                      # 主流程模块
│   └── main_pipeline.py           # 端到端流程
│
├── 4_LLM总结/                     # LLM 总结模块
│   └── meeting_summarizer.py      # 会议总结器（需改造）
│
├── 5_配置文件/                    # 配置文件
│   └── AzureSecretKey.csv         # Azure 密钥
│
├── API文档/                       # API 文档
│   ├── 火山API文档.txt
│   ├── azure api文档.txt
│   ├── 讯飞声纹识别api.txt
│   └── 火山热词.txt
│
├── 技术文档/                      # 技术文档
│   ├── 分差挽救机制说明.md
│   ├── 项目完成总结.md
│   ├── 评估逻辑审查报告.md
│   └── 新项目迁移清单.md
│
└── README.md                      # 本文件
```

## 🎯 新项目架构

```
会议 AI 助手
├── ASR 语音转写
│   ├── 主力：火山引擎
│   └── 备用：Azure
├── 声纹识别
│   └── 科大讯飞
└── LLM 会议总结
    └── Gemini 3 Pro
```

## 📋 核心模块说明

### 1. ASR 转写模块

**火山引擎（主力）**：
- 时间戳精度最高（348ms）
- 支持 TOS 对象存储
- 支持说话人分离
- 中英文混合识别

**Azure（备用）**：
- 本地文件直接上传
- 支持说话人分离（eastus 区域）
- 自动切分大文件

### 2. 声纹识别模块

**讯飞声纹识别**：
- 1:N 说话人检索
- 1:1 说话人验证
- 分差挽救机制（Gap Rescue）
- HMAC-SHA256 鉴权

**音频处理器**：
- 从 TOS 提取声纹样本
- 智能片段筛选（3-6秒）
- 格式转换（16kHz, 单声道, 16bit, WAV）

**ASR 修正器**：
- 基于声纹识别修正 ASR 聚类错误
- DER（说话人区分错误率）计算
- 保底机制

### 3. 主流程模块

**端到端流程**：
1. ASR 语音转写
2. 声纹样本提取
3. 声纹识别
4. ASR 聚类修正
5. 生成实名会议纪要

### 4. LLM 总结模块

**会议总结器**：
- ⚠️ 当前使用 OpenRouter API
- 🔄 需要改造为 Gemini 3 Pro
- 保留作为参考

### 5. 评估工具

**测试框架**：
- CER（字错误率）计算
- DER（说话人区分错误率）计算
- 时间戳偏移计算
- 使用 pyannote.metrics 专业库

## 🔧 使用建议

### 1. 模块化设计

建议新项目采用模块化架构：

```python
from src.asr import VolcanoASR, AzureASR
from src.voiceprint import IFlyTekVoiceprint
from src.llm import GeminiSummarizer
from src.pipeline import MeetingPipeline

# 组装流程
pipeline = MeetingPipeline(
    asr=VolcanoASR(),
    voiceprint=IFlyTekVoiceprint(),
    summarizer=GeminiSummarizer()
)
```

### 2. 配置管理

建议使用配置文件（YAML）：

```yaml
# config/asr_config.yaml
volcano:
  access_key: ${TOS_ACCESS_KEY}
  secret_key: ${TOS_SECRET_KEY}
  endpoint: https://tos-cn-beijing.volces.com

azure:
  subscription_key: ${AZURE_KEY}
  region: eastus
```

### 3. 改造 LLM 模块

将 OpenRouter 改为 Gemini 3 Pro：

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-3-pro')
```

## 📚 技术文档

详细的技术说明请参考 `技术文档/` 目录：

1. **分差挽救机制说明.md** - 声纹识别优化技术
2. **项目完成总结.md** - 项目总结和技术亮点
3. **评估逻辑审查报告.md** - CER/DER 计算逻辑
4. **新项目迁移清单.md** - 完整的迁移指南

## ⚠️ 注意事项

### 配置密钥

需要配置以下密钥：

1. **火山引擎 TOS**：
   - TOS_ACCESS_KEY
   - TOS_SECRET_KEY

2. **Azure**：
   - 见 `5_配置文件/AzureSecretKey.csv`

3. **讯飞声纹识别**：
   - XF_APP_ID
   - XF_API_KEY
   - XF_API_SECRET
   - XF_GROUP_ID

4. **Gemini 3 Pro**（新增）：
   - GEMINI_API_KEY

### 依赖安装

```bash
pip install requests
pip install tos
pip install pyannote.metrics
pip install google-generativeai  # Gemini
```

## 🎉 核心技术亮点

1. **分差挽救机制**：在短音频场景下提高识别准确率 50%
2. **智能说话人映射**：自动匹配 "Speaker X" 到真实姓名
3. **时间戳偏移算法 v2.0**：智能匹配 + 切分检测
4. **专业评估体系**：使用 pyannote.metrics 计算 DER
5. **保底机制**：识别失败不崩溃，保证系统可用性

## 📞 参考资料

- API 文档：见 `API文档/` 目录
- 技术文档：见 `技术文档/` 目录
- 迁移指南：`技术文档/新项目迁移清单.md`

---

**打包时间**: 2025-01-12  
**核心文件数**: 17 个  
**来源项目**: 会议录音实名识别系统
