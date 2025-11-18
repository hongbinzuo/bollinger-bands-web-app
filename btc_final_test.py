#!/usr/bin/env python3
print("=== BTC周二反弹策略分析器 ===")

import requests
from datetime import datetime, timedelta
import json

def get_btc_data():
    print("正在获取BTC数据...")
    
    # 尝试多种API参数组合
    api_configs = [
        {'category': 'linear', 'symbol': 'BTCUSDT', 'interval': '1', 'limit': 168},
        {'category': 'spot', 'symbol': 'BTCUSDT', 'interval': '1', 'limit': 168},
        {'category': 'linear', 'symbol': 'BTCUSDT', 'interval': 1, 'limit': 168},
        {'category': 'spot', 'symbol': 'BTCUSDT', 'interval': 1, 'limit': 168}
    ]
    
    for i, config in enumerate(api_configs):
        try:
            print(f"尝试配置 {i+1}: {config}")
            response = requests.get('https://api.bybit.com/v5/market/kline', params=config, timeout=10)
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  返回码: {data.get('retCode')}")
                print(f"  消息: {data.get('retMsg')}")
                
                if data.get('retCode') == 0:
                    klines = data.get('result', {}).get('list', [])
                    print(f"  获取到 {len(klines)} 条K线数据")
                    return klines
                else:
                    print(f"  API错误: {data.get('retMsg')}")
            else:
                print(f"  HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"  请求失败: {e}")
    
    print("所有API配置都失败了")
    return None

def analyze_tuesday_sessions(klines):
    print("\n分析周二时段...")
    
    if not klines:
        print("无数据可分析")
        return
    
    # 转换数据
    data_points = []
    for kline in klines:
        timestamp = int(kline[0])
        dt = datetime.fromtimestamp(timestamp / 1000)
        data_points.append({
            'datetime': dt,
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4])
        })
    
    print(f"处理了 {len(data_points)} 个数据点")
    
    # 筛选周二数据
    tuesday_data = [d for d in data_points if d['datetime'].weekday() == 1]
    print(f"找到 {len(tuesday_data)} 条周二数据")
    
    if not tuesday_data:
        print("无周二数据")
        return
    
    # 按日期分组
    tuesday_by_date = {}
    for d in tuesday_data:
        date_key = d['datetime'].date()
        if date_key not in tuesday_by_date:
            tuesday_by_date[date_key] = []
        tuesday_by_date[date_key].append(d)
    
    print(f"周二日期: {list(tuesday_by_date.keys())}")
    
    # 分析各时段
    sessions = {
        'asia': (0, 8),      # 亚盘
        'europe': (8, 16),    # 欧盘
        'us': (16, 24)       # 美盘
    }
    
    results = {}
    
    for session_name, (start_hour, end_hour) in sessions.items():
        print(f"\n分析 {session_name.upper()} 时段...")
        
        session_analyses = []
        
        for date, day_data in tuesday_by_date.items():
            # 筛选该时段的数据
            session_data = [d for d in day_data if start_hour <= d['datetime'].hour < end_hour]
            
            if session_data:
                # 按时间排序
                session_data.sort(key=lambda x: x['datetime'])
                
                open_price = session_data[0]['open']
                close_price = session_data[-1]['close']
                high_price = max(d['high'] for d in session_data)
                low_price = min(d['low'] for d in session_data)
                
                max_recovery = ((high_price - open_price) / open_price) * 100
                target_achieved = 1.0 <= max_recovery <= 1.5
                
                session_analyses.append({
                    'date': str(date),
                    'max_recovery_pct': max_recovery,
                    'target_achieved': target_achieved
                })
                
                print(f"  {date}: 反弹 {max_recovery:.2f}%, 目标达成: {target_achieved}")
        
        if session_analyses:
            total_sessions = len(session_analyses)
            target_achieved = sum(1 for s in session_analyses if s['target_achieved'])
            success_rate = (target_achieved / total_sessions) * 100
            avg_recovery = sum(s['max_recovery_pct'] for s in session_analyses) / total_sessions
            
            results[session_name] = {
                'total_sessions': total_sessions,
                'target_achieved': target_achieved,
                'success_rate': success_rate,
                'avg_recovery': avg_recovery
            }
            
            print(f"  {session_name.upper()} 统计: 成功率 {success_rate:.1f}%, 平均反弹 {avg_recovery:.2f}%")
    
    return results

def main():
    # 获取数据
    klines = get_btc_data()
    
    if not klines:
        print("无法获取数据")
        return
    
    # 分析周二
    results = analyze_tuesday_sessions(klines)
    
    if not results:
        print("无法分析数据")
        return
    
    # 输出结果
    print("\n" + "="*50)
    print("分析结果")
    print("="*50)
    
    for session_name, stats in results.items():
        print(f"\n{session_name.upper()}时段:")
        print(f"  总时段数: {stats['total_sessions']}")
        print(f"  目标达成: {stats['target_achieved']}")
        print(f"  成功率: {stats['success_rate']:.1f}%")
        print(f"  平均反弹: {stats['avg_recovery']:.2f}%")
    
    # 找出最佳时段
    if results:
        best_session = max(results.items(), key=lambda x: x[1]['success_rate'])
        print(f"\n最佳时段: {best_session[0].upper()}")
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
