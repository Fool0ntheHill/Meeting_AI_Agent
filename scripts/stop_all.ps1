# 停止所有服务

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  停止所有服务" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 停止后端 API（查找 uvicorn 进程）
Write-Host "停止后端 API..." -ForegroundColor Yellow
$uvicornProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*"
}
if ($uvicornProcesses) {
    $uvicornProcesses | Stop-Process -Force
    Write-Host "✓ 后端 API 已停止" -ForegroundColor Green
} else {
    Write-Host "  后端 API 未运行" -ForegroundColor Gray
}

# 停止 Worker（查找 worker.py 进程）
Write-Host "停止 Worker..." -ForegroundColor Yellow
$workerProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*worker.py*"
}
if ($workerProcesses) {
    $workerProcesses | Stop-Process -Force
    Write-Host "✓ Worker 已停止" -ForegroundColor Green
} else {
    Write-Host "  Worker 未运行" -ForegroundColor Gray
}

# 停止 Redis
Write-Host "停止 Redis..." -ForegroundColor Yellow
try {
    # 尝试优雅关闭
    redis-cli shutdown 2>$null
    Start-Sleep -Seconds 1
    
    # 检查是否还在运行
    $result = redis-cli ping 2>$null
    if ($result -ne "PONG") {
        Write-Host "✓ Redis 已停止" -ForegroundColor Green
    } else {
        Write-Host "  Redis 仍在运行（可能是系统服务）" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Redis 未运行" -ForegroundColor Gray
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "  所有服务已停止" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
