#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试新策略
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
                return df
            else:
                return pd.DataFrame()
        else:
            return pd.DataFrame()
            
    except Exception as e:
        return pd.DataFrame()

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("简单测试新策略")
    logger.info("=" * 60)
    
    # 创建修改策略实例
    modified_strategy = MultiTimeframeStrategy('modified')
    
    logger.info(f"新策略时间框架: {modified_strategy.timeframes}")
    logger.info(f"新策略止盈配置: {modified_strategy.take_profit_timeframes}")
    
    # 测试币种
    test_symbols = ['BTC_USDT', 'ETH_USDT']
    
    all_results = []
    
    # 测试每个币种
    for symbol in test_symbols:
        logger.info(f"\n测试币种: {symbol}")
        
        try:
            # 测试1D时间框架
            df = get_historical_data(symbol, '1d', days=30)
            if df.empty or len(df) < 50:
                logger.warning(f"{symbol} 1D数据不足")
                continue
            
            # 计算技术指标
            df = modified_strategy.calculate_emas(df, '1d')
            df = modified_strategy.calculate_bollinger_bands(df)
            df = df.dropna()
            
            if df.empty:
                logger.warning(f"{symbol} 1D计算指标后数据为空")
                continue
            
            # 判断趋势
            if modified_strategy.is_bullish_trend(df):
                trend = 'bullish'
                logger.info(f"{symbol} 1D: 多头趋势")
            elif modified_strategy.is_bearish_trend(df):
                trend = 'bearish'
                logger.info(f"{symbol} 1D: 空头趋势")
            else:
                logger.info(f"{symbol} 1D: 中性趋势")
                continue
            
            # 寻找信号
            signals = modified_strategy.find_ema_pullback_levels(df, trend, '1d', symbol)
            
            if signals:
                logger.info(f"{symbol} 1D: 找到{len(signals)}个信号")
                for signal in signals:
                    # 计算止盈（统一使用1分钟布林中轨）
                    take_profit_tf = '1m'
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
                            
                            all_results.append({
                                'symbol': symbol,
                                'timeframe': '1d',
                                'signal_type': signal['signal'],
                                'ema_period': signal['ema_period'],
                                'entry_price': entry_price,
                                'take_profit_price': bb_middle,
                                'profit_pct': profit_pct,
                                'signal_time': signal['signal_time'],
                                'condition': signal['condition']
                            })
                            
                            logger.info(f"  {signal['signal']} EMA{signal['ema_period']} 收益率: {profit_pct:.2f}%")
            else:
                logger.info(f"{symbol} 1D: 无信号")
            
            # 添加延迟
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"分析{symbol}失败: {e}")
            continue
    
    # 分析结果
    logger.info("\n" + "=" * 60)
    logger.info("新策略测试结果")
    logger.info("=" * 60)
    
    logger.info(f"总信号数: {len(all_results)}")
    if all_results:
        profits = [r['profit_pct'] for r in all_results]
        logger.info(f"平均收益率: {np.mean(profits):.2f}%")
        logger.info(f"最大收益率: {np.max(profits):.2f}%")
        logger.info(f"最小收益率: {np.min(profits):.2f}%")
        logger.info(f"正收益信号: {sum(1 for p in profits if p > 0)}/{len(profits)}")
        
        # 保存结果
        results_df = pd.DataFrame(all_results)
        results_df.to_csv('simple_new_strategy_results.csv', index=False, encoding='utf-8-sig')
        logger.info(f"\n结果已保存到: simple_new_strategy_results.csv")
        
        # 显示详细结果
        logger.info("\n详细信号列表:")
        for result in all_results:
            logger.info(f"  {result['symbol']} {result['timeframe']} {result['signal_type']} EMA{result['ema_period']} 收益率: {result['profit_pct']:.2f}%")
    
    else:
        logger.info("未找到任何信号")
    
    logger.info("\n新策略测试完成！")

if __name__ == "__main__":
    main()
