# 版本管理使用说明

## 📁 版本管理系统

我们已经为您创建了一个完整的版本管理系统，方便您管理不同的历史版本。

### 🚀 快速开始

#### 1. 创建版本备份
```bash
# 创建自动命名的备份
python version_manager.py backup

# 创建指定名称的备份
python version_manager.py backup --version v1.1.0 --description "添加新功能"

# 简写形式
python version_manager.py backup -v v1.1.0 -d "添加新功能"
```

#### 2. 查看所有版本
```bash
python version_manager.py list
```

#### 3. 恢复指定版本
```bash
python version_manager.py restore --version v1.0.0_20250816_164300
```

#### 4. 删除指定版本
```bash
python version_manager.py delete --version v1.0.0_20250816_164300
```

### 📋 当前版本信息

**版本**: v1.0.0_20250816_164300  
**状态**: 稳定版本  
**主要功能**:
- ✅ 布林带分析（多时间周期、批量处理、异步处理）
- ✅ 搜索和排序功能
- ✅ 分页显示（每页30条）
- ✅ 策略挂单（带搜索的下拉列表）
- ✅ 持仓管理
- ✅ CSV导出
- ✅ 去重逻辑

### 📁 目录结构

```
bollinger-bands-web-app/
├── app.py                    # 主应用文件
├── templates/               # 前端模板
│   └── index.html          # 主页面
├── versions/               # 版本备份目录
│   └── v1.0.0_20250816_164300/  # 当前版本备份
│       ├── app.py
│       ├── requirements.txt
│       ├── templates/
│       └── VERSION_INFO.md
├── version_manager.py      # 版本管理工具
└── VERSION_MANAGEMENT.md   # 本文件
```

### 🔧 版本管理工具功能

1. **自动备份**: 创建当前版本的完整备份
2. **版本列表**: 查看所有历史版本
3. **版本恢复**: 恢复到任意历史版本
4. **版本删除**: 删除不需要的版本
5. **自动保护**: 恢复前自动创建备份

### 💡 使用建议

1. **定期备份**: 在重大功能更新前创建备份
2. **版本命名**: 使用有意义的版本名称，如 `v1.1.0_feature_name`
3. **版本描述**: 添加详细的版本描述，便于后续查找
4. **测试恢复**: 定期测试版本恢复功能

### ⚠️ 注意事项

- 恢复版本会覆盖当前文件，请谨慎操作
- 删除版本操作不可恢复，请确认后再执行
- 建议在恢复前手动备份重要数据

### 🆘 常见问题

**Q: 如何查看某个版本的具体内容？**  
A: 直接查看 `versions/版本名/` 目录下的文件

**Q: 恢复版本后如何回到最新版本？**  
A: 使用 `python version_manager.py list` 查看版本列表，然后恢复到最新的备份版本

**Q: 可以同时保留多个版本吗？**  
A: 可以，每个版本都是独立的备份，不会相互影响
