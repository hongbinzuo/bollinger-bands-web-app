#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway vs 本地备份演示
澄清本地备份和Railway备份的区别
"""

import os
import platform
import socket

def check_current_environment():
    """检查当前运行环境"""
    print("=" * 70)
    print("🔍 当前运行环境检查")
    print("=" * 70)
    
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
        print("📊 数据来源: Railway容器内的用户真实数据")
    else:
        print("❌ 当前运行在本地环境中")
        print("📊 数据来源: 本地开发环境的测试数据")
    
    return is_railway

def explain_backup_difference():
    """解释备份的区别"""
    print("\n" + "=" * 70)
    print("📋 本地备份 vs Railway备份")
    print("=" * 70)
    
    print("\n🔴 本地备份（当前演示）:")
    print("   • 运行环境: 本地Windows")
    print("   • 数据来源: C:\\Users\\zuoho\\code\\bollinger-bands-web-app")
    print("   • 用户数据: 本地开发环境的测试数据")
    print("   • 用途: 开发测试")
    print("   • 命令: python railway_backup.py")
    
    print("\n🟢 Railway备份（生产环境）:")
    print("   • 运行环境: Railway容器")
    print("   • 数据来源: Railway容器内的用户真实数据")
    print("   • 用户数据: 生产环境中用户添加的真实币种")
    print("   • 用途: 生产数据保护")
    print("   • 命令: railway run python railway_backup.py")

def show_correct_workflow():
    """展示正确的工作流程"""
    print("\n" + "=" * 70)
    print("🚀 正确的Railway备份流程")
    print("=" * 70)
    
    print("\n📝 步骤1: 确保脚本已上传到Railway")
    print("   git add railway_backup.py")
    print("   git commit -m 'Add backup script'")
    print("   git push")
    print("   # 确保脚本在Railway容器中可用")
    
    print("\n📝 步骤2: 在本地执行Railway备份")
    print("   railway run python railway_backup.py")
    print("   # 这个命令会:")
    print("   # • 连接到Railway服务器")
    print("   # • 在Railway容器内执行脚本")
    print("   # • 备份容器内的真实用户数据")
    print("   # • 将Base64编码输出到日志")
    
    print("\n📝 步骤3: 获取备份结果")
    print("   railway logs --tail 100")
    print("   # 查看日志中的Base64编码")
    
    print("\n📝 步骤4: 下载备份文件")
    print("   # 复制Base64编码到本地文件")
    print("   # 使用 decode_backup.py 解码为ZIP文件")

def demonstrate_local_backup():
    """演示本地备份（仅用于测试）"""
    print("\n" + "=" * 70)
    print("🧪 本地备份演示（仅用于测试）")
    print("=" * 70)
    
    print("\n📝 当前演示的是本地备份:")
    print("   • 备份本地Windows文件")
    print("   • 数据来源: 本地开发环境")
    print("   • 这不是生产数据的备份")
    
    print("\n⚠️ 重要提醒:")
    print("   • 本地备份只包含测试数据")
    print("   • 不包含Railway生产环境中的用户真实数据")
    print("   • 要备份真实数据，必须使用railway run命令")

def show_railway_backup_script():
    """展示Railway备份脚本的内容"""
    print("\n" + "=" * 70)
    print("📝 Railway备份脚本内容")
    print("=" * 70)
    
    print("\n📋 railway_backup.py 脚本应该包含:")
    print("   • 在Railway容器内运行")
    print("   • 访问容器内的用户数据文件")
    print("   • 创建备份ZIP文件")
    print("   • 输出Base64编码到日志")
    
    print("\n📋 关键数据文件:")
    print("   • cache/custom_symbols.json - 用户添加的币种")
    print("   • bollinger_strategy.db - 数据库文件")
    print("   • cache/ - 缓存目录")
    print("   • logs/ - 日志目录")

def explain_why_local_backup_is_wrong():
    """解释为什么本地备份是错误的"""
    print("\n" + "=" * 70)
    print("❌ 为什么本地备份是错误的")
    print("=" * 70)
    
    print("\n🚫 问题1: 数据来源错误")
    print("   • 本地备份: 备份本地开发数据")
    print("   • 真实需求: 备份Railway生产数据")
    
    print("\n🚫 问题2: 用户数据丢失")
    print("   • 本地数据: 开发环境的测试数据")
    print("   • 生产数据: 用户真实添加的币种")
    
    print("\n🚫 问题3: 备份目的错误")
    print("   • 本地备份: 开发测试")
    print("   • 真实目的: 保护用户数据")
    
    print("\n✅ 正确的做法:")
    print("   • 使用 railway run 命令")
    print("   • 在Railway容器内执行备份")
    print("   • 备份真实的用户数据")

def show_correct_commands():
    """展示正确的命令"""
    print("\n" + "=" * 70)
    print("✅ 正确的命令")
    print("=" * 70)
    
    print("\n📝 备份Railway生产数据:")
    print("   railway run python railway_backup.py")
    print("   # 在Railway容器内执行，备份真实用户数据")
    
    print("\n📝 查看备份结果:")
    print("   railway logs --tail 100")
    print("   # 查看日志中的Base64编码")
    
    print("\n📝 下载备份文件:")
    print("   # 复制Base64编码到 backup_data.txt")
    print("   python decode_backup.py backup_data.txt")
    
    print("\n📝 恢复数据到Railway:")
    print("   railway run python railway_restore.py base64 \"编码\"")
    print("   # 将备份数据恢复到Railway容器")

def main():
    """主函数"""
    is_railway = check_current_environment()
    explain_backup_difference()
    show_correct_workflow()
    demonstrate_local_backup()
    show_railway_backup_script()
    explain_why_local_backup_is_wrong()
    show_correct_commands()
    
    print("\n" + "=" * 70)
    print("🎯 总结")
    print("=" * 70)
    
    if is_railway:
        print("✅ 当前在Railway容器中，可以直接执行备份")
        print("📝 命令: python railway_backup.py")
    else:
        print("❌ 当前在本地环境中")
        print("📝 要备份Railway真实数据，请使用:")
        print("   railway run python railway_backup.py")
        print("📝 这会备份Railway容器内的用户真实数据")

if __name__ == "__main__":
    main()

