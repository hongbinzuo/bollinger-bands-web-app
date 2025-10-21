#!/usr/bin/env python3
import requests
import sys

print("开始测试...")

try:
    print("1. 测试网络连接...")
    url = "https://api.bybit.com/v5/market/tickers"
    params = {'category': 'spot', 'symbol': 'BTCUSDT'}
    
    print("2. 发送请求...")
    response = requests.get(url, params=params, timeout=10)
    print(f"3. 响应状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"4. API响应: {data}")
        
        if data['retCode'] == 0:
            price = data['result']['list'][0]['lastPrice']
            print(f"5. BTC价格: ${price}")
        else:
            print(f"5. API错误: {data['retMsg']}")
    else:
        print(f"4. HTTP错误: {response.status_code}")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("测试完成")
