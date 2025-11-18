#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新策略：修改策略（去掉4H，统一1分钟止盈）
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_gate_top_symbols(limit=10):
    """获取GATE.IO前10个币种（快速测试）"""
    try:
        import requests
        
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            usdt_pairs = [t for t in data if t['currency_pair'].endswith('_USDT')]
            usdt_pairs.sort(key=lambda x: float(x.get('base_volume', 0)), reverse=True)
            
            symbols = [pair['currency_pair'] for pair in usdt_pairs[:limit]]
            logger.info(f"获取到GATE.IO前{len(symbols)}个币种")
            return symbols
        else:
            logger.error(f"获取币种失败: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"获取币种失败: {e}")
        return []

def get_historical_data(symbol, timeframe='1d', days=30):
    """获取历史数据"""
    try:
        import requests
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': symbol,
            'interval': timeframe,
            'from': start_ts,
            'to': end_ts
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df = df.dropna()
                return df
            else:
                return pd.DataFrame()
        else:
            return pd.DataFrame()
            
    except Exception as e:
        return pd.DataFrame()

def test_new_strategy():
    """测试新策略"""
    logger.info("=" * 60)
    logger.info("测试新策略（修改策略）")
    logger.info("=" * 60)
    
    # 创建修改策略实例
    modified_strategy = MultiTimeframeStrategy('modified')
    
    logger.info(f"新策略时间框架: {modified_strategy.timeframes}")
    logger.info(f"新策略止盈配置: {modified_strategy.take_profit_timeframes}")
    
    # 获取前10个币种
    symbols = get_gate_top_symbols(10)
    if not symbols:
        logger.error("无法获取币种列表")
        return
    
    logger.info(f"测试币种: {symbols}")
    
    results = []
    total_signals = 0
    
    # 测试每个币种
    for i, symbol in enumerate(symbols):
        logger.info(f"\n分析币种 {i+1}/{len(symbols)}: {symbol}")
        
        try:
            # 分析每个时间框架
            for tf in modified_strategy.timeframes:
                logger.info(f"  分析时间框架: {tf}")
                
                try:
                    # 获取数据
                    df = get_historical_data(symbol, tf, days=30)
                    if df.empty or len(df) < 50:
                        logger.warning(f"    {symbol} {tf}数据不足")
                        continue
                    
                    # 计算技术指标
                    df = modified_strategy.calculate_emas(df, tf)
                    df = modified_strategy.calculate_bollinger_bands(df)
                    df = df.dropna()
                    
                    if df.empty:
                        logger.warning(f"    {symbol} {tf}计算指标后数据为空")
                        continue
                    
                    # 判断趋势
                    if modified_strategy.is_bullish_trend(df):
                        trend = 'bullish'
                        logger.info(f"    {symbol} {tf}: 多头趋势")
                    elif modified_strategy.is_bearish_trend(df):
                        trend = 'bearish'
                        logger.info(f"    {symbol} {tf}: 空头趋势")
                    else:
                        logger.info(f"    {symbol} {tf}: 中性趋势")
                        continue
                    
                    # 寻找信号
                    signals = modified_strategy.find_ema_pullback_levels(df, trend, tf, symbol)
                    
                    if signals:
                        logger.info(f"    {symbol} {tf}: 找到{len(signals)}个信号")
                        for signal in signals:
                            # 计算止盈（统一使用1分钟布林中轨）
                            take_profit_tf = '1m'  # 新策略统一使用1分钟
                            tp_df = get_historical_data(symbol, take_profit_tf, days=30)
                            
                            if not tp_df.empty:
                                tp_df = modified_strategy.calculate_bollinger_bands(tp_df)
                                tp_df = tp_df.dropna()
                                
                                if not tp_df.empty:
                                    bb_middle = tp_df['bb_middle'].iloc[-1]
                                    entry_price = signal['entry_price']
                                    
                                    # 计算收益率
                                    if signal['signal'] == 'long':
                                        profit_pct = (bb_middle - entry_price) / entry_price * 100
                                    else:
                                        profit_pct = (entry_price - bb_middle) / entry_price * 100
                                    
                                    results.append({
                                        'symbol': symbol,
                                        'timeframe': tf,
                                        'signal_type': signal['signal'],
                                        'ema_period': signal['ema_period'],
                                        'entry_price': entry_price,
                                        'take_profit_price': bb_middle,
                                        'profit_pct': profit_pct,
                                        'signal_time': signal['signal_time'],
                                        'condition': signal['condition']
                                    })
                                    
                                    total_signals += 1
                                    logger.info(f"      {signal['signal']} EMA{signal['ema_period']} 收益率: {profit_pct:.2f}%")
                    else:
                        logger.info(f"    {symbol} {tf}: 无信号")
                    
                    # 添加延迟
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"    {symbol} {tf}分析失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"分析{symbol}失败: {e}")
            continue
    
    # 分析结果
    logger.info("\n" + "=" * 60)
    logger.info("新策略测试结果")
    logger.info("=" * 60)
    
    logger.info(f"总信号数: {total_signals}")
    if results:
        profits = [r['profit_pct'] for r in results]
        logger.info(f"平均收益率: {np.mean(profits):.2f}%")
        logger.info(f"最大收益率: {np.max(profits):.2f}%")
        logger.info(f"最小收益率: {np.min(profits):.2f}%")
        logger.info(f"正收益信号: {sum(1 for p in profits if p > 0)}/{len(profits)}")
        
        # 按时间框架统计
        tf_stats = {}
        for result in results:
            tf = result['timeframe']
            if tf not in tf_stats:
                tf_stats[tf] = []
            tf_stats[tf].append(result['profit_pct'])
        
        logger.info("\n按时间框架统计:")
        for tf, tf_profits in tf_stats.items():
            logger.info(f"  {tf}: {len(tf_profits)}个信号, 平均收益率: {np.mean(tf_profits):.2f}%")
        
        # 按EMA周期统计
        ema_stats = {}
        for result in results:
            ema = result['ema_period']
            if ema not in ema_stats:
                ema_stats[ema] = []
            ema_stats[ema].append(result['profit_pct'])
        
        logger.info("\n按EMA周期统计:")
        for ema, ema_profits in ema_stats.items():
            logger.info(f"  EMA{ema}: {len(ema_profits)}个信号, 平均收益率: {np.mean(ema_profits):.2f}%")
        
        # 保存结果
        results_df = pd.DataFrame(results)
        results_df.to_csv('new_strategy_test_results.csv', index=False, encoding='utf-8-sig')
        logger.info(f"\n结果已保存到: new_strategy_test_results.csv")
        
        # 显示详细结果
        logger.info("\n详细信号列表:")
        for result in results:
            logger.info(f"  {result['symbol']} {result['timeframe']} {result['signal_type']} EMA{result['ema_period']} 收益率: {result['profit_pct']:.2f}%")
    
    else:
        logger.info("未找到任何信号")
    
    logger.info("\n新策略测试完成！")

def main():
    """主函数"""
    test_new_strategy()

if __name__ == "__main__":
    main()
