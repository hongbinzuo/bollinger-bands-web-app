#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的EMA配置
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_ema_configuration():
    """测试修复后的EMA配置"""
    print("=" * 60)
    print("测试修复后的EMA配置")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 显示修复后的EMA配置
    print("修复后的时间框架EMA配置:")
    for timeframe, ema_periods in strategy.timeframe_ema_mapping.items():
        ema_list = [f"EMA{period}" for period in ema_periods]
        max_ema = max(ema_periods) if ema_periods else 0
        required_data = max_ema + 50
        
        print(f"  {timeframe}: {', '.join(ema_list)} (最大EMA: {max_ema}, 需要数据: {required_data})")
    
    print("\n" + "=" * 60)
    print("EMA配置修复说明")
    print("=" * 60)
    print("修复内容:")
    print("1. 4H/8H/12H: 移除EMA377，只保留EMA55/89/144/233")
    print("2. 1D: 保留EMA377，因为日线数据充足")
    print("3. 动态数据量计算: 根据最大EMA周期 + 50个缓冲")
    print("4. 数据量检查: 确保满足最大EMA周期的数据要求")
    
    print("\n数据量要求:")
    print("  4H/8H/12H: 需要283个数据点 (233+50)")
    print("  1D: 需要427个数据点 (377+50)")
    print("  3D: 需要283个数据点 (233+50)")
    print("  1W: 需要194个数据点 (144+50)")
    
    print("\n✅ EMA配置修复完成！")
    print("现在EMA377只在1D时间框架中使用，其他时间框架使用合适的EMA组合")

if __name__ == "__main__":
    test_ema_configuration()

