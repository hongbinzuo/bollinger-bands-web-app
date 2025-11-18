#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速历史回测脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy
import time

def test_symbol(symbol, strategy):
    """测试单个币种"""
    print(f"\n测试 {symbol}...")
    
    total_signals = 0
    timeframes = ['4h', '8h', '12h', '1d']
    
    for timeframe in timeframes:
        try:
            print(f"  分析 {timeframe}...")
            
            # 获取数据
            df = strategy.get_klines_data(symbol, timeframe, 100)
            if df.empty:
                print(f"    无数据")
                continue
            
            # 计算指标
            df = strategy.calculate_emas(df)
            df = strategy.calculate_bollinger_bands(df)
            df.dropna(inplace=True)
            
            if df.empty:
                print(f"    计算指标后无数据")
                continue
            
            # 判断趋势
            is_bullish = strategy.is_bullish_trend(df)
            is_bearish = strategy.is_bearish_trend(df)
            trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
            
            # 寻找信号
            pullback_signals = strategy.find_ema_pullback_levels(df, trend)
            
            total_signals += len(pullback_signals)
            print(f"    {timeframe}: {len(pullback_signals)} 个信号")
            
            # 显示信号详情
            for j, signal in enumerate(pullback_signals[:2]):
                print(f"      信号 {j+1}: {signal.get('signal')} EMA{signal.get('ema_period')}")
            
        except Exception as e:
            print(f"    {timeframe} 失败: {e}")
    
    return total_signals

def main():
    """主函数"""
    print("=" * 60)
    print("快速历史回测 - 测试所有20个币种")
    print("=" * 60)
    
    # 测试币种列表
    test_symbols = [
        'ENAUSDT', 'SOLUSDT', 'ETCUSDT', 'ETHUSDT', 'BTCUSDT',
        'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOTUSDT', 'DOGEUSDT',
        'AVAXUSDT', 'SHIBUSDT', 'MATICUSDT', 'LTCUSDT', 'UNIUSDT',
        'LINKUSDT', 'ATOMUSDT', 'XLMUSDT', 'BCHUSDT', 'FILUSDT'
    ]
    
    strategy = MultiTimeframeStrategy()
    all_results = []
    
    start_time = time.time()
    
    for i, symbol in enumerate(test_symbols):
        print(f"\n测试币种 {i+1}/{len(test_symbols)}: {symbol}")
        
        try:
            total_signals = test_symbol(symbol, strategy)
            all_results.append({
                'symbol': symbol,
                'total_signals': total_signals
            })
            
            # 减少延迟
            if i < len(test_symbols) - 1:
                time.sleep(1)
                
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
    print(f"回测耗时: {time.time() - start_time:.1f} 秒")
    
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
