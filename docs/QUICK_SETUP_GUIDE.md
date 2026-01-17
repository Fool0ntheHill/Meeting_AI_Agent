# 快速设置指南

在新电脑上快速启动项目的步骤。

---

## 📋 前置要求

- Python 3.12+
- Git
- Redis（可选，用于队列和缓存）

---

## 🚀 快速启动（5 分钟）

### 1. 克隆项目

```bash
git clone <你的仓库地址>
cd Meeting_AI_Agent
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境

```bash
# 复制配置文件
cp config/development.yaml.example config/development.yaml

# 复制环境变量文件
cp .env.example .env
```

**编辑 `config/development.yaml`**，填入你的 API 密钥：
- 火山引擎 ASR API 密钥
- 讯飞声纹识别 API 密钥
- Google Gemini API 密钥

### 5. 初始化数据库

```bash
# 数据库会自动创建，但需要运行迁移脚本添加新字段
python scripts/migrate_add_folders.py
python scripts/migrate_add_task_name.py
python scripts/migrate_add_content_modified_time.py
```

### 6. 启动后端

```bash
# 启动 API 服务器
python main.py

# 在另一个终端启动 Worker（可选）
python worker.py
```

后端将在 `http://localhost:8000` 运行。

---

## 🧪 验证安装

### 测试 API

```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试登录
python scripts/auth_helper.py
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/
pytest tests/integration/
```

---

## 📁 项目结构

```
Meeting_AI_Agent/
├── src/                    # 源代码
│   ├── api/               # API 路由和接口
│   ├── services/          # 业务逻辑
│   ├── providers/         # 外部服务提供商
│   ├── database/          # 数据库模型
│   ├── queue/             # 消息队列
│   └── utils/             # 工具函数
├── tests/                 # 测试
├── scripts/               # 脚本工具
├── docs/                  # 文档
├── config/                # 配置文件
├── main.py               # API 服务器入口
└── worker.py             # Worker 入口
```

---

## 🔧 常见问题

### 1. 数据库文件不存在

数据库会在首次运行时自动创建。如果需要测试数据：

```bash
python scripts/create_test_task.py
```

### 2. Redis 连接失败

如果没有安装 Redis，API 会降级到仅使用数据库模式。要安装 Redis：

**Windows**: 下载 Redis for Windows  
**macOS**: `brew install redis`  
**Linux**: `sudo apt-get install redis-server`

### 3. 端口被占用

修改 `main.py` 中的端口：

```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # 改为其他端口
```

---

## 📚 开发文档

- **API 文档**: `docs/API_QUICK_REFERENCE.md`
- **前端开发指南**: `docs/FRONTEND_DEVELOPMENT_GUIDE.md`
- **数据库迁移**: `docs/database_migration_guide.md`
- **生产部署**: `docs/production_deployment_guide.md`

---

## 🎯 前端开发

如果你只需要开发前端，后端已经提供了完整的 API：

1. 启动后端（按上述步骤）
2. 查看 API 文档：`docs/API_QUICK_REFERENCE.md`
3. 使用 TypeScript 类型定义：`docs/frontend-types.ts`

**API 基础地址**: `http://localhost:8000/api/v1`

**认证方式**: 开发环境使用 `POST /api/v1/auth/dev/login` 获取 JWT Token

---

## 📝 提交代码前检查

```bash
# 运行测试
pytest

# 检查代码格式
ruff check .

# 检查类型
mypy src/
```

---

## 🆘 需要帮助？

查看详细文档：
- `docs/README.md` - 文档索引
- `docs/快速开始.md` - 中文快速开始指南
- GitHub Issues - 提交问题
