# 用户数据备份指南

## 概述

本指南帮助您备份和恢复布林带策略系统中的用户数据，包括用户添加的自定义币种、数据库和其他重要文件。

## 需要备份的数据

### 1. 用户自定义币种
- **位置**: `cache/custom_symbols.json`
- **内容**: 用户通过Web界面添加的币种列表
- **重要性**: ⭐⭐⭐⭐⭐ (最高)

### 2. 数据库文件
- **位置**: `bollinger_strategy.db`
- **内容**: 分析结果、订单、持仓等数据
- **重要性**: ⭐⭐⭐⭐

### 3. 缓存文件
- **位置**: `cache/` 目录
- **内容**: 布林带分析缓存、API响应缓存等
- **重要性**: ⭐⭐⭐

### 4. 日志文件
- **位置**: `logs/` 目录
- **内容**: 系统运行日志
- **重要性**: ⭐⭐

## 备份方法

### 方法一：使用备份脚本（推荐）

1. **执行备份**:
   ```bash
   python backup_user_data.py
   ```

2. **备份结果**:
   - 创建时间戳命名的备份目录，如 `user_data_backup_20250827_202100`
   - 包含所有用户数据的完整备份
   - 生成备份信息文件 `backup_info.json`

### 方法二：手动备份

1. **备份自定义币种**:
   ```bash
   cp cache/custom_symbols.json user_backup/
   ```

2. **备份数据库**:
   ```bash
   cp bollinger_strategy.db user_backup/
   ```

3. **备份缓存目录**:
   ```bash
   cp -r cache user_backup/
   ```

## 恢复方法

### 使用恢复脚本

1. **执行恢复**:
   ```bash
   python restore_user_data.py user_data_backup_20250827_202100
   ```

2. **恢复过程**:
   - 自动恢复自定义币种
   - 恢复数据库文件
   - 恢复缓存目录
   - 显示恢复的币种列表

### 手动恢复

1. **恢复自定义币种**:
   ```bash
   mkdir -p cache
   cp user_backup/custom_symbols.json cache/
   ```

2. **恢复数据库**:
   ```bash
   cp user_backup/bollinger_strategy.db .
   ```

3. **恢复缓存**:
   ```bash
   rm -rf cache
   cp -r user_backup/cache .
   ```

## 部署时的数据迁移

### 场景1：更新应用代码

1. **备份当前数据**:
   ```bash
   python backup_user_data.py
   ```

2. **更新代码**:
   ```bash
   git pull origin main
   # 或上传新版本代码
   ```

3. **恢复用户数据**:
   ```bash
   python restore_user_data.py user_data_backup_20250827_202100
   ```

### 场景2：迁移到新服务器

1. **在旧服务器备份**:
   ```bash
   python backup_user_data.py
   ```

2. **传输备份文件**:
   ```bash
   scp -r user_data_backup_20250827_202100 user@new-server:/path/to/app/
   ```

3. **在新服务器恢复**:
   ```bash
   python restore_user_data.py user_data_backup_20250827_202100
   ```

## 备份文件结构

```
user_data_backup_20250827_202100/
├── custom_symbols.json          # 用户自定义币种
├── bollinger_strategy.db        # 数据库文件
├── cache/                       # 缓存目录
│   ├── custom_symbols.json
│   └── bollinger_cache.pkl
└── backup_info.json             # 备份信息
```

## 注意事项

### ⚠️ 重要提醒

1. **定期备份**: 建议每周备份一次用户数据
2. **测试恢复**: 在重要更新前，先测试恢复流程
3. **备份验证**: 恢复后检查币种列表是否正确
4. **文件权限**: 确保备份文件有适当的读写权限

### 🔧 故障排除

1. **备份失败**:
   - 检查磁盘空间
   - 确认文件权限
   - 查看错误日志

2. **恢复失败**:
   - 确认备份文件完整
   - 检查目标路径权限
   - 验证文件格式

3. **币种丢失**:
   - 检查 `custom_symbols.json` 文件内容
   - 确认恢复脚本执行成功
   - 重启应用验证

## 自动化备份

### 设置定时备份

在Linux/Mac系统中，可以设置cron任务：

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天凌晨2点备份）
0 2 * * * cd /path/to/app && python backup_user_data.py
```

### 备份清理

定期清理旧备份文件：

```bash
# 删除7天前的备份
find . -name "user_data_backup_*" -type d -mtime +7 -exec rm -rf {} \;
```

## 联系支持

如果在备份或恢复过程中遇到问题，请：

1. 检查日志文件
2. 确认文件权限
3. 验证备份文件完整性
4. 联系技术支持

---

**最后更新**: 2025-08-27
**版本**: 1.0

