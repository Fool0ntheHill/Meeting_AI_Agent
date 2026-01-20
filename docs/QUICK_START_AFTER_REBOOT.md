# 电脑重启后快速启动指南

## 启动顺序

电脑重启后，需要按以下顺序启动服务：

### 1. 启动 Redis（必需）

Redis 用于消息队列和缓存，必须先启动。

**方法 A: 使用 WSL (推荐)**
```bash
# 在 WSL 中启动 Redis
wsl redis-server
```

**方法 B: 使用 Windows Redis**
```powershell
# 如果安装了 Windows 版本的 Redis
redis-server
```

**方法 C: 使用 Docker**
```powershell
docker run -d -p 6379:6379 --name redis redis:latest
```

**验证 Redis 是否启动**:
```powershell
# 测试连接
redis-cli ping
# 应该返回: PONG
```

### 2. 激活虚拟环境

```powershell
# 在项目根目录
.\venv\Scripts\Activate.ps1
```

### 3. 启动后端 API

```powershell
# 方法 1: 使用 uvicorn 直接启动
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

# 方法 2: 使用 make 命令
make run
```

后端启动后访问: http://localhost:8000/docs

### 4. 启动 Worker（新终端）

打开新的终端窗口：

```powershell
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 启动 worker
python worker.py
```

## 一键启动脚本

我已经为你创建了启动脚本，使用方法：

```powershell
# 启动所有服务（Redis + 后端 + Worker）
.\scripts\start_all.ps1

# 或者分别启动
.\scripts\start_redis.ps1    # 启动 Redis
.\scripts\start_backend.ps1  # 启动后端
.\scripts\start_worker.ps1   # 启动 Worker
```

## 检查服务状态

```powershell
# 检查 Redis
redis-cli ping

# 检查后端 API
curl http://localhost:8000/health

# 检查 Worker（查看日志）
# Worker 会在终端输出日志
```

## 常见问题

### Redis 连接失败

**错误**: `ConnectionError: Error 10061 connecting to localhost:6379`

**解决方案**:
1. 确认 Redis 已启动: `redis-cli ping`
2. 检查端口是否被占用: `netstat -ano | findstr :6379`
3. 重启 Redis 服务

### 端口被占用

**错误**: `Address already in use`

**解决方案**:
```powershell
# 查找占用端口的进程
netstat -ano | findstr :8000

# 结束进程（替换 PID）
taskkill /PID <进程ID> /F
```

### Worker 无法连接到 Redis

**解决方案**:
1. 确认 Redis 已启动
2. 检查 `config/development.yaml` 中的 Redis 配置
3. 确认防火墙没有阻止连接

## 配置 Redis 自动启动（可选）

### 方法 1: WSL 自动启动

创建 Windows 计划任务，在登录时自动启动 WSL Redis：

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：用户登录时
4. 操作：启动程序
5. 程序：`wsl`
6. 参数：`redis-server`

### 方法 2: Docker 自动启动

```powershell
# 创建 Redis 容器并设置自动重启
docker run -d \
  --name redis \
  --restart always \
  -p 6379:6379 \
  redis:latest
```

### 方法 3: Windows 服务（需要 Windows Redis）

如果安装了 Windows 版本的 Redis，可以将其注册为 Windows 服务：

```powershell
# 以管理员身份运行
redis-server --service-install
redis-server --service-start

# 设置自动启动
sc config Redis start= auto
```

## 开发环境配置检查

```powershell
# 运行诊断脚本
python scripts/diagnose.py
```

这会检查：
- Python 版本
- 依赖包
- Redis 连接
- 配置文件
- 环境变量

## 快速测试

启动所有服务后，运行快速测试：

```powershell
# 测试 API
python test_quick.py

# 测试新 API
python test_quick_new_apis.py
```
