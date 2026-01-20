# 一键启动所有服务

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  启动所有服务" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. 启动 Redis
Write-Host "[1/3] 启动 Redis..." -ForegroundColor Yellow
& .\scripts\start_redis.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ Redis 启动失败，无法继续" -ForegroundColor Red
    exit 1
}

Write-Host ""
Start-Sleep -Seconds 2

# 2. 启动后端 API（新窗口）
Write-Host "[2/3] 启动后端 API（新窗口）..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\scripts\start_backend.ps1"
Write-Host "✓ 后端 API 已在新窗口启动" -ForegroundColor Green

Write-Host ""
Start-Sleep -Seconds 3

# 3. 启动 Worker（新窗口）
Write-Host "[3/3] 启动 Worker（新窗口）..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\scripts\start_worker.ps1"
Write-Host "✓ Worker 已在新窗口启动" -ForegroundColor Green

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "  所有服务启动完成" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "服务地址:" -ForegroundColor Cyan
Write-Host "  - 后端 API: http://localhost:8000" -ForegroundColor White
Write-Host "  - API 文档: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Redis: localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "提示: 关闭新打开的窗口可以停止对应的服务" -ForegroundColor Gray
Write-Host ""

# 等待用户按键
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
