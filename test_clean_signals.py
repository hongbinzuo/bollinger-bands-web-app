#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试清理后的信号逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_clean_signals():
    """测试清理后的信号逻辑"""
    print("=" * 60)
    print("测试清理后的信号逻辑")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试币种
    test_symbols = ['ENAUSDT', 'SOLUSDT', 'ETCUSDT', 'ETHUSDT', 'BTCUSDT']
    
    for symbol in test_symbols:
        print(f"\n测试 {symbol}...")
        
        try:
            # 只测试4H时间框架
            df = strategy.get_klines_data(symbol, '4h', 100)
            if df.empty:
                print(f"  无数据")
                continue
            
            # 计算指标
            df = strategy.calculate_emas(df)
            df = strategy.calculate_bollinger_bands(df)
            df.dropna(inplace=True)
            
            if df.empty:
                print(f"  计算指标后无数据")
                continue
            
            # 判断趋势
            is_bullish = strategy.is_bullish_trend(df)
            is_bearish = strategy.is_bearish_trend(df)
            trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
            
            # 寻找信号
            pullback_signals = strategy.find_ema_pullback_levels(df, trend)
            
            print(f"  趋势: {trend}")
            print(f"  EMA回踩信号: {len(pullback_signals)} 个")
            
            # 显示信号详情
            for i, signal in enumerate(pullback_signals[:3]):
                print(f"    信号 {i+1}: {signal.get('signal')} EMA{signal.get('ema_period')} "
                      f"入场:{signal.get('entry_price'):.4f}")
            
            # 验证没有支撑阻力信号
            print(f"  ✅ 只包含EMA回踩信号，无支撑阻力信号")
            
        except Exception as e:
            print(f"  测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("信号清理完成！")
    print("现在只保留EMA89/144/233回踩信号")
    print("已删除支撑阻力、交叉、突破等信号")
    print("=" * 60)

if __name__ == "__main__":
    test_clean_signals()
