#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动脚本 - 自动选择最佳启动方式
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_gunicorn():
    """检查Gunicorn是否可用"""
    try:
        import gunicorn
        return True
    except ImportError:
        return False

def install_gunicorn():
    """安装Gunicorn"""
    print("📦 正在安装Gunicorn...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "gunicorn"], 
                      check=True, capture_output=True, text=True)
        print("✅ Gunicorn安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Gunicorn安装失败: {e}")
        return False

def start_server():
    """启动服务器"""
    print("🚀 布林带策略系统快速启动")
    print("=" * 50)
    
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    # 检查并安装Gunicorn
    if not check_gunicorn():
        print("⚠️ Gunicorn未安装，正在安装...")
        if not install_gunicorn():
            print("🔄 回退到Flask开发服务器...")
            start_flask_dev()
            return
    
    # 使用Gunicorn启动
    print("🚀 使用Gunicorn启动服务器...")
    print("📊 配置信息:")
    print("   - 工作进程: 自动检测CPU核心数")
    print("   - 监听地址: 0.0.0.0:5000")
    print("   - 日志文件: logs/gunicorn_*.log")
    print("   - 超时时间: 120秒")
    print()
    
    try:
        # 启动Gunicorn
        cmd = ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("🔄 回退到Flask开发服务器...")
        start_flask_dev()

def start_flask_dev():
    """启动Flask开发服务器"""
    print("🚀 使用Flask开发服务器启动...")
    try:
        from app import app
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == '__main__':
    start_server()












