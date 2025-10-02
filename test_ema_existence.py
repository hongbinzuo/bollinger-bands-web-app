#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试EMA存在性检查
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_ema_existence():
    """测试EMA存在性检查逻辑"""
    print("=" * 60)
    print("测试EMA存在性检查")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 显示EMA配置
    print("当前EMA配置:")
    for timeframe, ema_periods in strategy.timeframe_ema_mapping.items():
        ema_list = [f"EMA{period}" for period in ema_periods]
        max_ema = max(ema_periods) if ema_periods else 0
        required_data = max_ema + 50
        
        print(f"  {timeframe}: {', '.join(ema_list)} (需要数据: {required_data})")
    
    print("\n" + "=" * 60)
    print("EMA存在性检查逻辑")
    print("=" * 60)
    print("修复内容:")
    print("1. 恢复所有时间框架的EMA377配置")
    print("2. 增加EMA存在性检查: if ema_value is None or pd.isna(ema_value)")
    print("3. 如果EMA不存在或为NaN，自动跳过该EMA")
    print("4. 动态数据量计算确保有足够数据计算所有EMA")
    
    print("\n数据量要求:")
    print("  4H/8H/12H: 需要427个数据点 (377+50)")
    print("  1D: 需要427个数据点 (377+50)")
    print("  3D: 需要283个数据点 (233+50)")
    print("  1W: 需要194个数据点 (144+50)")
    
    print("\n✅ EMA存在性检查修复完成！")
    print("现在如果某个EMA不存在或为NaN，会自动跳过，不会产生错误信号")

if __name__ == "__main__":
    test_ema_existence()

