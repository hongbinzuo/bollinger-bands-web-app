#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway备份说明脚本
解释本地备份和Railway备份的区别
"""

import os
import json
import platform
import socket

def check_environment():
    """检查当前运行环境"""
    print("=" * 60)
    print("🔍 环境检查")
    print("=" * 60)
    
    # 检查操作系统
    print(f"📍 操作系统: {platform.system()} {platform.release()}")
    
    # 检查主机名
    hostname = socket.gethostname()
    print(f"🖥️ 主机名: {hostname}")
    
    # 检查工作目录
    current_dir = os.getcwd()
    print(f"📁 当前目录: {current_dir}")
    
    # 检查环境变量
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    railway_project = os.getenv('RAILWAY_PROJECT_ID')
    
    print(f"🚂 Railway环境: {railway_env or '未设置'}")
    print(f"📋 Railway项目ID: {railway_project or '未设置'}")
    
    # 判断是否在Railway容器中
    is_railway = bool(railway_env or railway_project)
    
    if is_railway:
        print("✅ 当前运行在Railway容器中")
    else:
        print("❌ 当前运行在本地环境中")
    
    return is_railway

def show_backup_difference():
    """显示本地备份和Railway备份的区别"""
    print("\n" + "=" * 60)
    print("📋 本地备份 vs Railway备份")
    print("=" * 60)
    
    print("\n🔴 本地备份（当前情况）:")
    print("   • 备份本地Windows文件")
    print("   • 数据来源: C:\\Users\\zuoho\\code\\bollinger-bands-web-app")
    print("   • 用户数据: 本地开发环境的测试数据")
    print("   • 用途: 开发测试")
    
    print("\n🟢 Railway备份（生产环境）:")
    print("   • 备份Railway容器中的文件")
    print("   • 数据来源: Railway容器内的用户真实数据")
    print("   • 用户数据: 生产环境中用户添加的真实币种")
    print("   • 用途: 生产数据保护")
    
    print("\n" + "=" * 60)
    print("🚀 正确的Railway备份流程")
    print("=" * 60)
    
    print("\n1️⃣ 在本地Windows执行:")
    print("   railway run python railway_backup.py")
    
    print("\n2️⃣ Railway CLI会:")
    print("   • 连接到Railway服务器")
    print("   • 在Railway容器内执行备份脚本")
    print("   • 备份容器内的真实用户数据")
    print("   • 将Base64编码输出到日志")
    
    print("\n3️⃣ 在本地获取结果:")
    print("   railway logs")
    print("   # 复制Base64编码到本地文件")
    
    print("\n4️⃣ 恢复数据:")
    print("   railway run python railway_restore.py base64 \"...\"")
    print("   # 将备份数据恢复到Railway容器")

def demonstrate_correct_usage():
    """演示正确的使用方法"""
    print("\n" + "=" * 60)
    print("💡 正确的使用方法")
    print("=" * 60)
    
    print("\n📝 步骤1: 确保已安装Railway CLI")
    print("   npm install -g @railway/cli")
    
    print("\n📝 步骤2: 登录Railway")
    print("   railway login")
    
    print("\n📝 步骤3: 链接项目")
    print("   cd C:\\Users\\zuoho\\code\\bollinger-bands-web-app")
    print("   railway link")
    
    print("\n📝 步骤4: 执行Railway备份")
    print("   railway run python railway_backup.py")
    print("   # 这会备份Railway容器内的真实数据")
    
    print("\n📝 步骤5: 获取备份结果")
    print("   railway logs")
    print("   # 查看日志中的Base64编码")
    
    print("\n📝 步骤6: 保存备份数据")
    print("   # 复制Base64编码到本地文件 backup_data.txt")
    
    print("\n📝 步骤7: 恢复数据")
    print("   railway run python railway_restore.py base64 \"$(cat backup_data.txt)\"")
    
    print("\n" + "=" * 60)
    print("⚠️ 重要提醒")
    print("=" * 60)
    
    print("\n• 当前演示脚本备份的是本地数据")
    print("• 要备份Railway生产数据，必须使用railway run命令")
    print("• Railway容器内的数据才是用户真实添加的币种")
    print("• 本地数据只是开发环境的测试数据")

def main():
    """主函数"""
    is_railway = check_environment()
    show_backup_difference()
    demonstrate_correct_usage()
    
    if not is_railway:
        print("\n🎯 总结:")
        print("当前您在本地环境中，要备份Railway的真实数据，请使用:")
        print("railway run python railway_backup.py")

if __name__ == "__main__":
    main()

