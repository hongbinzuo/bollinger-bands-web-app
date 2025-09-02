@echo off
chcp 65001 >nul
echo ========================================
echo Railway用户数据备份脚本 (Windows版本)
echo ========================================

echo.
echo 正在检查Railway CLI...
railway --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Railway CLI未安装或未添加到PATH
    echo.
    echo 请先安装Railway CLI:
    echo npm install -g @railway/cli
    echo.
    pause
    exit /b 1
)

echo ✅ Railway CLI已安装

echo.
echo 正在检查项目链接...
railway status >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ 项目未链接到Railway
    echo 正在尝试链接项目...
    railway link
    if %errorlevel% neq 0 (
        echo ❌ 项目链接失败
        pause
        exit /b 1
    )
)

echo ✅ 项目已链接

echo.
echo 开始执行备份...
railway run python railway_backup.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ 备份完成!
    echo.
    echo 📋 下一步操作:
    echo 1. 查看Railway日志获取Base64编码
    echo 2. 保存Base64编码到安全位置
    echo 3. 用于后续数据恢复
    echo.
    echo 查看日志命令: railway logs
) else (
    echo.
    echo ❌ 备份失败，请检查错误信息
)

echo.
pause

