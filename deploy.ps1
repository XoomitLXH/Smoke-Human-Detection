# 在项目文件夹内右键“用 PowerShell 运行”，或在项目目录下执行: .\deploy.ps1
# 一键完成 Git 初始化、提交、绑定远程、推送

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 确保在仓库内
if (-not (Test-Path ".git")) {
    Write-Host "正在初始化 Git 仓库..."
    git init
}

git config core.quotepath false
Write-Host "添加文件..."
git add .
$status = git status --short
if (-not $status) {
    Write-Host "没有需要提交的更改，跳过提交。"
} else {
    Write-Host "提交..."
    git commit -m "第十六届服务外包创新创业大赛国二作品Demo"
}
git branch -M main

$remote = "https://github.com/XoomitLXH/A25-Demo.git"
git remote remove origin 2>$null
git remote add origin $remote
Write-Host "正在推送到 GitHub ($remote) ..."
Write-Host "若提示登录，请在浏览器中完成授权。"
git push -u origin main
Write-Host "完成。"
