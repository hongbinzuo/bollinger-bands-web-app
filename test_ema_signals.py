#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试EMA信号描述格式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_ema_signal_descriptions():
    """测试EMA信号描述格式"""
    print("=" * 60)
    print("测试EMA信号描述格式")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试币种
    test_symbols = ['ENAUSDT', 'SOLUSDT', 'ETCUSDT', 'ETHUSDT', 'BTCUSDT']
    
    for symbol in test_symbols:
        print(f"\n测试 {symbol}...")
        
        try:
            # 测试4H时间框架
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
                print(f"    信号 {i+1}:")
                print(f"      类型: {signal.get('signal')}")
                print(f"      触发EMA: EMA{signal.get('ema_period')}")
                print(f"      入场价: {signal.get('entry_price'):.4f}")
                print(f"      EMA值: {signal.get('ema_value'):.4f}")
                print(f"      条件: {signal.get('condition')}")
                print(f"      描述: {signal.get('description')}")
                print()
            
        except Exception as e:
            print(f"  测试失败: {e}")
    
    print("=" * 60)
    print("EMA信号描述格式测试完成！")
    print("现在每个信号都会明确显示触发的EMA类型")
    print("=" * 60)

if __name__ == "__main__":
    test_ema_signal_descriptions()
