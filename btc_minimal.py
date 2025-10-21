#!/usr/bin/env python3
print("开始BTC分析...")

import requests
print("导入requests成功")

try:
    print("发送API请求...")
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        'category': 'spot',
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'limit': 24  # 只获取24小时数据
    }
    
    response = requests.get(url, params=params, timeout=10)
    print(f"API响应状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"API返回码: {data['retCode']}")
        
        if data['retCode'] == 0:
            klines = data['result']['list']
            print(f"获取到 {len(klines)} 条K线数据")
            
            # 简单分析
            if klines:
                latest = klines[0]  # 最新的数据
                print(f"最新价格: {latest[4]}")  # close price
                print(f"时间戳: {latest[0]}")
                
                # 检查是否是周二
                from datetime import datetime
                timestamp = int(latest[0])
                dt = datetime.fromtimestamp(timestamp / 1000)
                weekday = dt.weekday()  # 0=Monday, 1=Tuesday
                print(f"日期: {dt}")
                print(f"星期: {weekday} (1=Tuesday)")
                
                if weekday == 1:
                    print("✅ 今天是周二！")
                else:
                    print("❌ 今天不是周二")
        else:
            print(f"API错误: {data['retMsg']}")
    else:
        print(f"HTTP错误: {response.status_code}")
        
except Exception as e:
    print(f"发生错误: {e}")
    import traceback
    traceback.print_exc()

print("分析完成")
