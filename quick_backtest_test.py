#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速回测测试：只测试几个币种
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
                df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open', 'quote_volume', 'trades'])
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
    logger.info("快速回测测试")
    logger.info("=" * 60)
    
    # 创建策略实例
    strategy = MultiTimeframeStrategy('modified')
    logger.info(f"策略时间框架: {strategy.timeframes}")
    logger.info(f"策略止盈配置: {strategy.take_profit_timeframes}")
    
    # 设置回测开始时间（今天早上8点）
    today = datetime.now().date()
    start_time = datetime.combine(today, datetime.min.time().replace(hour=8))
    logger.info(f"回测开始时间: {start_time}")
    
    # 测试币种
    test_symbols = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']
    
    # 回测参数
    initial_capital = 10000
    current_capital = initial_capital
    stop_loss_pct = 0.10
    total_signals = 0
    win_signals = 0
    loss_signals = 0
    
    logger.info(f"初始资金: {initial_capital}U")
    logger.info(f"止损设置: {stop_loss_pct*100}%")
    
    for symbol in test_symbols:
        logger.info(f"\n测试币种: {symbol}")
        
        try:
            # 获取1D数据
            df = get_historical_data(symbol, '1d', days=7)
            if df.empty or len(df) < 50:
                logger.warning(f"{symbol} 1D数据不足")
                continue
            
            logger.info(f"获取到{len(df)}条数据")
            
            # 计算技术指标
            df = strategy.calculate_emas(df, '1d')
            df = strategy.calculate_bollinger_bands(df)
            df = df.dropna()
            
            if df.empty:
                logger.warning(f"{symbol} 计算指标后数据为空")
                continue
            
            # 判断趋势
            if strategy.is_bullish_trend(df):
                trend = 'bullish'
                logger.info(f"{symbol} 1D: 多头趋势")
            elif strategy.is_bearish_trend(df):
                trend = 'bearish'
                logger.info(f"{symbol} 1D: 空头趋势")
            else:
                logger.info(f"{symbol} 1D: 中性趋势")
                continue
            
            # 寻找信号
            signals = strategy.find_ema_pullback_levels(df, trend, '1d', symbol)
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
            
            logger.info(f"{symbol} 有效信号数: {len(valid_signals)}")
            total_signals += len(valid_signals)
            
            # 模拟交易结果
            for signal in valid_signals:
                entry_price = signal['entry_price']
                take_profit_price = signal['take_profit_price']
                signal_type = signal['signal']
                
                # 计算止损价格
                if signal_type == 'long':
                    stop_loss_price = entry_price * (1 - stop_loss_pct)
                else:
                    stop_loss_price = entry_price * (1 + stop_loss_pct)
                
                # 模拟价格走势（简化版）
                # 这里我们假设有50%的概率达到止盈，50%的概率达到止损
                import random
                if random.random() < 0.5:
                    # 止盈
                    if signal_type == 'long':
                        profit_pct = (take_profit_price - entry_price) / entry_price
                    else:
                        profit_pct = (entry_price - take_profit_price) / entry_price
                    
                    profit_usd = current_capital * profit_pct
                    current_capital += profit_usd
                    win_signals += 1
                    logger.info(f"    ✅ 胜: 止盈 收益率:{profit_pct:.2%} 盈亏:{profit_usd:.2f}U 余额:{current_capital:.2f}U")
                else:
                    # 止损
                    profit_usd = current_capital * (-stop_loss_pct)
                    current_capital += profit_usd
                    loss_signals += 1
                    logger.info(f"    ❌ 败: 止损 收益率:{-stop_loss_pct:.2%} 盈亏:{profit_usd:.2f}U 余额:{current_capital:.2f}U")
            
        except Exception as e:
            logger.error(f"测试{symbol}失败: {e}")
            continue
    
    # 分析结果
    logger.info("\n" + "=" * 60)
    logger.info("回测结果分析")
    logger.info("=" * 60)
    
    logger.info(f"总信号数: {total_signals}")
    logger.info(f"胜信号数: {win_signals}")
    logger.info(f"败信号数: {loss_signals}")
    
    if total_signals > 0:
        win_rate = win_signals / total_signals * 100
        logger.info(f"胜率: {win_rate:.2f}%")
    
    logger.info(f"初始资金: {initial_capital}U")
    logger.info(f"最终余额: {current_capital:.2f}U")
    
    total_return = (current_capital - initial_capital) / initial_capital * 100
    logger.info(f"总收益率: {total_return:.2f}%")
    
    if total_return > 0:
        logger.info("✅ 策略盈利！")
    else:
        logger.info("❌ 策略亏损！")
    
    logger.info("\n快速回测完成！")

if __name__ == "__main__":
    main()

