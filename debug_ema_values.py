#!/usr/bin/env python3
"""
调试EMA值和价格距离，检查为什么没有EMA信号
"""

import requests
import json

def debug_ema_values():
    url = 'http://localhost:5000/multi_timeframe/analyze_multiple_symbols'
    
    # 测试数据
    test_data = {
        'symbols': ['BTCUSDT'],
        'page': 1,
        'page_size': 5
    }
    
    print("调试EMA值和价格距离...")
    
    try:
        response = requests.post(url, json=test_data, timeout=30)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            print(f"结果数量: {len(results)}")
            
            for i, result in enumerate(results):
                symbol = result.get('symbol', 'N/A')
                print(f"\n=== {symbol} ===")
                
                # 检查原始K线数据
                klines_data = result.get('klines_data', {})
                if klines_data:
                    print(f"K线数据时间范围: {klines_data.get('time_range', 'N/A')}")
                    print(f"K线数量: {klines_data.get('total_candles', 'N/A')}")
                    
                    # 检查最新的K线数据
                    latest_candle = klines_data.get('latest_candle', {})
                    if latest_candle:
                        current_price = latest_candle.get('close', 0)
                        print(f"当前价格: {current_price}")
                        
                        # 检查各个EMA值
                        for period in [89, 144, 233, 377]:
                            ema_value = latest_candle.get(f'ema{period}')
                            if ema_value:
                                distance = abs(current_price - ema_value) / ema_value * 100
                                print(f"EMA{period}: {ema_value:.4f}, 距离: {distance:.2f}%")
                            else:
                                print(f"EMA{period}: 未计算")
                
                # 检查趋势判断
                trend_analysis = result.get('trend_analysis', {})
                if trend_analysis:
                    print(f"趋势判断: {trend_analysis.get('trend', 'N/A')}")
                    print(f"趋势强度: {trend_analysis.get('strength', 'N/A')}")
                
                # 检查EMA信号
                ema_signals = result.get('ema_pullback_signals', [])
                print(f"EMA信号数量: {len(ema_signals)}")
                
                for j, signal in enumerate(ema_signals):
                    print(f"  EMA信号{j+1}: {signal.get('type', 'N/A')} - EMA{signal.get('ema_period', 'N/A')}")
                    print(f"    价格距离: {signal.get('price_distance', 'N/A')}")
                    print(f"    条件: {signal.get('condition', 'N/A')}")
                
                # 检查所有信号
                all_signals = result.get('all_signals', [])
                print(f"总信号数量: {len(all_signals)}")
                
                signal_types = {}
                for signal in all_signals:
                    signal_type = signal.get('signal_type', 'unknown')
                    if signal_type not in signal_types:
                        signal_types[signal_type] = 0
                    signal_types[signal_type] += 1
                
                print(f"信号类型统计: {signal_types}")
                
        else:
            print(f"错误: {response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    debug_ema_values()



