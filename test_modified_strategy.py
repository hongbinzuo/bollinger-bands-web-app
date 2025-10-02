#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修改后的新策略配置
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_modified_strategy():
    """测试修改后的策略配置"""
    print("=" * 60)
    print("测试修改后的新策略配置")
    print("=" * 60)
    
    # 创建修改策略实例
    modified_strategy = MultiTimeframeStrategy('modified')
    
    print("新策略配置:")
    print(f"  时间框架: {modified_strategy.timeframes}")
    print(f"  止盈配置: {modified_strategy.take_profit_timeframes}")
    
    # 验证配置
    expected_timeframes = ['8h', '12h', '1d', '3d', '1w']
    expected_take_profit = {'8h': '3m', '12h': '3m', '1d': '3m', '3d': '3m', '1w': '3m'}
    
    print("\n验证配置:")
    print(f"  时间框架正确: {modified_strategy.timeframes == expected_timeframes}")
    print(f"  止盈配置正确: {modified_strategy.take_profit_timeframes == expected_take_profit}")
    
    print("\n策略对比:")
    print("原策略:")
    print("  - 时间框架: 4H, 8H, 12H, 1D, 3D, 1W")
    print("  - 止盈: 4H→5M, 8H→15M, 12H→30M, 1D→1H, 3D→4H, 1W→1D")
    
    print("\n修改策略:")
    print("  - 时间框架: 8H, 12H, 1D, 3D, 1W (去掉4H)")
    print("  - 止盈: 全部使用3分钟布林中轨")
    
    print("\n✅ 新策略配置修改完成！")
    print("现在修改策略统一使用3分钟布林中轨作为止盈目标")

if __name__ == "__main__":
    test_modified_strategy()
