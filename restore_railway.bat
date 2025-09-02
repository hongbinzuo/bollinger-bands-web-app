@echo off
chcp 65001 >nul
echo ========================================
echo Railway用户数据恢复脚本 (Windows版本)
echo ========================================

if "%~1"=="" (
    echo.
    echo 使用方法: restore_railway.bat <backup_base64.txt>
    echo.
    echo 示例: restore_railway.bat backup_data.txt
    echo.
    echo 其中 backup_data.txt 包含Base64编码的备份数据
    echo.
    pause
    exit /b 1
)

if not exist "%~1" (
    echo.
    echo ❌ 备份文件不存在: %~1
    echo.
    pause
    exit /b 1
)

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
echo 正在读取备份数据...
set /p BASE64_CONTENT=<"%~1"

if "%BASE64_CONTENT%"=="" (
    echo ❌ 备份文件为空或格式错误
    pause
    exit /b 1
)

echo ✅ 备份数据读取成功

echo.
echo 开始执行恢复...
railway run python railway_restore.py base64 "%BASE64_CONTENT%"

if %errorlevel% equ 0 (
    echo.
    echo ✅ 恢复完成!
    echo.
    echo 📋 下一步操作:
    echo 1. 重新部署应用
    echo 2. 验证数据恢复是否正确
    echo 3. 检查用户币种列表
    echo.
    echo 重新部署命令: railway up
) else (
    echo.
    echo ❌ 恢复失败，请检查错误信息
)

echo.
pause
