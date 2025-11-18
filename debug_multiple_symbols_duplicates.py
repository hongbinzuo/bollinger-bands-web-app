#!/usr/bin/env python3
"""
调试多币种分析中的重复信号问题
"""

import requests
import json
from collections import defaultdict

def analyze_multiple_symbols_duplicates():
    """分析多币种分析中的重复信号问题"""
    print("=== 调试多币种分析中的重复信号问题 ===")
    
    # 测试多个币种
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    print(f"分析币种: {test_symbols}")
    
    try:
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                               json={'symbols': test_symbols}, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"分析成功: {data['total_signals']} 个信号")
                
                signals = data.get('signals', [])
                print(f"信号总数: {len(signals)}")
                
                # 分析重复信号
                signal_groups = defaultdict(list)
                for signal in signals:
                    # 创建信号标识
                    signal_id = (
                        signal.get('symbol', ''),
                        signal.get('timeframe', ''),
                        signal.get('signal_type', ''),
                        round(signal.get('entry_price', 0), 6),
                        round(signal.get('take_profit', 0), 6)
                    )
                    signal_groups[signal_id].append(signal)
                
                # 检查重复
                duplicates = {k: v for k, v in signal_groups.items() if len(v) > 1}
                if duplicates:
                    print(f"\n发现 {len(duplicates)} 组重复信号:")
                    for signal_id, signal_list in list(duplicates.items())[:5]:  # 只显示前5组
                        print(f"重复组: {signal_id}")
                        for i, signal in enumerate(signal_list):
                            print(f"  {i+1}. {signal}")
                else:
                    print("\n✅ 无重复信号")
                
                # 按币种统计信号
                symbol_counts = defaultdict(int)
                for signal in signals:
                    symbol_counts[signal.get('symbol', '')] += 1
                
                print(f"\n按币种统计:")
                for symbol, count in symbol_counts.items():
                    print(f"  {symbol}: {count} 个信号")
                
                # 显示前20个信号
                print(f"\n前20个信号:")
                for i, signal in enumerate(signals[:20]):
                    print(f"  {i+1}. {signal.get('symbol')} {signal.get('timeframe')} {signal.get('signal_type')} 收益率:{signal.get('profit_pct')}%")
                    
            else:
                print(f"分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"分析异常: {e}")

if __name__ == "__main__":
    analyze_multiple_symbols_duplicates()

