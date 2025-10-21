#!/usr/bin/env python3
print("=== BTC周一策略快速验证 ===")

import requests
from datetime import datetime, timedelta

def get_btc_data_quick():
    """快速获取BTC数据"""
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'linear',
            'symbol': 'BTCUSDT',
            'interval': '240',  # 4小时K线
            'limit': 1000
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['retCode'] == 0:
            return data['result']['list']
        return None
    except:
        return None

def analyze_monday_quick():
    print("获取数据...")
    klines = get_btc_data_quick()
    
    if not klines:
        print("获取数据失败")
        return
    
    print(f"获取到 {len(klines)} 条数据")
    
    # 转换数据
    data_points = []
    for kline in klines:
        timestamp = int(kline[0])
        dt = datetime.fromtimestamp(timestamp / 1000)
        data_points.append({
            'date': dt.date(),
            'datetime': dt,
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4])
        })
    
    # 按日期分组
    daily_data = {}
    for d in data_points:
        if d['date'] not in daily_data:
            daily_data[d['date']] = []
        daily_data[d['date']].append(d)
    
    # 找到所有周一
    mondays = [date for date in daily_data.keys() if date.weekday() == 0]
    mondays.sort()
    
    print(f"找到 {len(mondays)} 个周一")
    
    if len(mondays) < 5:
        print("周一数据不足")
        return
    
    # 分析策略
    reversal_signals = 0  # 周一上涨后反转
    bottom_signals = 0    # 周一下跌后反弹
    reversal_accurate = 0
    bottom_accurate = 0
    
    print("\n分析结果:")
    print("-" * 50)
    
    for monday in mondays[-10:]:  # 只分析最近10个周一
        monday_data = daily_data[monday]
        monday_open = monday_data[0]['open']
        monday_close = monday_data[-1]['close']
        monday_change = ((monday_close - monday_open) / monday_open) * 100
        
        # 找后续表现（周二到周五）
        next_days = []
        for i in range(1, 5):
            next_date = monday + timedelta(days=i)
            if next_date in daily_data:
                next_days.append(next_date)
        
        if not next_days:
            continue
            
        # 计算后续最高最低点
        max_price = monday_close
        min_price = monday_close
        
        for date in next_days:
            day_data = daily_data[date]
            day_high = max(d['high'] for d in day_data)
            day_low = min(d['low'] for d in day_data)
            max_price = max(max_price, day_high)
            min_price = min(min_price, day_low)
        
        # 最终价格
        final_date = next_days[-1]
        final_close = daily_data[final_date][-1]['close']
        final_change = ((final_close - monday_close) / monday_close) * 100
        
        # 判断信号
        if monday_change > 1:  # 周一上涨
            reversal_signals += 1
            if final_change < -1:  # 后续下跌
                reversal_accurate += 1
                signal = "✅"
            else:
                signal = "❌"
            print(f"{monday}: 周一+{monday_change:.1f}% -> 后续{final_change:.1f}% {signal}")
            
        elif monday_change < -1:  # 周一下跌
            bottom_signals += 1
            if final_change > 1:  # 后续上涨
                bottom_accurate += 1
                signal = "✅"
            else:
                signal = "❌"
            print(f"{monday}: 周一{monday_change:.1f}% -> 后续+{final_change:.1f}% {signal}")
    
    # 结果统计
    print("\n" + "="*50)
    print("策略验证结果:")
    print("="*50)
    
    reversal_rate = (reversal_accurate / reversal_signals) * 100 if reversal_signals > 0 else 0
    bottom_rate = (bottom_accurate / bottom_signals) * 100 if bottom_signals > 0 else 0
    
    print(f"反转信号: {reversal_accurate}/{reversal_signals} ({reversal_rate:.1f}%)")
    print(f"底部信号: {bottom_accurate}/{bottom_signals} ({bottom_rate:.1f}%)")
    
    total_signals = reversal_signals + bottom_signals
    total_accurate = reversal_accurate + bottom_accurate
    overall_rate = (total_accurate / total_signals) * 100 if total_signals > 0 else 0
    
    print(f"总体准确率: {total_accurate}/{total_signals} ({overall_rate:.1f}%)")
    
    print(f"\n原始策略声称: 64%反转, 36%底部")
    print(f"实际验证结果: {reversal_rate:.1f}%反转, {bottom_rate:.1f}%底部")
    
    if overall_rate > 60:
        print("✅ 策略表现良好")
    elif overall_rate > 40:
        print("⚠️ 策略表现一般")
    else:
        print("❌ 策略表现不佳")

if __name__ == "__main__":
    analyze_monday_quick()
