#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速回测：测试单个币种的策略
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
                logger.info(f"获取{symbol} {timeframe}数据: {len(df)}条")
                return df
            else:
                logger.warning(f"{symbol} {timeframe}无数据")
                return pd.DataFrame()
        else:
            logger.error(f"获取{symbol}数据失败: {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"获取{symbol}历史数据失败: {e}")
        return pd.DataFrame()

def test_strategy_on_symbol(strategy, symbol):
    """测试单个币种的策略"""
    logger.info(f"测试{symbol} - 策略: {strategy.strategy_type}")
    
    results = []
    
    # 测试每个时间框架
    for timeframe in strategy.timeframes:
        logger.info(f"  分析时间框架: {timeframe}")
        
        try:
            # 获取数据
            df = get_historical_data(symbol, timeframe, days=30)
            if df.empty or len(df) < 50:
                logger.warning(f"    {symbol} {timeframe}数据不足")
                continue
            
            # 计算技术指标
            df = strategy.calculate_emas(df, timeframe)
            df = strategy.calculate_bollinger_bands(df)
            df = df.dropna()
            
            if df.empty:
                logger.warning(f"    {symbol} {timeframe}计算指标后数据为空")
                continue
            
            # 判断趋势
            if strategy.is_bullish_trend(df):
                trend = 'bullish'
                logger.info(f"    {symbol} {timeframe}: 多头趋势")
            elif strategy.is_bearish_trend(df):
                trend = 'bearish'
                logger.info(f"    {symbol} {timeframe}: 空头趋势")
            else:
                logger.info(f"    {symbol} {timeframe}: 中性趋势")
                continue
            
            # 寻找信号
            signals = strategy.find_ema_pullback_levels(df, trend, timeframe, symbol)
            
            if signals:
                logger.info(f"    {symbol} {timeframe}: 找到{len(signals)}个信号")
                for signal in signals:
                    # 计算止盈
                    take_profit_tf = strategy.take_profit_timeframes.get(timeframe, '15m')
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
                                'timeframe': timeframe,
                                'strategy': strategy.strategy_type,
                                'signal_type': signal['signal'],
                                'ema_period': signal['ema_period'],
                                'entry_price': entry_price,
                                'take_profit_price': bb_middle,
                                'profit_pct': profit_pct,
                                'signal_time': signal['signal_time'],
                                'condition': signal['condition']
                            })
                            
                            logger.info(f"      {signal['signal']} EMA{signal['ema_period']} 收益率: {profit_pct:.2f}%")
            else:
                logger.info(f"    {symbol} {timeframe}: 无信号")
            
            # 添加延迟
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"    {symbol} {timeframe}分析失败: {e}")
            continue
    
    return results

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("快速回测测试")
    logger.info("=" * 60)
    
    # 测试币种
    test_symbols = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']
    
    # 创建策略实例
    original_strategy = MultiTimeframeStrategy('original')
    modified_strategy = MultiTimeframeStrategy('modified')
    
    logger.info(f"原策略时间框架: {original_strategy.timeframes}")
    logger.info(f"修改策略时间框架: {modified_strategy.timeframes}")
    
    # 测试原策略
    logger.info("\n" + "=" * 40)
    logger.info("测试原策略")
    logger.info("=" * 40)
    
    original_results = []
    for symbol in test_symbols:
        results = test_strategy_on_symbol(original_strategy, symbol)
        original_results.extend(results)
    
    # 测试修改策略
    logger.info("\n" + "=" * 40)
    logger.info("测试修改策略")
    logger.info("=" * 40)
    
    modified_results = []
    for symbol in test_symbols:
        results = test_strategy_on_symbol(modified_strategy, symbol)
        modified_results.extend(results)
    
    # 输出结果
    logger.info("\n" + "=" * 60)
    logger.info("回测结果")
    logger.info("=" * 60)
    
    logger.info(f"原策略信号数: {len(original_results)}")
    if original_results:
        original_profits = [r['profit_pct'] for r in original_results]
        logger.info(f"原策略平均收益率: {np.mean(original_profits):.2f}%")
        logger.info(f"原策略最大收益率: {np.max(original_profits):.2f}%")
        logger.info(f"原策略最小收益率: {np.min(original_profits):.2f}%")
    
    logger.info(f"修改策略信号数: {len(modified_results)}")
    if modified_results:
        modified_profits = [r['profit_pct'] for r in modified_results]
        logger.info(f"修改策略平均收益率: {np.mean(modified_profits):.2f}%")
        logger.info(f"修改策略最大收益率: {np.max(modified_profits):.2f}%")
        logger.info(f"修改策略最小收益率: {np.min(modified_profits):.2f}%")
    
    # 保存结果
    if original_results:
        original_df = pd.DataFrame(original_results)
        original_df.to_csv('quick_backtest_original.csv', index=False, encoding='utf-8-sig')
        logger.info("原策略结果已保存到: quick_backtest_original.csv")
    
    if modified_results:
        modified_df = pd.DataFrame(modified_results)
        modified_df.to_csv('quick_backtest_modified.csv', index=False, encoding='utf-8-sig')
        logger.info("修改策略结果已保存到: quick_backtest_modified.csv")
    
    logger.info("快速回测完成！")

if __name__ == "__main__":
    main()