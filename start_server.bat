@echo off
chcp 65001 >nul
echo ============================================================
echo 🎯 布林带策略系统启动器
echo ============================================================
echo.

echo 📋 选择启动模式:
echo 1. Gunicorn (推荐 - 生产级)
echo 2. Flask开发模式
echo 3. Flask生产模式
echo.

set /p choice="请选择 (1-3): "

if "%choice%"=="1" (
    echo 🚀 启动Gunicorn服务器...
    python start_server.py --mode gunicorn
) else if "%choice%"=="2" (
    echo 🚀 启动Flask开发服务器...
    python start_server.py --mode flask-dev
) else if "%choice%"=="3" (
    echo 🚀 启动Flask生产服务器...
    python start_server.py --mode flask-prod
) else (
    echo ❌ 无效选择，使用默认模式...
    python start_server.py --mode gunicorn
)

pause



















