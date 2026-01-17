@echo off
REM 检查 Python 版本脚本

echo ========================================
echo Python 版本检查
echo ========================================
echo.

echo [1] 检查系统 Python 版本:
python --version
echo.

echo [2] 检查是否有 Python 3.12 可用:
py -3.12 --version 2>nul
if %errorlevel% equ 0 (
    echo    ^> Python 3.12 可用 (使用 py -3.12 调用^)
) else (
    echo    ^> Python 3.12 不可用
)
echo.

echo [3] 列出所有已安装的 Python 版本:
py --list 2>nul
if %errorlevel% neq 0 (
    echo    ^> py launcher 不可用
)
echo.

echo [4] 检查虚拟环境:
if exist "venv\Scripts\python.exe" (
    echo    ^> 虚拟环境已存在
    echo    ^> 虚拟环境 Python 版本:
    venv\Scripts\python.exe --version
) else (
    echo    ^> 虚拟环境不存在
)
echo.

echo ========================================
echo 建议操作:
echo ========================================
echo.

python --version | findstr "3.12" >nul
if %errorlevel% equ 0 (
    echo [OK] 当前 Python 版本正确 (3.12^)
    echo.
    echo 下一步:
    echo   1. 创建虚拟环境: python -m venv venv
    echo   2. 激活虚拟环境: venv\Scripts\activate
    echo   3. 安装依赖: pip install -r requirements.txt
) else (
    echo [!] 当前 Python 版本不是 3.12
    echo.
    py -3.12 --version 2>nul
    if %errorlevel% equ 0 (
        echo 检测到 Python 3.12 已安装!
        echo.
        echo 推荐操作:
        echo   1. 使用 py -3.12 创建虚拟环境:
        echo      py -3.12 -m venv venv
        echo   2. 激活虚拟环境:
        echo      venv\Scripts\activate
        echo   3. 安装依赖:
        echo      pip install -r requirements.txt
    ) else (
        echo 系统未检测到 Python 3.12
        echo.
        echo 请先安装 Python 3.12:
        echo   方法 1: 访问 https://www.python.org/downloads/
        echo   方法 2: 使用 pyenv-win
        echo   方法 3: 使用 Chocolatey (choco install python312^)
        echo.
        echo 详细说明: docs\install_python312_windows.md
    )
)
echo.

pause
