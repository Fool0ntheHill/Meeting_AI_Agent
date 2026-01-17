# 文档索引

本目录包含项目的所有文档，按类型组织。

## 📁 文档结构

```
docs/
├── README.md                          # 本文件 - 文档索引
├── PHASE_2_TASKS_ADDED.md            # Phase 2 任务说明
│
├── summaries/                         # 任务完成总结
│   ├── TASK_18_COMPLETION_SUMMARY.md # Task 18: 任务管理 API
│   ├── TASK_19_COMPLETION_SUMMARY.md # Task 19: 修正与重新生成 API
│   ├── TASK_19.4_IMPLEMENTATION_SUMMARY.md # Task 19.4: 任务确认 API
│   ├── TASK_20_COMPLETION_SUMMARY.md # Task 20: 热词管理 API
│   ├── TASK_21_COMPLETION_SUMMARY.md # Task 21: 提示词模板管理 API
│   ├── TASK_22_COMPLETION_SUMMARY.md # Task 22: 衍生内容管理 API
│   ├── TASK_23_COMPLETION_SUMMARY.md # Task 23: 鉴权与中间件
│   ├── TASK_24_COMPLETION_SUMMARY.md # Task 24: API 层测试检查点
│   └── TASK_25_COMPLETION_SUMMARY.md # Task 25: 前端联调准备
│
├── api_references/                    # 项目 API 文档
│   ├── README.md                     # API 文档索引
│   ├── API_USAGE_GUIDE.md           # API 使用指南
│   ├── openapi.json                 # OpenAPI 规范 (JSON)
│   ├── openapi.yaml                 # OpenAPI 规范 (YAML)
│   └── postman_collection.json      # Postman 集合
│
├── external_api_docs/                # 外部服务 API 参考
│   ├── README.md                     # 外部 API 文档索引
│   ├── volcano_asr_api.txt           # 火山引擎 ASR API
│   ├── volcano_hotword_api.txt       # 火山引擎热词 API
│   ├── azure_speech_api.txt          # Azure Speech API
│   ├── iflytek_voiceprint_api.txt    # 科大讯飞声纹 API
│   └── gemini/                       # Google Gemini API 文档
│
├── implementation/                    # 实现总结文档
│   ├── API_IMPLEMENTATION_SUMMARY.md # API 层实现总结
│   ├── DATABASE_IMPLEMENTATION_SUMMARY.md # 数据库实现总结
│   ├── QUEUE_WORKER_IMPLEMENTATION.md # 队列和 Worker 实现总结
│   └── PYTHON_VERSION_UPDATE_SUMMARY.md # Python 版本更新总结
│
├── testing/                           # 测试相关文档
│   ├── TESTING_READY.md              # 测试就绪说明
│   ├── TEST_RESULTS.md               # 测试结果
│   ├── 快速测试指南.md                # 快速测试指南
│   └── 测试配置指南.md                # 测试配置指南
│
└── [其他文档]                         # 技术文档和指南
    ├── database_design_improvements.md
    ├── database_migration_guide.md
    ├── gap_rescue_implementation.md
    ├── hotword_api_testing_guide.md
    ├── improvement_roadmap.md
    ├── install_python312_windows.md
    ├── phase2_clarification.md
    ├── queue_worker_improvements.md
    ├── speaker_recognition_threshold_tuning.md
    ├── task_confirmation_api.md
    ├── v3_api_migration_summary.md
    └── volcano_asr_v3_migration.md
```

## 📚 文档分类

### 1. 任务完成总结 (`summaries/`)

记录每个任务的完成情况，包括：
- 实现内容
- 测试结果
- 文件清单
- 下一步建议

**按任务编号查找**:
- Task 18: 任务管理 API
- Task 19: 修正与重新生成 API (含 19.1, 19.3, 19.4)
- Task 20: 热词管理 API
- Task 21: 提示词模板管理 API
- Task 22: 衍生内容管理 API
- Task 23: 鉴权与中间件
- Task 24: API 层测试检查点
- Task 25: 前端联调准备

### 2. API 参考文档 (`api_references/`)

项目自己的 API 文档和规范：
- **README.md**: API 文档索引
- **API_USAGE_GUIDE.md**: 完整的 API 使用指南
- **openapi.json/yaml**: OpenAPI 3.1.0 规范文件
- **postman_collection.json**: Postman 测试集合

### 3. 外部 API 参考 (`external_api_docs/`)

外部服务 API 的参考文档（开发时查阅）：
- **README.md**: 外部 API 文档索引
- **volcano_*.txt**: 火山引擎 API 文档
- **azure_speech_api.txt**: Azure Speech API 文档
- **iflytek_voiceprint_api.txt**: 科大讯飞声纹 API 文档
- **gemini/**: Google Gemini API 文档集合

### 4. 实现总结 (`implementation/`)

记录各个模块的实现总结：
- **API_IMPLEMENTATION_SUMMARY.md**: API 层整体实现
- **DATABASE_IMPLEMENTATION_SUMMARY.md**: 数据库设计和实现
- **QUEUE_WORKER_IMPLEMENTATION.md**: 异步任务队列实现
- **PYTHON_VERSION_UPDATE_SUMMARY.md**: Python 版本升级记录

### 4. 测试文档 (`testing/`)

测试相关的文档和指南：
- **TESTING_READY.md**: 测试环境准备
- **TEST_RESULTS.md**: 测试结果记录
- **快速测试指南.md**: 快速开始测试
- **测试配置指南.md**: 测试配置说明

### 5. 技术文档 (根目录)

各种技术实现和改进文档：
- **improvement_roadmap.md**: 改进路线图 (Phase 2 规划)
- **phase2_clarification.md**: Phase 2 任务澄清
- **database_migration_guide.md**: 数据库迁移指南
- **hotword_api_testing_guide.md**: 热词 API 测试指南
- **task_confirmation_api.md**: 任务确认 API 文档
- 等等...

## 🔍 快速查找

### 按功能查找

**API 相关**:
- [API 参考文档](api_references/README.md) ⭐ 项目 API
- [API 使用指南](api_references/API_USAGE_GUIDE.md) ⭐ 使用指南
- [OpenAPI 规范](api_references/openapi.yaml) ⭐ OpenAPI 3.1.0
- [Postman 集合](api_references/postman_collection.json) ⭐ 测试集合
- [外部 API 参考](external_api_docs/README.md) ⭐ 外部服务 API
- [API 实现总结](implementation/API_IMPLEMENTATION_SUMMARY.md)
- [Task 18: 任务管理 API](summaries/TASK_18_COMPLETION_SUMMARY.md)
- [Task 19: 修正 API](summaries/TASK_19_COMPLETION_SUMMARY.md)
- [Task 20: 热词 API](summaries/TASK_20_COMPLETION_SUMMARY.md)
- [Task 21: 模板 API](summaries/TASK_21_COMPLETION_SUMMARY.md)
- [Task 22: 衍生内容 API](summaries/TASK_22_COMPLETION_SUMMARY.md)
- [Task 25: 前端联调准备](summaries/TASK_25_COMPLETION_SUMMARY.md) ⭐ 新增

**数据库相关**:
- [数据库实现总结](implementation/DATABASE_IMPLEMENTATION_SUMMARY.md)
- [数据库迁移指南](database_migration_guide.md)
- [数据库设计改进](database_design_improvements.md)

**测试相关**:
- [测试就绪说明](testing/TESTING_READY.md)
- [测试结果](testing/TEST_RESULTS.md)
- [快速测试指南](testing/快速测试指南.md)
- [Task 24: 测试检查点](summaries/TASK_24_COMPLETION_SUMMARY.md)

**队列和 Worker**:
- [队列实现总结](implementation/QUEUE_WORKER_IMPLEMENTATION.md)
- [队列改进建议](queue_worker_improvements.md)

**Phase 2 规划**:
- [Phase 2 任务说明](PHASE_2_TASKS_ADDED.md)
- [改进路线图](improvement_roadmap.md)
- [Phase 2 澄清](phase2_clarification.md)

### 按时间查找

文档按任务完成顺序：
1. Task 18 (2026-01-14)
2. Task 19 (2026-01-14)
3. Task 19.4 (2026-01-14)
4. Task 20 (2026-01-14)
5. Task 21 (2026-01-14)
6. Task 22 (2026-01-14)
7. Task 23 (2026-01-14)
8. Task 24 (2026-01-14)
9. Task 25 (2026-01-14) ⭐ 新增

## 📝 文档规范

### 任务完成总结格式

每个任务完成总结应包含：
1. 完成时间
2. 任务概述
3. 实现内容
4. 测试结果
5. 文件清单
6. 下一步建议

### 实现总结格式

实现总结应包含：
1. 概述
2. 架构设计
3. 关键实现
4. 测试覆盖
5. 已知问题
6. 改进建议

## 🔗 相关资源

- [需求文档](../.kiro/specs/meeting-minutes-agent/requirements.md)
- [设计文档](../.kiro/specs/meeting-minutes-agent/design.md)
- [任务列表](../.kiro/specs/meeting-minutes-agent/tasks.md)
- [项目 README](../README.md)

## 📊 项目状态

**Phase 1 (MVP)**: ✅ 完成
- Task 1-25 全部完成 ⭐ 更新
- 151 个单元测试通过
- API 层完整实现
- API 文档完整 (OpenAPI + 使用指南 + Postman) ⭐ 新增

**Phase 2 (改进)**: 🚧 规划中
- Task 32: JWT 鉴权 (P0)
- Task 33: LLM 真实调用 (P0)
- Task 34: 热词连接 ASR (P0)
- 其他 P1/P2 任务

详见 [Phase 2 任务说明](PHASE_2_TASKS_ADDED.md)
