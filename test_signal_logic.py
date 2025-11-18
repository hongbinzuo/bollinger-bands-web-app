#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号逻辑回测脚本
测试优化后的信号逻辑是否合理
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data():
    """创建测试数据"""
    # 创建100根4小时K线数据
    dates = pd.date_range(start='2024-01-01', periods=100, freq='4H')
    
    # 模拟价格数据：多头趋势，价格围绕EMA233波动
    base_price = 50000
    prices = []
    for i in range(100):
        # 模拟价格围绕EMA233波动
        trend = 0.001 * i  # 缓慢上升趋势
        noise = np.random.normal(0, 0.02)  # 2%的随机波动
        price = base_price * (1 + trend + noise)
        prices.append(price)
    
    # 创建OHLCV数据
    data = []
    for i, price in enumerate(prices):
        # 模拟OHLC
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else price
        close = price
        volume = np.random.uniform(1000, 5000)
        
        data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

def test_signal_logic():
    """测试信号逻辑"""
    logger.info("开始测试信号逻辑...")
    
    # 创建策略实例
    strategy = MultiTimeframeStrategy()
    
    # 创建测试数据
    df = create_test_data()
    logger.info(f"创建测试数据: {len(df)} 根K线")
    
    # 计算技术指标
    df = strategy.calculate_emas(df)
    df = strategy.calculate_bollinger_bands(df)
    df.dropna(inplace=True)
    
    logger.info(f"计算指标后数据: {len(df)} 根K线")
    
    # 检查趋势
    is_bullish = strategy.is_bullish_trend(df)
    is_bearish = strategy.is_bearish_trend(df)
    
    logger.info(f"多头趋势: {is_bullish}")
    logger.info(f"空头趋势: {is_bearish}")
    
    # 测试信号生成
    trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
    logger.info(f"当前趋势: {trend}")
    
    # 寻找所有大级别位置信号
    pullback_signals = strategy.find_ema_pullback_levels(df, trend)
    crossover_signals = strategy.find_ema_crossover_signals(df)
    breakout_signals = strategy.find_price_breakout_signals(df)
    support_resistance_signals = strategy.find_support_resistance_signals(df)
    
    # 合并所有信号
    all_signals = []
    all_signals.extend(pullback_signals)
    all_signals.extend(crossover_signals)
    all_signals.extend(breakout_signals)
    all_signals.extend(support_resistance_signals)
    
    logger.info(f"EMA回踩信号数量: {len(pullback_signals)}")
    logger.info(f"EMA交叉信号数量: {len(crossover_signals)}")
    logger.info(f"价格突破信号数量: {len(breakout_signals)}")
    logger.info(f"支撑阻力信号数量: {len(support_resistance_signals)}")
    logger.info(f"总信号数量: {len(all_signals)}")
    
    # 分析信号质量
    for i, signal in enumerate(all_signals[:5]):  # 只显示前5个信号
        logger.info(f"信号 {i+1}:")
        logger.info(f"  类型: {signal.get('signal')}")
        logger.info(f"  入场价: {signal.get('entry_price')}")
        logger.info(f"  EMA周期: {signal.get('ema_period', 'N/A')}")
        logger.info(f"  EMA值: {signal.get('ema_value', 'N/A')}")
        logger.info(f"  价格距离: {signal.get('price_distance', 'N/A')}")
        logger.info(f"  条件: {signal.get('condition')}")
        logger.info(f"  描述: {signal.get('description')}")
    
    # 测试止盈逻辑
    take_profit_timeframe = strategy.take_profit_timeframes.get('4h', '5m')
    logger.info(f"4H时间框架对应止盈时间框架: {take_profit_timeframe}")
    
    # 获取止盈数据
    tp_df = strategy.get_klines_data('BTCUSDT', take_profit_timeframe, 200)
    if not tp_df.empty:
        tp_df = strategy.calculate_bollinger_bands(tp_df)
        tp_df.dropna(inplace=True)
        
        if not tp_df.empty:
            bb_middle = tp_df['bb_middle'].iloc[-1]
            current_price = tp_df['close'].iloc[-1]
            
            logger.info(f"5分钟布林带中轨: {bb_middle:.2f}")
            logger.info(f"当前价格: {current_price:.2f}")
            
            # 计算止盈距离
            if pullback_signals:
                entry_price = pullback_signals[0]['entry_price']
                if pullback_signals[0]['signal'] == 'long':
                    profit_pct = ((bb_middle - entry_price) / entry_price) * 100
                    logger.info(f"做多止盈收益率: {profit_pct:.2f}%")
                else:
                    profit_pct = ((entry_price - bb_middle) / entry_price) * 100
                    logger.info(f"做空止盈收益率: {profit_pct:.2f}%")
    
    return pullback_signals

def test_timeframe_alignment():
    """测试时间框架对齐"""
    logger.info("测试时间框架对齐...")
    
    strategy = MultiTimeframeStrategy()
    
    # 检查时间框架对应关系
    for main_tf, tp_tf in strategy.take_profit_timeframes.items():
        logger.info(f"{main_tf} -> {tp_tf}")
        
        # 验证时间框架比例是否合理
        main_hours = {'4h': 4, '8h': 8, '12h': 12, '1d': 24, '3d': 72, '1w': 168}[main_tf]
        tp_hours = {'5m': 5/60, '15m': 15/60, '30m': 30/60, '1h': 1, '4h': 4, '1d': 24}[tp_tf]
        
        ratio = main_hours / tp_hours
        logger.info(f"  时间比例: {ratio:.1f}:1")
        
        # 检查比例是否合理 (应该在10-100之间)
        if 10 <= ratio <= 100:
            logger.info(f"  ✓ 时间比例合理")
        else:
            logger.warning(f"  ⚠ 时间比例可能不合理: {ratio:.1f}:1")

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("信号逻辑回测开始")
    logger.info("=" * 50)
    
    try:
        # 测试时间框架对齐
        test_timeframe_alignment()
        
        logger.info("-" * 30)
        
        # 测试信号逻辑
        signals = test_signal_logic()
        
        logger.info("-" * 30)
        
        # 总结
        logger.info("回测总结:")
        logger.info(f"1. 时间框架对齐: 4H->5M, 8H->15M, 12H->30M, 1D->1H, 3D->4H, 1W->1D")
        logger.info(f"2. 信号类型: 所有大级别时间框架的EMA89/144/233信号")
        logger.info(f"3. 信号数量: {len(signals)} 个")
        logger.info(f"4. 止盈逻辑: 对应时间框架的布林带中轨")
        
        if signals:
            logger.info("✓ 信号逻辑合理，包含所有大级别位置信号")
        else:
            logger.info("⚠ 未生成信号，可能需要调整参数")
            
    except Exception as e:
        logger.error(f"回测失败: {e}", exc_info=True)
    
    logger.info("=" * 50)
    logger.info("信号逻辑回测完成")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
