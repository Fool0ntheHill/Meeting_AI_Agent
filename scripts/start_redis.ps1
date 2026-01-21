# Start Redis Service

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Starting Redis Service" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if Redis is already running
$redisRunning = $false
try {
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
    if ($result -eq "PONG") {
        $redisRunning = $true
    }
} catch {
    $redisRunning = $false
}

if ($redisRunning) {
    Write-Host "OK Redis is already running" -ForegroundColor Green
    Write-Host ""
    exit 0
}

Write-Host "Starting Redis..." -ForegroundColor Yellow
Write-Host ""

# Try Method 1: Docker Redis
Write-Host "Trying to start Redis using Docker..." -ForegroundColor Yellow
try {
    # Check if redis container exists
    $containers = docker ps -a --filter "name=redis" --format "{{.Names}}" 2>$null
    
    if ($containers) {
        # Container exists, start it
        Write-Host "  Found existing Redis container, starting..." -ForegroundColor Gray
        docker start $containers[0] 2>$null | Out-Null
    } else {
        # Create new container
        Write-Host "  Creating new Redis container..." -ForegroundColor Gray
        docker run -d --name redis -p 6379:6379 redis:latest 2>$null | Out-Null
    }
    
    Start-Sleep -Seconds 3
    
    $result = python -c $testScript 2>$null
    if ($result -eq "PONG") {
        Write-Host "OK Redis started successfully (Docker)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Redis running on: localhost:6379" -ForegroundColor Cyan
        exit 0
    }
} catch {
    Write-Host "X Docker Redis failed to start" -ForegroundColor Red
}

# Try Method 2: WSL Redis
Write-Host "Trying to start Redis using WSL..." -ForegroundColor Yellow
try {
    Start-Process wsl -ArgumentList "redis-server" -WindowStyle Normal
    Start-Sleep -Seconds 2
    
    $result = python -c $testScript 2>$null
    if ($result -eq "PONG") {
        Write-Host "OK Redis started successfully (WSL)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Redis running on: localhost:6379" -ForegroundColor Cyan
        exit 0
    }
} catch {
    Write-Host "X WSL Redis failed to start" -ForegroundColor Red
}

# Try Method 3: Windows Redis
Write-Host "Trying to start Redis using Windows..." -ForegroundColor Yellow
try {
    Start-Process redis-server -WindowStyle Normal
    Start-Sleep -Seconds 2
    
    $result = python -c $testScript 2>$null
    if ($result -eq "PONG") {
        Write-Host "OK Redis started successfully (Windows)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Redis running on: localhost:6379" -ForegroundColor Cyan
        exit 0
    }
} catch {
    Write-Host "X Windows Redis failed to start" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Red
Write-Host "  Redis Failed to Start" -ForegroundColor Red
Write-Host "================================" -ForegroundColor Red
Write-Host ""
Write-Host "Please install Redis manually:" -ForegroundColor Yellow
Write-Host "  1. Docker: docker run -d -p 6379:6379 --name redis redis:latest" -ForegroundColor Yellow
Write-Host "  2. WSL: wsl --install, then sudo apt install redis-server" -ForegroundColor Yellow
Write-Host "  3. Windows: Download Redis for Windows" -ForegroundColor Yellow
Write-Host ""

exit 1
