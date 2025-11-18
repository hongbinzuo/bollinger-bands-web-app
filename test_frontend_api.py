#!/usr/bin/env python3
"""
测试前端API调用
"""

import requests
import json

def test_frontend_api_calls():
    """测试前端API调用"""
    print("=== 测试前端API调用 ===")
    
    # 1. 测试获取币种列表
    print("\n1. 测试获取币种列表")
    try:
        response = requests.get('http://localhost:5000/multi_timeframe/get_top_symbols', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"成功获取 {data['count']} 个币种")
            print(f"前5个币种: {data['symbols'][:5]}")
            symbols = data['symbols'][:5]  # 只取前5个测试
        else:
            print(f"获取币种失败: {response.status_code}")
            return
    except Exception as e:
        print(f"获取币种异常: {e}")
        return
    
    # 2. 测试分析多个币种
    print(f"\n2. 测试分析多个币种: {symbols}")
    try:
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                               json={'symbols': symbols}, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"分析成功:")
                print(f"  请求币种: {data['symbols_requested']}")
                print(f"  处理币种: {data['symbols_processed']}")
                print(f"  总信号数: {data['total_signals']}")
                
                # 分析信号分布
                signal_by_symbol = {}
                for signal in data.get('signals', []):
                    symbol = signal['symbol']
                    signal_by_symbol[symbol] = signal_by_symbol.get(symbol, 0) + 1
                
                print(f"  按币种分布: {signal_by_symbol}")
                
                # 显示每个币种的信号详情
                for symbol in symbols:
                    symbol_signals = [s for s in data.get('signals', []) if s['symbol'] == symbol]
                    print(f"  {symbol}: {len(symbol_signals)} 个信号")
                    if symbol_signals:
                        for signal in symbol_signals[:3]:  # 只显示前3个
                            print(f"    {signal['timeframe']} {signal['signal_type']} 收益率:{signal['profit_pct']}%")
                
                return data
            else:
                print(f"分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"分析多个币种异常: {e}")
    return None

if __name__ == "__main__":
    test_frontend_api_calls()

