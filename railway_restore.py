#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway环境用户数据恢复脚本
支持从Base64编码或ZIP文件恢复
"""

import os
import json
import shutil
import zipfile
import base64
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RailwayRestore:
    def __init__(self):
        self.restore_dir = "railway_restore_temp"
        
    def restore_from_base64(self, base64_content):
        """从Base64编码恢复数据"""
        try:
            logger.info("开始从Base64编码恢复数据...")
            
            # 解码Base64内容
            zip_content = base64.b64decode(base64_content)
            
            # 保存为临时ZIP文件
            temp_zip = "temp_backup.zip"
            with open(temp_zip, 'wb') as f:
                f.write(zip_content)
            
            # 解压并恢复
            success = self.restore_from_zip(temp_zip)
            
            # 清理临时文件
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            
            return success
            
        except Exception as e:
            logger.error(f"从Base64恢复失败: {e}")
            return False
    
    def restore_from_zip(self, zip_path):
        """从ZIP文件恢复数据"""
        try:
            logger.info(f"开始从ZIP文件恢复: {zip_path}")
            
            # 创建临时目录
            os.makedirs(self.restore_dir, exist_ok=True)
            
            # 解压ZIP文件
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(self.restore_dir)
            
            # 恢复数据
            success = self.restore_data()
            
            # 清理临时目录
            if os.path.exists(self.restore_dir):
                shutil.rmtree(self.restore_dir)
            
            return success
            
        except Exception as e:
            logger.error(f"从ZIP恢复失败: {e}")
            return False
    
    def restore_data(self):
        """恢复数据文件"""
        try:
            # 恢复自定义币种
            custom_symbols_file = os.path.join(self.restore_dir, "custom_symbols.json")
            if os.path.exists(custom_symbols_file):
                os.makedirs("cache", exist_ok=True)
                shutil.copy2(custom_symbols_file, "cache/custom_symbols.json")
                logger.info("✅ 恢复自定义币种")
                
                # 显示恢复的币种
                with open("cache/custom_symbols.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"恢复的币种: {data.get('symbols', [])}")
            else:
                logger.warning("⚠️ 自定义币种文件不存在")
            
            # 恢复数据库
            db_file = os.path.join(self.restore_dir, "bollinger_strategy.db")
            if os.path.exists(db_file):
                shutil.copy2(db_file, "bollinger_strategy.db")
                logger.info("✅ 恢复数据库")
            else:
                logger.warning("⚠️ 数据库文件不存在")
            
            # 恢复缓存目录
            cache_backup = os.path.join(self.restore_dir, "cache")
            if os.path.exists(cache_backup):
                if os.path.exists("cache"):
                    shutil.rmtree("cache")
                shutil.copytree(cache_backup, "cache")
                logger.info("✅ 恢复缓存目录")
            else:
                logger.warning("⚠️ 缓存目录不存在")
            
            logger.info("🎉 Railway数据恢复完成!")
            return True
            
        except Exception as e:
            logger.error(f"恢复数据失败: {e}")
            return False

def main():
    """主函数"""
    restore = RailwayRestore()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("1. 从Base64编码恢复:")
        print("   python railway_restore.py base64 <base64_content>")
        print("2. 从ZIP文件恢复:")
        print("   python railway_restore.py zip <zip_file_path>")
        return
    
    method = sys.argv[1]
    
    if method == "base64":
        if len(sys.argv) < 3:
            print("❌ 请提供Base64编码内容")
            return
        
        base64_content = sys.argv[2]
        success = restore.restore_from_base64(base64_content)
        
    elif method == "zip":
        if len(sys.argv) < 3:
            print("❌ 请提供ZIP文件路径")
            return
        
        zip_path = sys.argv[2]
        if not os.path.exists(zip_path):
            print(f"❌ ZIP文件不存在: {zip_path}")
            return
        
        success = restore.restore_from_zip(zip_path)
        
    else:
        print(f"❌ 不支持的方法: {method}")
        return
    
    if success:
        print("\n✅ Railway恢复成功!")
        print("💡 现在可以重新启动应用了")
    else:
        print("\n❌ Railway恢复失败")

if __name__ == "__main__":
    main()

