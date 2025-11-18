#!/usr/bin/env python3
"""
安装BTC周二反弹策略分析器依赖
"""

import subprocess
import sys

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ 成功安装 {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装 {package} 失败: {e}")
        return False

def main():
    """安装所需依赖"""
    packages = [
        "requests",
        "pandas", 
        "numpy"
    ]
    
    print("开始安装BTC分析器依赖...")
    print("=" * 40)
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n安装完成: {success_count}/{len(packages)} 个包成功安装")
    
    if success_count == len(packages):
        print("\n✅ 所有依赖安装成功！")
        print("现在可以运行:")
        print("  python btc_tuesday_quick_test.py  # 快速测试")
        print("  python btc_tuesday_recovery_analyzer.py  # 完整分析")
    else:
        print("\n❌ 部分依赖安装失败，请手动安装")

if __name__ == "__main__":
    main()
