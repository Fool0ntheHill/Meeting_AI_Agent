# Git 初始化和推送脚本
# 使用方法: .\scripts\git_setup_and_push.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git 仓库初始化和推送" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否已经是 Git 仓库
if (Test-Path .git) {
    Write-Host "✓ 已经是 Git 仓库" -ForegroundColor Green
} else {
    Write-Host "初始化 Git 仓库..." -ForegroundColor Yellow
    git init
    Write-Host "✓ Git 仓库初始化完成" -ForegroundColor Green
}

Write-Host ""
Write-Host "添加所有文件..." -ForegroundColor Yellow
git add .

Write-Host ""
Write-Host "提交文件..." -ForegroundColor Yellow
git commit -m "完整项目备份 - 包含配置、数据库、上传文件"

Write-Host ""
Write-Host "设置主分支为 main..." -ForegroundColor Yellow
git branch -M main

Write-Host ""
Write-Host "添加远程仓库..." -ForegroundColor Yellow
$repoUrl = "https://github.com/Fool0ntheHill/Meeting_AI_Agent.git"
Write-Host "仓库地址: $repoUrl" -ForegroundColor Cyan

# 检查是否已经添加了 origin
$remotes = git remote
if ($remotes -contains "origin") {
    Write-Host "远程仓库 origin 已存在，更新地址..." -ForegroundColor Yellow
    git remote set-url origin $repoUrl
} else {
    git remote add origin $repoUrl
}

Write-Host ""
Write-Host "推送到 GitHub..." -ForegroundColor Yellow
Write-Host "注意: 如果这是第一次推送，可能需要输入 GitHub 用户名和密码/Token" -ForegroundColor Yellow
Write-Host ""

git push -u origin main

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ 完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "仓库地址: https://github.com/Fool0ntheHill/Meeting_AI_Agent" -ForegroundColor Cyan
Write-Host ""
Write-Host "在另一台电脑上使用:" -ForegroundColor Yellow
Write-Host "  git clone https://github.com/Fool0ntheHill/Meeting_AI_Agent.git" -ForegroundColor White
Write-Host "  cd Meeting_AI_Agent" -ForegroundColor White
Write-Host "  python -m venv venv" -ForegroundColor White
Write-Host "  venv\Scripts\activate" -ForegroundColor White
Write-Host "  pip install -r requirements.txt" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
