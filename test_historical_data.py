#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试历史数据脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_single_symbol(symbol: str):
    """测试单个币种"""
    print(f"\n测试 {symbol}...")
    
    strategy = MultiTimeframeStrategy()
    total_signals = 0
    
    # 测试主要时间框架
    timeframes = ['4h', '8h', '12h', '1d']
    
    for timeframe in timeframes:
        try:
            print(f"  分析 {timeframe} 时间框架...")
            
            # 获取数据
            df = strategy.get_klines_data(symbol, timeframe, 100)
            if df.empty:
                print(f"    {symbol} {timeframe}: 无数据")
                continue
            
            # 计算指标
            df = strategy.calculate_emas(df)
            df = strategy.calculate_bollinger_bands(df)
            df.dropna(inplace=True)
            
            if df.empty:
                print(f"    {symbol} {timeframe}: 计算指标后无数据")
                continue
            
            # 判断趋势
            is_bullish = strategy.is_bullish_trend(df)
            is_bearish = strategy.is_bearish_trend(df)
            trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
            
            print(f"    趋势: {trend}")
            
            # 寻找信号
            pullback_signals = strategy.find_ema_pullback_levels(df, trend)
            
            # 计算止盈
            take_profit_timeframe = strategy.take_profit_timeframes.get(timeframe, '15m')
            take_profit_price = None
            
            try:
                tp_df = strategy.get_klines_data(symbol, take_profit_timeframe, 50)
                if not tp_df.empty:
                    tp_df = strategy.calculate_bollinger_bands(tp_df)
                    tp_df.dropna(inplace=True)
                    if not tp_df.empty:
                        take_profit_price = tp_df['bb_middle'].iloc[-1]
            except Exception as e:
                print(f"    计算止盈失败: {e}")
            
            # 为信号添加止盈信息
            for signal in pullback_signals:
                signal['timeframe'] = timeframe
                signal['trend'] = trend
                signal['take_profit_timeframe'] = take_profit_timeframe
                signal['take_profit_price'] = take_profit_price
                
                # 计算收益率
                entry_price = signal.get('entry_price', 0)
                if entry_price > 0 and take_profit_price and take_profit_price > 0:
                    if signal.get('signal') == 'long':
                        profit_pct = ((take_profit_price - entry_price) / entry_price) * 100
                    else:
                        profit_pct = ((entry_price - take_profit_price) / entry_price) * 100
                    signal['profit_pct'] = round(profit_pct, 2)
                else:
                    signal['profit_pct'] = 0
            
            total_signals += len(pullback_signals)
            print(f"    {timeframe}: {len(pullback_signals)} 个信号")
            
            # 显示信号详情
            for i, signal in enumerate(pullback_signals[:2]):  # 只显示前2个
                profit = signal.get('profit_pct', 0)
                print(f"      信号 {i+1}: {signal.get('signal')} EMA{signal.get('ema_period')} "
                      f"入场:{signal.get('entry_price'):.2f} 止盈:{take_profit_price:.2f} "
                      f"收益:{profit:.1f}%")
            
        except Exception as e:
            print(f"    {timeframe} 分析失败: {e}")
    
    return total_signals

def main():
    """主函数"""
    print("=" * 60)
    print("历史数据回测测试")
    print("=" * 60)
    
    # 测试币种列表
    test_symbols = [
        'ENAUSDT', 'SOLUSDT', 'ETCUSDT', 'ETHUSDT', 'BTCUSDT'
    ]
    
    all_results = []
    
    for i, symbol in enumerate(test_symbols):
        print(f"\n测试币种 {i+1}/{len(test_symbols)}: {symbol}")
        
        try:
            total_signals = test_single_symbol(symbol)
            all_results.append({
                'symbol': symbol,
                'total_signals': total_signals
            })
            
        except Exception as e:
            print(f"测试 {symbol} 失败: {e}")
            all_results.append({
                'symbol': symbol,
                'error': str(e),
                'total_signals': 0
            })
    
    # 计算总结
    total_signals = sum(r.get('total_signals', 0) for r in all_results)
    successful_symbols = len([r for r in all_results if r.get('total_signals', 0) > 0])
    
    print("\n" + "=" * 60)
    print("回测总结")
    print("=" * 60)
    print(f"测试币种数量: {len(test_symbols)}")
    print(f"成功分析币种: {successful_symbols}")
    print(f"总信号数量: {total_signals}")
    
    # 显示每个币种的结果
    print("\n各币种信号统计:")
    for result in all_results:
        symbol = result['symbol']
        total = result.get('total_signals', 0)
        if total > 0:
            print(f"  {symbol}: {total} 个信号")
        else:
            print(f"  {symbol}: 无信号")
    
    print("\n回测完成！")

if __name__ == "__main__":
    main()
