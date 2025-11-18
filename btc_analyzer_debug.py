#!/usr/bin/env python3
import requests
import pandas as pd
from datetime import datetime
import json

print("=== BTC周二反弹策略分析器 (调试版) ===")

def get_btc_data():
    print("1. 获取BTC数据...")
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'limit': 168
        }
        
        response = requests.get(url, params=params, timeout=10)
        print(f"   HTTP状态: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   HTTP错误: {response.status_code}")
            return None
            
        data = response.json()
        print(f"   API返回码: {data['retCode']}")
        
        if data['retCode'] != 0:
            print(f"   API错误: {data['retMsg']}")
            return None
            
        klines = data['result']['list']
        print(f"   获取到 {len(klines)} 条K线数据")
        
        if not klines:
            print("   无K线数据")
            return None
            
        # 转换为DataFrame
        print("2. 转换数据格式...")
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        # 数据类型转换
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col])
        
        # 时间转换
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['datetime_utc'] = df['datetime'].dt.tz_localize('UTC')
        
        print(f"   数据范围: {df['datetime_utc'].min()} 至 {df['datetime_utc'].max()}")
        print(f"   数据行数: {len(df)}")
        
        return df
        
    except Exception as e:
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_tuesday(df):
    print("3. 分析周二数据...")
    
    if df is None or df.empty:
        print("   无数据可分析")
        return None
        
    # 筛选周二数据
    tuesday_data = df[df['datetime_utc'].dt.weekday == 1].copy()
    print(f"   找到 {len(tuesday_data)} 条周二数据")
    
    if tuesday_data.empty:
        print("   无周二数据")
        return None
        
    # 按日期分组
    tuesday_dates = tuesday_data['datetime_utc'].dt.date.unique()
    print(f"   周二日期: {list(tuesday_dates)}")
    
    # 时段分析
    sessions = {
        'asia': (0, 8),      # 亚盘
        'europe': (8, 16),   # 欧盘  
        'us': (16, 24)       # 美盘
    }
    
    results = {}
    
    for session_name, (start_hour, end_hour) in sessions.items():
        print(f"   分析 {session_name} 时段...")
        
        # 筛选该时段数据
        session_data = tuesday_data[
            (tuesday_data['datetime_utc'].dt.hour >= start_hour) & 
            (tuesday_data['datetime_utc'].dt.hour < end_hour)
        ]
        
        print(f"     {session_name} 时段数据: {len(session_data)} 条")
        
        if not session_data.empty:
            # 按日期分组分析
            daily_analysis = []
            for date, day_data in session_data.groupby(session_data['datetime_utc'].dt.date):
                open_price = day_data.iloc[0]['open']
                close_price = day_data.iloc[-1]['close']
                high_price = day_data['high'].max()
                low_price = day_data['low'].min()
                
                max_recovery = ((high_price - open_price) / open_price) * 100
                target_achieved = 1.0 <= max_recovery <= 1.5
                
                daily_analysis.append({
                    'date': str(date),
                    'max_recovery_pct': max_recovery,
                    'target_achieved': target_achieved
                })
                
                print(f"     {date}: 反弹 {max_recovery:.2f}%, 目标达成: {target_achieved}")
            
            # 统计
            total_sessions = len(daily_analysis)
            target_achieved = sum(1 for d in daily_analysis if d['target_achieved'])
            success_rate = (target_achieved / total_sessions) * 100 if total_sessions > 0 else 0
            avg_recovery = sum(d['max_recovery_pct'] for d in daily_analysis) / total_sessions if total_sessions > 0 else 0
            
            results[session_name] = {
                'total_sessions': total_sessions,
                'target_achieved': target_achieved,
                'success_rate': success_rate,
                'avg_recovery': avg_recovery
            }
            
            print(f"     {session_name} 统计: 成功率 {success_rate:.1f}%, 平均反弹 {avg_recovery:.2f}%")
    
    return results

def main():
    # 获取数据
    df = get_btc_data()
    
    if df is None:
        print("无法获取数据，程序退出")
        return
    
    # 分析周二
    results = analyze_tuesday(df)
    
    if results is None:
        print("无法分析周二数据")
        return
    
    # 输出结果
    print("\n=== 分析结果 ===")
    for session_name, stats in results.items():
        print(f"{session_name.upper()}时段:")
        print(f"  总时段数: {stats['total_sessions']}")
        print(f"  目标达成: {stats['target_achieved']}")
        print(f"  成功率: {stats['success_rate']:.1f}%")
        print(f"  平均反弹: {stats['avg_recovery']:.2f}%")
        print()
    
    # 找出最佳时段
    if results:
        best_session = max(results.items(), key=lambda x: x[1]['success_rate'])
        print(f"最佳时段: {best_session[0].upper()}")
        print(f"成功率: {best_session[1]['success_rate']:.1f}%")
        
        # 当前时间判断
        now_utc = datetime.utcnow()
        current_hour = now_utc.hour
        
        if 0 <= current_hour < 8:
            current_session = "asia"
        elif 8 <= current_hour < 16:
            current_session = "europe"
        elif 16 <= current_hour < 24:
            current_session = "us"
        else:
            current_session = "unknown"
        
        print(f"\n当前时间: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"当前时段: {current_session.upper()}")
        
        if current_session == best_session[0]:
            print("✅ 当前正处于最佳时段！")
        else:
            print(f"⏰ 建议等待 {best_session[0].upper()} 时段")

if __name__ == "__main__":
    main()
