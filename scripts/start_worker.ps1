# 启动 Worker 服务

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  启动 Worker 服务" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否在虚拟环境中
if (-not $env:VIRTUAL_ENV) {
    Write-Host "正在激活虚拟环境..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
}

# 检查 Redis 是否运行
Write-Host "检查 Redis 连接..." -ForegroundColor Yellow
try {
    $result = redis-cli ping 2>$null
    if ($result -ne "PONG") {
        Write-Host "✗ Redis 未运行，请先启动 Redis" -ForegroundColor Red
        Write-Host "  运行: .\scripts\start_redis.ps1" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    Write-Host "✓ Redis 连接正常" -ForegroundColor Green
} catch {
    Write-Host "✗ Redis 未运行，请先启动 Redis" -ForegroundColor Red
    Write-Host "  运行: .\scripts\start_redis.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "正在启动 Worker..." -ForegroundColor Yellow
Write-Host "Worker 将处理队列中的任务" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host ""

# 启动 worker
python worker.py
