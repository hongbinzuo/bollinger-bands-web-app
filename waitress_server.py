#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Waitress服务器启动脚本
Windows兼容的生产级WSGI服务器
"""

import os
import sys
from pathlib import Path

def create_logs_dir():
    """创建日志目录"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    print(f"📁 日志目录: {logs_dir.absolute()}")

def start_waitress():
    """使用Waitress启动服务器"""
    print("🚀 使用Waitress启动服务器...")
    
    # 检查Waitress是否安装
    try:
        import waitress
        print("✅ Waitress已安装")
    except ImportError:
        print("❌ Waitress未安装，正在安装...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "waitress"], check=True)
        print("✅ Waitress安装完成")
        import waitress
    
    # 导入Flask应用
    from app import app
    
    # 配置信息
    host = "0.0.0.0"
    port = 5000
    threads = 4  # 线程数
    
    print("📊 服务器配置:")
    print(f"   - 监听地址: {host}:{port}")
    print(f"   - 线程数: {threads}")
    print(f"   - 服务器: Waitress")
    print("=" * 50)
    
    try:
        # 启动Waitress服务器
        waitress.serve(
            app,
            host=host,
            port=port,
            threads=threads,
            connection_limit=1000,
            cleanup_interval=30,
            send_bytes=18000,
            channel_timeout=120,
            log_socket_errors=True
        )
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

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

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 布林带策略系统 - Waitress服务器")
    print("=" * 60)
    
    # 创建日志目录
    create_logs_dir()
    
    # 启动Waitress服务器
    start_waitress()

if __name__ == '__main__':
    main()
