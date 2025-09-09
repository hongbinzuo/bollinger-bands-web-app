#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试信号生成问题
"""

from multi_timeframe_strategy import MultiTimeframeStrategy
import pandas as pd

def debug_signal_generation():
    strategy = MultiTimeframeStrategy()
    print('=== 调试信号生成 ===')

    # 测试BTCUSDT
    symbol = 'BTCUSDT'
    timeframe = '4h'
    print(f'测试币种: {symbol} {timeframe}')

    # 获取数据
    df = strategy.get_klines_data(symbol, timeframe, 300)
    print(f'数据点数: {len(df)}')

    if not df.empty:
        # 计算指标
        df = strategy.calculate_emas(df)
        df = strategy.calculate_bollinger_bands(df)
        df.dropna(inplace=True)
        print(f'计算指标后数据点数: {len(df)}')
        
        if not df.empty:
            # 检查趋势
            is_bullish = strategy.is_bullish_trend(df)
            is_bearish = strategy.is_bearish_trend(df)
            print(f'多头趋势: {is_bullish}')
            print(f'空头趋势: {is_bearish}')
            
            # 检查EMA值
            latest = df.iloc[0]
            print(f'当前价格: {latest["close"]}')
            for period in [89, 144, 233, 377]:
                ema_col = f'ema{period}'
                if ema_col in latest:
                    print(f'EMA{period}: {latest[ema_col]}')
            
            # 测试回撤信号
            trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
            print(f'当前趋势: {trend}')
            
            pullback_levels = strategy.find_ema_pullback_levels(df, trend)
            print(f'回撤信号数: {len(pullback_levels)}')
            
            # 测试支撑阻力信号
            sr_signals = strategy.find_support_resistance_signals(df)
            print(f'支撑阻力信号数: {len(sr_signals)}')
            
            # 测试交叉信号
            crossover_signals = strategy.find_ema_crossover_signals(df)
            print(f'交叉信号数: {len(crossover_signals)}')
            
            # 测试突破信号
            breakout_signals = strategy.find_price_breakout_signals(df)
            print(f'突破信号数: {len(breakout_signals)}')
            
            # 显示所有信号
            all_signals = pullback_levels + crossover_signals + breakout_signals + sr_signals
            print(f'总信号数: {len(all_signals)}')
            
            if all_signals:
                print('信号详情:')
                for i, signal in enumerate(all_signals[:3]):
                    print(f'  {i+1}. {signal}')
            
            # 详细分析为什么没有信号
            print('\n=== 详细分析 ===')
            
            # 分析回撤信号条件
            if trend == 'bullish':
                print('多头趋势回撤信号分析:')
                for period in [89, 144, 233, 377]:
                    ema_col = f'ema{period}'
                    if ema_col in latest:
                        ema_value = latest[ema_col]
                        current_price = latest['close']
                        price_distance = abs(current_price - ema_value) / ema_value
                        print(f'  EMA{period}: {ema_value}, 距离: {price_distance:.4f} ({price_distance*100:.2f}%)')
                        if price_distance <= 0.05:
                            print(f'    ✅ 满足距离条件')
                        else:
                            print(f'    ❌ 距离太远')
                        
                        # 检查量能条件
                        avg_volume = df['volume'].rolling(window=20).mean().iloc[1]
                        current_volume = latest['volume']
                        print(f'    当前量: {current_volume}, 平均量: {avg_volume}')
                        if current_volume > avg_volume:
                            print(f'    ✅ 满足量能条件')
                        else:
                            print(f'    ❌ 量能不足')
            
            # 分析支撑阻力信号
            print('\n支撑阻力信号分析:')
            recent_data = df.head(20)
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            current_price = latest['close']
            
            print(f'当前价格: {current_price}')
            print('最近20根K线的高低点:')
            for i in range(min(5, len(highs))):
                print(f'  K线{i}: 高{highs[i]}, 低{lows[i]}')
            
            # 寻找局部高点
            resistance_candidates = []
            for i in range(1, len(highs) - 1):
                if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                    resistance_candidates.append(highs[i])
            
            print(f'阻力位候选: {resistance_candidates}')
            for resistance in resistance_candidates:
                distance = abs(current_price - resistance) / resistance
                print(f'  阻力位 {resistance}: 距离 {distance:.4f} ({distance*100:.2f}%)')
                if distance <= 0.03:
                    print(f'    ✅ 满足距离条件')
                else:
                    print(f'    ❌ 距离太远')
        else:
            print('计算指标后数据为空')
    else:
        print('无法获取数据')

if __name__ == "__main__":
    debug_signal_generation()
