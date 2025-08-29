#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway备份脚本（正确版本）
包含环境检查，确保在Railway容器中运行
"""

import os
import json
import base64
import zipfile
import shutil
from datetime import datetime

def check_railway_environment():
    """检查是否在Railway容器中运行"""
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    railway_project = os.getenv('RAILWAY_PROJECT_ID')
    
    if not railway_env and not railway_project:
        print("=" * 60)
        print("❌ 环境检查失败")
        print("=" * 60)
        print("当前运行在本地环境中，无法访问Railway容器数据")
        print()
        print("📝 正确的使用方法:")
        print("   railway run python railway_backup_correct.py")
        print()
        print("📝 或者使用交互式shell:")
        print("   railway shell")
        print("   $ python railway_backup_correct.py")
        print()
        print("⚠️ 重要提醒:")
        print("   • 本地运行只能备份本地测试数据")
        print("   • 要备份Railway生产数据，必须在容器内运行")
        print("   • 使用railway run命令自动在容器内执行")
        return False
    
    print("=" * 60)
    print("✅ 环境检查通过")
    print("=" * 60)
    print(f"🚂 Railway环境: {railway_env}")
    print(f"📋 项目ID: {railway_project}")
    print(f"🖥️ 主机名: {os.getenv('HOSTNAME', '未知')}")
    print(f"📁 工作目录: {os.getcwd()}")
    return True

def backup_user_data():
    """备份用户数据"""
    print("\n" + "=" * 60)
    print("📦 开始备份用户数据")
    print("=" * 60)
    
    # 创建临时备份目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"railway_backup_{timestamp}"
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        print(f"📁 创建备份目录: {backup_dir}")
        
        # 备份文件列表
        files_to_backup = [
            'cache/custom_symbols.json',
            'bollinger_strategy.db'
        ]
        
        # 备份目录列表
        dirs_to_backup = [
            'cache',
            'logs'
        ]
        
        # 备份文件
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                shutil.copy2(file_path, backup_dir)
                print(f"✅ 备份文件: {file_path}")
            else:
                print(f"⚠️ 文件不存在: {file_path}")
        
        # 备份目录
        for dir_path in dirs_to_backup:
            if os.path.exists(dir_path):
                shutil.copytree(dir_path, os.path.join(backup_dir, dir_path))
                print(f"✅ 备份目录: {dir_path}")
            else:
                print(f"⚠️ 目录不存在: {dir_path}")
        
        # 创建备份信息文件
        backup_info = {
            "backup_time": datetime.now().isoformat(),
            "railway_environment": os.getenv('RAILWAY_ENVIRONMENT'),
            "railway_project_id": os.getenv('RAILWAY_PROJECT_ID'),
            "hostname": os.getenv('HOSTNAME'),
            "files_backed_up": [],
            "dirs_backed_up": []
        }
        
        # 记录备份的文件和目录
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                backup_info["files_backed_up"].append(file_path)
        
        for dir_path in dirs_to_backup:
            if os.path.exists(dir_path):
                backup_info["dirs_backed_up"].append(dir_path)
        
        with open(os.path.join(backup_dir, 'backup_info.json'), 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 创建备份信息: backup_info.json")
        
        # 创建ZIP文件
        zip_filename = f"{backup_dir}.zip"
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_dir)
                    zipf.write(file_path, arcname)
        
        # 获取ZIP文件大小
        zip_size = os.path.getsize(zip_filename)
        
        print(f"✅ 创建ZIP文件: {zip_filename}")
        print(f"📊 文件大小: {zip_size:,} 字节 ({zip_size/1024:.1f} KB)")
        
        # 转换为Base64编码
        with open(zip_filename, 'rb') as f:
            zip_data = f.read()
        
        base64_data = base64.b64encode(zip_data).decode('utf-8')
        
        print("\n" + "=" * 60)
        print("📦 备份完成")
        print("=" * 60)
        print(f"📁 备份文件: {zip_filename}")
        print(f"📊 文件大小: {zip_size:,} 字节")
        print(f"🔢 Base64长度: {len(base64_data):,} 字符")
        
        print("\n" + "=" * 60)
        print("📥 下载说明")
        print("=" * 60)
        print("请从日志中复制以下Base64编码:")
        print("=" * 60)
        print(base64_data)
        print("=" * 60)
        
        print("\n💡 使用方法:")
        print("1. 复制上面的Base64编码")
        print("2. 保存到本地文件 backup_data.txt")
        print("3. 运行: python decode_backup.py backup_data.txt")
        
        # 清理临时文件
        shutil.rmtree(backup_dir)
        os.remove(zip_filename)
        print(f"\n🧹 清理临时文件完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 Railway备份脚本启动")
    print("=" * 60)
    
    # 检查环境
    if not check_railway_environment():
        return
    
    # 执行备份
    success = backup_user_data()
    
    if success:
        print("\n🎉 备份成功完成!")
        print("📝 请从日志中复制Base64编码进行下载")
    else:
        print("\n❌ 备份失败!")
        print("📝 请检查错误信息并重试")

if __name__ == "__main__":
    main()
