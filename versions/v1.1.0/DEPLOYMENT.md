# 🚀 部署指南

## 解决 ModuleNotFoundError: No module named 'distutils' 问题

这个错误通常出现在Python 3.12+版本中，因为`distutils`模块已被移除。以下是解决方案：

### 方案1: 使用Python 3.11 (推荐)

在`runtime.txt`中指定Python 3.11版本：
```
python-3.11.7
```

### 方案2: 添加setuptools依赖

在`requirements.txt`中添加：
```
setuptools>=65.0.0
```

## 部署平台配置

### Railway

1. **连接GitHub仓库**
2. **自动检测配置**：
   - 构建命令：`pip install -r requirements.txt`
   - 启动命令：`gunicorn app:app`

3. **环境变量**（可选）：
   ```
   PORT=5000
   ```

### Render

1. **创建Web Service**
2. **配置**：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Python Version: 3.11

3. **环境变量**：
   ```
   PYTHON_VERSION=3.11.7
   ```

### Heroku

1. **创建应用**
2. **配置**：
   - 使用`Procfile`：`web: gunicorn app:app`
   - 使用`runtime.txt`指定Python版本

3. **部署命令**：
   ```bash
   heroku create your-app-name
   git push heroku main
   ```

### Vercel

1. **创建vercel.json**：
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "app.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app.py"
       }
     ]
   }
   ```

2. **部署**：
   ```bash
   vercel
   ```

## 常见问题解决

### 1. distutils错误
- 确保使用Python 3.11
- 添加setuptools依赖

### 2. 端口配置
- 使用环境变量`PORT`
- 默认端口5000

### 3. 依赖安装失败
- 检查requirements.txt格式
- 确保所有依赖版本兼容

### 4. 静态文件问题
- 确保templates目录存在
- 检查文件路径

## 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py

# 或使用gunicorn
gunicorn app:app
```

## 健康检查

部署后访问：`https://your-app-url/health`

应该返回：
```json
{
  "status": "healthy",
  "timestamp": "2025-08-15T17:12:00"
}
```
