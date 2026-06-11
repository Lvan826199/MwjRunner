@echo off
REM MwjRunner 示例一键运行脚本（Windows）
REM 用途：启动 FastAPI 示例服务，运行主要示例用例（基础/数据驱动/断言/提取器/认证/变量函数，
REM       不含 advanced/ 和 hooks/ 演示用例），生成报告，停止服务

setlocal EnableDelayedExpansion

echo === MwjRunner 示例一键运行 ===
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

echo [1/4] 安装示例服务依赖...
cd /d "%SCRIPT_DIR%api"
uv sync --quiet
echo   依赖已就绪

echo [2/4] 启动 FastAPI 示例服务...
start /B uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
echo   等待服务启动（5秒）...
timeout /t 5 /nobreak > nul

curl -sf http://127.0.0.1:8000/health > nul 2>&1
if errorlevel 1 (
    echo   ERROR: 示例服务启动失败
    call :stop_server
    exit /b 1
)
echo   服务已就绪 → http://127.0.0.1:8000

echo [3/4] 运行示例用例...
cd /d "%PROJECT_ROOT%"

echo.
echo --- 运行基础示例（smoke 标签）---
uv run mwjrunner run examples/cases/ --base-url http://127.0.0.1:8000 --tags smoke --report console,json,html

echo.
echo --- 运行数据驱动示例 ---
uv run mwjrunner run examples/cases/data_driven/ --base-url http://127.0.0.1:8000 --report console,json,html

echo.
echo --- 运行断言扩展示例 ---
uv run mwjrunner run examples/cases/assertions/ --base-url http://127.0.0.1:8000 --report console,json,html

echo.
echo --- 运行提取器示例 ---
uv run mwjrunner run examples/cases/extractors/ --base-url http://127.0.0.1:8000 --report console,json,html

echo.
echo --- 运行认证示例 ---
uv run mwjrunner run examples/cases/auth/ --base-url http://127.0.0.1:8000 --report console,json,html

echo.
echo --- 运行变量函数示例 ---
uv run mwjrunner run examples/cases/variables/ --base-url http://127.0.0.1:8000 --report console,json,html

echo [4/4] 停止示例服务...
call :stop_server
echo   服务已停止

echo.
echo === 完成！报告已生成到 reports/ 目录 ===
exit /b 0

REM 按命令行精确终止 uvicorn 示例服务进程，避免误杀其他 Python 进程
:stop_server
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn app\.main:app' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" > nul 2>&1
exit /b 0
