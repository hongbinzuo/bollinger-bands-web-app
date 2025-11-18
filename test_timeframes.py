#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不同时间框架的信号生成
"""

import requests
import json

def test_timeframes():
    # 测试单个币种的所有时间框架
    response = requests.post('http://localhost:5000/multi_timeframe/analyze_symbol', 
                            json={'symbol': 'BTCUSDT'},
                            headers={'Content-Type': 'application/json'})

    data = response.json()
    print('=== 单币种多时间框架测试 ===')
    print(f'状态码: {response.status_code}')
    print(f'成功: {data.get("success")}')

    if data.get('success'):
        results = data.get('results', [])
        print(f'时间框架数量: {len(results)}')
        
        for result in results:
            timeframe = result.get('timeframe')
            status = result.get('status')
            trend = result.get('trend')
            signal_count = result.get('signal_count', 0)
            current_price = result.get('current_price', 0)
            take_profit_price = result.get('take_profit_price', 0)
            
            print(f'\n📊 {timeframe}:')
            print(f'   状态: {status}')
            print(f'   趋势: {trend}')
            print(f'   信号数量: {signal_count}')
            print(f'   当前价格: {current_price:.2f}')
            print(f'   止盈价格: {take_profit_price:.2f}')
            
            if signal_count > 0 and take_profit_price > 0:
                # 计算收益率（假设做空信号）
                profit_pct = ((current_price - take_profit_price) / current_price) * 100
                print(f'   预期收益率: {profit_pct:.2f}%')

if __name__ == "__main__":
    test_timeframes()
