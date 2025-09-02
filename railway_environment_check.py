#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway环境变量检查
正确识别Railway容器环境
"""

import os
import platform
import socket

def check_railway_environment():
    """检查Railway环境变量"""
    print("=" * 70)
    print("🔍 Railway环境变量检查")
    print("=" * 70)
    
    # 检查操作系统
    print(f"📍 操作系统: {platform.system()} {platform.release()}")
    
    # 检查主机名
    hostname = socket.gethostname()
    print(f"🖥️ 主机名: {hostname}")
    
    # 检查工作目录
    current_dir = os.getcwd()
    print(f"📁 当前目录: {current_dir}")
    
    # 检查所有可能的环境变量
    print("\n📋 环境变量检查:")
    
    # Railway相关环境变量
    railway_vars = [
        'RAILWAY_ENVIRONMENT',
        'RAILWAY_PROJECT_ID',
        'RAILWAY_SERVICE_ID',
        'RAILWAY_DEPLOYMENT_ID',
        'RAILWAY_TOKEN',
        'RAILWAY_PROJECT_NAME',
        'RAILWAY_SERVICE_NAME',
        'PORT',
        'RAILWAY_STATIC_URL',
        'RAILWAY_PUBLIC_DOMAIN'
    ]
    
    railway_found = False
    for var in railway_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {value}")
            railway_found = True
        else:
            print(f"   ❌ {var}: 未设置")
    
    # 检查其他可能的环境变量
    print("\n📋 其他环境变量:")
    other_vars = [
        'HOME',
        'USER',
        'PATH',
        'PYTHONPATH',
        'VIRTUAL_ENV'
    ]
    
    for var in other_vars:
        value = os.getenv(var)
        if value:
            print(f"   📝 {var}: {value}")
    
    # 检查容器相关环境变量
    print("\n📋 容器环境变量:")
    container_vars = [
        'KUBERNETES_SERVICE_HOST',
        'DOCKER_CONTAINER',
        'HOSTNAME',
        'PWD'
    ]
    
    for var in container_vars:
        value = os.getenv(var)
        if value:
            print(f"   🐳 {var}: {value}")
    
    return railway_found

def explain_railway_detection():
    """解释Railway环境检测"""
    print("\n" + "=" * 70)
    print("📝 Railway环境检测说明")
    print("=" * 70)
    
    print("\n🔍 检测方法:")
    print("   1. 检查RAILWAY_*环境变量")
    print("   2. 检查容器相关环境变量")
    print("   3. 检查系统特征")
    
    print("\n✅ Railway容器特征:")
    print("   • 存在RAILWAY_ENVIRONMENT变量")
    print("   • 存在RAILWAY_PROJECT_ID变量")
    print("   • 存在RAILWAY_SERVICE_ID变量")
    print("   • 主机名通常包含容器ID")
    print("   • 工作目录通常是/app")
    
    print("\n❌ 本地环境特征:")
    print("   • 没有RAILWAY_*环境变量")
    print("   • 主机名是本地计算机名")
    print("   • 工作目录是本地路径")
    print("   • 存在本地用户环境变量")

def show_correct_backup_approach():
    """展示正确的备份方法"""
    print("\n" + "=" * 70)
    print("🚀 正确的备份方法")
    print("=" * 70)
    
    print("\n📝 方法1: 使用railway run（推荐）")
    print("   railway run python railway_backup.py")
    print("   # 这个命令会在Railway容器内执行")
    print("   # 自动访问容器内的用户数据")
    
    print("\n📝 方法2: 使用railway shell")
    print("   railway shell")
    print("   # 在交互式shell中执行:")
    print("   $ python railway_backup.py")
    
    print("\n📝 方法3: 检查环境变量")
    print("   # 在脚本中检查RAILWAY_*环境变量")
    print("   # 确保在正确的环境中执行")

def demonstrate_environment_check():
    """演示环境检查"""
    print("\n" + "=" * 70)
    print("🧪 环境检查演示")
    print("=" * 70)
    
    print("\n📝 在脚本中添加环境检查:")
    print("   import os")
    print("   ")
    print("   def is_railway_environment():")
    print("       railway_env = os.getenv('RAILWAY_ENVIRONMENT')")
    print("       railway_project = os.getenv('RAILWAY_PROJECT_ID')")
    print("       return bool(railway_env or railway_project)")
    print("   ")
    print("   if is_railway_environment():")
    print("       print('✅ 运行在Railway容器中')")
    print("       # 执行备份逻辑")
    print("   else:")
    print("       print('❌ 运行在本地环境中')")
    print("       print('请使用: railway run python script.py')")

def show_railway_backup_script_template():
    """展示Railway备份脚本模板"""
    print("\n" + "=" * 70)
    print("📝 Railway备份脚本模板")
    print("=" * 70)
    
    print("\n📋 脚本应该包含:")
    print("   #!/usr/bin/env python3")
    print("   import os")
    print("   import json")
    print("   import base64")
    print("   import zipfile")
    print("   from datetime import datetime")
    print("   ")
    print("   def check_environment():")
    print("       railway_env = os.getenv('RAILWAY_ENVIRONMENT')")
    print("       if not railway_env:")
    print("           print('❌ 请在Railway容器中运行此脚本')")
    print("           print('使用: railway run python script.py')")
    print("           return False")
    print("       print('✅ 运行在Railway容器中')")
    print("       return True")
    print("   ")
    print("   def backup_user_data():")
    print("       # 备份逻辑")
    print("       pass")
    print("   ")
    print("   if __name__ == '__main__':")
    print("       if check_environment():")
    print("           backup_user_data()")

def main():
    """主函数"""
    railway_found = check_railway_environment()
    explain_railway_detection()
    show_correct_backup_approach()
    demonstrate_environment_check()
    show_railway_backup_script_template()
    
    print("\n" + "=" * 70)
    print("🎯 总结")
    print("=" * 70)
    
    if railway_found:
        print("✅ 检测到Railway环境变量")
        print("📝 当前运行在Railway容器中")
        print("📊 可以直接执行备份脚本")
    else:
        print("❌ 未检测到Railway环境变量")
        print("📝 当前运行在本地环境中")
        print("📊 要备份Railway数据，请使用:")
        print("   railway run python railway_backup.py")

if __name__ == "__main__":
    main()

