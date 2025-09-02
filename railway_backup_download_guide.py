#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway备份文件下载指南
详细说明如何获取备份文件
"""

def explain_backup_download_methods():
    """解释备份文件下载的各种方法"""
    print("=" * 70)
    print("📥 Railway备份文件下载方法")
    print("=" * 70)
    
    print("\n🎯 方法1: 通过Base64编码（推荐）")
    print("   • 备份脚本输出Base64编码到日志")
    print("   • 从日志中复制Base64编码")
    print("   • 在本地解码为ZIP文件")
    print("   • 无需登录容器，无需额外权限")
    
    print("\n🎯 方法2: 通过Railway CLI下载")
    print("   • 使用 railway run 命令在容器内创建下载链接")
    print("   • 通过HTTP链接下载备份文件")
    print("   • 需要临时暴露文件服务")
    
    print("\n🎯 方法3: 通过环境变量传输")
    print("   • 将Base64编码设置为环境变量")
    print("   • 通过 railway variables 命令获取")
    print("   • 适合小型备份文件")

def show_base64_method():
    """展示Base64方法的具体步骤"""
    print("\n" + "=" * 70)
    print("🔧 方法1: Base64编码下载（推荐）")
    print("=" * 70)
    
    print("\n📋 步骤1: 执行备份")
    print("   railway run python railway_backup.py")
    print("   # 脚本会自动输出Base64编码到日志")
    
    print("\n📋 步骤2: 查看日志")
    print("   railway logs --tail 100")
    print("   # 查找类似输出:")
    print("   # ================================================")
    print("   # 📦 备份文件已创建")
    print("   # 文件名: railway_backup_20250827_204246.zip")
    print("   # 大小: 12345 字节")
    print("   # Base64编码:")
    print("   # UEsDBBQAAAAIAA...")
    print("   # ================================================")
    
    print("\n📋 步骤3: 复制Base64编码")
    print("   # 手动复制Base64编码部分")
    print("   # 保存到本地文件 backup_data.txt")
    
    print("\n📋 步骤4: 解码为ZIP文件")
    print("   # 使用Python脚本解码:")
    print("   python decode_backup.py backup_data.txt")
    print("   # 或者使用在线Base64解码工具")

def show_cli_download_method():
    """展示CLI下载方法"""
    print("\n" + "=" * 70)
    print("🔧 方法2: Railway CLI下载")
    print("=" * 70)
    
    print("\n📋 步骤1: 创建下载脚本")
    print("   # 在容器内创建临时HTTP服务器")
    print("   railway run python create_download_server.py")
    
    print("\n📋 步骤2: 获取下载链接")
    print("   # 脚本会输出类似:")
    print("   # 📥 下载链接: http://localhost:8080/backup.zip")
    print("   # 请在浏览器中访问此链接下载文件")
    
    print("\n📋 步骤3: 下载文件")
    print("   # 使用浏览器或curl下载:")
    print("   curl -O http://localhost:8080/backup.zip")
    
    print("\n⚠️ 注意事项:")
    print("   • 需要临时暴露端口")
    print("   • 下载完成后需要关闭服务器")
    print("   • 适合大型备份文件")

def show_environment_method():
    """展示环境变量方法"""
    print("\n" + "=" * 70)
    print("🔧 方法3: 环境变量传输")
    print("=" * 70)
    
    print("\n📋 步骤1: 设置环境变量")
    print("   railway run python set_backup_env.py")
    print("   # 脚本会将Base64编码设置为环境变量")
    
    print("\n📋 步骤2: 获取环境变量")
    print("   railway variables")
    print("   # 查看所有环境变量")
    print("   # 找到 BACKUP_DATA 变量")
    
    print("\n📋 步骤3: 下载环境变量")
    print("   railway variables get BACKUP_DATA > backup_data.txt")
    print("   # 将Base64编码保存到本地文件")
    
    print("\n⚠️ 限制:")
    print("   • 环境变量有大小限制")
    print("   • 适合小型备份文件")
    print("   • 大型文件建议使用其他方法")

def create_download_scripts():
    """创建下载相关的脚本"""
    print("\n" + "=" * 70)
    print("📝 创建下载脚本")
    print("=" * 70)
    
    print("\n📋 需要创建的脚本:")
    print("   • decode_backup.py - Base64解码脚本")
    print("   • create_download_server.py - 下载服务器脚本")
    print("   • set_backup_env.py - 环境变量设置脚本")
    print("   • download_backup.bat - Windows下载批处理")

def show_practical_example():
    """展示实际操作示例"""
    print("\n" + "=" * 70)
    print("🎯 实际操作示例（推荐方法）")
    print("=" * 70)
    
    print("\n📝 完整操作流程:")
    print("   1. 执行备份: railway run python railway_backup.py")
    print("   2. 查看日志: railway logs --tail 50")
    print("   3. 查找Base64编码输出")
    print("   4. 复制Base64编码（UEsDBBQAAAAIAA...）")
    print("   5. 创建 backup_data.txt 文件")
    print("   6. 粘贴Base64编码到文件")
    print("   7. 运行解码脚本: python decode_backup.py backup_data.txt")
    print("   8. 获得 railway_backup_20250827_204246.zip 文件")
    
    print("\n💡 提示:")
    print("   • Base64编码通常很长，确保完整复制")
    print("   • 不要包含换行符或空格")
    print("   • 保存文件时使用UTF-8编码")
    print("   • 解码后的ZIP文件可以直接解压使用")

def explain_advantages():
    """解释各种方法的优势"""
    print("\n" + "=" * 70)
    print("✅ 各种方法的优势")
    print("=" * 70)
    
    print("\n🎯 Base64编码方法:")
    print("   ✅ 无需额外权限")
    print("   ✅ 无需暴露端口")
    print("   ✅ 适合所有大小的文件")
    print("   ✅ 操作简单直接")
    print("   ✅ 最安全可靠")
    
    print("\n🎯 CLI下载方法:")
    print("   ✅ 适合大型文件")
    print("   ✅ 下载速度快")
    print("   ✅ 支持断点续传")
    print("   ❌ 需要临时暴露端口")
    print("   ❌ 操作相对复杂")
    
    print("\n🎯 环境变量方法:")
    print("   ✅ 操作简单")
    print("   ✅ 无需额外脚本")
    print("   ❌ 有大小限制")
    print("   ❌ 不适合大型文件")

def main():
    """主函数"""
    explain_backup_download_methods()
    show_base64_method()
    show_cli_download_method()
    show_environment_method()
    create_download_scripts()
    show_practical_example()
    explain_advantages()
    
    print("\n" + "=" * 70)
    print("🎯 总结")
    print("=" * 70)
    print("• 不需要登录到容器")
    print("• 推荐使用Base64编码方法")
    print("• 通过Railway CLI获取备份文件")
    print("• 操作简单，安全可靠")

if __name__ == "__main__":
    main()

