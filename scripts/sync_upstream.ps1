# 同步上游 Spider_XHS 到 vendor/spider_xhs
#
# 上游文件一律不手改，整层替换。这样永远不会产生 merge 冲突，
# 升级失败时只要 git revert 这一个 commit 就能回到上一版。
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts\sync_upstream.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\sync_upstream.ps1 -Apply

param(
    [switch]$Apply
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$vendor = Join-Path $root "vendor\spider_xhs"
$paths = @("apis", "xhs_utils", "requirements.txt", "package.json", "package-lock.json")

Push-Location $root
try {
    Write-Host "拉取 upstream..."
    git fetch upstream --prune 2>&1 | Out-Host

    $commits = git log --oneline HEAD..upstream/master -- vendor/spider_xhs 2>&1
    if (-not $commits) {
        $upstreamHead = git rev-parse --short upstream/master
        $vendorHead = (Get-Content (Join-Path $vendor "UPSTREAM_COMMIT") -ErrorAction SilentlyContinue)
        if ($vendorHead -and $vendorHead.Trim() -eq $upstreamHead) {
            Write-Host "vendor 已经是 upstream/master（$upstreamHead），不需要同步。"
            exit 0
        }
    }

    $head = git rev-parse --short upstream/master
    Write-Host "上游当前 commit：$head"
    Write-Host ""
    Write-Host "上游最近提交："
    git log --oneline -5 upstream/master 2>&1 | ForEach-Object { Write-Host "  $_" }

    if (-not $Apply) {
        Write-Host ""
        Write-Host "只检查，未替换。确认后加 -Apply 执行。"
        exit 0
    }

    $branch = "sync/upstream-" + (Get-Date -Format "yyyyMMdd-HHmm")
    git checkout -b $branch 2>&1 | Out-Host

    Write-Host "导出上游文件到临时包..."
    $tmp = Join-Path $env:TEMP ("spider_xhs_" + [guid]::NewGuid().ToString("N") + ".zip")
    git archive --format=zip -o $tmp upstream/master -- @paths 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "导出失败，放弃。"
        exit 2
    }

    Write-Host "解压覆盖 vendor..."
    Expand-Archive -Path $tmp -DestinationPath $vendor -Force
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    Set-Content -Path (Join-Path $vendor "UPSTREAM_COMMIT") -Value $head -Encoding utf8

    Write-Host "安装上游 Node 依赖..."
    Push-Location $vendor
    npm install --no-audit --no-fund 2>&1 | Select-Object -Last 3 | Out-Host
    Pop-Location

    Write-Host "跑 doctor 验证签名..."
    & $python -m xhsops doctor --limit 5 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "doctor 未通过。这次上游更新不可用。"
        Write-Host "放弃：git reset --hard ORIG_HEAD"
        Write-Host "保留排查：git checkout -"
        exit 3
    }

    git add vendor/spider_xhs 2>&1 | Out-Host
    git -c user.name="Ymm2358" -c user.email="2412308133@qq.com" commit -m "chore(sync): 上游 vendor 更新到 $head" 2>&1 | Out-Host

    Write-Host ""
    Write-Host "同步完成，doctor 通过。下一步："
    Write-Host "  git push -u origin $branch"
    Write-Host "  gh pr create --repo Ymm2358/Spider_XHS --base master --head $branch"
}
finally {
    Pop-Location
}
