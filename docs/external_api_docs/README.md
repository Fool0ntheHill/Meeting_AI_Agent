# 外部 API 参考文档

本目录包含项目使用的外部服务 API 的参考文档，用于开发时查阅。

## 📁 目录结构

```
external_api_docs/
├── README.md                           # 本文件
├── volcano_asr_api.txt                 # 火山引擎 ASR API 文档
├── volcano_hotword_api.txt             # 火山引擎热词 API 文档
├── volcano_hotword_management_api.txt  # 火山引擎热词管理 API 文档
├── volcano_auth_params.txt             # 火山引擎鉴权公共参数
├── azure_speech_api.txt                # Azure Speech API 文档
├── iflytek_voiceprint_api.txt          # 科大讯飞声纹识别 API 文档
├── createboostingtable.py              # 火山热词表创建脚本
└── gemini/                             # Google Gemini API 文档
    ├── google.txt
    ├── google2_api.txt
    ├── google_chirp3.txt
    ├── Gemini 模型.txt
    ├── 文本生成.txt
    ├── 函数调用.txt
    └── ... (更多 Gemini 相关文档)
```

## 📚 文档说明

### 1. 火山引擎 (Volcano Engine)

**ASR 语音转写**:
- `volcano_asr_api.txt` - ASR API 完整文档
- `volcano_auth_params.txt` - 鉴权公共参数说明

**热词管理**:
- `volcano_hotword_api.txt` - 热词 API 基础文档
- `volcano_hotword_management_api.txt` - 热词管理 API 详细文档
- `createboostingtable.py` - 热词表创建示例脚本

**相关代码**:
- `src/providers/volcano_asr.py` - ASR 提供商实现
- `src/providers/volcano_hotword.py` - 热词客户端实现

### 2. Azure Speech

**文档**:
- `azure_speech_api.txt` - Azure Speech Service API 文档

**相关代码**:
- `src/providers/azure_asr.py` - Azure ASR 提供商实现

### 3. 科大讯飞 (iFlytek)

**文档**:
- `iflytek_voiceprint_api.txt` - 声纹识别 API 文档

**相关代码**:
- `src/providers/iflytek_voiceprint.py` - 声纹识别提供商实现

### 4. Google Gemini

**目录**: `gemini/`

**核心文档**:
- `Gemini 模型.txt` - Gemini 模型概述
- `Gemini 3 开发者指南.txt` - 开发者指南
- `文本生成.txt` - 文本生成 API
- `使用 Gemini API 进行函数调用.txt` - 函数调用功能

**高级功能**:
- `长上下文.txt` - 长上下文处理
- `上下文缓存.txt` - 上下文缓存
- `结构化输出.txt` - 结构化输出
- `使用 Google 搜索建立依据.txt` - Grounding 功能
- `文件 API.txt` - 文件处理
- `Batch API.txt` - 批处理 API

**其他**:
- `OpenAI 兼容性.txt` - OpenAI API 兼容性
- `提示设计策略.txt` - Prompt 设计最佳实践

**相关代码**:
- `src/providers/gemini_llm.py` - Gemini LLM 提供商实现

## 🔗 相关文档

### 项目 API 文档
- [项目 API 参考](../api_references/README.md) - 我们自己的 API 文档
- [API 使用指南](../api_references/API_USAGE_GUIDE.md) - 完整的使用指南
- [OpenAPI 规范](../api_references/openapi.yaml) - OpenAPI 3.1.0 规范

### 实现文档
- [火山 ASR V3 迁移](../volcano_asr_v3_migration.md) - V3 API 迁移指南
- [热词 API 测试指南](../hotword_api_testing_guide.md) - 热词功能测试
- [说话人识别阈值调优](../speaker_recognition_threshold_tuning.md) - 声纹识别调优

## 📝 使用说明

### 查阅方式

1. **开发时参考**: 实现提供商时查阅对应的 API 文档
2. **调试问题**: 遇到 API 调用问题时查阅参数说明
3. **功能扩展**: 添加新功能时查阅高级功能文档

### 文档更新

这些文档是外部服务的参考文档，如需更新:
1. 访问对应服务的官方文档网站
2. 下载最新的 API 文档
3. 替换本目录中的对应文件

### 官方文档链接

- **火山引擎**: https://www.volcengine.com/docs/
- **Azure Speech**: https://learn.microsoft.com/azure/cognitive-services/speech-service/
- **科大讯飞**: https://www.xfyun.cn/doc/
- **Google Gemini**: https://ai.google.dev/docs

## ⚠️ 注意事项

1. **仅供参考**: 这些文档仅供开发参考，不是项目的核心文档
2. **版本差异**: 文档可能与实际使用的 API 版本有差异，以官方最新文档为准
3. **敏感信息**: 不要在这些文档中添加 API Key 等敏感信息
4. **定期更新**: 建议定期检查官方文档更新

## 🔍 快速查找

### 按功能查找

**语音转写 (ASR)**:
- 火山引擎: `volcano_asr_api.txt`
- Azure: `azure_speech_api.txt`

**声纹识别**:
- 科大讯飞: `iflytek_voiceprint_api.txt`

**热词管理**:
- 火山引擎: `volcano_hotword_api.txt`, `volcano_hotword_management_api.txt`

**LLM 生成**:
- Google Gemini: `gemini/` 目录下的所有文档

### 按提供商查找

- **火山引擎**: `volcano_*.txt`
- **Azure**: `azure_*.txt`
- **科大讯飞**: `iflytek_*.txt`
- **Google**: `gemini/` 目录

---

**最后更新**: 2026-01-14  
**维护者**: 开发团队
