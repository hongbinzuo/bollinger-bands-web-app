#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化历史回测脚本
测试最近3个月的20个币种数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_single_symbol(symbol: str, strategy: MultiTimeframeStrategy):
    """测试单个币种"""
    logger.info(f"开始测试 {symbol}...")
    
    results = {
        'symbol': symbol,
        'timeframes': {},
        'total_signals': 0
    }
    
    for timeframe in ['4h', '8h', '12h', '1d']:  # 只测试主要时间框架
        try:
            logger.info(f"  测试 {symbol} {timeframe}...")
            
            # 获取数据
            df = strategy.get_klines_data(symbol, timeframe, 200)
            if df.empty:
                logger.warning(f"    {symbol} {timeframe}: 无数据")
                continue
            
            # 计算指标
            df = strategy.calculate_emas(df)
            df = strategy.calculate_bollinger_bands(df)
            df.dropna(inplace=True)
            
            if df.empty:
                logger.warning(f"    {symbol} {timeframe}: 计算指标后无数据")
                continue
            
            # 判断趋势
            is_bullish = strategy.is_bullish_trend(df)
            is_bearish = strategy.is_bearish_trend(df)
            trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
            
            # 寻找信号
            pullback_signals = strategy.find_ema_pullback_levels(df, trend)
            
            # 计算止盈
            take_profit_timeframe = strategy.take_profit_timeframes.get(timeframe, '15m')
            take_profit_price = None
            
            try:
                tp_df = strategy.get_klines_data(symbol, take_profit_timeframe, 100)
                if not tp_df.empty:
                    tp_df = strategy.calculate_bollinger_bands(tp_df)
                    tp_df.dropna(inplace=True)
                    if not tp_df.empty:
                        take_profit_price = tp_df['bb_middle'].iloc[-1]
            except:
                pass
            
            # 计算收益率
            for signal in pullback_signals:
                entry_price = signal.get('entry_price', 0)
                if entry_price > 0 and take_profit_price and take_profit_price > 0:
                    if signal.get('signal') == 'long':
                        profit_pct = ((take_profit_price - entry_price) / entry_price) * 100
                    else:
                        profit_pct = ((entry_price - take_profit_price) / entry_price) * 100
                    signal['profit_pct'] = round(profit_pct, 2)
                    signal['take_profit_price'] = take_profit_price
                else:
                    signal['profit_pct'] = 0
                    signal['take_profit_price'] = 0
            
            results['timeframes'][timeframe] = {
                'trend': trend,
                'signals': pullback_signals,
                'signal_count': len(pullback_signals),
                'take_profit_price': take_profit_price,
                'current_price': df['close'].iloc[-1] if not df.empty else 0
            }
            
            results['total_signals'] += len(pullback_signals)
            
            logger.info(f"    {symbol} {timeframe}: {len(pullback_signals)} 个信号")
            
            # 显示信号详情
            for i, signal in enumerate(pullback_signals[:3]):  # 只显示前3个
                logger.info(f"      信号 {i+1}: {signal.get('signal')} EMA{signal.get('ema_period')} "
                          f"入场:{signal.get('entry_price'):.2f} 止盈:{signal.get('take_profit_price', 0):.2f} "
                          f"收益:{signal.get('profit_pct', 0):.1f}%")
            
        except Exception as e:
            logger.error(f"    {symbol} {timeframe} 测试失败: {e}")
            results['timeframes'][timeframe] = {
                'error': str(e),
                'signals': [],
                'signal_count': 0
            }
    
    return results

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始历史回测 - 最近3个月数据")
    logger.info("=" * 60)
    
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
        logger.info(f"\n测试币种 {i+1}/{len(test_symbols)}: {symbol}")
        
        try:
            result = test_single_symbol(symbol, strategy)
            all_results.append(result)
            
            # 添加延迟避免API限制
            if i < len(test_symbols) - 1:
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"测试 {symbol} 失败: {e}")
            all_results.append({
                'symbol': symbol,
                'error': str(e),
                'total_signals': 0
            })
    
    # 计算总结
    total_signals = sum(r.get('total_signals', 0) for r in all_results)
    successful_symbols = len([r for r in all_results if r.get('total_signals', 0) > 0])
    
    logger.info("\n" + "=" * 60)
    logger.info("回测总结")
    logger.info("=" * 60)
    logger.info(f"测试币种数量: {len(test_symbols)}")
    logger.info(f"成功分析币种: {successful_symbols}")
    logger.info(f"总信号数量: {total_signals}")
    logger.info(f"回测耗时: {time.time() - start_time:.1f} 秒")
    
    # 显示每个币种的结果
    logger.info("\n各币种信号统计:")
    for result in all_results:
        symbol = result['symbol']
        total = result.get('total_signals', 0)
        if total > 0:
            logger.info(f"  {symbol}: {total} 个信号")
            
            # 显示时间框架详情
            for tf, tf_result in result.get('timeframes', {}).items():
                if tf_result.get('signal_count', 0) > 0:
                    logger.info(f"    {tf}: {tf_result['signal_count']} 个信号")
                    
                    # 显示信号详情
                    for signal in tf_result.get('signals', [])[:2]:  # 只显示前2个
                        profit = signal.get('profit_pct', 0)
                        logger.info(f"      {signal.get('signal')} EMA{signal.get('ema_period')} "
                                  f"收益:{profit:.1f}%")
        else:
            logger.info(f"  {symbol}: 无信号")
    
    # 计算平均收益率
    all_profits = []
    for result in all_results:
        for tf_result in result.get('timeframes', {}).values():
            for signal in tf_result.get('signals', []):
                profit = signal.get('profit_pct', 0)
                if profit != 0:
                    all_profits.append(profit)
    
    if all_profits:
        avg_profit = np.mean(all_profits)
        max_profit = np.max(all_profits)
        min_profit = np.min(all_profits)
        
        logger.info(f"\n收益率统计:")
        logger.info(f"  平均收益率: {avg_profit:.1f}%")
        logger.info(f"  最大收益率: {max_profit:.1f}%")
        logger.info(f"  最小收益率: {min_profit:.1f}%")
        logger.info(f"  有收益率的信号: {len(all_profits)} 个")
    
    logger.info("\n回测完成！")

if __name__ == "__main__":
    main()
