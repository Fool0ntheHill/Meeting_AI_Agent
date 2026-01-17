# PowerShell 脚本: 设置 Python 3.12 环境
# 使用方法: .\scripts\setup_python312.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python 3.12 环境设置脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查当前 Python 版本
Write-Host "[1/6] 检查当前 Python 版本..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "当前版本: $pythonVersion" -ForegroundColor White

if ($pythonVersion -match "3\.12") {
    Write-Host "✓ 已经是 Python 3.12" -ForegroundColor Green
} else {
    Write-Host "✗ 当前不是 Python 3.12" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先安装 Python 3.12:" -ForegroundColor Yellow
    Write-Host "  方法 1: 使用 pyenv-win (推荐)" -ForegroundColor White
    Write-Host "    pyenv install 3.12.8" -ForegroundColor Gray
    Write-Host "    pyenv local 3.12.8" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  方法 2: 直接下载安装" -ForegroundColor White
    Write-Host "    访问: https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host "    下载 Python 3.12.x 并安装" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  方法 3: 使用 py launcher" -ForegroundColor White
    Write-Host "    py -3.12 -m venv venv" -ForegroundColor Gray
    Write-Host ""
    Write-Host "详细说明请查看: docs/install_python312_windows.md" -ForegroundColor Cyan
    Write-Host ""
    
    # 检查是否有 Python 3.12 可用
    $py312Available = py -3.12 --version 2>&1
    if ($py312Available -match "3\.12") {
        Write-Host "检测到系统已安装 Python 3.12!" -ForegroundColor Green
        Write-Host "可以使用 'py -3.12' 来调用" -ForegroundColor White
        Write-Host ""
        $usePy312 = Read-Host "是否使用 py -3.12 创建虚拟环境? (y/n)"
        if ($usePy312 -eq "y" -or $usePy312 -eq "Y") {
            Write-Host ""
            Write-Host "[2/6] 使用 Python 3.12 创建虚拟环境..." -ForegroundColor Yellow
            py -3.12 -m venv venv
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ 虚拟环境创建成功" -ForegroundColor Green
            } else {
                Write-Host "✗ 虚拟环境创建失败" -ForegroundColor Red
                exit 1
            }
            
            Write-Host ""
            Write-Host "[3/6] 激活虚拟环境..." -ForegroundColor Yellow
            & .\venv\Scripts\Activate.ps1
            
            Write-Host ""
            Write-Host "[4/6] 验证 Python 版本..." -ForegroundColor Yellow
            $venvPythonVersion = python --version 2>&1
            Write-Host "虚拟环境版本: $venvPythonVersion" -ForegroundColor White
            
            if ($venvPythonVersion -match "3\.12") {
                Write-Host "✓ 虚拟环境使用 Python 3.12" -ForegroundColor Green
            } else {
                Write-Host "✗ 虚拟环境版本不正确" -ForegroundColor Red
                exit 1
            }
            
            Write-Host ""
            Write-Host "[5/6] 升级 pip..." -ForegroundColor Yellow
            python -m pip install --upgrade pip
            
            Write-Host ""
            Write-Host "[6/6] 安装项目依赖..." -ForegroundColor Yellow
            pip install -r requirements.txt
            
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Cyan
            Write-Host "✓ 环境设置完成!" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "下一步:" -ForegroundColor Yellow
            Write-Host "  1. 验证安装: python -c `"import pyhub; print('pyhub OK')`"" -ForegroundColor White
            Write-Host "  2. 运行测试: python scripts/test_e2e_limited.py --audio test_data/meeting.wav --skip-speaker-recognition" -ForegroundColor White
            Write-Host ""
        } else {
            Write-Host "已取消" -ForegroundColor Yellow
            exit 0
        }
    } else {
        Write-Host "系统未检测到 Python 3.12" -ForegroundColor Red
        Write-Host "请先安装 Python 3.12 后再运行此脚本" -ForegroundColor Yellow
        exit 1
    }
    exit 0
}

# 如果已经是 Python 3.12,继续设置虚拟环境
Write-Host ""
Write-Host "[2/6] 检查虚拟环境..." -ForegroundColor Yellow

if (Test-Path "venv") {
    Write-Host "✓ 虚拟环境已存在" -ForegroundColor Green
    $recreate = Read-Host "是否重新创建虚拟环境? (y/n)"
    if ($recreate -eq "y" -or $recreate -eq "Y") {
        Write-Host "删除旧的虚拟环境..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force venv
        Write-Host "创建新的虚拟环境..." -ForegroundColor Yellow
        python -m venv venv
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ 虚拟环境创建成功" -ForegroundColor Green
        } else {
            Write-Host "✗ 虚拟环境创建失败" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 虚拟环境创建成功" -ForegroundColor Green
    } else {
        Write-Host "✗ 虚拟环境创建失败" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[3/6] 激活虚拟环境..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "[4/6] 验证 Python 版本..." -ForegroundColor Yellow
$venvPythonVersion = python --version 2>&1
Write-Host "虚拟环境版本: $venvPythonVersion" -ForegroundColor White

if ($venvPythonVersion -match "3\.12") {
    Write-Host "✓ 虚拟环境使用 Python 3.12" -ForegroundColor Green
} else {
    Write-Host "✗ 虚拟环境版本不正确" -ForegroundColor Red
    Write-Host "请确保系统 Python 版本为 3.12" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[5/6] 升级 pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host ""
Write-Host "[6/6] 安装项目依赖..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 依赖安装成功" -ForegroundColor Green
} else {
    Write-Host "✗ 依赖安装失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ 环境设置完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "验证安装:" -ForegroundColor Yellow
Write-Host ""

# 验证 pyhub
Write-Host "测试 pyhub..." -ForegroundColor White
python -c "import pyhub; print('✓ pyhub 安装成功')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ pyhub 可用" -ForegroundColor Green
} else {
    Write-Host "✗ pyhub 不可用" -ForegroundColor Red
}

Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 运行配置检查: python scripts/check_config.py --config config/test.yaml" -ForegroundColor White
Write-Host "  2. 运行单元测试: pytest tests/unit/ -v" -ForegroundColor White
Write-Host "  3. 运行端到端测试: python scripts/test_e2e_limited.py --audio test_data/meeting.wav --skip-speaker-recognition" -ForegroundColor White
Write-Host ""
Write-Host "提示: 每次打开新终端时,需要激活虚拟环境:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\activate" -ForegroundColor Gray
Write-Host ""
