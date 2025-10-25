@echo off
chcp 65001 >nul
echo ============================================================
echo 🎯 布林带策略系统 - Waitress服务器
echo ============================================================
echo.

echo 📦 检查并安装Waitress...
python -c "import waitress" 2>nul
if errorlevel 1 (
    echo ⚠️ Waitress未安装，正在安装...
    pip install waitress
    if errorlevel 1 (
        echo ❌ 安装失败，请手动运行: pip install waitress
        pause
        exit /b 1
    )
    echo ✅ Waitress安装完成
) else (
    echo ✅ Waitress已安装
)

echo.
echo 🚀 启动Waitress服务器...
python waitress_server.py

pause
























