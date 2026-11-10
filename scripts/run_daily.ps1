# 每日采集 + 日报

每天定时跑这一条即可。任何一个关键词卡住都不会拖垮整轮：
batch 会按关键词起子进程，超时连同子进程树一起结束。

用法：
  powershell -ExecutionPolicy Bypass -File scripts\run_daily.ps1
  powershell -ExecutionPolicy Bypass -File scripts\run_daily.ps1 -SkipCollect

参数：
  -SkipCollect  只重算日报，不重新采集（调指标时用）
  -Timeout      单个关键词的超时秒数，默认 120
  -Direction    只跑某个方向，默认 all

日志写到 logs\daily-YYYY-MM-DD.log，失败也会留下记录。
注意：不要给小红书挂代理。XHS_PROXY 留空。

param(
    [switch]$SkipCollect,
    [int]$Timeout = 120,
    [string]$Direction = "all"
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("daily-" + (Get-Date -Format "yyyy-MM-dd") + ".log")

function Write-Log($message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $message
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

Write-Log "开始，方向=$Direction，超时=${Timeout}s"

if (-not (Test-Path $python)) {
    Write-Log "找不到 $python，先创建虚拟环境：python -m venv .venv && .venv\Scripts\pip install -r requirements.txt -r requirements-xhsops.txt"
    exit 1
}

Push-Location $root
try {
    Write-Log "doctor 自检"
    & $python -m xhsops doctor --limit 5 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) {
        Write-Log "doctor 未通过，停止。先解决 Cookie 或风控问题。"
        exit 2
    }

    if (-not $SkipCollect) {
        Write-Log "采集"
        & $python -m xhsops batch --direction $Direction --timeout $Timeout 2>&1 | Tee-Object -FilePath $log -Append
        Write-Log "采集结束，退出码 $LASTEXITCODE"

        Write-Log "补作者粉丝数（低频，触发安全验证会自动停）"
        & $python -m xhsops enrich --limit 10 2>&1 | Tee-Object -FilePath $log -Append
    }

    Write-Log "生成日报"
    & $python -m xhsops brief 2>&1 | Tee-Object -FilePath $log -Append

    $today = Get-Date -Format "yyyy-MM-dd"
    $brief = Join-Path $root "reports\$today\brief.md"
    if (Test-Path $brief) {
        Write-Log "完成：$brief"
    } else {
        Write-Log "日报没有生成，检查上面的报错"
        exit 3
    }
}
finally {
    Pop-Location
}
