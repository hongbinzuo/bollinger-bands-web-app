#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量测试脚本
验证K线数据获取、技术指标计算、信号准确性
"""

import sys
import os
import pandas as pd
import numpy as np
import time
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_data_retrieval():
    """测试数据获取质量"""
    print("🔍 测试数据获取质量")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    test_timeframes = ['4h', '8h', '12h', '1d']
    
    for symbol in test_symbols:
        print(f"\n📊 测试币种: {symbol}")
        print("-" * 30)
        
        for timeframe in test_timeframes:
            try:
                # 获取K线数据
                df = strategy.get_klines_data(symbol, timeframe, 100)
                
                if df.empty:
                    print(f"  ❌ {timeframe}: 数据为空")
                    continue
                
                # 检查数据完整性
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    print(f"  ❌ {timeframe}: 缺少列 {missing_columns}")
                    continue
                
                # 检查数据质量
                data_quality_issues = []
                
                # 检查是否有NaN值
                nan_counts = df.isnull().sum()
                if nan_counts.any():
                    data_quality_issues.append(f"NaN值: {nan_counts.to_dict()}")
                
                # 检查价格数据合理性
                if (df['close'] <= 0).any():
                    data_quality_issues.append("价格数据包含非正值")
                
                if (df['high'] < df['low']).any():
                    data_quality_issues.append("最高价低于最低价")
                
                if (df['high'] < df['close']).any() or (df['high'] < df['open']).any():
                    data_quality_issues.append("最高价低于收盘价或开盘价")
                
                if (df['low'] > df['close']).any() or (df['low'] > df['open']).any():
                    data_quality_issues.append("最低价高于收盘价或开盘价")
                
                # 检查成交量
                if (df['volume'] < 0).any():
                    data_quality_issues.append("成交量包含负值")
                
                if data_quality_issues:
                    print(f"  ⚠️  {timeframe}: 数据质量问题")
                    for issue in data_quality_issues:
                        print(f"    - {issue}")
                else:
                    print(f"  ✅ {timeframe}: 数据质量良好")
                    print(f"    📊 数据点数: {len(df)}")
                    print(f"    📈 价格范围: {df['close'].min():.6f} - {df['close'].max():.6f}")
                    print(f"    📊 平均成交量: {df['volume'].mean():.2f}")
                
            except Exception as e:
                print(f"  ❌ {timeframe}: 获取数据异常 - {e}")

def test_technical_indicators():
    """测试技术指标计算"""
    print("\n🔍 测试技术指标计算")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    symbol = 'BTCUSDT'
    timeframe = '4h'
    
    try:
        # 获取数据
        df = strategy.get_klines_data(symbol, timeframe, 300)
        if df.empty:
            print("❌ 无法获取测试数据")
            return
        
        print(f"📊 测试币种: {symbol} ({timeframe})")
        print(f"📈 数据点数: {len(df)}")
        
        # 测试EMA计算
        print("\n📈 测试EMA计算:")
        df_with_ema = strategy.calculate_emas(df.copy())
        
        ema_periods = strategy.ema_periods
        for period in ema_periods:
            ema_col = f'ema{period}'
            if ema_col in df_with_ema.columns:
                ema_values = df_with_ema[ema_col].dropna()
                if len(ema_values) > 0:
                    print(f"  ✅ EMA{period}: {len(ema_values)}个有效值")
                    print(f"    📊 最新值: {ema_values.iloc[0]:.6f}")
                    print(f"    📈 范围: {ema_values.min():.6f} - {ema_values.max():.6f}")
                else:
                    print(f"  ❌ EMA{period}: 无有效值")
            else:
                print(f"  ❌ EMA{period}: 列不存在")
        
        # 测试布林带计算
        print("\n📊 测试布林带计算:")
        df_with_bb = strategy.calculate_bollinger_bands(df.copy())
        
        bb_columns = ['bb_middle', 'bb_upper', 'bb_lower', 'bb_std']
        for col in bb_columns:
            if col in df_with_bb.columns:
                bb_values = df_with_bb[col].dropna()
                if len(bb_values) > 0:
                    print(f"  ✅ {col}: {len(bb_values)}个有效值")
                    print(f"    📊 最新值: {bb_values.iloc[0]:.6f}")
                else:
                    print(f"  ❌ {col}: 无有效值")
            else:
                print(f"  ❌ {col}: 列不存在")
        
        # 测试趋势判断
        print("\n📈 测试趋势判断:")
        if all(f'ema{period}' in df_with_ema.columns for period in [89, 144, 233]):
            is_bullish = strategy.is_bullish_trend(df_with_ema)
            is_bearish = strategy.is_bearish_trend(df_with_ema)
            
            print(f"  📊 多头趋势: {is_bullish}")
            print(f"  📊 空头趋势: {is_bearish}")
            print(f"  📊 趋势状态: {'多头' if is_bullish else '空头' if is_bearish else '中性'}")
        else:
            print("  ❌ 无法判断趋势: EMA数据不完整")
        
    except Exception as e:
        print(f"❌ 技术指标测试异常: {e}")
        import traceback
        traceback.print_exc()

def test_signal_accuracy():
    """测试信号准确性"""
    print("\n🔍 测试信号准确性")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    symbol = 'BTCUSDT'
    timeframe = '4h'
    
    try:
        # 获取数据并计算指标
        df = strategy.get_klines_data(symbol, timeframe, 300)
        if df.empty:
            print("❌ 无法获取测试数据")
            return
        
        df = strategy.calculate_emas(df)
        df = strategy.calculate_bollinger_bands(df)
        df.dropna(inplace=True)
        
        if df.empty:
            print("❌ 计算指标后数据为空")
            return
        
        print(f"📊 测试币种: {symbol} ({timeframe})")
        print(f"📈 有效数据点: {len(df)}")
        
        # 测试回撤信号
        print("\n🎯 测试回撤信号:")
        trend = 'bullish' if strategy.is_bullish_trend(df) else 'bearish'
        pullback_levels = strategy.find_ema_pullback_levels(df, trend)
        
        print(f"  📊 当前趋势: {trend}")
        print(f"  🎯 回撤信号数: {len(pullback_levels)}")
        
        for i, level in enumerate(pullback_levels[:3]):  # 只显示前3个
            print(f"    {i+1}. EMA{level['ema_period']}: {level['type']} @ {level['ema_value']:.6f}")
            print(f"       入场价: {level['entry_price']:.6f}")
            print(f"       距离: {level['price_distance']:.4f}")
        
        # 测试交叉信号
        print("\n🔄 测试交叉信号:")
        crossover_signals = strategy.find_ema_crossover_signals(df)
        print(f"  🎯 交叉信号数: {len(crossover_signals)}")
        
        for i, signal in enumerate(crossover_signals[:3]):  # 只显示前3个
            print(f"    {i+1}. {signal['type']}: {signal['signal']}")
            print(f"       EMA89: {signal['ema89']:.6f}")
            print(f"       EMA233: {signal['ema233']:.6f}")
            print(f"       强度: {signal['strength']}")
        
        # 测试突破信号
        print("\n💥 测试突破信号:")
        breakout_signals = strategy.find_price_breakout_signals(df)
        print(f"  🎯 突破信号数: {len(breakout_signals)}")
        
        for i, signal in enumerate(breakout_signals[:3]):  # 只显示前3个
            print(f"    {i+1}. {signal['type']}: {signal['signal']}")
            print(f"       突破位: {signal.get('breakout_level', signal.get('breakdown_level', 'N/A')):.6f}")
            print(f"       当前价: {signal['current_price']:.6f}")
            print(f"       强度: {signal['strength']}")
        
        # 测试支撑阻力信号
        print("\n📊 测试支撑阻力信号:")
        sr_signals = strategy.find_support_resistance_signals(df)
        print(f"  🎯 支撑阻力信号数: {len(sr_signals)}")
        
        for i, signal in enumerate(sr_signals[:3]):  # 只显示前3个
            print(f"    {i+1}. {signal['type']}: {signal['signal']}")
            print(f"       价位: {signal['level']:.6f}")
            print(f"       当前价: {signal['current_price']:.6f}")
            print(f"       距离: {signal['distance']:.4f}")
        
    except Exception as e:
        print(f"❌ 信号准确性测试异常: {e}")
        import traceback
        traceback.print_exc()

def test_data_consistency():
    """测试数据一致性"""
    print("\n🔍 测试数据一致性")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    symbol = 'BTCUSDT'
    
    # 测试不同时间框架的数据一致性
    timeframes = ['4h', '8h', '12h', '1d']
    results = {}
    
    for timeframe in timeframes:
        try:
            df = strategy.get_klines_data(symbol, timeframe, 50)
            if not df.empty:
                latest_price = df['close'].iloc[0]
                results[timeframe] = latest_price
                print(f"  📊 {timeframe}: 最新价格 {latest_price:.6f}")
            else:
                print(f"  ❌ {timeframe}: 无数据")
        except Exception as e:
            print(f"  ❌ {timeframe}: 异常 - {e}")
    
    # 检查价格一致性
    if len(results) > 1:
        prices = list(results.values())
        price_range = max(prices) - min(prices)
        price_avg = sum(prices) / len(prices)
        price_variance = price_range / price_avg * 100
        
        print(f"\n📊 价格一致性分析:")
        print(f"  📈 价格范围: {min(prices):.6f} - {max(prices):.6f}")
        print(f"  📊 价格差异: {price_range:.6f}")
        print(f"  📊 差异百分比: {price_variance:.2f}%")
        
        if price_variance < 5:
            print("  ✅ 价格一致性良好 (< 5%)")
        elif price_variance < 10:
            print("  ⚠️  价格一致性一般 (< 10%)")
        else:
            print("  ❌ 价格一致性较差 (> 10%)")

def test_edge_cases():
    """测试边界情况"""
    print("\n🔍 测试边界情况")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试无效币种
    print("📊 测试无效币种:")
    invalid_symbols = ['INVALID123', 'NONEXISTENT', 'TEST_SYMBOL']
    
    for symbol in invalid_symbols:
        try:
            df = strategy.get_klines_data(symbol, '4h', 10)
            if df.empty:
                print(f"  ✅ {symbol}: 正确处理无效币种")
            else:
                print(f"  ⚠️  {symbol}: 意外返回数据")
        except Exception as e:
            print(f"  ✅ {symbol}: 正确处理异常 - {type(e).__name__}")
    
    # 测试无效时间框架
    print("\n📊 测试无效时间框架:")
    invalid_timeframes = ['1s', '2h', '6h', '2d', '1m']
    
    for timeframe in invalid_timeframes:
        try:
            df = strategy.get_klines_data('BTCUSDT', timeframe, 10)
            if df.empty:
                print(f"  ✅ {timeframe}: 正确处理无效时间框架")
            else:
                print(f"  ⚠️  {timeframe}: 意外返回数据")
        except Exception as e:
            print(f"  ✅ {timeframe}: 正确处理异常 - {type(e).__name__}")
    
    # 测试极小数据量
    print("\n📊 测试极小数据量:")
    try:
        df = strategy.get_klines_data('BTCUSDT', '4h', 5)
        if df.empty:
            print("  ✅ 极小数据量: 正确处理")
        else:
            print(f"  ⚠️  极小数据量: 返回 {len(df)} 条数据")
    except Exception as e:
        print(f"  ✅ 极小数据量: 正确处理异常 - {type(e).__name__}")

def main():
    """主测试函数"""
    print("🚀 数据质量测试开始")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. 测试数据获取质量
        test_data_retrieval()
        
        # 2. 测试技术指标计算
        test_technical_indicators()
        
        # 3. 测试信号准确性
        test_signal_accuracy()
        
        # 4. 测试数据一致性
        test_data_consistency()
        
        # 5. 测试边界情况
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 数据质量测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

