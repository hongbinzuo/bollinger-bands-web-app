# Railway部署指南 - MySQL数据库

## 🚀 Railway MySQL部署步骤

### 1. 创建Railway项目
1. 访问 [Railway.app](https://railway.app)
2. 使用GitHub账号登录
3. 点击 "New Project" → "Deploy from GitHub repo"
4. 选择您的 `bollinger-bands-web-app` 仓库

### 2. 添加MySQL数据库
1. 在项目仪表板中点击 "New"
2. 选择 "Database" → "MySQL"
3. 等待MySQL实例创建完成

### 3. 配置环境变量
Railway会自动为MySQL数据库生成以下环境变量：
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

在项目设置中添加：
```
DATABASE_TYPE=mysql
FLASK_ENV=production
FLASK_DEBUG=false
```

### 4. 连接数据库到应用
1. 在MySQL数据库页面点击 "Connect"
2. 选择您的应用服务
3. Railway会自动共享环境变量

### 5. 部署应用
1. Railway会自动检测到您的代码并开始构建
2. 构建完成后应用会自动部署
3. 访问生成的域名即可使用

## 💰 费用说明

### 免费计划限制
- **每月$5额度**
- MySQL实例会消耗部分额度
- 建议监控使用情况

### 付费计划
- **$5/月起** - 包含更多资源
- 无限制的MySQL使用
- 更好的性能

## 🔧 本地开发配置

### 使用MySQL
```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DATABASE_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=your_username
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=bollinger_strategy

# 运行应用
python app.py
```

### 使用SQLite (默认)
```bash
# 无需额外配置，直接运行
python app.py
```

## 📊 数据库表结构

### analysis_results (分析结果)
- `id` - 主键
- `symbol` - 币种符号
- `current_price` - 当前价格
- `order_price` - 挂单价格
- `status` - 状态
- `timeframe` - 时间级别
- `created_at` - 创建时间

### orders (挂单)
- `id` - 主键
- `symbol` - 币种符号
- `price` - 价格
- `amount` - 数量
- `status` - 状态
- `created_at` - 创建时间

### positions (仓位)
- `id` - 主键
- `symbol` - 币种符号
- `size` - 仓位大小
- `price` - 开仓价格
- `type` - 类型 (long/short)
- `current_price` - 当前价格
- `pnl` - 盈亏
- `created_at` - 创建时间

## 🔍 故障排除

### 常见问题
1. **数据库连接失败**
   - 检查环境变量是否正确设置
   - 确认MySQL实例是否正常运行

2. **表创建失败**
   - 检查数据库权限
   - 确认数据库名称是否正确

3. **应用启动失败**
   - 检查依赖是否正确安装
   - 查看Railway日志

### 日志查看
在Railway仪表板中：
1. 选择您的应用服务
2. 点击 "Logs" 标签
3. 查看实时日志输出

## 📈 性能优化

### MySQL优化建议
1. **索引优化** - 已为常用查询字段添加索引
2. **连接池** - 使用连接管理器避免连接泄漏
3. **查询优化** - 使用参数化查询防止SQL注入

### 监控建议
1. 定期检查数据库连接数
2. 监控查询性能
3. 关注存储空间使用情况



