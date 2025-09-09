#!/usr/bin/env python3
"""
简单测试去重逻辑
"""

import requests
import json

def test_simple_deduplication():
    """简单测试去重逻辑"""
    print("=== 简单测试去重逻辑 ===")
    
    # 测试单个币种
    symbol = 'BTCUSDT'
    print(f"测试币种: {symbol}")
    
    try:
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_symbol', 
                               json={'symbol': symbol}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"单个币种分析成功: {data['successful_timeframes']}/{data['total_timeframes_analyzed']} 个时间框架")
                
                # 统计信号
                total_signals = 0
                for result in data['results']:
                    if result['status'] == 'success':
                        signal_count = len(result.get('all_signals', []))
                        total_signals += signal_count
                        print(f"  {result['timeframe']}: {signal_count} 个信号")
                
                print(f"单个币种总信号数: {total_signals}")
                
                # 现在测试多币种分析
                print(f"\n测试多币种分析...")
                response2 = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                                        json={'symbols': [symbol]}, timeout=30)
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    if data2['success']:
                        print(f"多币种分析成功: {data2['total_signals']} 个信号")
                        
                        # 检查是否有重复
                        signals = data2.get('signals', [])
                        print(f"多币种信号总数: {len(signals)}")
                        
                        # 简单检查：如果多币种分析的信号数等于单个币种分析的信号数，说明没有重复
                        if len(signals) == total_signals:
                            print("✅ 去重成功：多币种分析信号数等于单个币种分析信号数")
                        else:
                            print(f"❌ 去重失败：多币种分析信号数({len(signals)}) != 单个币种分析信号数({total_signals})")
                            
                            # 显示重复的信号
                            print("重复信号示例:")
                            for i, signal in enumerate(signals[:5]):
                                print(f"  {i+1}. {signal.get('symbol')} {signal.get('timeframe')} {signal.get('signal_type')} 收益率:{signal.get('profit_pct')}%")
                    else:
                        print(f"多币种分析失败: {data2.get('error', '未知错误')}")
                else:
                    print(f"多币种分析HTTP错误: {response2.status_code}")
            else:
                print(f"单个币种分析失败: {data.get('error', '未知错误')}")
        else:
            print(f"单个币种分析HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"测试异常: {e}")

if __name__ == "__main__":
    test_simple_deduplication()

