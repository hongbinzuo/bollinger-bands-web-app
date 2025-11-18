# Railway环境用户数据备份指南

## 概述

由于Railway是无状态的环境，用户数据备份需要特殊处理。本指南提供多种备份方案来保护用户添加的币种数据。

## Railway环境特点

- **无状态**: 容器重启后数据会丢失
- **临时存储**: 文件系统是临时的
- **环境变量**: 可以通过环境变量配置
- **日志输出**: 可以通过日志获取数据

## 备份方案

### 方案1: 通过Railway CLI执行备份（推荐）

#### 1. 安装Railway CLI
```bash
npm install -g @railway/cli
```

#### 2. 登录Railway
```bash
railway login
```

#### 3. 执行备份命令
```bash
# 进入项目目录
railway link

# 执行备份脚本
railway run python railway_backup.py
```

#### 4. 查看备份结果
备份脚本会在Railway日志中输出Base64编码的备份文件，您可以：
- 复制Base64编码内容
- 保存到本地文件
- 用于后续恢复

### 方案2: 通过Railway Dashboard执行

#### 1. 在Railway Dashboard中
- 进入项目
- 点击"Deployments"
- 选择最新部署
- 点击"View Logs"

#### 2. 在日志中执行命令
```bash
# 在Railway Dashboard的终端中执行
python railway_backup.py
```

#### 3. 获取备份数据
备份脚本会在日志中输出类似以下内容：
```
================================================================================
📦 备份文件已创建，请手动下载:
文件名: railway_backup_20250827_203355.zip
大小: 12345 字节
Base64编码（用于手动恢复）:
UEsDBBQAAAAIAA...
================================================================================
```

### 方案3: 设置定时备份

#### 1. 创建定时任务脚本
```bash
# 在Railway中创建定时任务
railway run python -c "
import schedule
import time
import subprocess

def backup_job():
    subprocess.run(['python', 'railway_backup.py'])

schedule.every().day.at('02:00').do(backup_job)

while True:
    schedule.run_pending()
    time.sleep(60)
"
```

#### 2. 使用GitHub Actions（推荐）
创建 `.github/workflows/backup.yml`:
```yaml
name: Railway Backup

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点
  workflow_dispatch:     # 手动触发

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      
      - name: Execute Backup
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: |
          railway login --token $RAILWAY_TOKEN
          railway run python railway_backup.py
      
      - name: Save Backup Logs
        run: |
          # 保存备份日志到GitHub
          echo "Backup completed at $(date)" >> backup.log
```

## 恢复方法

### 方法1: 从Base64编码恢复

#### 1. 准备Base64编码
从Railway日志中复制Base64编码内容

#### 2. 执行恢复
```bash
# 在Railway中执行
railway run python railway_restore.py base64 "UEsDBBQAAAAIAA..."
```

### 方法2: 从ZIP文件恢复

#### 1. 上传ZIP文件
将备份ZIP文件上传到Railway项目

#### 2. 执行恢复
```bash
railway run python railway_restore.py zip railway_backup_20250827_203355.zip
```

### 方法3: 通过环境变量恢复

#### 1. 设置环境变量
在Railway Dashboard中设置环境变量：
```
BACKUP_DATA_BASE64=UEsDBBQAAAAIAA...
```

#### 2. 修改应用启动脚本
在 `app.py` 中添加自动恢复逻辑：
```python
import os
import base64
import zipfile

def auto_restore_from_env():
    """从环境变量自动恢复备份"""
    backup_data = os.getenv('BACKUP_DATA_BASE64')
    if backup_data:
        try:
            # 解码并恢复数据
            zip_content = base64.b64decode(backup_data)
            with open('temp_backup.zip', 'wb') as f:
                f.write(zip_content)
            
            # 解压并恢复
            with zipfile.ZipFile('temp_backup.zip', 'r') as zipf:
                zipf.extractall('.')
            
            os.remove('temp_backup.zip')
            print("✅ 自动恢复完成")
        except Exception as e:
            print(f"❌ 自动恢复失败: {e}")

# 在应用启动时调用
if __name__ == '__main__':
    auto_restore_from_env()
    app.run()
```

## 最佳实践

### 1. 定期备份
- **频率**: 每天凌晨2点
- **保留**: 最近7天的备份
- **验证**: 定期测试恢复流程

### 2. 备份验证
```bash
# 验证备份内容
railway run python -c "
import json
with open('cache/custom_symbols.json', 'r') as f:
    data = json.load(f)
    print(f'币种数量: {len(data[\"symbols\"])}')
    print(f'币种列表: {data[\"symbols\"]}')
"
```

### 3. 监控备份状态
- 检查Railway日志中的备份信息
- 确认Base64编码完整性
- 验证文件大小合理性

### 4. 安全存储
- 将Base64编码保存到安全位置
- 使用加密存储备份数据
- 定期更新备份密钥

## 故障排除

### 常见问题

#### 1. 备份脚本执行失败
```bash
# 检查Python环境
railway run python --version

# 检查依赖
railway run pip list

# 检查文件权限
railway run ls -la
```

#### 2. Base64编码不完整
- 确保复制完整的Base64字符串
- 检查是否有换行符干扰
- 验证编码格式正确

#### 3. 恢复失败
```bash
# 检查文件结构
railway run find . -name "*.json" -o -name "*.db"

# 检查文件内容
railway run cat cache/custom_symbols.json
```

#### 4. 磁盘空间不足
```bash
# 检查磁盘使用情况
railway run df -h

# 清理临时文件
railway run rm -rf railway_backup_*
```

## 自动化脚本

### 创建一键备份脚本
```bash
#!/bin/bash
# backup_railway.sh

echo "开始Railway备份..."

# 执行备份
railway run python railway_backup.py

# 获取日志中的Base64编码
railway logs | grep -A 100 "Base64编码" | head -n 1 > backup_base64.txt

echo "备份完成，Base64编码已保存到 backup_base64.txt"
```

### 创建一键恢复脚本
```bash
#!/bin/bash
# restore_railway.sh

if [ -z "$1" ]; then
    echo "使用方法: ./restore_railway.sh <backup_base64.txt>"
    exit 1
fi

echo "开始Railway恢复..."

# 读取Base64编码
BASE64_CONTENT=$(cat $1)

# 执行恢复
railway run python railway_restore.py base64 "$BASE64_CONTENT"

echo "恢复完成"
```

## 联系支持

如果在Railway备份过程中遇到问题：

1. 检查Railway项目状态
2. 查看Railway日志
3. 验证环境变量配置
4. 联系技术支持

---

**最后更新**: 2025-08-27  
**版本**: 1.0  
**适用环境**: Railway

