#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版回测脚本：测试GATE.IO数据获取和策略
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
    """获取GATE.IO前10个币种（测试用）"""
    try:
        import requests
        
        # 获取交易量数据
        ticker_url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(ticker_url, timeout=10)
        
        if response.status_code == 200:
            tickers = response.json()
            # 筛选USDT交易对，按24h交易量排序
            usdt_tickers = [t for t in tickers if t['currency_pair'].endswith('_USDT')]
            usdt_tickers.sort(key=lambda x: float(x.get('base_volume', 0)), reverse=True)
            
            top_symbols = [t['currency_pair'] for t in usdt_tickers[:limit]]
            logger.info(f"获取到GATE.IO前{len(top_symbols)}个币种: {top_symbols}")
            return top_symbols
        else:
            logger.error(f"获取交易量数据失败: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"获取GATE.IO币种失败: {e}")
        return []

def get_historical_data(symbol, timeframe='1d', days=7):
    """获取历史数据"""
    try:
        import requests
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 转换为时间戳
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        # 获取K线数据
        url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
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
                # 转换为DataFrame
                df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                # 转换数据类型
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
            df = get_historical_data(symbol, timeframe, days=7)
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
                    results.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'strategy': strategy.strategy_type,
                        'signal_type': signal['signal'],
                        'ema_period': signal['ema_period'],
                        'entry_price': signal['entry_price'],
                        'condition': signal['condition']
                    })
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
    logger.info("开始简化版回测")
    logger.info("=" * 60)
    
    # 获取前10个币种
    logger.info("获取GATE.IO前10个币种...")
    symbols = get_gate_top_symbols(10)
    
    if not symbols:
        logger.error("无法获取币种列表")
        return
    
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
    for symbol in symbols[:3]:  # 只测试前3个币种
        results = test_strategy_on_symbol(original_strategy, symbol)
        original_results.extend(results)
    
    # 测试修改策略
    logger.info("\n" + "=" * 40)
    logger.info("测试修改策略")
    logger.info("=" * 40)
    
    modified_results = []
    for symbol in symbols[:3]:  # 只测试前3个币种
        results = test_strategy_on_symbol(modified_strategy, symbol)
        modified_results.extend(results)
    
    # 输出结果
    logger.info("\n" + "=" * 60)
    logger.info("回测结果")
    logger.info("=" * 60)
    
    logger.info(f"原策略信号数: {len(original_results)}")
    for result in original_results:
        logger.info(f"  {result['symbol']} {result['timeframe']} {result['signal_type']} EMA{result['ema_period']}")
    
    logger.info(f"修改策略信号数: {len(modified_results)}")
    for result in modified_results:
        logger.info(f"  {result['symbol']} {result['timeframe']} {result['signal_type']} EMA{result['ema_period']}")
    
    logger.info("回测完成！")

if __name__ == "__main__":
    main()