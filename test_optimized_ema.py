#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的EMA配置
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_optimized_ema_config():
    """测试优化后的EMA配置"""
    print("=" * 60)
    print("测试优化后的EMA配置")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 显示时间框架对应的EMA组合
    print("时间框架对应的EMA组合:")
    for timeframe, ema_periods in strategy.timeframe_ema_mapping.items():
        ema_list = [f"EMA{period}" for period in ema_periods]
        print(f"  {timeframe}: {', '.join(ema_list)}")
    
    print("\n" + "=" * 60)
    print("测试不同时间框架的EMA计算")
    print("=" * 60)
    
    # 测试币种
    test_symbol = 'BTCUSDT'
    
    for timeframe in strategy.timeframes:
        print(f"\n测试 {timeframe} 时间框架...")
        
        try:
            # 获取数据
            df = strategy.get_klines_data(test_symbol, timeframe, 100)
            if df.empty:
                print(f"  无数据")
                continue
            
            # 计算指标
            df = strategy.calculate_emas(df, timeframe)
            df = strategy.calculate_bollinger_bands(df)
            df.dropna(inplace=True)
            
            if df.empty:
                print(f"  计算指标后无数据")
                continue
            
            # 显示计算的EMA
            ema_periods = strategy.timeframe_ema_mapping.get(timeframe, [89, 144, 233])
            print(f"  计算的EMA: {[f'EMA{period}' for period in ema_periods]}")
            
            # 显示EMA值
            for period in ema_periods:
                ema_col = f'ema{period}'
                if ema_col in df.columns:
                    ema_value = df[ema_col].iloc[-1]
                    print(f"    EMA{period}: {ema_value:.4f}")
            
            # 判断趋势
            is_bullish = strategy.is_bullish_trend(df)
            is_bearish = strategy.is_bearish_trend(df)
            trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
            
            # 寻找信号
            pullback_signals = strategy.find_ema_pullback_levels(df, trend, timeframe)
            
            print(f"  趋势: {trend}")
            print(f"  信号数量: {len(pullback_signals)} 个")
            
            # 显示信号详情
            for i, signal in enumerate(pullback_signals[:2]):
                print(f"    信号 {i+1}: {signal.get('signal')} EMA{signal.get('ema_period')}")
            
        except Exception as e:
            print(f"  测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("EMA配置优化完成！")
    print("现在不同时间框架使用对应的EMA组合")
    print("=" * 60)

if __name__ == "__main__":
    test_optimized_ema_config()
