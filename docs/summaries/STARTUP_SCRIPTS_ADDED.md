# 启动脚本和快速启动指南

## 概述

为了方便电脑重启后快速启动服务，添加了一套完整的启动脚本和配置指南。

## 新增文件

### 文档
- `docs/QUICK_START_AFTER_REBOOT.md` - 电脑重启后快速启动指南

### 启动脚本
- `scripts/start_all.ps1` - 一键启动所有服务
- `scripts/start_redis.ps1` - 启动 Redis 服务
- `scripts/start_backend.ps1` - 启动后端 API
- `scripts/start_worker.ps1` - 启动 Worker
- `scripts/stop_all.ps1` - 停止所有服务

## 使用方法

### 快速启动（推荐）

```powershell
# 在项目根目录运行
.\scripts\start_all.ps1
```

这会自动：
1. 启动 Redis（尝试 WSL、Windows、Docker 三种方式）
2. 在新窗口启动后端 API
3. 在新窗口启动 Worker

### 分步启动

```powershell
# 1. 启动 Redis
.\scripts\start_redis.ps1

# 2. 启动后端（新终端）
.\scripts\start_backend.ps1

# 3. 启动 Worker（新终端）
.\scripts\start_worker.ps1
```

### 停止服务

```powershell
.\scripts\stop_all.ps1
```

## 脚本功能

### start_redis.ps1
- 自动检测 Redis 是否已运行
- 尝试三种启动方式：
  1. WSL Redis
  2. Windows Redis
  3. Docker Redis
- 提供安装指导

### start_backend.ps1
- 检查虚拟环境
- 验证 Redis 连接
- 启动 uvicorn 服务器
- 显示访问地址

### start_worker.ps1
- 检查虚拟环境
- 验证 Redis 连接
- 启动 worker 进程

### start_all.ps1
- 按顺序启动所有服务
- 在新窗口打开后端和 Worker
- 显示服务状态和地址

### stop_all.ps1
- 停止后端 API 进程
- 停止 Worker 进程
- 优雅关闭 Redis

## Redis 配置选项

### 方法 1: WSL (推荐)

```bash
# 安装 WSL
wsl --install

# 在 WSL 中安装 Redis
sudo apt update
sudo apt install redis-server

# 启动 Redis
redis-server
```

### 方法 2: Docker

```powershell
# 创建并启动 Redis 容器
docker run -d --name redis --restart always -p 6379:6379 redis:latest
```

### 方法 3: Windows Redis

下载并安装 Windows 版本的 Redis，然后注册为服务：

```powershell
# 以管理员身份运行
redis-server --service-install
redis-server --service-start
sc config Redis start= auto
```

## 自动启动配置

### Windows 计划任务（WSL Redis）

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：用户登录时
4. 操作：启动程序 `wsl`，参数 `redis-server`

### Docker 自动重启

```powershell
docker update --restart always redis
```

## 故障排查

### Redis 连接失败

```powershell
# 检查 Redis 状态
redis-cli ping

# 查看端口占用
netstat -ano | findstr :6379
```

### 端口被占用

```powershell
# 查找占用进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

### 虚拟环境问题

```powershell
# 重新激活虚拟环境
.\venv\Scripts\Activate.ps1

# 检查 Python 版本
python --version
```

## 更新内容

### README.md
- 添加"电脑重启后快速启动"章节
- 链接到详细启动指南

### 文档组织
- 所有启动相关文档集中在 `docs/QUICK_START_AFTER_REBOOT.md`
- 脚本统一放在 `scripts/` 目录

## 测试

所有脚本已在 Windows 11 + PowerShell 7 环境下测试通过。

支持的 Redis 安装方式：
- ✅ WSL Redis
- ✅ Docker Redis
- ✅ Windows Redis（未完全测试）

## 后续改进

1. 添加健康检查脚本
2. 支持配置文件选择（development/production）
3. 添加日志查看工具
4. 创建系统托盘应用（可选）
