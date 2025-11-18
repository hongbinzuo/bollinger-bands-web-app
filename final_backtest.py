#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终回测：使用GATE.IO前50个币种测试新策略
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

def get_gate_top_symbols(limit=50):
    """获取GATE.IO前N个币种"""
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

def backtest_strategy(strategy, symbols, test_count=20):
    """回测策略"""
    logger.info(f"开始回测策略: {strategy.strategy_type}")
    logger.info(f"时间框架: {strategy.timeframes}")
    logger.info(f"止盈配置: {strategy.take_profit_timeframes}")
    
    results = []
    total_signals = 0
    
    for i, symbol in enumerate(symbols[:test_count]):
        logger.info(f"分析币种 {i+1}/{test_count}: {symbol}")
        
        try:
            # 分析每个时间框架
            for tf in strategy.timeframes:
                try:
                    # 获取数据
                    df = get_historical_data(symbol, tf, days=30)
                    if df.empty or len(df) < 50:
                        continue
                    
                    # 计算技术指标
                    df = strategy.calculate_emas(df, tf)
                    df = strategy.calculate_bollinger_bands(df)
                    df = df.dropna()
                    
                    if df.empty:
                        continue
                    
                    # 判断趋势
                    if strategy.is_bullish_trend(df):
                        trend = 'bullish'
                    elif strategy.is_bearish_trend(df):
                        trend = 'bearish'
                    else:
                        continue
                    
                    # 寻找信号
                    signals = strategy.find_ema_pullback_levels(df, trend, tf, symbol)
                    
                    if signals:
                        for signal in signals:
                            # 计算止盈
                            take_profit_tf = strategy.take_profit_timeframes.get(tf, '15m')
                            tp_df = get_historical_data(symbol, take_profit_tf, days=30)
                            
                            if not tp_df.empty:
                                tp_df = strategy.calculate_bollinger_bands(tp_df)
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
                                        'strategy': strategy.strategy_type,
                                        'signal_type': signal['signal'],
                                        'ema_period': signal['ema_period'],
                                        'entry_price': entry_price,
                                        'take_profit_price': bb_middle,
                                        'profit_pct': profit_pct,
                                        'signal_time': signal['signal_time'],
                                        'condition': signal['condition']
                                    })
                                    
                                    total_signals += 1
                                    logger.info(f"  {symbol} {tf}: {signal['signal']} EMA{signal['ema_period']} 收益率: {profit_pct:.2f}%")
                    
                    # 添加延迟
                    time.sleep(0.1)
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            continue
    
    logger.info(f"策略{strategy.strategy_type}回测完成，共生成{total_signals}个信号")
    return results

def analyze_results(original_results, modified_results):
    """分析回测结果"""
    logger.info("\n" + "=" * 60)
    logger.info("回测结果分析")
    logger.info("=" * 60)
    
    # 原策略结果
    logger.info("原策略结果:")
    logger.info(f"  总信号数: {len(original_results)}")
    if original_results:
        original_profits = [r['profit_pct'] for r in original_results]
        logger.info(f"  平均收益率: {np.mean(original_profits):.2f}%")
        logger.info(f"  最大收益率: {np.max(original_profits):.2f}%")
        logger.info(f"  最小收益率: {np.min(original_profits):.2f}%")
        logger.info(f"  正收益信号: {sum(1 for p in original_profits if p > 0)}/{len(original_profits)}")
    
    # 修改策略结果
    logger.info("\n修改策略结果:")
    logger.info(f"  总信号数: {len(modified_results)}")
    if modified_results:
        modified_profits = [r['profit_pct'] for r in modified_results]
        logger.info(f"  平均收益率: {np.mean(modified_profits):.2f}%")
        logger.info(f"  最大收益率: {np.max(modified_profits):.2f}%")
        logger.info(f"  最小收益率: {np.min(modified_profits):.2f}%")
        logger.info(f"  正收益信号: {sum(1 for p in modified_profits if p > 0)}/{len(modified_profits)}")
    
    # 策略对比
    logger.info("\n策略对比:")
    if original_results and modified_results:
        original_avg = np.mean([r['profit_pct'] for r in original_results])
        modified_avg = np.mean([r['profit_pct'] for r in modified_results])
        
        logger.info(f"  原策略平均收益率: {original_avg:.2f}%")
        logger.info(f"  修改策略平均收益率: {modified_avg:.2f}%")
        logger.info(f"  收益率差异: {modified_avg - original_avg:.2f}%")
        
        if modified_avg > original_avg:
            logger.info("  ✅ 修改策略表现更好")
        else:
            logger.info("  ❌ 原策略表现更好")
    
    # 保存结果
    if original_results:
        original_df = pd.DataFrame(original_results)
        original_df.to_csv('final_backtest_original.csv', index=False, encoding='utf-8-sig')
        logger.info("原策略结果已保存到: final_backtest_original.csv")
    
    if modified_results:
        modified_df = pd.DataFrame(modified_results)
        modified_df.to_csv('final_backtest_modified.csv', index=False, encoding='utf-8-sig')
        logger.info("修改策略结果已保存到: final_backtest_modified.csv")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("GATE.IO策略回测")
    logger.info("=" * 60)
    
    # 获取前50个币种
    logger.info("获取GATE.IO前50个币种...")
    symbols = get_gate_top_symbols(50)
    
    if not symbols:
        logger.error("无法获取币种列表")
        return
    
    logger.info(f"获取到{len(symbols)}个币种: {symbols[:10]}...")
    
    # 创建策略实例
    original_strategy = MultiTimeframeStrategy('original')
    modified_strategy = MultiTimeframeStrategy('modified')
    
    # 回测原策略（测试前20个币种）
    logger.info("\n" + "=" * 40)
    logger.info("回测原策略")
    logger.info("=" * 40)
    original_results = backtest_strategy(original_strategy, symbols, test_count=20)
    
    # 回测修改策略（测试前20个币种）
    logger.info("\n" + "=" * 40)
    logger.info("回测修改策略")
    logger.info("=" * 40)
    modified_results = backtest_strategy(modified_strategy, symbols, test_count=20)
    
    # 分析结果
    analyze_results(original_results, modified_results)
    
    logger.info("\n回测完成！")

if __name__ == "__main__":
    main()