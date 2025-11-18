#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway备份演示脚本
展示完整的备份流程和文件位置
"""

import os
import json
import shutil
import zipfile
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demonstrate_backup_process():
    """演示备份过程"""
    print("=" * 60)
    print("🚀 Railway备份流程演示")
    print("=" * 60)
    
    # 1. 显示当前工作目录
    current_dir = os.getcwd()
    print(f"📍 当前工作目录: {current_dir}")
    
    # 2. 检查用户数据文件
    print("\n📁 检查用户数据文件:")
    
    custom_symbols_file = "cache/custom_symbols.json"
    if os.path.exists(custom_symbols_file):
        with open(custom_symbols_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"   ✅ 自定义币种文件: {custom_symbols_file}")
            print(f"   📊 币种数量: {len(data.get('symbols', []))}")
            print(f"   🪙 币种列表: {data.get('symbols', [])}")
    else:
        print(f"   ❌ 自定义币种文件不存在: {custom_symbols_file}")
    
    db_file = "bollinger_strategy.db"
    if os.path.exists(db_file):
        size = os.path.getsize(db_file)
        print(f"   ✅ 数据库文件: {db_file} ({size} 字节)")
    else:
        print(f"   ❌ 数据库文件不存在: {db_file}")
    
    # 3. 创建演示备份
    print("\n🔄 创建演示备份:")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    demo_backup_dir = f"demo_backup_{timestamp}"
    
    try:
        # 创建备份目录
        os.makedirs(demo_backup_dir, exist_ok=True)
        print(f"   📂 创建备份目录: {demo_backup_dir}")
        
        # 备份文件
        if os.path.exists(custom_symbols_file):
            shutil.copy2(custom_symbols_file, f"{demo_backup_dir}/custom_symbols.json")
            print(f"   ✅ 备份自定义币种")
        
        if os.path.exists(db_file):
            shutil.copy2(db_file, f"{demo_backup_dir}/bollinger_strategy.db")
            print(f"   ✅ 备份数据库")
        
        # 创建ZIP文件
        zip_path = f"{demo_backup_dir}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(demo_backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, demo_backup_dir)
                    zipf.write(file_path, arcname)
        
        zip_size = os.path.getsize(zip_path)
        print(f"   📦 创建ZIP文件: {zip_path} ({zip_size} 字节)")
        
        # 4. 模拟Base64输出
        print("\n📤 模拟Railway日志输出:")
        print("=" * 60)
        print("📦 备份文件已创建，请手动下载:")
        print(f"文件名: {os.path.basename(zip_path)}")
        print(f"大小: {zip_size} 字节")
        print("Base64编码（用于手动恢复）:")
        
        # 读取ZIP文件并转换为Base64
        with open(zip_path, 'rb') as f:
            content = f.read()
            import base64
            base64_content = base64.b64encode(content).decode('utf-8')
            print(base64_content[:100] + "...")  # 只显示前100个字符
        print("=" * 60)
        
        # 5. 清理演示文件
        print("\n🧹 清理演示文件:")
        if os.path.exists(demo_backup_dir):
            shutil.rmtree(demo_backup_dir)
            print(f"   ✅ 删除临时目录: {demo_backup_dir}")
        
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print(f"   ✅ 删除演示ZIP: {zip_path}")
        
        # 6. 总结
        print("\n📋 备份流程总结:")
        print("   1. 本地执行: railway run python railway_backup.py")
        print("   2. Railway容器内: 创建临时备份文件")
        print("   3. Railway日志: 输出Base64编码")
        print("   4. 本地保存: 复制Base64编码到文件")
        print("   5. 本地恢复: 使用Base64编码恢复数据")
        
        print("\n💡 关键要点:")
        print("   • 备份脚本在Railway容器内执行")
        print("   • 备份文件存储在容器临时空间")
        print("   • Base64编码通过日志传输到本地")
        print("   • 本地保存Base64编码用于恢复")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 演示失败: {e}")
        return False

if __name__ == "__main__":
    demonstrate_backup_process()

