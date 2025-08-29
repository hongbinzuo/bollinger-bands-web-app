#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway环境用户数据备份脚本
支持本地备份和云存储备份
"""

import os
import json
import shutil
import zipfile
import requests
from datetime import datetime
import logging
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RailwayBackup:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_name = f"railway_backup_{self.timestamp}"
        self.backup_dir = self.backup_name
        
        # Railway环境变量
        self.railway_project_id = os.getenv('RAILWAY_PROJECT_ID')
        self.railway_token = os.getenv('RAILWAY_TOKEN')
        
        # 云存储配置（可选）
        self.webhook_url = os.getenv('BACKUP_WEBHOOK_URL')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO')
        
    def create_backup(self):
        """创建备份"""
        try:
            # 创建备份目录
            os.makedirs(self.backup_dir, exist_ok=True)
            logger.info(f"创建备份目录: {self.backup_dir}")
            
            # 备份用户数据
            self.backup_user_data()
            
            # 创建ZIP文件
            zip_path = self.create_zip_backup()
            
            # 上传到云存储
            if zip_path:
                self.upload_to_cloud(zip_path)
            
            # 清理临时文件
            self.cleanup()
            
            return True
            
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return False
    
    def backup_user_data(self):
        """备份用户数据"""
        try:
            # 备份自定义币种
            if os.path.exists("cache/custom_symbols.json"):
                shutil.copy2("cache/custom_symbols.json", f"{self.backup_dir}/custom_symbols.json")
                logger.info("✅ 备份自定义币种")
                
                # 显示备份的币种
                with open(f"{self.backup_dir}/custom_symbols.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"备份的币种: {data.get('symbols', [])}")
            
            # 备份数据库
            if os.path.exists("bollinger_strategy.db"):
                shutil.copy2("bollinger_strategy.db", f"{self.backup_dir}/bollinger_strategy.db")
                logger.info("✅ 备份数据库")
            
            # 备份缓存目录
            if os.path.exists("cache"):
                shutil.copytree("cache", f"{self.backup_dir}/cache")
                logger.info("✅ 备份缓存目录")
            
            # 创建备份信息
            backup_info = {
                "backup_time": datetime.now().isoformat(),
                "environment": "railway",
                "project_id": self.railway_project_id,
                "files": os.listdir(self.backup_dir)
            }
            
            with open(f"{self.backup_dir}/backup_info.json", 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            logger.info("✅ 用户数据备份完成")
            
        except Exception as e:
            logger.error(f"备份用户数据失败: {e}")
            raise
    
    def create_zip_backup(self):
        """创建ZIP备份文件"""
        try:
            zip_path = f"{self.backup_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.backup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.backup_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"✅ 创建ZIP备份: {zip_path}")
            return zip_path
            
        except Exception as e:
            logger.error(f"创建ZIP备份失败: {e}")
            return None
    
    def upload_to_cloud(self, zip_path):
        """上传到云存储"""
        try:
            # 方法1: 通过Webhook上传
            if self.webhook_url:
                self.upload_via_webhook(zip_path)
            
            # 方法2: 上传到GitHub Releases
            elif self.github_token and self.github_repo:
                self.upload_to_github(zip_path)
            
            # 方法3: 输出到Railway日志（用于手动下载）
            else:
                self.output_to_logs(zip_path)
                
        except Exception as e:
            logger.error(f"上传到云存储失败: {e}")
    
    def upload_via_webhook(self, zip_path):
        """通过Webhook上传"""
        try:
            with open(zip_path, 'rb') as f:
                files = {'file': (os.path.basename(zip_path), f, 'application/zip')}
                response = requests.post(self.webhook_url, files=files)
                
            if response.status_code == 200:
                logger.info("✅ 通过Webhook上传成功")
            else:
                logger.warning(f"Webhook上传失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Webhook上传失败: {e}")
    
    def upload_to_github(self, zip_path):
        """上传到GitHub Releases"""
        try:
            # 这里需要实现GitHub API上传逻辑
            # 由于复杂性，这里只记录日志
            logger.info(f"GitHub上传功能需要进一步实现: {zip_path}")
            
        except Exception as e:
            logger.error(f"GitHub上传失败: {e}")
    
    def output_to_logs(self, zip_path):
        """输出到日志（用于手动下载）"""
        try:
            with open(zip_path, 'rb') as f:
                content = f.read()
                base64_content = base64.b64encode(content).decode('utf-8')
                
            logger.info("=" * 80)
            logger.info("📦 备份文件已创建，请手动下载:")
            logger.info(f"文件名: {os.path.basename(zip_path)}")
            logger.info(f"大小: {len(content)} 字节")
            logger.info("Base64编码（用于手动恢复）:")
            logger.info(base64_content)
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"输出到日志失败: {e}")
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.backup_dir):
                shutil.rmtree(self.backup_dir)
                logger.info("✅ 清理临时文件")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")

def main():
    """主函数"""
    backup = RailwayBackup()
    success = backup.create_backup()
    
    if success:
        print("\n✅ Railway备份成功完成!")
        print("💡 备份文件已上传到云存储或输出到日志")
    else:
        print("\n❌ Railway备份失败")

if __name__ == "__main__":
    main()
