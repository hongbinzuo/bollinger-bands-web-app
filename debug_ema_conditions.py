#!/usr/bin/env python3
"""
调试EMA信号生成条件
"""

import requests
import json

def debug_ema_conditions():
    url = 'http://localhost:5000/multi_timeframe/analyze_symbol'
    
    # 测试单个币种，查看详细分析结果
    test_data = {
        'symbol': 'BTCUSDT',
        'timeframes': ['1h', '4h', '1d']
    }
    
    print("调试EMA信号生成条件...")
    
    try:
        response = requests.post(url, json=test_data, timeout=30)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            print(f"分析结果数量: {len(results)}")
            
            for i, result in enumerate(results):
                print(f"\n=== 时间框架 {i+1}: {result.get('timeframe', 'N/A')} ===")
                print(f"状态: {result.get('status', 'N/A')}")
                
                if result.get('status') == 'success':
                    signals = result.get('signals', [])
                    print(f"信号数量: {len(signals)}")
                    
                    # 统计信号类型
                    signal_types = {}
                    for signal in signals:
                        signal_type = signal.get('signal', 'unknown')
                        if signal_type not in signal_types:
                            signal_types[signal_type] = 0
                        signal_types[signal_type] += 1
                    
                    print(f"信号类型统计: {signal_types}")
                    
                    # 显示EMA相关信号
                    ema_signals = []
                    for signal in signals:
                        if 'ema' in str(signal).lower() or signal.get('ema_period') is not None:
                            ema_signals.append(signal)
                    
                    print(f"EMA相关信号: {len(ema_signals)}个")
                    
                    # 显示前几个信号的详细信息
                    for j, signal in enumerate(signals[:3]):
                        print(f"\n--- 信号 {j+1} ---")
                        print(f"信号类型: {signal.get('signal', 'N/A')}")
                        print(f"EMA周期: {signal.get('ema_period', 'N/A')}")
                        print(f"信号条件: {signal.get('condition', 'N/A')}")
                        print(f"详细描述: {signal.get('description', 'N/A')}")
                        
                        # 显示原始数据的关键字段
                        print(f"原始数据: {signal}")
                        
                else:
                    print(f"分析失败: {result.get('message', 'N/A')}")
                    
        else:
            print(f"错误: {response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    debug_ema_conditions()



