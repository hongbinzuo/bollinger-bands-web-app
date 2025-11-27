#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器启动脚本
支持多种启动方式
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def create_logs_dir():
    """创建日志目录"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    print(f"📁 日志目录: {logs_dir.absolute()}")

def start_gunicorn():
    """使用Gunicorn启动服务器"""
    print("🚀 使用Gunicorn启动服务器...")
    
    # 检查Gunicorn是否安装
    try:
        import gunicorn
        print(f"✅ Gunicorn版本: {gunicorn.__version__}")
    except ImportError:
        print("❌ Gunicorn未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "gunicorn"], check=True)
        print("✅ Gunicorn安装完成")
    
    # 启动命令
    cmd = [
        "gunicorn",
        "--config", "gunicorn.conf.py",
        "app:app"
    ]
    
    print(f"🔧 启动命令: {' '.join(cmd)}")
    subprocess.run(cmd)

def start_flask_dev():
    """使用Flask开发服务器启动"""
    print("🚀 使用Flask开发服务器启动...")
    
    # 设置环境变量
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    # 启动Flask应用
    from app import app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True,
        use_reloader=False
    )

def start_flask_prod():
    """使用Flask生产模式启动"""
    print("🚀 使用Flask生产模式启动...")
    
    # 设置环境变量
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_DEBUG'] = '0'
    
    # 启动Flask应用
    from app import app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动布林带策略系统')
    parser.add_argument(
        '--mode', 
        choices=['gunicorn', 'flask-dev', 'flask-prod'], 
        default='gunicorn',
        help='启动模式 (默认: gunicorn)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 布林带策略系统启动器")
    print("=" * 60)
    
    # 创建日志目录
    create_logs_dir()
    
    # 根据模式启动
    if args.mode == 'gunicorn':
        start_gunicorn()
    elif args.mode == 'flask-dev':
        start_flask_dev()
    elif args.mode == 'flask-prod':
        start_flask_prod()

if __name__ == '__main__':
    main()



























