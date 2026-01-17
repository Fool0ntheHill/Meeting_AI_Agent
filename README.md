# 会议纪要 Agent

基于 ASR、声纹识别和 LLM 的生产级会议录音处理系统

## 功能特性

- ✅ **双轨 ASR 转写**: 火山引擎(主) + Azure(备用),自动降级
- ✅ **声纹识别**: 科大讯飞 1:N 检索,支持分差挽救
- ✅ **ASR 修正**: 基于声纹聚类的全局身份投票
- ✅ **多类型内容生成**: 会议纪要、行动项、摘要笔记等
- ✅ **提示词模板系统**: 可复用、可定制的生成策略
- ✅ **版本管理**: 每次生成创建新版本,支持历史追溯
- ✅ **异步任务处理**: Producer-Consumer 架构,支持横向扩展
- ✅ **成本控制**: 预估成本、配额管理、自动熔断

## 架构设计

系统采用分层架构 + 异步任务处理:

```
┌─────────────┐
│  Web API    │ (Producer)
└──────┬──────┘
       │
   ┌───▼────┐
   │ Queue  │ (Redis/RabbitMQ)
   └───┬────┘
       │
┌──────▼──────┐
│  Workers    │ (Consumer)
└─────────────┘
```

详细设计文档: `.kiro/specs/meeting-minutes-agent/design.md`

## 快速开始

### 1. 环境要求

- Python 3.11+
- PostgreSQL 14+ (可选,用于持久化)
- Redis 6+ (可选,用于消息队列)

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
make install
# 或
pip install -r requirements.txt
```

### 3. 配置 API 密钥

```bash
# 复制配置模板
cp config/test.yaml.example config/test.yaml

# 编辑配置文件,填入 API 密钥
# 必需: 火山引擎 ASR + Gemini LLM
# 可选: Azure ASR + 科大讯飞声纹识别
```

**当前配置状态**:
- ✅ 火山引擎 ASR: 已配置
- ✅ Gemini LLM: 已配置(2个密钥)
- ✅ Azure ASR: 已配置(备用)
- ✅ 科大讯飞声纹识别: 已配置
- ✅ TOS 存储: 已配置

详细配置说明: [测试配置指南](docs/测试配置指南.md)

### 4. 验证配置

```bash
# 运行配置检查工具
python scripts/check_config.py --config config/test.yaml
```

### 5. 准备测试音频

将你的会议录音文件放到 `test_data/` 目录:

```bash
# 复制音频文件
cp /path/to/your/meeting.wav test_data/
```

参考: [test_data/README.md](test_data/README.md)

### 6. 运行端到端测试

```bash
# 基础测试(跳过说话人识别) - 推荐首次使用
python scripts/test_e2e.py \
  --audio test_data/meeting.wav \
  --skip-speaker-recognition \
  --config config/test.yaml

# 完整测试(包含说话人识别)
python scripts/test_e2e.py \
  --audio test_data/meeting.wav \
  --config config/test.yaml

# 测试多文件拼接
python scripts/test_e2e.py \
  --audio test_data/part1.wav test_data/part2.wav \
  --file-order 0 1 \
  --skip-speaker-recognition \
  --config config/test.yaml
```

**快速测试指南**: [docs/快速测试指南.md](docs/快速测试指南.md) ⭐

更多测试选项: [测试说明](docs/测试说明.md)

### 5. 运行单元测试

```bash
# 运行所有测试
make test

# 运行测试并生成覆盖率报告
make test-cov

# 运行特定测试
pytest tests/unit/test_services_pipeline.py -v
```

## 开发指南

### 代码质量

```bash
# 格式化代码
make format

# 代码检查
make lint

# 类型检查
make type-check
```

### 测试

```bash
# 运行所有测试
make test

# 运行测试并生成覆盖率报告
make test-cov

# 运行属性测试
pytest -m property

# 运行集成测试
pytest -m integration
```

### 项目结构

```
src/
├── core/           # 核心抽象层(接口、模型、异常)
├── providers/      # 服务提供商实现(ASR、声纹、LLM)
├── services/       # 业务逻辑层(转写、识别、生成)
├── api/            # API 层(路由、请求/响应模型)
├── workers/        # Worker 层(异步任务执行)
├── utils/          # 工具模块(音频、存储、日志)
├── config/         # 配置管理
└── db/             # 数据库层(ORM、迁移)

tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
└── fixtures/       # 测试夹具
```

## API 使用示例

### 1. 获取 JWT Token (开发环境)

```bash
curl -X POST "http://localhost:8000/api/v1/auth/dev/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}'
```

响应:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "user_test_user",
  "tenant_id": "tenant_test_user",
  "expires_in": 86400
}
```

### 2. 创建任务

```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_files": ["meeting.wav"],
    "meeting_type": "weekly_sync",
    "asr_language": "zh-CN+en-US",
    "output_language": "zh-CN",
    "prompt_instance": {
      "template_id": "tpl_001",
      "language": "zh-CN",
      "parameters": {
        "meeting_description": "会议标题: 产品规划会议"
      }
    }
  }'
```

### 3. 查询任务状态

```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. 列出衍生内容

```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}/artifacts" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**注意**: 
- 开发环境使用 `/auth/dev/login` 获取 JWT Token
- 生产环境将使用企业微信等第三方认证
- Token 默认有效期 24 小时

## 文档

### 快速开始
- ⭐ [快速测试指南](docs/快速测试指南.md) - 3步快速测试
- [快速开始](docs/快速开始.md) - 5分钟快速开始
- [测试配置指南](docs/测试配置指南.md) - 详细配置说明
- [测试说明](docs/测试说明.md) - 完整测试文档

### 设计文档
- [需求文档](.kiro/specs/meeting-minutes-agent/requirements.md) - 48个需求
- [设计文档](.kiro/specs/meeting-minutes-agent/design.md) - 完整架构设计
- [任务列表](.kiro/specs/meeting-minutes-agent/tasks.md) - 31个实施任务

### 迁移指南
- [迁移实施计划](docs/迁移实施计划.md)
- [文件迁移指南](docs/文件迁移指南.md)
- [架构设计](docs/新项目架构设计.md)

## 参考资料

- 旧项目代码: `AI参考文件夹/`
- API 文档: `api docs/`
- 技术文档: `docs/`

## License

MIT
