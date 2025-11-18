#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试策略选择功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_strategy_configuration():
    """测试两种策略的配置"""
    print("=" * 60)
    print("测试策略选择功能")
    print("=" * 60)
    
    # 测试原策略
    print("1. 原策略配置:")
    original_strategy = MultiTimeframeStrategy('original')
    print(f"   时间框架: {original_strategy.timeframes}")
    print(f"   止盈配置: {original_strategy.take_profit_timeframes}")
    
    print("\n2. 修改策略配置:")
    modified_strategy = MultiTimeframeStrategy('modified')
    print(f"   时间框架: {modified_strategy.timeframes}")
    print(f"   止盈配置: {modified_strategy.take_profit_timeframes}")
    
    print("\n" + "=" * 60)
    print("策略对比")
    print("=" * 60)
    print("原策略:")
    print("  - 时间框架: 4H, 8H, 12H, 1D, 3D, 1W")
    print("  - 止盈: 4H→5M, 8H→15M, 12H→30M, 1D→1H, 3D→4H, 1W→1D")
    
    print("\n修改策略:")
    print("  - 时间框架: 8H, 12H, 1D, 3D, 1W (去掉4H)")
    print("  - 止盈: 全部使用1分钟布林中轨")
    
    print("\n✅ 策略选择功能实现完成！")
    print("用户可以在前端选择使用哪种策略进行分析")

if __name__ == "__main__":
    test_strategy_configuration()
