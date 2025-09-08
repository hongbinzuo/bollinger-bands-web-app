#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复币种脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import DEFAULT_SYMBOLS

def clean_duplicates():
    """清理重复币种"""
    print("🔍 清理重复币种")
    print("=" * 50)
    
    # 去重并保持顺序
    unique_symbols = []
    seen = set()
    
    for symbol in DEFAULT_SYMBOLS:
        if symbol not in seen:
            unique_symbols.append(symbol)
            seen.add(symbol)
    
    print(f"📊 原始币种数量: {len(DEFAULT_SYMBOLS)}")
    print(f"📊 去重后数量: {len(unique_symbols)}")
    print(f"📊 删除重复币种: {len(DEFAULT_SYMBOLS) - len(unique_symbols)}")
    
    # 按字母顺序排序
    unique_symbols.sort()
    
    print()
    print("🔍 去重后的币种列表:")
    print("DEFAULT_SYMBOLS = [")
    
    # 每行显示10个币种
    for i in range(0, len(unique_symbols), 10):
        line_symbols = unique_symbols[i:i+10]
        if i + 10 < len(unique_symbols):
            symbols_str = ', '.join([f"'{s}'" for s in line_symbols])
            print(f"    {symbols_str},")
        else:
            symbols_str = ', '.join([f"'{s}'" for s in line_symbols])
            print(f"    {symbols_str}")
    
    print("]")
    
    return unique_symbols

if __name__ == "__main__":
    clean_duplicates()
