#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
布林带策略挂单系统 - 版本管理工具
用于备份、恢复和管理不同版本
"""

import os
import shutil
import json
from datetime import datetime
import argparse

class VersionManager:
    def __init__(self, project_root="."):
        self.project_root = project_root
        self.versions_dir = os.path.join(project_root, "versions")
        self.version_info_file = "version_info.json"
        
        # 确保versions目录存在
        if not os.path.exists(self.versions_dir):
            os.makedirs(self.versions_dir)
    
    def create_backup(self, version_name=None, description=""):
        """创建当前版本的备份"""
        if not version_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_name = f"v1.0.0_{timestamp}"
        
        version_dir = os.path.join(self.versions_dir, version_name)
        
        if os.path.exists(version_dir):
            print(f"❌ 版本 {version_name} 已存在")
            return False
        
        # 创建版本目录
        os.makedirs(version_dir)
        
        # 需要备份的文件和目录
        files_to_backup = [
            "app.py",
            "requirements.txt",
            "README.md",
            "DEPLOYMENT.md",
            "Procfile",
            "runtime.txt",
            "vercel.json"
        ]
        
        dirs_to_backup = [
            "templates"
        ]
        
        # 备份文件
        for file_name in files_to_backup:
            src_path = os.path.join(self.project_root, file_name)
            if os.path.exists(src_path):
                dst_path = os.path.join(version_dir, file_name)
                shutil.copy2(src_path, dst_path)
                print(f"✅ 备份文件: {file_name}")
        
        # 备份目录
        for dir_name in dirs_to_backup:
            src_path = os.path.join(self.project_root, dir_name)
            if os.path.exists(src_path):
                dst_path = os.path.join(version_dir, dir_name)
                shutil.copytree(src_path, dst_path)
                print(f"✅ 备份目录: {dir_name}")
        
        # 创建版本信息
        version_info = {
            "version": version_name,
            "created_at": datetime.now().isoformat(),
            "description": description,
            "files": files_to_backup + dirs_to_backup
        }
        
        info_path = os.path.join(version_dir, self.version_info_file)
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 版本备份完成: {version_name}")
        return True
    
    def list_versions(self):
        """列出所有版本"""
        if not os.path.exists(self.versions_dir):
            print("❌ versions目录不存在")
            return
        
        versions = []
        for item in os.listdir(self.versions_dir):
            version_dir = os.path.join(self.versions_dir, item)
            if os.path.isdir(version_dir):
                info_path = os.path.join(version_dir, self.version_info_file)
                if os.path.exists(info_path):
                    with open(info_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    versions.append(info)
                else:
                    versions.append({
                        "version": item,
                        "created_at": "未知",
                        "description": "无描述"
                    })
        
        if not versions:
            print("📁 暂无版本备份")
            return
        
        print("📋 版本列表:")
        print("-" * 80)
        for version in sorted(versions, key=lambda x: x.get('created_at', ''), reverse=True):
            print(f"版本: {version['version']}")
            print(f"创建时间: {version['created_at']}")
            print(f"描述: {version.get('description', '无描述')}")
            print("-" * 80)
    
    def restore_version(self, version_name):
        """恢复到指定版本"""
        version_dir = os.path.join(self.versions_dir, version_name)
        
        if not os.path.exists(version_dir):
            print(f"❌ 版本 {version_name} 不存在")
            return False
        
        # 确认恢复
        print(f"⚠️  即将恢复版本: {version_name}")
        confirm = input("确认恢复吗？这将覆盖当前文件 (y/N): ")
        if confirm.lower() != 'y':
            print("❌ 取消恢复")
            return False
        
        # 备份当前版本
        current_backup = f"backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.create_backup(current_backup, "恢复前的自动备份")
        
        # 恢复文件
        for item in os.listdir(version_dir):
            if item == self.version_info_file:
                continue
            
            src_path = os.path.join(version_dir, item)
            dst_path = os.path.join(self.project_root, item)
            
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            
            print(f"✅ 恢复: {item}")
        
        print(f"✅ 版本恢复完成: {version_name}")
        return True
    
    def delete_version(self, version_name):
        """删除指定版本"""
        version_dir = os.path.join(self.versions_dir, version_name)
        
        if not os.path.exists(version_dir):
            print(f"❌ 版本 {version_name} 不存在")
            return False
        
        # 确认删除
        print(f"⚠️  即将删除版本: {version_name}")
        confirm = input("确认删除吗？此操作不可恢复 (y/N): ")
        if confirm.lower() != 'y':
            print("❌ 取消删除")
            return False
        
        shutil.rmtree(version_dir)
        print(f"✅ 版本删除完成: {version_name}")
        return True

def main():
    parser = argparse.ArgumentParser(description="布林带策略挂单系统 - 版本管理工具")
    parser.add_argument("action", choices=["backup", "list", "restore", "delete"], 
                       help="操作类型")
    parser.add_argument("--version", "-v", help="版本名称")
    parser.add_argument("--description", "-d", default="", help="版本描述")
    
    args = parser.parse_args()
    
    manager = VersionManager()
    
    if args.action == "backup":
        manager.create_backup(args.version, args.description)
    elif args.action == "list":
        manager.list_versions()
    elif args.action == "restore":
        if not args.version:
            print("❌ 请指定要恢复的版本名称")
            return
        manager.restore_version(args.version)
    elif args.action == "delete":
        if not args.version:
            print("❌ 请指定要删除的版本名称")
            return
        manager.delete_version(args.version)

if __name__ == "__main__":
    main()
