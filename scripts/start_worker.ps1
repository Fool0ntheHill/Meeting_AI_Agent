# Start Worker Service

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Starting Worker Service" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if in virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
}

# Check Redis connection
Write-Host "Checking Redis connection..." -ForegroundColor Yellow
try {
    # Use Python to test Redis connection
    $testScript = @"
import redis
try:
    r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
    r.ping()
    print('PONG')
except:
    print('FAIL')
"@
    
    $result = python -c $testScript 2>$null
    if ($result -ne "PONG") {
        Write-Host "X Redis is not running, please start Redis first" -ForegroundColor Red
        Write-Host "  Run: .\scripts\start_redis.ps1" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    Write-Host "OK Redis connection successful" -ForegroundColor Green
} catch {
    Write-Host "X Redis is not running, please start Redis first" -ForegroundColor Red
    Write-Host "  Run: .\scripts\start_redis.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Starting Worker..." -ForegroundColor Yellow
Write-Host "Worker will process tasks from the queue" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Start worker
python worker.py
