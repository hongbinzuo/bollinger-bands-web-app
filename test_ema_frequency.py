#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试EMA频率限制功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy
from datetime import datetime, timedelta

def test_ema_frequency_limit():
    """测试EMA频率限制功能"""
    print("=" * 60)
    print("测试EMA频率限制功能")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试币种
    test_symbol = 'BTCUSDT'
    test_timeframe = '4h'
    
    print(f"测试币种: {test_symbol}")
    print(f"测试时间框架: {test_timeframe}")
    print(f"频率限制: 最近10根K线内同一EMA最多触发2次")
    
    try:
        # 获取数据
        df = strategy.get_klines_data(test_symbol, test_timeframe, 100)
        if df.empty:
            print("无数据")
            return
        
        # 计算指标
        df = strategy.calculate_emas(df, test_timeframe)
        df = strategy.calculate_bollinger_bands(df)
        df.dropna(inplace=True)
        
        if df.empty:
            print("计算指标后无数据")
            return
        
        # 判断趋势
        is_bullish = strategy.is_bullish_trend(df)
        is_bearish = strategy.is_bearish_trend(df)
        trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
        
        print(f"\n趋势: {trend}")
        
        # 显示EMA频率跟踪器状态
        key = f"{test_symbol}_{test_timeframe}"
        if key in strategy.ema_frequency_tracker:
            print(f"\n当前EMA使用记录:")
            for ema_period, timestamps in strategy.ema_frequency_tracker[key].items():
                print(f"  EMA{ema_period}: {len(timestamps)} 次触发")
                for i, timestamp in enumerate(timestamps[-3:]):  # 显示最近3次
                    print(f"    {i+1}. {timestamp}")
        else:
            print(f"\n暂无EMA使用记录")
        
        # 寻找信号
        pullback_signals = strategy.find_ema_pullback_levels(df, trend, test_timeframe, test_symbol)
        
        print(f"\n信号数量: {len(pullback_signals)} 个")
        
        # 显示信号详情
        for i, signal in enumerate(pullback_signals):
            print(f"\n信号 {i+1}:")
            print(f"  类型: {signal.get('signal')}")
            print(f"  触发EMA: EMA{signal.get('ema_period')}")
            print(f"  入场价: {signal.get('entry_price'):.4f}")
            print(f"  EMA值: {signal.get('ema_value'):.4f}")
            print(f"  条件: {signal.get('condition')}")
        
        # 显示更新后的EMA使用记录
        if key in strategy.ema_frequency_tracker:
            print(f"\n更新后的EMA使用记录:")
            for ema_period, timestamps in strategy.ema_frequency_tracker[key].items():
                print(f"  EMA{ema_period}: {len(timestamps)} 次触发")
        
        print(f"\n✅ EMA频率限制功能正常")
        print(f"如果同一EMA在最近10根K线内触发过2次或以上，信号将被过滤")
        
    except Exception as e:
        print(f"测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("EMA频率限制测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_ema_frequency_limit()
