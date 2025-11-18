#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway容器访问指南
详细说明如何与Railway容器交互
"""

def explain_railway_container_access():
    """解释Railway容器访问方法"""
    print("=" * 70)
    print("🚀 Railway容器访问方法")
    print("=" * 70)
    
    print("\n📋 Railway容器访问方式:")
    print("   • railway run - 在容器内执行命令")
    print("   • railway shell - 启动交互式shell")
    print("   • railway logs - 查看容器日志")
    print("   • railway connect - 端口转发")
    print("   • Railway Dashboard - Web界面")

def show_railway_run_method():
    """展示railway run方法"""
    print("\n" + "=" * 70)
    print("🔧 方法1: railway run（推荐）")
    print("=" * 70)
    
    print("\n📝 基本用法:")
    print("   railway run <command>")
    print("   # 在Railway容器内执行单个命令")
    
    print("\n📝 常用示例:")
    print("   railway run python --version")
    print("   railway run ls -la")
    print("   railway run cat cache/custom_symbols.json")
    print("   railway run python railway_backup.py")
    
    print("\n✅ 优势:")
    print("   • 简单直接")
    print("   • 适合执行脚本")
    print("   • 无需额外配置")
    print("   • 自动连接到正确的容器")

def show_railway_shell_method():
    """展示railway shell方法"""
    print("\n" + "=" * 70)
    print("🔧 方法2: railway shell（交互式）")
    print("=" * 70)
    
    print("\n📝 基本用法:")
    print("   railway shell")
    print("   # 启动交互式shell会话")
    
    print("\n📝 在shell中可以执行:")
    print("   $ ls -la                    # 查看文件")
    print("   $ cat cache/custom_symbols.json  # 查看用户数据")
    print("   $ python railway_backup.py  # 执行备份")
    print("   $ exit                      # 退出shell")
    
    print("\n✅ 优势:")
    print("   • 交互式操作")
    print("   • 可以执行多个命令")
    print("   • 类似SSH终端体验")
    print("   • 适合调试和探索")
    
    print("\n⚠️ 注意:")
    print("   • 会话有超时限制")
    print("   • 容器重启会断开连接")
    print("   • 适合短期操作")

def show_railway_logs_method():
    """展示railway logs方法"""
    print("\n" + "=" * 70)
    print("🔧 方法3: railway logs（日志查看）")
    print("=" * 70)
    
    print("\n📝 基本用法:")
    print("   railway logs")
    print("   # 查看容器日志")
    
    print("\n📝 常用选项:")
    print("   railway logs --follow       # 实时跟踪")
    print("   railway logs --tail 100     # 显示最近100行")
    print("   railway logs --output logs.txt  # 保存到文件")
    
    print("\n✅ 用途:")
    print("   • 查看应用运行状态")
    print("   • 调试错误信息")
    print("   • 监控备份脚本输出")
    print("   • 获取Base64编码数据")

def show_railway_connect_method():
    """展示railway connect方法"""
    print("\n" + "=" * 70)
    print("🔧 方法4: railway connect（端口转发）")
    print("=" * 70)
    
    print("\n📝 基本用法:")
    print("   railway connect")
    print("   # 将本地端口转发到Railway容器")
    
    print("\n📝 指定端口:")
    print("   railway connect 8080")
    print("   # 将本地8080端口转发到容器8080端口")
    
    print("\n✅ 用途:")
    print("   • 本地访问容器服务")
    print("   • 调试Web应用")
    print("   • 数据库连接")
    print("   • 文件下载服务")

def show_dashboard_method():
    """展示Dashboard方法"""
    print("\n" + "=" * 70)
    print("🔧 方法5: Railway Dashboard（Web界面）")
    print("=" * 70)
    
    print("\n📝 访问方式:")
    print("   • 登录 https://railway.app")
    print("   • 选择您的项目")
    print("   • 查看部署状态和日志")
    
    print("\n✅ 功能:")
    print("   • 查看部署状态")
    print("   • 查看实时日志")
    print("   • 管理环境变量")
    print("   • 查看资源使用情况")
    print("   • 重启服务")

def show_practical_examples():
    """展示实际使用示例"""
    print("\n" + "=" * 70)
    print("🎯 实际使用示例")
    print("=" * 70)
    
    print("\n📝 查看容器内文件:")
    print("   railway run ls -la")
    print("   railway run cat cache/custom_symbols.json")
    
    print("\n📝 执行备份脚本:")
    print("   railway run python railway_backup.py")
    
    print("\n📝 查看备份结果:")
    print("   railway logs --tail 50")
    
    print("\n📝 交互式操作:")
    print("   railway shell")
    print("   # 在shell中执行多个命令")
    
    print("\n📝 端口转发:")
    print("   railway connect 8080")
    print("   # 在浏览器访问 http://localhost:8080")

def show_common_commands():
    """展示常用命令"""
    print("\n" + "=" * 70)
    print("📋 常用Railway命令")
    print("=" * 70)
    
    print("\n🔍 查看状态:")
    print("   railway status              # 查看项目状态")
    print("   railway logs                # 查看日志")
    print("   railway variables           # 查看环境变量")
    
    print("\n🚀 执行命令:")
    print("   railway run <command>       # 执行单个命令")
    print("   railway shell               # 启动交互式shell")
    print("   railway connect [port]      # 端口转发")
    
    print("\n📁 文件操作:")
    print("   railway run ls -la          # 列出文件")
    print("   railway run cat <file>      # 查看文件内容")
    print("   railway run python <script> # 执行Python脚本")
    
    print("\n🔧 管理操作:")
    print("   railway up                  # 部署项目")
    print("   railway down                # 停止服务")
    print("   railway restart             # 重启服务")

def show_troubleshooting():
    """展示故障排除"""
    print("\n" + "=" * 70)
    print("🔧 故障排除")
    print("=" * 70)
    
    print("\n❌ 常见问题:")
    print("   • railway: command not found")
    print("     → 安装Railway CLI: npm install -g @railway/cli")
    
    print("   • Project not linked")
    print("     → 链接项目: railway link")
    
    print("   • Service not running")
    print("     → 启动服务: railway up")
    
    print("   • Permission denied")
    print("     → 检查文件权限和路径")
    
    print("\n✅ 解决步骤:")
    print("   1. 确保已安装Railway CLI")
    print("   2. 确保已登录: railway login")
    print("   3. 确保项目已链接: railway link")
    print("   4. 确保服务正在运行: railway status")

def main():
    """主函数"""
    explain_railway_container_access()
    show_railway_run_method()
    show_railway_shell_method()
    show_railway_logs_method()
    show_railway_connect_method()
    show_dashboard_method()
    show_practical_examples()
    show_common_commands()
    show_troubleshooting()
    
    print("\n" + "=" * 70)
    print("🎯 总结")
    print("=" * 70)
    print("• Railway没有传统SSH终端")
    print("• 使用 railway run 执行命令")
    print("• 使用 railway shell 交互式操作")
    print("• 使用 railway logs 查看日志")
    print("• 使用 railway connect 端口转发")

if __name__ == "__main__":
    main()

