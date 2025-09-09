#!/usr/bin/env python3
"""
测试单个币种API调用
"""

import requests
import json

def test_single_symbols():
    """测试单个币种分析"""
    symbols = ['ETHUSDT', 'BTCUSDT', 'SOLUSDT']
    
    for symbol in symbols:
        print(f"\n=== 测试币种: {symbol} ===")
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
                else:
                    print(f"分析失败: {data.get('error', '未知错误')}")
            else:
                print(f"HTTP错误: {response.status_code}")
        except Exception as e:
            print(f"分析币种失败: {e}")

if __name__ == "__main__":
    test_single_symbols()

