# ETH 日报 Git 推送脚本
# 使用方法：在 PowerShell 中运行 .\git_push.ps1

$ErrorActionPreference = "Continue"

# 配置
$repoPath = "C:/Users/ZhuanZ（无密码）/mk-trading"
$commitMessage = "feat: 自动更新ETH日报 $(Get-Date -Format 'yyyyMMdd')"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      ETH 日报 Git 推送脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Git 是否安装
try {
    $gitVersion = git --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: Git 未安装或未添加到 PATH" -ForegroundColor Red
        Write-Host "请从 https://git-scm.com/download/win 下载并安装 Git" -ForegroundColor Yellow
        Write-Host "安装时请勾选 'Add to PATH' 选项" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Git 版本: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: Git 未安装或未添加到 PATH" -ForegroundColor Red
    Write-Host "请从 https://git-scm.com/download/win 下载并安装 Git" -ForegroundColor Yellow
    exit 1
}

# 切换到仓库目录
Set-Location $repoPath
Write-Host "工作目录: $repoPath" -ForegroundColor Gray

# 检查是否为 Git 仓库
if (-not (Test-Path .git)) {
    Write-Host "初始化 Git 仓库..." -ForegroundColor Yellow
    git init
    Write-Host "Git 仓库已初始化" -ForegroundColor Green
    
    # 添加远程仓库（如果存在）
    Write-Host ""
    Write-Host "提示: 如果需要推送到 GitHub，请运行以下命令添加远程仓库：" -ForegroundColor Cyan
    Write-Host "  git remote add origin https://github.com/wanglin141319-bit/eth.git" -ForegroundColor White
    Write-Host ""
}

# 检查远程仓库
$remote = git remote -v 2>$null
if (-not $remote) {
    Write-Host "警告: 未配置远程仓库" -ForegroundColor Yellow
    Write-Host "请运行: git remote add origin <your-repo-url>" -ForegroundColor Yellow
}

# Git 操作
Write-Host ""
Write-Host "执行 Git 操作..." -ForegroundColor Cyan

# git add
try {
    git add .
    Write-Host "✓ git add ." -ForegroundColor Green
} catch {
    Write-Host "✗ git add 失败: $_" -ForegroundColor Red
    exit 1
}

# git status
$status = git status --porcelain
if (-not $status) {
    Write-Host "没有要提交的更改" -ForegroundColor Yellow
    exit 0
}

# git commit
try {
    git commit -m "$commitMessage"
    Write-Host "✓ git commit -m "$commitMessage"" -ForegroundColor Green
} catch {
    Write-Host "✗ git commit 失败: $_" -ForegroundColor Red
    exit 1
}

# git push
try {
    $currentBranch = git branch --show-current
    git push origin $currentBranch
    Write-Host "✓ git push origin $currentBranch" -ForegroundColor Green
} catch {
    Write-Host "✗ git push 失败: $_" -ForegroundColor Red
    Write-Host "可能的解决方案:" -ForegroundColor Yellow
    Write-Host "  1. 检查网络连接" -ForegroundColor Yellow
    Write-Host "  2. 运行 'git remote -v' 确认远程仓库配置正确" -ForegroundColor Yellow
    Write-Host "  3. 如果需要认证，运行 'git config --global credential.helper manager'" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "      Git 推送成功完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
