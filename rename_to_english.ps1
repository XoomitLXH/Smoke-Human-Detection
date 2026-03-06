# 在项目文件夹内运行此脚本，将当前文件夹重命名为英文
# 运行方式：在项目目录下 PowerShell 执行 .\rename_to_english.ps1

$newName = "A25-Smoke-Human-Detection-Demo"
$currentPath = (Get-Location).Path

if (Split-Path -Leaf $currentPath -eq $newName) {
    Write-Host "文件夹已经是英文名: $newName"
    exit 0
}

$parent = Split-Path -Parent $currentPath
Set-Location $parent
Rename-Item -LiteralPath $currentPath -NewName $newName
$newPath = Join-Path $parent $newName
Write-Host "已重命名为: $newName"
Write-Host "新路径: $newPath"
Write-Host "请关闭 Cursor 后，用新路径重新打开项目: $newPath"
Set-Location $newPath
