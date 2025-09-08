#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多时间框架策略信号测试脚本
测试多时间框架EMA回撤策略是否能正常返回信号
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_single_symbol():
    """测试单个币种信号生成"""
    print("=" * 60)
    print("测试单个币种信号生成")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试币种列表
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']
    
    for symbol in test_symbols:
        print(f"\n🔍 测试币种: {symbol}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            result = strategy.analyze_symbol(symbol)
            end_time = time.time()
            
            print(f"✅ 分析完成，耗时: {end_time - start_time:.2f}秒")
            print(f"📊 总时间框架数: {result['total_timeframes']}")
            print(f"✅ 成功分析数: {result['successful_timeframes']}")
            
            # 检查每个时间框架的结果
            for tf_result in result['results']:
                timeframe = tf_result['timeframe']
                status = tf_result['status']
                
                if status == 'success':
                    trend = tf_result['trend']
                    signal_count = tf_result['signal_count']
                    current_price = tf_result['current_price']
                    
                    print(f"  📈 {timeframe}: {trend}趋势, {signal_count}个信号, 价格: {current_price}")
                    
                    # 显示具体信号
                    if tf_result['all_signals']:
                        print(f"    🎯 信号详情:")
                        for i, signal in enumerate(tf_result['all_signals'][:3]):  # 只显示前3个信号
                            signal_type = signal.get('type', 'unknown')
                            signal_direction = signal.get('signal', 'unknown')
                            print(f"      {i+1}. {signal_type} - {signal_direction}")
                else:
                    print(f"  ❌ {timeframe}: {tf_result.get('message', '分析失败')}")
            
        except Exception as e:
            print(f"❌ 测试 {symbol} 失败: {e}")
        
        print()

def test_multiple_symbols():
    """测试多个币种批量分析"""
    print("=" * 60)
    print("测试多个币种批量分析")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试币种列表
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
    
    print(f"📋 测试币种列表: {', '.join(test_symbols)}")
    print()
    
    try:
        start_time = time.time()
        results = strategy.analyze_multiple_symbols(test_symbols)
        end_time = time.time()
        
        print(f"✅ 批量分析完成，耗时: {end_time - start_time:.2f}秒")
        print(f"📊 处理币种数: {len(results)}")
        
        # 统计信号数量
        total_signals = 0
        successful_symbols = 0
        
        for symbol, symbol_results in results.items():
            print(f"\n🔍 币种: {symbol}")
            print("-" * 30)
            
            symbol_signal_count = 0
            symbol_success_count = 0
            
            for tf_result in symbol_results:
                if tf_result['status'] == 'success':
                    symbol_success_count += 1
                    signal_count = tf_result.get('signal_count', 0)
                    symbol_signal_count += signal_count
                    
                    timeframe = tf_result['timeframe']
                    trend = tf_result['trend']
                    print(f"  📈 {timeframe}: {trend}趋势, {signal_count}个信号")
                else:
                    timeframe = tf_result['timeframe']
                    print(f"  ❌ {timeframe}: {tf_result.get('message', '分析失败')}")
            
            if symbol_success_count > 0:
                successful_symbols += 1
                total_signals += symbol_signal_count
                print(f"  ✅ 成功: {symbol_success_count}/{len(symbol_results)} 时间框架, 总信号: {symbol_signal_count}")
            else:
                print(f"  ❌ 失败: 所有时间框架分析失败")
        
        print(f"\n📊 批量分析统计:")
        print(f"  ✅ 成功币种: {successful_symbols}/{len(test_symbols)}")
        print(f"  🎯 总信号数: {total_signals}")
        print(f"  ⏱️  平均耗时: {(end_time - start_time)/len(test_symbols):.2f}秒/币种")
        
    except Exception as e:
        print(f"❌ 批量分析失败: {e}")

def test_signal_data_format():
    """测试信号数据格式和完整性"""
    print("=" * 60)
    print("测试信号数据格式和完整性")
    print("=" * 60)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试一个币种
    symbol = 'BTCUSDT'
    print(f"🔍 测试币种: {symbol}")
    
    try:
        result = strategy.analyze_symbol(symbol)
        
        # 检查数据结构
        required_keys = ['symbol', 'results', 'total_timeframes', 'successful_timeframes']
        for key in required_keys:
            if key in result:
                print(f"✅ 包含字段: {key}")
            else:
                print(f"❌ 缺少字段: {key}")
        
        # 检查每个时间框架的结果
        for tf_result in result['results']:
            timeframe = tf_result['timeframe']
            status = tf_result['status']
            
            print(f"\n📊 时间框架: {timeframe}")
            print(f"  状态: {status}")
            
            if status == 'success':
                # 检查成功结果的数据结构
                success_keys = ['trend', 'current_price', 'all_signals', 'signal_count']
                for key in success_keys:
                    if key in tf_result:
                        print(f"  ✅ {key}: {type(tf_result[key])}")
                    else:
                        print(f"  ❌ 缺少字段: {key}")
                
                # 检查信号数据
                signals = tf_result.get('all_signals', [])
                print(f"  🎯 信号数量: {len(signals)}")
                
                if signals:
                    # 检查第一个信号的数据结构
                    first_signal = signals[0]
                    signal_keys = ['type', 'signal', 'ema_period', 'entry_price']
                    print(f"  📋 信号字段检查:")
                    for key in signal_keys:
                        if key in first_signal:
                            print(f"    ✅ {key}: {first_signal[key]}")
                        else:
                            print(f"    ❌ 缺少字段: {key}")
            else:
                print(f"  ❌ 分析失败: {tf_result.get('message', '未知错误')}")
        
    except Exception as e:
        print(f"❌ 数据格式测试失败: {e}")

def test_api_endpoints():
    """测试API端点功能"""
    print("=" * 60)
    print("测试API端点功能")
    print("=" * 60)
    
    try:
        # 导入API模块
        from multi_timeframe_api import strategy
        
        # 测试策略信息
        print("🔍 测试策略信息获取...")
        info = {
            'strategy_name': 'Multi-Timeframe EMA Pullback Strategy',
            'timeframes': strategy.timeframes,
            'ema_periods': strategy.ema_periods,
            'take_profit_mapping': strategy.take_profit_timeframes
        }
        
        print(f"✅ 策略名称: {info['strategy_name']}")
        print(f"📊 支持时间框架: {info['timeframes']}")
        print(f"📈 EMA周期: {info['ema_periods']}")
        print(f"🎯 止盈映射: {info['take_profit_mapping']}")
        
        # 测试币种验证
        print(f"\n🔍 测试币种验证...")
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'INVALID_SYMBOL']
        
        for symbol in test_symbols:
            is_valid = strategy.validate_symbol(symbol)
            status = "✅ 有效" if is_valid else "❌ 无效"
            print(f"  {symbol}: {status}")
        
    except Exception as e:
        print(f"❌ API端点测试失败: {e}")

def main():
    """主测试函数"""
    print("🚀 多时间框架策略信号测试开始")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. 测试单个币种
        test_single_symbol()
        
        # 2. 测试多个币种
        test_multiple_symbols()
        
        # 3. 测试数据格式
        test_signal_data_format()
        
        # 4. 测试API端点
        test_api_endpoints()
        
        print("=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
