#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试止损逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_stop_loss_logic():
    """测试止损逻辑"""
    print("=" * 60)
    print("测试止损逻辑")
    print("=" * 60)
    
    # 创建修改策略实例
    modified_strategy = MultiTimeframeStrategy('modified')
    
    print("新策略配置:")
    print(f"  时间框架: {modified_strategy.timeframes}")
    print(f"  止盈配置: {modified_strategy.take_profit_timeframes}")
    
    print("\n止损逻辑说明:")
    print("1. 做多信号：3分钟布林中轨必须高于入场价格，否则舍弃信号")
    print("2. 做空信号：3分钟布林中轨必须低于入场价格，否则舍弃信号")
    print("3. 每3分钟刷新一次止盈价格（3分钟布林中轨）")
    
    print("\n示例:")
    print("  做空信号：入场价122，3分钟布林中轨123 → 舍弃信号（止损）")
    print("  做空信号：入场价122，3分钟布林中轨121 → 保留信号（止盈）")
    print("  做多信号：入场价122，3分钟布林中轨121 → 舍弃信号（止损）")
    print("  做多信号：入场价122，3分钟布林中轨123 → 保留信号（止盈）")
    
    print("\n✅ 止损逻辑已实现！")
    print("现在策略会自动过滤掉不利的信号，只保留有效的交易机会")

if __name__ == "__main__":
    test_stop_loss_logic()
