#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试新策略 - 只测试1个币种
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
    """获取历史数据 - 只获取7天数据"""
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
        
        response = requests.get(url, params=params, timeout=5)  # 减少超时时间
        
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
    logger.info("快速测试新策略")
    logger.info("=" * 60)
    
    # 创建修改策略实例
    modified_strategy = MultiTimeframeStrategy('modified')
    
    logger.info(f"新策略时间框架: {modified_strategy.timeframes}")
    logger.info(f"新策略止盈配置: {modified_strategy.take_profit_timeframes}")
    
    # 只测试BTC
    symbol = 'BTC_USDT'
    logger.info(f"\n测试币种: {symbol}")
    
    try:
        # 只测试1D时间框架
        logger.info("获取1D数据...")
        df = get_historical_data(symbol, '1d', days=7)
        if df.empty or len(df) < 50:
            logger.warning(f"{symbol} 1D数据不足")
            return
        
        logger.info(f"获取到{len(df)}条数据")
        
        # 计算技术指标
        logger.info("计算技术指标...")
        df = modified_strategy.calculate_emas(df, '1d')
        df = modified_strategy.calculate_bollinger_bands(df)
        df = df.dropna()
        
        if df.empty:
            logger.warning(f"{symbol} 1D计算指标后数据为空")
            return
        
        logger.info(f"计算指标后数据长度: {len(df)}")
        
        # 判断趋势
        if modified_strategy.is_bullish_trend(df):
            trend = 'bullish'
            logger.info(f"{symbol} 1D: 多头趋势")
        elif modified_strategy.is_bearish_trend(df):
            trend = 'bearish'
            logger.info(f"{symbol} 1D: 空头趋势")
        else:
            logger.info(f"{symbol} 1D: 中性趋势")
            return
        
        # 寻找信号
        logger.info("寻找信号...")
        signals = modified_strategy.find_ema_pullback_levels(df, trend, '1d', symbol)
        
        if signals:
            logger.info(f"{symbol} 1D: 找到{len(signals)}个信号")
            for signal in signals:
                logger.info(f"  {signal['signal']} EMA{signal['ema_period']} 入场价: {signal['entry_price']:.4f}")
                
                # 计算止盈（统一使用1分钟布林中轨）
                logger.info("计算止盈...")
                take_profit_tf = '1m'
                tp_df = get_historical_data(symbol, take_profit_tf, days=7)
                
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
                        
                        logger.info(f"    止盈价: {bb_middle:.4f}")
                        logger.info(f"    收益率: {profit_pct:.2f}%")
        else:
            logger.info(f"{symbol} 1D: 无信号")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
    
    logger.info("\n快速测试完成！")

if __name__ == "__main__":
    main()
