#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单胜率测试
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

def get_historical_data(symbol, timeframe='1d', days=7):
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

def test_single_symbol(symbol):
    """测试单个币种"""
    logger.info(f"测试币种: {symbol}")
    
    # 创建策略实例
    strategy = MultiTimeframeStrategy('modified')
    
    try:
        # 获取1D数据
        df = get_historical_data(symbol, '1d', days=7)
        if df.empty or len(df) < 50:
            logger.warning(f"{symbol} 1D数据不足")
            return []
        
        logger.info(f"获取到{len(df)}条数据")
        
        # 计算技术指标
        df = strategy.calculate_emas(df, '1d')
        df = strategy.calculate_bollinger_bands(df)
        df = df.dropna()
        
        if df.empty:
            logger.warning(f"{symbol} 计算指标后数据为空")
            return []
        
        # 判断趋势
        if strategy.is_bullish_trend(df):
            trend = 'bullish'
            logger.info(f"{symbol} 1D: 多头趋势")
        elif strategy.is_bearish_trend(df):
            trend = 'bearish'
            logger.info(f"{symbol} 1D: 空头趋势")
        else:
            logger.info(f"{symbol} 1D: 中性趋势")
            return []
        
        # 寻找信号
        signals = strategy.find_ema_pullback_levels(df, trend, '1d', symbol)
        
        if signals:
            logger.info(f"{symbol} 1D: 找到{len(signals)}个信号")
            
            # 检查每个信号
            valid_signals = []
            for signal in signals:
                # 获取3分钟数据检查止盈
                tp_df = get_historical_data(symbol, '3m', days=7)
                if not tp_df.empty:
                    tp_df = strategy.calculate_bollinger_bands(tp_df)
                    tp_df = tp_df.dropna()
                    
                    if not tp_df.empty:
                        bb_middle = tp_df['bb_middle'].iloc[-1]
                        entry_price = signal['entry_price']
                        
                        # 检查止损条件
                        if signal['signal'] == 'short':
                            # 做空信号：3分钟布林中轨应该低于入场价格
                            if bb_middle < entry_price:
                                signal['take_profit_price'] = bb_middle
                                valid_signals.append(signal)
                                logger.info(f"  有效信号: {signal['signal']} EMA{signal['ema_period']} 入场:{entry_price:.4f} 止盈:{bb_middle:.4f}")
                        else:
                            # 做多信号：3分钟布林中轨应该高于入场价格
                            if bb_middle > entry_price:
                                signal['take_profit_price'] = bb_middle
                                valid_signals.append(signal)
                                logger.info(f"  有效信号: {signal['signal']} EMA{signal['ema_period']} 入场:{entry_price:.4f} 止盈:{bb_middle:.4f}")
            
            return valid_signals
        else:
            logger.info(f"{symbol} 1D: 无信号")
            return []
        
    except Exception as e:
        logger.error(f"测试{symbol}失败: {e}")
        return []

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("简单胜率测试")
    logger.info("=" * 60)
    
    # 测试币种
    test_symbols = ['BTC_USDT', 'ETH_USDT']
    
    all_signals = []
    
    # 测试每个币种
    for symbol in test_symbols:
        signals = test_single_symbol(symbol)
        all_signals.extend(signals)
    
    # 分析结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果")
    logger.info("=" * 60)
    
    logger.info(f"总信号数: {len(all_signals)}")
    
    if all_signals:
        # 按信号类型统计
        long_signals = [s for s in all_signals if s['signal'] == 'long']
        short_signals = [s for s in all_signals if s['signal'] == 'short']
        
        logger.info(f"做多信号: {len(long_signals)}")
        logger.info(f"做空信号: {len(short_signals)}")
        
        # 按EMA周期统计
        ema_stats = {}
        for signal in all_signals:
            ema = signal['ema_period']
            if ema not in ema_stats:
                ema_stats[ema] = []
            ema_stats[ema].append(signal)
        
        logger.info("\n按EMA周期统计:")
        for ema, ema_signals in ema_stats.items():
            logger.info(f"  EMA{ema}: {len(ema_signals)}个信号")
        
        # 保存结果
        results_df = pd.DataFrame(all_signals)
        results_df.to_csv('simple_winrate_test_results.csv', index=False, encoding='utf-8-sig')
        logger.info(f"\n结果已保存到: simple_winrate_test_results.csv")
        
        # 显示详细结果
        logger.info("\n详细信号列表:")
        for signal in all_signals:
            logger.info(f"  {signal['symbol']} {signal['signal']} EMA{signal['ema_period']} 入场:{signal['entry_price']:.4f} 止盈:{signal['take_profit_price']:.4f}")
    
    else:
        logger.info("未找到任何有效信号")
    
    logger.info("\n测试完成！")

if __name__ == "__main__":
    main()

