#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据备份脚本
"""

import os
import json
import shutil
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_user_data():
    """备份用户数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"user_data_backup_{timestamp}"
    
    try:
        # 创建备份目录
        os.makedirs(backup_dir, exist_ok=True)
        logger.info(f"创建备份目录: {backup_dir}")
        
        # 备份自定义币种
        if os.path.exists("cache/custom_symbols.json"):
            shutil.copy2("cache/custom_symbols.json", f"{backup_dir}/custom_symbols.json")
            logger.info("备份自定义币种")
        
        # 备份数据库
        if os.path.exists("bollinger_strategy.db"):
            shutil.copy2("bollinger_strategy.db", f"{backup_dir}/bollinger_strategy.db")
            logger.info("备份数据库")
        
        # 备份整个cache目录
        if os.path.exists("cache"):
            shutil.copytree("cache", f"{backup_dir}/cache")
            logger.info("备份缓存目录")
        
        # 创建备份信息
        backup_info = {
            "backup_time": datetime.now().isoformat(),
            "files": os.listdir(backup_dir)
        }
        
        with open(f"{backup_dir}/backup_info.json", 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        logger.info("备份完成!")
        return backup_dir
        
    except Exception as e:
        logger.error(f"备份失败: {e}")
        return None

if __name__ == "__main__":
    backup_dir = backup_user_data()
    if backup_dir:
        print(f"✅ 备份成功: {backup_dir}")
    else:
        print("❌ 备份失败")
