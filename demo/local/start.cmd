@echo off
chcp 65001 >nul
setlocal EnableExtensions DisableDelayedExpansion
title BBS 本地演示（一键启动）

rem ---------------------------------------------------------------------------
rem 一键启动入口：
rem   · 切到脚本所在目录，兼容中文/空格路径
rem   · 使用后端虚拟环境 Python 的绝对路径
rem   · 出错时保留窗口，方便查看原因
rem   · 可传参：start.cmd --check
rem ---------------------------------------------------------------------------
cd /d "%~dp0"

set "PYTHON=%~dp0..\..\..\bbs-app-backend\.venv\Scripts\python.exe"
set "RUNNER=%~dp0run.py"

if not exist "%PYTHON%" (
    echo.
    echo [错误] 找不到后端虚拟环境的 Python：
    echo        %PYTHON%
    echo.
    echo 请确认 D:\项目\BBS\bbs-app-backend\.venv 已创建且依赖已安装。
    goto :failed
)

if not exist "%RUNNER%" (
    echo.
    echo [错误] 找不到启动脚本：
    echo        %RUNNER%
    goto :failed
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUNBUFFERED=1"

echo.
echo ================================================================
echo  BBS 本地演示 · 一键启动
echo  后端 API  : http://127.0.0.1:8001
echo  移动 H5   : http://127.0.0.1:5183
echo  PC 网页   : http://127.0.0.1:5184
echo  管理后台  : http://127.0.0.1:5185（依赖已安装时）
echo  停止服务  : 在本窗口按 Ctrl+C
echo ================================================================
echo.

"%PYTHON%" "%RUNNER%" %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo [启动器已退出] 退出码：%EXIT_CODE%
    echo 请查看上方错误信息和 logs\ 目录，窗口将保留。
    goto :failed
)

echo 启动器已结束（退出码 0）。数据库未删除。
echo 按任意键关闭窗口。
pause >nul
exit /b 0

:failed
echo.
echo 按任意键关闭窗口，本窗口内容可用于排查。
pause >nul
exit /b 1
