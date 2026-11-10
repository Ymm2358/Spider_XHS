# 注册每日计划任务。需要管理员权限：
#   右键 PowerShell -> 以管理员身份运行
#   powershell -ExecutionPolicy Bypass -File E:\xhs-ops\scripts\install_task.ps1
#
# 默认每天 07:30 跑 run_daily.ps1。改时间就改下面的 -At。

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root "scripts\run_daily.ps1"

if (-not (Test-Path $script)) {
    throw "找不到 $script"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""

$trigger = New-ScheduledTaskTrigger -Daily -At "07:30"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName "xhs-ops-daily" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "小红书选题雷达：每日采集、补粉丝数、生成日报" `
    -Force | Out-Null

Write-Host "已注册计划任务 xhs-ops-daily，每天 07:30 运行。"
Write-Host "手动测试：schtasks /Run /TN xhs-ops-daily"
Write-Host "查看状态：schtasks /Query /TN xhs-ops-daily /V /FO LIST"
Write-Host "删除任务：schtasks /Delete /TN xhs-ops-daily /F"
