@echo off
chcp 65001 >nul
echo ================================================================
echo 📥 Railway备份文件下载工具
echo ================================================================

echo.
echo 📋 这个工具将帮助您:
echo   1. 执行Railway备份
echo   2. 获取Base64编码
echo   3. 解码为ZIP文件
echo.

REM 检查Railway CLI是否安装
echo 🔍 检查Railway CLI安装状态...
railway --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Railway CLI未安装或未添加到PATH
    echo.
    echo 📝 请先安装Railway CLI:
    echo   npm install -g @railway/cli
    echo.
    echo 📝 或者使用包管理器:
    echo   choco install railway-cli
    echo   或
    echo   scoop install railway
    echo.
    pause
    exit /b 1
)

echo ✅ Railway CLI已安装

REM 检查项目链接
echo.
echo 🔍 检查项目链接状态...
railway status >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 项目未链接到Railway
    echo.
    echo 📝 请先链接项目:
    echo   railway link
    echo.
    pause
    exit /b 1
)

echo ✅ 项目已链接到Railway

REM 执行备份
echo.
echo 🚀 开始执行Railway备份...
echo 📝 这可能需要几分钟时间，请耐心等待...
echo.

railway run python railway_backup.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ 备份执行失败
    echo 📝 请检查:
    echo   • 备份脚本是否存在
    echo   • 项目是否正确链接
    echo   • Railway服务是否正常运行
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ 备份执行完成

REM 查看日志
echo.
echo 📋 查看备份日志...
echo 📝 请查找包含Base64编码的输出
echo.

railway logs --tail 50

echo.
echo ================================================================
echo 📥 下载说明
echo ================================================================
echo.
echo 📝 请按照以下步骤操作:
echo.
echo 1️⃣ 在上面的日志中查找类似输出:
echo    ================================================
echo    📦 备份文件已创建
echo    文件名: railway_backup_20250827_204246.zip
echo    大小: 12345 字节
echo    Base64编码:
echo    UEsDBBQAAAAIAA...
echo    ================================================
echo.
echo 2️⃣ 复制Base64编码部分（UEsDBBQAAAAIAA...）
echo.
echo 3️⃣ 创建 backup_data.txt 文件并粘贴编码
echo.
echo 4️⃣ 运行解码命令:
echo    python decode_backup.py backup_data.txt
echo.
echo 5️⃣ 获得ZIP备份文件
echo.

REM 询问是否继续
echo.
set /p continue="是否现在创建 backup_data.txt 文件? (y/N): "
if /i "%continue%"=="y" (
    echo.
    echo 📝 创建 backup_data.txt 文件...
    echo 请将Base64编码粘贴到下面的文件中，然后保存并关闭:
    echo.
    notepad backup_data.txt
    
    if exist backup_data.txt (
        echo.
        echo ✅ backup_data.txt 文件已创建
        echo.
        set /p decode="是否现在解码为ZIP文件? (y/N): "
        if /i "%decode%"=="y" (
            echo.
            echo 🔓 开始解码...
            python decode_backup.py backup_data.txt
            
            if %errorlevel% equ 0 (
                echo.
                echo 🎉 下载完成!
                echo 📁 您可以在当前目录找到ZIP备份文件
            ) else (
                echo.
                echo ❌ 解码失败，请检查Base64编码是否正确
            )
        )
    ) else (
        echo.
        echo ❌ 未创建 backup_data.txt 文件
    )
)

echo.
echo ================================================================
echo 📖 其他下载方法
echo ================================================================
echo.
echo 🔧 方法1: 使用在线Base64解码工具
echo    • 访问 https://base64.guru/converter/decode/file
echo    • 粘贴Base64编码
echo    • 下载解码后的文件
echo.
echo 🔧 方法2: 使用PowerShell解码
echo    powershell -Command "Add-Type -AssemblyName System.Web.Extensions; [System.Web.HttpUtility]::UrlDecode([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((Get-Content backup_data.txt)))) | Out-File -Encoding UTF8 backup.zip"
echo.
echo 🔧 方法3: 使用Python直接解码
echo    python -c "import base64; open('backup.zip', 'wb').write(base64.b64decode(open('backup_data.txt').read()))"
echo.

pause

