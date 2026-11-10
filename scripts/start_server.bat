@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo 正在启动 xhs-ops 本地服务...
echo.
.venv\Scripts\python.exe -m xhsops serve
echo.
echo 服务已停止。按任意键关闭窗口。
pause >nul
