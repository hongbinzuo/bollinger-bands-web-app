#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试止盈点位计算逻辑
"""

from multi_timeframe_strategy import MultiTimeframeStrategy
import pandas as pd

def test_take_profit_logic():
    strategy = MultiTimeframeStrategy()
    symbol = 'BTCUSDT'
    
    print("=== 止盈点位计算逻辑详解 ===\n")
    
    # 测试不同时间框架
    timeframes = ['4h', '8h', '12h', '1d', '3d', '1w']
    
    for timeframe in timeframes:
        print(f"📊 时间框架: {timeframe}")
        print("-" * 50)
        
        # 获取主时间框架数据
        main_df = strategy.get_klines_data(symbol, timeframe, 300)
        if main_df is None or main_df.empty:
            print(f"❌ 无法获取 {timeframe} 数据")
            continue
            
        main_df = strategy.calculate_emas(main_df)
        main_df.dropna(inplace=True)
        
        if main_df.empty:
            print(f"❌ {timeframe} 数据为空")
            continue
        
        # 判断趋势
        is_bullish = strategy.is_bullish_trend(main_df)
        is_bearish = strategy.is_bearish_trend(main_df)
        trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
        
        print(f"📈 主时间框架趋势: {trend}")
        
        # 获取止盈时间框架
        take_profit_timeframe = strategy.take_profit_timeframes.get(timeframe, '15m')
        print(f"⏰ 止盈时间框架: {take_profit_timeframe}")
        
        # 获取止盈时间框架数据
        tp_df = strategy.get_klines_data(symbol, take_profit_timeframe, 200)
        if tp_df is None or tp_df.empty:
            print(f"❌ 无法获取 {take_profit_timeframe} 数据")
            continue
            
        tp_df = strategy.calculate_bollinger_bands(tp_df)
        tp_df.dropna(inplace=True)
        
        if tp_df.empty:
            print(f"❌ {take_profit_timeframe} 数据为空")
            continue
        
        # 布林带指标
        bb_middle = tp_df['bb_middle'].iloc[0]
        bb_lower = tp_df['bb_lower'].iloc[0]
        bb_upper = tp_df['bb_upper'].iloc[0]
        current_price = tp_df['close'].iloc[0]
        entry_price = main_df['close'].iloc[0]
        
        print(f"💰 入场价格: {entry_price:.2f}")
        print(f"📊 止盈时间框架当前价格: {current_price:.2f}")
        print(f"📈 布林带上轨: {bb_upper:.2f}")
        print(f"📊 布林带中轨: {bb_middle:.2f}")
        print(f"📉 布林带下轨: {bb_lower:.2f}")
        
        # 计算止盈价格
        if trend == 'bullish':
            take_profit_price = bb_middle
            print(f"🟢 多头趋势 → 使用布林带中轨作为止盈: {take_profit_price:.2f}")
        elif trend == 'bearish':
            take_profit_price = bb_lower
            print(f"🔴 空头趋势 → 使用布林带下轨作为止盈: {take_profit_price:.2f}")
        else:
            if current_price > bb_middle:
                take_profit_price = bb_lower
                print(f"⚪ 中性趋势(价格在中轨上方) → 使用布林带下轨作为止盈: {take_profit_price:.2f}")
            else:
                take_profit_price = bb_middle
                print(f"⚪ 中性趋势(价格在中轨下方) → 使用布林带中轨作为止盈: {take_profit_price:.2f}")
        
        # 合理性检查
        print(f"\n🔍 合理性检查:")
        print(f"   原始止盈价格: {take_profit_price:.2f}")
        
        # 模拟信号类型判断（简化版）
        # 这里我们假设根据趋势判断主要信号类型
        if trend == 'bearish':
            main_signal_type = 'short'
        elif trend == 'bullish':
            main_signal_type = 'long'
        else:
            # 中性趋势，根据价格位置判断
            main_signal_type = 'short' if current_price > bb_middle else 'long'
        
        print(f"   主要信号类型: {main_signal_type}")
        
        # 调整止盈价格
        if main_signal_type == 'short':
            if take_profit_price >= entry_price:
                take_profit_price = entry_price * 0.95
                print(f"   🔧 做空信号调整: 止盈价格调整为入场价格的95% = {take_profit_price:.2f}")
        else:
            if take_profit_price <= entry_price:
                take_profit_price = entry_price * 1.05
                print(f"   🔧 做多信号调整: 止盈价格调整为入场价格的105% = {take_profit_price:.2f}")
        
        # 计算收益率
        if main_signal_type == 'long':
            profit_pct = ((take_profit_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - take_profit_price) / entry_price) * 100
        
        print(f"   📊 最终止盈价格: {take_profit_price:.2f}")
        print(f"   💰 预期收益率: {profit_pct:.2f}%")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_take_profit_logic()
