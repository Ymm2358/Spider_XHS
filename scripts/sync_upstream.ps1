# 同步上游 Spider_XHS
#
# 默认只检查不合并：拉取 upstream，列出新提交和受影响文件。
# 加 -Apply 才真正开分支合并，并在合并后跑 doctor 作为门禁。
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
Push-Location $root

try {
    Write-Host "拉取 upstream..."
    git fetch upstream --prune 2>&1 | Out-Host

    $commits = git log --oneline HEAD..upstream/master
    if (-not $commits) {
        Write-Host "已经是最新，没有需要同步的提交。"
        exit 0
    }

    Write-Host ""
    Write-Host "上游新提交："
    $commits | ForEach-Object { Write-Host "  $_" }

    Write-Host ""
    Write-Host "受影响的文件（只看我们依赖的部分）："
    git diff --stat HEAD upstream/master -- apis/xhs_pc_apis.py apis/xhs_creator_apis.py xhs_utils requirements.txt package.json | Out-Host

    if (-not $Apply) {
        Write-Host ""
        Write-Host "只检查，未合并。确认后加 -Apply 执行。"
        exit 0
    }

    $branch = "sync/upstream-" + (Get-Date -Format "yyyyMMdd-HHmm")
    Write-Host ""
    Write-Host "创建分支 $branch 并合并 upstream/master"
    git checkout -b $branch 2>&1 | Out-Host
    git merge upstream/master --no-edit 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "合并有冲突。手工处理后重新跑 doctor，或 git merge --abort 放弃。"
        exit 2
    }

    Write-Host "合并完成，跑 doctor 验证签名是否还能用"
    & $python -m xhsops doctor --limit 5 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "doctor 未通过，这次上游更新不可用。"
        Write-Host "放弃这次合并：git reset --hard ORIG_HEAD"
        Write-Host "保留分支排查：git checkout -"
        exit 3
    }

    Write-Host ""
    Write-Host "doctor 通过。下一步："
    Write-Host "  git push -u origin $branch"
    Write-Host "  gh pr create --base main --head $branch --title 'chore(sync): 同步上游 $(Get-Date -Format 'yyyy-MM-dd')'"
}
finally {
    Pop-Location
}
