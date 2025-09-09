#!/usr/bin/env python3
"""
最终测试去重效果
"""

import requests
import json
from collections import defaultdict

def test_final_deduplication():
    """最终测试去重效果"""
    print("=== 最终测试去重效果 ===")
    
    # 测试多个币种
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    print(f"测试币种: {test_symbols}")
    
    try:
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                               json={'symbols': test_symbols}, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ 多币种分析成功: {data['total_signals']} 个信号")
                
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
                        round(signal.get('level', 0), 6),
                        signal.get('type', ''),
                        round(signal.get('distance', 0), 8)
                    )
                    signal_groups[signal_id].append(signal)
                
                # 检查重复
                duplicates = {k: v for k, v in signal_groups.items() if len(v) > 1}
                if duplicates:
                    print(f"❌ 发现 {len(duplicates)} 组重复信号:")
                    for signal_id, signal_list in list(duplicates.items())[:3]:  # 只显示前3组
                        print(f"重复组: {signal_id}")
                        print(f"  重复数量: {len(signal_list)}")
                else:
                    print("✅ 无重复信号！去重成功！")
                
                # 按币种统计信号
                symbol_counts = defaultdict(int)
                for signal in signals:
                    symbol_counts[signal.get('symbol', '')] += 1
                
                print(f"\n按币种统计:")
                for symbol, count in symbol_counts.items():
                    print(f"  {symbol}: {count} 个信号")
                
                # 显示前10个信号
                print(f"\n前10个信号:")
                for i, signal in enumerate(signals[:10]):
                    print(f"  {i+1}. {signal.get('symbol')} {signal.get('timeframe')} {signal.get('signal_type')} 收益率:{signal.get('profit_pct')}%")
                    
            else:
                print(f"❌ 分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试异常: {e}")

if __name__ == "__main__":
    test_final_deduplication()

