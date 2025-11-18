# 📊 布林带分析器 Web应用

一个现代化的加密货币布林带分析工具，支持实时获取价格数据并计算智能挂单价格。

## ✨ 功能特性

- 🔄 **双数据源支持**: 优先使用Binance API，失败时自动切换到Gate.io
- 📈 **实时布林带计算**: 12小时K线数据，20周期移动平均线
- 🎯 **智能挂单价格**: 根据价格位置自动计算最佳挂单价格
- 📱 **响应式设计**: 支持手机、平板、电脑访问
- 📊 **实时分析**: 显示分析进度和结果统计
- 📥 **CSV导出**: 一键下载分析结果
- 🌐 **Web界面**: 现代化UI设计，操作简单
- 💾 **智能缓存**: 当天查询过的币种自动缓存，提高查询速度
- 🔄 **强制刷新**: 一键获取最新数据，绕过缓存
- ➕ **币种管理**: 动态添加、删除、查询币种
- ✅ **格式验证**: 自动验证币种格式，确保数据质量

## 🚀 快速开始

### 本地运行

1. **克隆仓库**
```bash
git clone https://github.com/yourusername/bollinger-bands-web-app.git
cd bollinger-bands-web-app
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **启动应用**
```bash
python app.py
```

4. **访问应用**
打开浏览器访问: http://127.0.0.1:5000

### 云部署

#### Railway (推荐)
```bash
# 1. 安装Railway CLI
npm install -g @railway/cli

# 2. 登录Railway
railway login

# 3. 初始化项目
railway init

# 4. 部署
railway up
```

#### Render
1. 连接GitHub仓库
2. 设置构建命令: `pip install -r requirements.txt`
3. 设置启动命令: `python app.py`
4. 自动部署

#### Vercel
```bash
# 1. 安装Vercel CLI
npm install -g vercel

# 2. 部署
vercel
```

## 📋 使用说明

### 币种管理
- **添加币种**: 输入逗号分隔的币种列表，自动添加到分析列表
- **删除币种**: 输入要删除的币种，从列表中移除
- **查询币种**: 输入单个币种，检查是否存在于当前列表中
- **格式验证**: 自动验证币种格式（字母数字组合，最大10字符）
- **预填充**: 默认包含130个热门币种

### 分析结果
- **币种**: 加密货币符号
- **当前价格**: 实时价格
- **中轨**: 20周期移动平均线
- **下轨**: 布林带下轨
- **挂单价格**: 智能计算的挂单价格
- **状态**: 分析成功/失败状态
- **数据源**: Binance或Gate.io
- **缓存时间**: 数据缓存的时间戳

### 挂单价格逻辑
- 价格在中轨和下轨之间 → 挂单价格 = 下轨
- 价格在中轨与(中轨×1.02)之间 → 挂单价格 = 下轨
- 价格在上轨与中轨之间 → 挂单价格 = 中轨
- 价格低于下轨 → 挂单价格 = "已破下轨"
- 其他情况 → 挂单价格 = 中轨

## 🛠️ 技术栈

- **后端**: Flask (Python)
- **前端**: HTML5, CSS3, JavaScript
- **数据处理**: Pandas, NumPy
- **API**: Binance API, Gate.io API
- **部署**: Railway, Render, Vercel

## 📁 项目结构

```
bollinger-bands-web-app/
├── app.py                 # Flask主应用
├── templates/
│   └── index.html        # 前端界面
├── requirements.txt      # Python依赖
├── README.md            # 项目说明
└── .gitignore           # Git忽略文件
```

## 🔧 API接口

### POST /analyze
分析币种列表
```json
{
  "symbols": ["BTC", "ETH", "SOL"],
  "force_refresh": false
}
```

### POST /add_symbols
添加币种到列表
```json
{
  "symbols": "BTC, ETH, SOL",
  "current_symbols": ["BTC", "ETH"]
}
```

### POST /remove_symbols
从列表中删除币种
```json
{
  "symbols": "BTC, ETH",
  "current_symbols": ["BTC", "ETH", "SOL"]
}
```

### POST /search_symbol
查询币种是否存在
```json
{
  "symbol": "BTC",
  "current_symbols": ["BTC", "ETH", "SOL"]
}
```

### POST /clear_cache
清除缓存数据
```json
{}
```

### POST /download_csv
下载CSV文件
```json
{
  "results": [...]
}
```

### GET /health
健康检查
```json
{
  "status": "healthy",
  "timestamp": "2025-08-15T17:12:00"
}
```

## 💡 使用技巧

- **快捷键**: Ctrl+Enter 快速开始分析
- **批量分析**: 一次可以分析多个币种
- **实时监控**: 分析过程中显示进度
- **数据导出**: 分析完成后可下载CSV文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
- [Gate.io API](https://www.gate.io/docs/developers/apiv4)
- [Flask文档](https://flask.palletsprojects.com/)
- [Pandas文档](https://pandas.pydata.org/)

---

⭐ 如果这个项目对您有帮助，请给个Star！
