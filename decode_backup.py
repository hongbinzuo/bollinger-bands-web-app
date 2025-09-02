#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway备份文件解码脚本
将Base64编码的备份数据解码为ZIP文件
"""

import base64
import sys
import os
from datetime import datetime

def decode_backup_file(input_file):
    """解码Base64编码的备份文件"""
    print("=" * 60)
    print("🔧 Railway备份文件解码工具")
    print("=" * 60)
    
    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"❌ 错误: 输入文件 '{input_file}' 不存在")
        return False
    
    try:
        # 读取Base64编码
        print(f"📖 读取Base64编码文件: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            base64_content = f.read().strip()
        
        if not base64_content:
            print("❌ 错误: 文件内容为空")
            return False
        
        # 检查Base64编码格式
        if not base64_content.startswith('UEsDBBQAAAAIAA'):
            print("⚠️ 警告: 这可能不是有效的ZIP文件Base64编码")
            print("   通常ZIP文件的Base64编码以 'UEsDBBQAAAAIAA' 开头")
            response = input("是否继续解码? (y/N): ")
            if response.lower() != 'y':
                return False
        
        # 解码Base64
        print("🔓 解码Base64编码...")
        try:
            zip_data = base64.b64decode(base64_content)
        except Exception as e:
            print(f"❌ 错误: Base64解码失败 - {e}")
            return False
        
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"railway_backup_{timestamp}.zip"
        
        # 保存ZIP文件
        print(f"💾 保存ZIP文件: {output_file}")
        with open(output_file, 'wb') as f:
            f.write(zip_data)
        
        # 显示文件信息
        file_size = len(zip_data)
        print(f"✅ 解码完成!")
        print(f"📁 输出文件: {output_file}")
        print(f"📊 文件大小: {file_size:,} 字节 ({file_size/1024:.1f} KB)")
        
        # 验证ZIP文件
        try:
            import zipfile
            with zipfile.ZipFile(output_file, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                print(f"📋 包含文件数量: {len(file_list)}")
                print("📋 文件列表:")
                for file_name in file_list:
                    print(f"   • {file_name}")
        except Exception as e:
            print(f"⚠️ 警告: 无法验证ZIP文件内容 - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 60)
    print("📖 使用说明")
    print("=" * 60)
    
    print("\n📝 使用方法:")
    print("   python decode_backup.py <base64_file>")
    print("   例如: python decode_backup.py backup_data.txt")
    
    print("\n📝 操作步骤:")
    print("   1. 执行备份: railway run python railway_backup.py")
    print("   2. 查看日志: railway logs --tail 100")
    print("   3. 复制Base64编码到 backup_data.txt")
    print("   4. 运行解码: python decode_backup.py backup_data.txt")
    print("   5. 获得ZIP备份文件")
    
    print("\n💡 提示:")
    print("   • Base64编码通常很长，确保完整复制")
    print("   • 不要包含换行符或空格")
    print("   • 保存文件时使用UTF-8编码")
    print("   • 解码后的ZIP文件可以直接解压使用")

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("❌ 错误: 请提供Base64编码文件路径")
        show_usage()
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if input_file in ['-h', '--help', 'help']:
        show_usage()
        return
    
    success = decode_backup_file(input_file)
    
    if success:
        print("\n🎉 解码成功! 您现在可以:")
        print("   • 解压ZIP文件查看备份内容")
        print("   • 使用 restore_user_data.py 恢复数据")
        print("   • 保存ZIP文件作为备份")
    else:
        print("\n❌ 解码失败! 请检查:")
        print("   • Base64编码是否完整")
        print("   • 文件格式是否正确")
        print("   • 文件编码是否为UTF-8")
        sys.exit(1)

if __name__ == "__main__":
    main()

