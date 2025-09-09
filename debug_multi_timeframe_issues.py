#!/usr/bin/env python3
"""
调试多时间框架信号重复和币种问题
"""

import requests
import json
import time
from typing import Dict, List

def test_get_top_symbols():
    """测试获取币种列表"""
    print("=== 测试获取币种列表 ===")
    try:
        response = requests.get('http://localhost:5000/multi_timeframe/get_top_symbols', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"成功获取 {data['count']} 个币种")
            print(f"数据源: {data['source']}")
            print("前10个币种:", data['symbols'][:10])
            return data['symbols']
        else:
            print(f"HTTP错误: {response.status_code}")
            return []
    except Exception as e:
        print(f"获取币种列表失败: {e}")
        return []

def test_analyze_single_symbol(symbol: str):
    """测试分析单个币种"""
    print(f"\n=== 测试分析币种: {symbol} ===")
    try:
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_symbol', 
                               json={'symbol': symbol}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"分析成功: {data['successful_timeframes']}/{data['total_timeframes_analyzed']} 个时间框架")
                
                # 统计信号
                total_signals = 0
                for result in data['results']:
                    if result['status'] == 'success':
                        signal_count = len(result.get('all_signals', []))
                        total_signals += signal_count
                        print(f"  {result['timeframe']}: {signal_count} 个信号")
                
                print(f"总信号数: {total_signals}")
                return data
            else:
                print(f"分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"分析币种失败: {e}")
    return None

def test_analyze_multiple_symbols(symbols: List[str]):
    """测试分析多个币种"""
    print(f"\n=== 测试分析多个币种: {len(symbols)} 个 ===")
    try:
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                               json={'symbols': symbols}, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"分析成功:")
                print(f"  请求币种: {data['symbols_requested']}")
                print(f"  处理币种: {data['symbols_processed']}")
                print(f"  总时间框架分析: {data['total_timeframe_analyses']}")
                print(f"  成功时间框架分析: {data['successful_timeframe_analyses']}")
                print(f"  总信号数: {data['total_signals']}")
                
                # 分析信号分布
                signal_by_symbol = {}
                signal_by_timeframe = {}
                signal_by_type = {}
                
                for signal in data.get('signals', []):
                    symbol = signal['symbol']
                    timeframe = signal['timeframe']
                    signal_type = signal['signal_type']
                    
                    signal_by_symbol[symbol] = signal_by_symbol.get(symbol, 0) + 1
                    signal_by_timeframe[timeframe] = signal_by_timeframe.get(timeframe, 0) + 1
                    signal_by_type[signal_type] = signal_by_type.get(signal_type, 0) + 1
                
                print(f"\n信号分布:")
                print(f"  按币种: {dict(list(signal_by_symbol.items())[:5])}")
                print(f"  按时间框架: {signal_by_timeframe}")
                print(f"  按信号类型: {signal_by_type}")
                
                return data
            else:
                print(f"分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"分析多个币种失败: {e}")
    return None

def check_duplicate_signals(signals: List[Dict]):
    """检查重复信号"""
    print(f"\n=== 检查重复信号 ===")
    
    # 按币种和时间框架分组
    signal_groups = {}
    for signal in signals:
        key = f"{signal['symbol']}_{signal['timeframe']}"
        if key not in signal_groups:
            signal_groups[key] = []
        signal_groups[key].append(signal)
    
    # 检查重复
    duplicates = []
    for key, group in signal_groups.items():
        if len(group) > 1:
            duplicates.append((key, len(group)))
    
    if duplicates:
        print(f"发现 {len(duplicates)} 个币种-时间框架组合有重复信号:")
        for key, count in duplicates[:5]:  # 只显示前5个
            print(f"  {key}: {count} 个信号")
    else:
        print("未发现重复信号")
    
    return duplicates

def main():
    print("开始调试多时间框架问题...")
    
    # 1. 测试获取币种列表
    symbols = test_get_top_symbols()
    if not symbols:
        print("无法获取币种列表，退出")
        return
    
    # 2. 测试分析单个币种（BTC）
    btc_result = test_analyze_single_symbol('BTCUSDT')
    
    # 3. 测试分析前5个币种
    test_symbols = symbols[:5]
    multi_result = test_analyze_multiple_symbols(test_symbols)
    
    if multi_result and 'signals' in multi_result:
        # 4. 检查重复信号
        check_duplicate_signals(multi_result['signals'])
        
        # 5. 显示详细信号信息
        print(f"\n=== 详细信号信息 ===")
        for signal in multi_result['signals'][:10]:  # 只显示前10个
            print(f"{signal['symbol']} {signal['timeframe']} {signal['signal_type']} "
                  f"收益率:{signal['profit_pct']}% 入场:{signal['entry_price']} 止盈:{signal['take_profit']}")

if __name__ == "__main__":
    main()

