# API 文档重组说明

## 📋 重组概述

**日期**: 2026-01-14  
**原因**: 分离项目 API 文档和外部服务 API 参考文档，提高文档组织清晰度

## 🔄 变更内容

### 之前的结构

```
docs/api_references/          # 混杂了项目和外部 API 文档
├── API_USAGE_GUIDE.md       # 项目 API 文档
├── openapi.json             # 项目 API 文档
├── openapi.yaml             # 项目 API 文档
├── postman_collection.json  # 项目 API 文档
├── README.md                # 项目 API 文档
├── 火山API文档.txt           # 外部参考文档 ❌
├── 火山热词.txt              # 外部参考文档 ❌
├── azure api文档.txt        # 外部参考文档 ❌
├── 讯飞声纹识别api.txt       # 外部参考文档 ❌
├── google.txt               # 外部参考文档 ❌
├── google2_api.txt          # 外部参考文档 ❌
└── google_chirp3.txt        # 外部参考文档 ❌

api docs/                     # 重复的外部参考文档
├── 火山API文档.txt
├── 火山鉴权公共参数.txt
├── 火山热词管理API.txt
├── azure api文档.txt
├── 讯飞声纹识别api.txt
├── createboostingtable.py
└── gemini/
    └── ... (20+ 个文档)
```

### 重组后的结构

```
docs/
├── api_references/                    # ✅ 项目 API 文档（清晰）
│   ├── README.md                     # API 文档索引
│   ├── API_USAGE_GUIDE.md           # 完整的 API 使用指南
│   ├── openapi.json                 # OpenAPI 规范 (JSON)
│   ├── openapi.yaml                 # OpenAPI 规范 (YAML)
│   └── postman_collection.json      # Postman 测试集合
│
└── external_api_docs/                # ✅ 外部服务 API 参考（统一）
    ├── README.md                     # 外部 API 文档索引
    ├── volcano_asr_api.txt           # 火山引擎 ASR
    ├── volcano_hotword_api.txt       # 火山引擎热词
    ├── volcano_hotword_management_api.txt
    ├── volcano_auth_params.txt       # 火山引擎鉴权
    ├── azure_speech_api.txt          # Azure Speech
    ├── iflytek_voiceprint_api.txt    # 科大讯飞声纹
    ├── createboostingtable.py        # 热词表创建脚本
    └── gemini/                       # Google Gemini
        ├── google.txt
        ├── google2_api.txt
        ├── google_chirp3.txt
        ├── Gemini 模型.txt
        ├── 文本生成.txt
        └── ... (20+ 个文档)
```

## 📝 变更详情

### 1. 项目 API 文档 (`docs/api_references/`)

**保留文件** (5 个):
- ✅ `README.md` - API 文档索引
- ✅ `API_USAGE_GUIDE.md` - 完整的使用指南 (19 KB)
- ✅ `openapi.json` - OpenAPI 3.1.0 规范 (96 KB)
- ✅ `openapi.yaml` - OpenAPI 3.1.0 规范 (69 KB)
- ✅ `postman_collection.json` - Postman 集合 (已修复 JSON 格式)

**用途**: 
- 前端开发人员集成 API
- 查看 Swagger UI 文档
- 导入 Postman 测试
- 生成客户端代码

### 2. 外部 API 参考 (`docs/external_api_docs/`)

**移动文件** (8 个主文件 + gemini 目录):
- 📦 `volcano_asr_api.txt` (从 `docs/api_references/火山API文档.txt`)
- 📦 `volcano_hotword_api.txt` (从 `docs/api_references/火山热词.txt`)
- 📦 `volcano_hotword_management_api.txt` (从 `api docs/`)
- 📦 `volcano_auth_params.txt` (从 `api docs/火山鉴权公共参数.txt`)
- 📦 `azure_speech_api.txt` (从 `docs/api_references/azure api文档.txt`)
- 📦 `iflytek_voiceprint_api.txt` (从 `docs/api_references/讯飞声纹识别api.txt`)
- 📦 `createboostingtable.py` (从 `api docs/`)
- 📦 `gemini/` (从 `docs/api_references/` 和 `api docs/gemini/` 合并)

**新增文件**:
- ✨ `README.md` - 外部 API 文档索引和使用说明

**用途**:
- 开发时查阅外部服务 API
- 调试 API 调用问题
- 了解高级功能

### 3. 删除的目录

- ❌ `api docs/` - 已删除（内容已合并到 `docs/external_api_docs/`）

## 🎯 重组目标

### 1. 清晰分离

**项目 API 文档** (`docs/api_references/`):
- 面向前端开发人员
- 描述我们自己的 API
- 用于集成和测试

**外部 API 参考** (`docs/external_api_docs/`):
- 面向后端开发人员
- 描述外部服务的 API
- 用于开发和调试

### 2. 统一管理

- 所有外部 API 文档集中在一个目录
- 避免重复和混乱
- 便于维护和更新

### 3. 改进命名

- 使用英文文件名（更规范）
- 描述性命名（一目了然）
- 统一命名规则

## 📊 文件统计

### 移动前
- `docs/api_references/`: 12 个文件（混杂）
- `api docs/`: 7 个文件 + gemini 目录（重复）

### 移动后
- `docs/api_references/`: 5 个文件（纯净）✅
- `docs/external_api_docs/`: 9 个文件 + gemini 目录（统一）✅

### 减少冗余
- 删除重复文件
- 统一文档位置
- 清晰的目录结构

## 🔗 相关文档

### 项目文档
- [文档索引](./README.md)
- [API 参考文档](./api_references/README.md)
- [外部 API 参考](./external_api_docs/README.md)

### 使用指南
- [API 使用指南](./api_references/API_USAGE_GUIDE.md)
- [快速测试指南](./testing/快速测试指南.md)

## ✅ 验证清单

- [x] 项目 API 文档完整（5 个文件）
- [x] 外部 API 参考完整（8 个文件 + gemini 目录）
- [x] Postman 集合 JSON 格式正确
- [x] 创建 README 索引文件
- [x] 删除重复的 `api docs/` 目录
- [x] 更新文档索引链接

## 📌 注意事项

1. **Postman 集合已修复**: 修复了 JSON 格式错误，现在可以正常导入
2. **文件重命名**: 外部 API 文档使用英文文件名，更规范
3. **目录删除**: `api docs/` 目录已删除，内容已合并
4. **文档完整**: 所有外部 API 文档都已保留，没有丢失

## 🎉 重组完成

文档结构现在更加清晰和专业：
- ✅ 项目 API 文档独立且完整
- ✅ 外部 API 参考统一管理
- ✅ 文件命名规范统一
- ✅ 索引文档完善

---

**重组时间**: 2026-01-14  
**执行者**: Kiro AI Assistant  
**状态**: ✅ 完成
