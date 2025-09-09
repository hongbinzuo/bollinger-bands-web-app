#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API信号返回
"""

import requests
import json

def test_api_signals():
    try:
        # 测试API
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_symbol', 
                                json={'symbol': 'BTCUSDT'},
                                headers={'Content-Type': 'application/json'})

        data = response.json()
        print('API响应状态:', response.status_code)
        print('成功:', data.get('success'))
        print('成功时间框架:', data.get('successful_timeframes'))

        if data.get('results'):
            for result in data['results'][:2]:  # 只看前2个时间框架
                if result['status'] == 'success':
                    print(f"时间框架 {result['timeframe']}: {result['signal_count']}个信号")
                    if result['all_signals']:
                        signal = result['all_signals'][0]
                        print(f'  第一个信号: {signal}')
                        print(f'  信号类型: {signal.get("type")}')
                        print(f'  信号方向: {signal.get("signal")}')
                        print(f'  入场价格: {signal.get("entry_price")}')
                        print(f'  EMA周期: {signal.get("ema_period")}')
        
        # 测试批量分析
        print('\n=== 测试批量分析 ===')
        response2 = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                                 json={'symbols': ['BTCUSDT', 'ETHUSDT']},
                                 headers={'Content-Type': 'application/json'})
        
        data2 = response2.json()
        print('批量分析成功:', data2.get('success'))
        print('总信号数:', data2.get('total_signals'))
        print('成功信号数:', data2.get('successful_signals'))
        
        if data2.get('signals'):
            print(f'前3个信号:')
            for i, signal in enumerate(data2['signals'][:3]):
                print(f'  {i+1}. {signal["symbol"]} {signal["timeframe"]} {signal["signal_type"]} {signal["entry_price"]}')
        
    except Exception as e:
        print(f'测试失败: {e}')

if __name__ == "__main__":
    test_api_signals()
