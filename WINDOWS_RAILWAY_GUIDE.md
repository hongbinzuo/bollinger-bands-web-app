# Windows环境Railway CLI安装和使用指南

## 概述

本指南专门为Windows用户提供Railway CLI的安装、配置和使用方法，包括用户数据备份和恢复的完整流程。

## 系统要求

- **操作系统**: Windows 10/11
- **Node.js**: 版本 14.0 或更高
- **npm**: 版本 6.0 或更高
- **PowerShell**: Windows PowerShell 5.1 或更高

## 安装方法

### 方法1: 使用npm安装（推荐）

#### 1. 检查Node.js安装
打开命令提示符或PowerShell，执行：
```cmd
node --version
npm --version
```

如果未安装Node.js，请从 [Node.js官网](https://nodejs.org/) 下载并安装LTS版本。

#### 2. 安装Railway CLI
```cmd
npm install -g @railway/cli
```

#### 3. 验证安装
```cmd
railway --version
```

### 方法2: 使用Chocolatey安装

#### 1. 安装Chocolatey
以管理员身份运行PowerShell，执行：
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### 2. 安装Railway CLI
```powershell
choco install railway-cli
```

### 方法3: 使用Scoop安装

#### 1. 安装Scoop
在PowerShell中执行：
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
```

#### 2. 安装Railway CLI
```powershell
scoop install railway-cli
```

## 配置和登录

### 1. 登录Railway
```cmd
railway login
```

系统会打开浏览器进行身份验证。

### 2. 链接项目
```cmd
# 进入项目目录
cd C:\Users\zuoho\code\bollinger-bands-web-app

# 链接到Railway项目
railway link
```

### 3. 验证配置
```cmd
# 查看项目状态
railway status

# 查看部署历史
railway deployments
```

## 使用批处理脚本

### 1. 备份脚本使用
```cmd
# 直接运行备份脚本
backup_railway.bat
```

脚本会自动：
- 检查Railway CLI安装状态
- 验证项目链接
- 执行备份操作
- 显示操作结果

### 2. 恢复脚本使用
```cmd
# 从备份文件恢复
restore_railway.bat backup_data.txt
```

其中 `backup_data.txt` 包含Base64编码的备份数据。

## 手动操作步骤

### 1. 执行备份
```cmd
# 进入项目目录
cd C:\Users\zuoho\code\bollinger-bands-web-app

# 执行备份
railway run python railway_backup.py
```

### 2. 查看备份结果
```cmd
# 查看实时日志
railway logs

# 查看最近的日志
railway logs --tail 100
```

### 3. 恢复数据
```cmd
# 从Base64编码恢复
railway run python railway_restore.py base64 "UEsDBBQAAAAIAA..."
```

## 常见问题解决

### 1. PATH环境变量问题
如果提示 `railway` 命令未找到：

1. 检查npm全局安装路径：
   ```cmd
   npm config get prefix
   ```

2. 将路径添加到系统PATH环境变量：
   - 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
   - 在"系统变量"中找到"Path"
   - 添加npm全局安装路径

3. 重启命令提示符或PowerShell

### 2. 权限问题
如果遇到权限错误：

1. 以管理员身份运行命令提示符或PowerShell
2. 或者修改npm配置：
   ```cmd
   npm config set prefix C:\Users\%USERNAME%\AppData\Roaming\npm
   ```

### 3. 网络连接问题
如果无法连接到Railway：

1. 检查网络连接
2. 确认防火墙设置
3. 尝试使用VPN
4. 检查Railway服务状态

### 4. 项目链接失败
如果项目链接失败：

1. 确认已登录Railway：
   ```cmd
   railway whoami
   ```

2. 重新登录：
   ```cmd
   railway logout
   railway login
   ```

3. 手动指定项目ID：
   ```cmd
   railway link --project <project-id>
   ```

## 高级功能

### 1. 查看项目信息
```cmd
# 查看项目详情
railway project

# 查看服务列表
railway service

# 查看变量
railway variables
```

### 2. 部署管理
```cmd
# 部署项目
railway up

# 查看部署状态
railway status

# 回滚部署
railway rollback
```

### 3. 日志管理
```cmd
# 查看实时日志
railway logs --follow

# 查看特定服务的日志
railway logs --service <service-name>

# 导出日志
railway logs --output logs.txt
```

## 自动化脚本

### 1. 创建定时备份任务
使用Windows任务计划程序：

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（每天凌晨2点）
4. 设置操作：启动程序 `backup_railway.bat`

### 2. 创建PowerShell脚本
```powershell
# backup_railway.ps1
param(
    [string]$BackupFile = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
)

Write-Host "开始Railway备份..." -ForegroundColor Green

# 执行备份
railway run python railway_backup.py

# 获取Base64编码并保存
railway logs | Select-String "Base64编码" -Context 0,1 | 
    ForEach-Object { $_.Line.Split(":")[1].Trim() } | 
    Out-File $BackupFile -Encoding UTF8

Write-Host "备份完成，数据已保存到: $BackupFile" -ForegroundColor Green
```

## 最佳实践

### 1. 定期备份
- 设置每日自动备份
- 保留最近7天的备份
- 定期测试恢复流程

### 2. 安全存储
- 将备份文件存储在安全位置
- 使用加密存储敏感数据
- 定期更新备份密钥

### 3. 监控和日志
- 监控备份执行状态
- 记录备份操作日志
- 设置备份失败告警

### 4. 测试恢复
- 定期测试数据恢复
- 验证恢复数据的完整性
- 记录恢复测试结果

## 故障排除

### 1. 检查系统状态
```cmd
# 检查Node.js版本
node --version

# 检查npm版本
npm --version

# 检查Railway CLI版本
railway --version

# 检查Python版本
python --version
```

### 2. 检查网络连接
```cmd
# 测试网络连接
ping api.railway.app

# 测试DNS解析
nslookup api.railway.app
```

### 3. 检查文件权限
```cmd
# 检查当前目录权限
dir

# 检查文件是否存在
if exist railway_backup.py echo 文件存在
```

## 联系支持

如果在Windows环境下遇到问题：

1. 检查系统要求是否满足
2. 查看错误日志和输出信息
3. 尝试重新安装Railway CLI
4. 联系技术支持

---

**最后更新**: 2025-08-27  
**版本**: 1.0  
**适用环境**: Windows 10/11

