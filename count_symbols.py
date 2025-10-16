#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计币种数量脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import DEFAULT_SYMBOLS, get_all_symbols, load_custom_symbols

def count_symbols():
    """统计币种数量"""
    print("🔍 币种数量统计")
    print("=" * 50)
    
    # 统计默认币种
    default_count = len(DEFAULT_SYMBOLS)
    print(f"📊 默认币种数量: {default_count}")
    
    # 统计自定义币种
    custom_symbols = load_custom_symbols()
    custom_count = len(custom_symbols)
    print(f"📊 自定义币种数量: {custom_count}")
    
    # 统计总币种
    all_symbols = get_all_symbols()
    total_count = len(all_symbols)
    print(f"📊 总币种数量: {total_count}")
    
    print()
    print("🔍 币种列表预览:")
    print(f"前10个币种: {all_symbols[:10]}")
    print(f"后10个币种: {all_symbols[-10:]}")
    
    print()
    print("🔍 重复币种检查:")
    # 检查重复币种
    seen = set()
    duplicates = set()
    for symbol in DEFAULT_SYMBOLS:
        if symbol in seen:
            duplicates.add(symbol)
        else:
            seen.add(symbol)
    
    if duplicates:
        print(f"❌ 发现重复币种: {duplicates}")
    else:
        print("✅ 没有重复币种")
    
    print()
    print("🔍 币种格式检查:")
    # 检查币种格式
    invalid_symbols = []
    for symbol in DEFAULT_SYMBOLS:
        if not symbol.endswith('USDT'):
            invalid_symbols.append(symbol)
    
    if invalid_symbols:
        print(f"❌ 格式不正确的币种: {invalid_symbols}")
    else:
        print("✅ 所有币种格式正确")

if __name__ == "__main__":
    count_symbols()






















