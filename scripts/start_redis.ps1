# 启动 Redis 服务

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  启动 Redis 服务" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Redis 是否已经在运行
$redisRunning = $false
try {
    $result = redis-cli ping 2>$null
    if ($result -eq "PONG") {
        $redisRunning = $true
    }
} catch {
    $redisRunning = $false
}

if ($redisRunning) {
    Write-Host "✓ Redis 已经在运行" -ForegroundColor Green
    Write-Host ""
    exit 0
}

Write-Host "正在启动 Redis..." -ForegroundColor Yellow
Write-Host ""

# 尝试方法 1: WSL Redis
Write-Host "尝试使用 WSL 启动 Redis..." -ForegroundColor Yellow
try {
    Start-Process wsl -ArgumentList "redis-server" -WindowStyle Normal
    Start-Sleep -Seconds 2
    
    $result = redis-cli ping 2>$null
    if ($result -eq "PONG") {
        Write-Host "✓ Redis 启动成功 (WSL)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Redis 运行在: localhost:6379" -ForegroundColor Cyan
        exit 0
    }
} catch {
    Write-Host "✗ WSL Redis 启动失败" -ForegroundColor Red
}

# 尝试方法 2: Windows Redis
Write-Host "尝试使用 Windows Redis..." -ForegroundColor Yellow
try {
    Start-Process redis-server -WindowStyle Normal
    Start-Sleep -Seconds 2
    
    $result = redis-cli ping 2>$null
    if ($result -eq "PONG") {
        Write-Host "✓ Redis 启动成功 (Windows)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Redis 运行在: localhost:6379" -ForegroundColor Cyan
        exit 0
    }
} catch {
    Write-Host "✗ Windows Redis 启动失败" -ForegroundColor Red
}

# 尝试方法 3: Docker Redis
Write-Host "尝试使用 Docker 启动 Redis..." -ForegroundColor Yellow
try {
    # 检查是否已有 redis 容器
    $container = docker ps -a --filter "name=redis" --format "{{.Names}}" 2>$null
    
    if ($container -eq "redis") {
        # 容器存在，启动它
        docker start redis 2>$null
    } else {
        # 创建新容器
        docker run -d --name redis -p 6379:6379 redis:latest 2>$null
    }
    
    Start-Sleep -Seconds 3
    
    $result = redis-cli ping 2>$null
    if ($result -eq "PONG") {
        Write-Host "✓ Redis 启动成功 (Docker)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Redis 运行在: localhost:6379" -ForegroundColor Cyan
        exit 0
    }
} catch {
    Write-Host "✗ Docker Redis 启动失败" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Red
Write-Host "  Redis 启动失败" -ForegroundColor Red
Write-Host "================================" -ForegroundColor Red
Write-Host ""
Write-Host "请手动安装 Redis:" -ForegroundColor Yellow
Write-Host "  1. WSL: wsl --install, 然后 sudo apt install redis-server" -ForegroundColor Yellow
Write-Host "  2. Windows: 下载 Redis for Windows" -ForegroundColor Yellow
Write-Host "  3. Docker: docker run -d -p 6379:6379 redis:latest" -ForegroundColor Yellow
Write-Host ""

exit 1
