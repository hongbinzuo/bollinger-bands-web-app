#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gunicorn配置文件
生产级Web服务器配置
"""

import multiprocessing
import os

# 服务器配置
bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1  # 推荐的工作进程数
worker_class = "sync"
worker_connections = 1000
timeout = 120  # 请求超时时间（秒）
keepalive = 2
max_requests = 1000  # 每个工作进程处理的最大请求数
max_requests_jitter = 100  # 随机抖动，避免所有进程同时重启

# 日志配置
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程管理
preload_app = True  # 预加载应用，节省内存
daemon = False  # 不以后台进程运行，便于调试
pidfile = "gunicorn.pid"

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 性能优化
worker_tmp_dir = "/dev/shm"  # 使用内存作为临时目录（Linux）
# Windows下使用系统临时目录
if os.name == 'nt':
    worker_tmp_dir = os.environ.get('TEMP', '/tmp')

# 环境变量
raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=.',
]

def when_ready(server):
    """服务器准备就绪时的回调"""
    server.log.info("🚀 Gunicorn服务器已启动")
    server.log.info(f"📊 工作进程数: {server.cfg.workers}")
    server.log.info(f"🌐 监听地址: {server.cfg.bind}")

def worker_int(worker):
    """工作进程中断时的回调"""
    worker.log.info("⚠️ 工作进程被中断")

def pre_fork(server, worker):
    """工作进程fork前的回调"""
    server.log.info(f"🔄 启动工作进程 {worker.pid}")

def post_fork(server, worker):
    """工作进程fork后的回调"""
    server.log.info(f"✅ 工作进程 {worker.pid} 已启动")

def worker_abort(worker):
    """工作进程异常退出时的回调"""
    worker.log.info(f"❌ 工作进程 {worker.pid} 异常退出")




















