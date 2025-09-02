# GitHub Actions 自动备份设置指南

## 🚀 功能说明

这个GitHub Actions工作流会自动备份您的Railway应用数据，包括：
- 用户自定义币种
- 数据库文件
- 缓存目录
- 日志文件

## 📋 设置步骤

### 1. 获取Railway Token

```bash
# 在本地终端中执行
railway login
railway whoami
```

然后访问 [Railway Tokens页面](https://railway.app/account/tokens) 创建新的token。

### 2. 获取Railway项目ID

```bash
# 在本地终端中执行
railway status
```

项目ID格式：`45eb250e-3416-451d-b5d0-33b8dad4f4aa`

### 3. 在GitHub仓库中设置Secrets

1. 进入您的GitHub仓库
2. 点击 "Settings" 标签
3. 点击左侧 "Secrets and variables" → "Actions"
4. 点击 "New repository secret"
5. 添加以下两个secrets：

#### Secret 1: RAILWAY_TOKEN
- **Name**: `RAILWAY_TOKEN`
- **Value**: 从步骤1获取的Railway token

#### Secret 2: RAILWAY_PROJECT_ID
- **Name**: `RAILWAY_PROJECT_ID`
- **Value**: 从步骤2获取的项目ID

## 🔄 使用方法

### 手动触发备份
1. 进入GitHub仓库
2. 点击 "Actions" 标签
3. 选择 "Railway Backup" 工作流
4. 点击 "Run workflow" 按钮
5. 选择分支（通常是main）
6. 点击 "Run workflow"

### 自动备份
- 工作流会在每天凌晨2点自动运行
- 备份文件会自动上传到GitHub Releases
- 同时保存为Artifact（保留30天）

## 📥 下载备份文件

### 方法1: 从GitHub Releases下载
1. 在仓库页面点击 "Releases"
2. 找到最新的备份版本（如 "Railway Backup 123"）
3. 下载ZIP文件

### 方法2: 从GitHub Actions Artifacts下载
1. 在 "Actions" 页面点击运行记录
2. 点击 "railway-backup-XXX" artifact
3. 下载ZIP文件

## 🔧 故障排除

### 常见问题
1. **认证失败**: 检查RAILWAY_TOKEN是否正确
2. **项目链接失败**: 检查RAILWAY_PROJECT_ID是否正确
3. **备份文件未生成**: 检查Railway应用是否正常运行

### 查看日志
1. 在Actions页面点击运行记录
2. 查看每个步骤的执行日志
3. 根据错误信息进行调试

## 📝 注意事项

- 备份文件包含敏感数据，请妥善保管
- 建议定期测试恢复流程
- 如果Railway应用结构发生变化，可能需要更新备份脚本
- GitHub Actions有使用限制，免费账户每月有2000分钟限制

## 🆘 获取帮助

如果遇到问题：
1. 检查GitHub Actions的执行日志
2. 确认所有secrets设置正确
3. 验证Railway应用状态
4. 查看Railway应用日志
