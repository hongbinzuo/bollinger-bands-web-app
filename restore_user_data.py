#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据恢复脚本
"""

import os
import json
import shutil
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def restore_user_data(backup_path):
    """从备份恢复用户数据"""
    try:
        logger.info(f"开始从 {backup_path} 恢复数据...")
        
        # 恢复自定义币种
        custom_symbols_file = os.path.join(backup_path, "custom_symbols.json")
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
        db_file = os.path.join(backup_path, "bollinger_strategy.db")
        if os.path.exists(db_file):
            shutil.copy2(db_file, "bollinger_strategy.db")
            logger.info("✅ 恢复数据库")
        else:
            logger.warning("⚠️ 数据库文件不存在")
        
        # 恢复缓存目录
        cache_backup = os.path.join(backup_path, "cache")
        if os.path.exists(cache_backup):
            if os.path.exists("cache"):
                shutil.rmtree("cache")
            shutil.copytree(cache_backup, "cache")
            logger.info("✅ 恢复缓存目录")
        else:
            logger.warning("⚠️ 缓存目录不存在")
        
        logger.info("🎉 数据恢复完成!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 恢复数据失败: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python restore_user_data.py <backup_path>")
        print("示例: python restore_user_data.py user_data_backup_20250827_202100")
        return
    
    backup_path = sys.argv[1]
    
    if not os.path.exists(backup_path):
        print(f"❌ 备份路径不存在: {backup_path}")
        return
    
    success = restore_user_data(backup_path)
    
    if success:
        print("\n✅ 恢复成功!")
        print("💡 现在可以重新启动应用了")
    else:
        print("\n❌ 恢复失败")

if __name__ == "__main__":
    main()

