#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC周二反弹策略快速测试
简化版本，用于快速验证策略
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json

def get_btc_data_quick():
    """快速获取BTC数据"""
    try:
        # 使用Bybit API获取最近7天的1小时数据
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'limit': 168  # 7天 * 24小时
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['retCode'] != 0:
            print(f"API错误: {data['retMsg']}")
            return None
            
        klines = data['result']['list']
        if not klines:
            print("无数据")
            return None
            
        # 转换为DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        
        # 数据类型转换
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col])
        
        # 时间转换
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['datetime_utc'] = df['datetime'].dt.tz_localize('UTC')
        
        return df.sort_values('datetime_utc').reset_index(drop=True)
        
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

def analyze_tuesday_sessions(df):
    """分析周二时段"""
    # 筛选周二数据
    tuesday_data = df[df['datetime_utc'].dt.weekday == 1].copy()
    
    if tuesday_data.empty:
        print("未找到周二数据")
        return None
    
    # 时段定义
    sessions = {
        'asia': (0, 8),      # 亚盘: 00:00-08:00 UTC
        'europe': (8, 16),   # 欧盘: 08:00-16:00 UTC  
        'us': (16, 24)       # 美盘: 16:00-24:00 UTC
    }
    
    results = {}
    
    for session_name, (start_hour, end_hour) in sessions.items():
        # 筛选该时段数据
        session_data = tuesday_data[
            (tuesday_data['datetime_utc'].dt.hour >= start_hour) & 
            (tuesday_data['datetime_utc'].dt.hour < end_hour)
        ]
        
        if not session_data.empty:
            open_price = session_data.iloc[0]['open']
            close_price = session_data.iloc[-1]['close']
            high_price = session_data['high'].max()
            low_price = session_data['low'].min()
            
            # 计算反弹幅度
            max_recovery = ((high_price - open_price) / open_price) * 100
            
            # 判断是否在1-1.5%范围内
            target_achieved = 1.0 <= max_recovery <= 1.5
            
            results[session_name] = {
                'sessions_analyzed': len(session_data.groupby(session_data['datetime_utc'].dt.date)),
                'max_recovery_pct': max_recovery,
                'target_achieved': target_achieved,
                'avg_recovery': session_data.groupby(session_data['datetime_utc'].dt.date).apply(
                    lambda x: ((x['high'].max() - x.iloc[0]['open']) / x.iloc[0]['open']) * 100
                ).mean()
            }
    
    return results

def main():
    print("BTC周二反弹策略快速分析")
    print("=" * 40)
    
    # 获取数据
    print("正在获取BTC数据...")
    try:
        df = get_btc_data_quick()
        print(f"数据获取完成，DataFrame类型: {type(df)}")
    except Exception as e:
        print(f"获取数据时出错: {e}")
        return
    
    if df is None:
        print("无法获取数据")
        return
    
    print(f"获取到 {len(df)} 小时数据")
    print(f"数据范围: {df['datetime_utc'].min()} 至 {df['datetime_utc'].max()}")
    
    # 分析周二
    print("\n分析周二时段...")
    results = analyze_tuesday_sessions(df)
    
    if not results:
        print("无周二数据")
        return
    
    print("\n各时段分析结果:")
    print("-" * 40)
    
    for session_name, stats in results.items():
        print(f"\n{session_name.upper()}时段:")
        print(f"  分析时段数: {stats['sessions_analyzed']}")
        print(f"  平均反弹: {stats['avg_recovery']:.2f}%")
        print(f"  目标达成: {'是' if stats['target_achieved'] else '否'}")
    
    # 找出最佳时段
    best_session = max(results.items(), key=lambda x: x[1]['avg_recovery'])
    print(f"\n最佳时段: {best_session[0].upper()}")
    print(f"平均反弹: {best_session[1]['avg_recovery']:.2f}%")
    
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
