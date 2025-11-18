#!/usr/bin/env python3
print("=== BTC周二低点到周三高点反弹策略分析器 ===")

import requests
from datetime import datetime, timedelta
import json

def get_btc_yearly_data():
    print("正在获取BTC一年数据...")
    
    # 获取一年的数据，使用1小时K线
    api_config = {
        'category': 'linear', 
        'symbol': 'BTCUSDT', 
        'interval': '60',  # 1小时K线
        'limit': 8760  # 一年约8760小时
    }
    
    try:
        print(f"请求参数: {api_config}")
        response = requests.get('https://api.bybit.com/v5/market/kline', params=api_config, timeout=30)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"返回码: {data.get('retCode')}")
            print(f"消息: {data.get('retMsg')}")
            
            if data.get('retCode') == 0:
                klines = data.get('result', {}).get('list', [])
                print(f"获取到 {len(klines)} 条K线数据")
                return klines
            else:
                print(f"API错误: {data.get('retMsg')}")
                return None
        else:
            print(f"HTTP错误: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"请求失败: {e}")
        return None

def analyze_tuesday_to_wednesday_recovery(klines):
    print("\n分析周二低点到周三高点反弹...")
    
    if not klines:
        print("无数据可分析")
        return None
    
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
    print(f"数据时间范围: {data_points[0]['datetime']} 至 {data_points[-1]['datetime']}")
    
    # 按日期分组
    daily_data = {}
    for d in data_points:
        date_key = d['datetime'].date()
        if date_key not in daily_data:
            daily_data[date_key] = []
        daily_data[date_key].append(d)
    
    print(f"总交易日数: {len(daily_data)}")
    
    # 找到所有周二和周三
    tuesday_wednesday_pairs = []
    
    for date in sorted(daily_data.keys()):
        if date.weekday() == 1:  # 周二
            next_day = date + timedelta(days=1)
            if next_day in daily_data:  # 确保周三也有数据
                tuesday_wednesday_pairs.append((date, next_day))
    
    print(f"找到 {len(tuesday_wednesday_pairs)} 个周二-周三交易日对")
    
    if not tuesday_wednesday_pairs:
        print("无周二-周三交易日对")
        return None
    
    # 分析每个周二-周三对
    analyses = []
    
    for tuesday_date, wednesday_date in tuesday_wednesday_pairs:
        print(f"\n分析 {tuesday_date} 到 {wednesday_date}:")
        
        # 周二数据
        tuesday_data = daily_data[tuesday_date]
        tuesday_data.sort(key=lambda x: x['datetime'])
        
        # 周三数据
        wednesday_data = daily_data[wednesday_date]
        wednesday_data.sort(key=lambda x: x['datetime'])
        
        # 找到周二最低点
        tuesday_low = min(d['low'] for d in tuesday_data)
        tuesday_low_time = min(d['datetime'] for d in tuesday_data if d['low'] == tuesday_low)
        
        # 找到周三最高点
        wednesday_high = max(d['high'] for d in wednesday_data)
        wednesday_high_time = max(d['datetime'] for d in wednesday_data if d['high'] == wednesday_high)
        
        # 计算反弹幅度
        recovery_pct = ((wednesday_high - tuesday_low) / tuesday_low) * 100
        
        # 判断是否在1-1.5%范围内
        target_achieved = 1.0 <= recovery_pct <= 1.5
        
        # 计算各时段的表现
        sessions_analysis = analyze_sessions_in_period(tuesday_data, wednesday_data, tuesday_low)
        
        analysis = {
            'tuesday_date': str(tuesday_date),
            'wednesday_date': str(wednesday_date),
            'tuesday_low': tuesday_low,
            'tuesday_low_time': tuesday_low_time.isoformat(),
            'wednesday_high': wednesday_high,
            'wednesday_high_time': wednesday_high_time.isoformat(),
            'recovery_pct': recovery_pct,
            'target_achieved': target_achieved,
            'sessions_analysis': sessions_analysis
        }
        
        analyses.append(analysis)
        
        status = "✅" if target_achieved else "❌"
        print(f"  周二低点: ${tuesday_low:.2f} ({tuesday_low_time.strftime('%H:%M')})")
        print(f"  周三高点: ${wednesday_high:.2f} ({wednesday_high_time.strftime('%H:%M')})")
        print(f"  反弹幅度: {recovery_pct:.2f}% {status}")
        
        # 显示各时段表现
        for session_name, session_stats in sessions_analysis.items():
            if session_stats['has_data']:
                print(f"    {session_name.upper()}: 反弹 {session_stats['recovery_pct']:.2f}%")
    
    return analyses

def analyze_sessions_in_period(tuesday_data, wednesday_data, tuesday_low):
    """分析各时段在周二低点到周三高点期间的表现"""
    
    sessions = {
        'asia': (0, 8),      # 亚盘: 00:00-08:00 UTC
        'europe': (8, 16),   # 欧盘: 08:00-16:00 UTC
        'us': (16, 24)       # 美盘: 16:00-24:00 UTC
    }
    
    sessions_analysis = {}
    
    for session_name, (start_hour, end_hour) in sessions.items():
        # 收集该时段的所有数据（周二+周三）
        session_data = []
        
        for day_data in [tuesday_data, wednesday_data]:
            for d in day_data:
                if start_hour <= d['datetime'].hour < end_hour:
                    session_data.append(d)
        
        if session_data:
            session_data.sort(key=lambda x: x['datetime'])
            
            # 找到该时段内的最高点
            session_high = max(d['high'] for d in session_data)
            
            # 计算从周二低点到该时段最高点的反弹
            recovery_pct = ((session_high - tuesday_low) / tuesday_low) * 100
            
            sessions_analysis[session_name] = {
                'has_data': True,
                'recovery_pct': recovery_pct,
                'session_high': session_high,
                'data_points': len(session_data)
            }
        else:
            sessions_analysis[session_name] = {
                'has_data': False,
                'recovery_pct': 0,
                'session_high': 0,
                'data_points': 0
            }
    
    return sessions_analysis

def generate_detailed_report(analyses):
    """生成详细报告"""
    if not analyses:
        return "无分析结果"
    
    report = []
    report.append("=" * 70)
    report.append("BTC周二低点到周三高点反弹策略分析报告")
    report.append("=" * 70)
    
    # 总体统计
    total_pairs = len(analyses)
    target_achieved = sum(1 for a in analyses if a['target_achieved'])
    overall_success_rate = (target_achieved / total_pairs) * 100 if total_pairs > 0 else 0
    
    report.append(f"\n总体统计:")
    report.append(f"  总周二-周三交易日对: {total_pairs}")
    report.append(f"  目标达成次数: {target_achieved}")
    report.append(f"  整体成功率: {overall_success_rate:.1f}%")
    
    # 各时段统计
    sessions_stats = {
        'asia': {'total': 0, 'achieved': 0, 'recoveries': []},
        'europe': {'total': 0, 'achieved': 0, 'recoveries': []},
        'us': {'total': 0, 'achieved': 0, 'recoveries': []}
    }
    
    for analysis in analyses:
        for session_name, session_analysis in analysis['sessions_analysis'].items():
            if session_analysis['has_data']:
                sessions_stats[session_name]['total'] += 1
                sessions_stats[session_name]['recoveries'].append(session_analysis['recovery_pct'])
                
                if 1.0 <= session_analysis['recovery_pct'] <= 1.5:
                    sessions_stats[session_name]['achieved'] += 1
    
    report.append(f"\n各时段统计:")
    for session_name, stats in sessions_stats.items():
        if stats['total'] > 0:
            success_rate = (stats['achieved'] / stats['total']) * 100
            avg_recovery = sum(stats['recoveries']) / len(stats['recoveries'])
            max_recovery = max(stats['recoveries'])
            
            report.append(f"\n{session_name.upper()}时段:")
            report.append(f"  有效数据: {stats['total']} 次")
            report.append(f"  目标达成: {stats['achieved']} 次 ({success_rate:.1f}%)")
            report.append(f"  平均反弹: {avg_recovery:.2f}%")
            report.append(f"  最大反弹: {max_recovery:.2f}%")
    
    # 目标达成案例
    target_cases = [a for a in analyses if a['target_achieved']]
    if target_cases:
        report.append(f"\n目标达成案例:")
        for case in target_cases:
            report.append(f"  {case['tuesday_date']} 到 {case['wednesday_date']}: 反弹 {case['recovery_pct']:.2f}%")
    
    # 策略建议
    report.append(f"\n策略建议:")
    if overall_success_rate > 60:
        report.append(f"✅ 策略表现优异，成功率 {overall_success_rate:.1f}%")
    elif overall_success_rate > 40:
        report.append(f"⚠️ 策略表现一般，成功率 {overall_success_rate:.1f}%")
    else:
        report.append(f"❌ 策略表现不佳，成功率 {overall_success_rate:.1f}%，需要重新评估")
    
    return "\n".join(report)

def main():
    # 获取数据
    klines = get_btc_yearly_data()
    
    if not klines:
        print("无法获取数据")
        return
    
    # 分析周二到周三反弹
    analyses = analyze_tuesday_to_wednesday_recovery(klines)
    
    if not analyses:
        print("无法分析数据")
        return
    
    # 生成详细报告
    report = generate_detailed_report(analyses)
    print("\n" + report)
    
    # 保存报告到文件
    with open('btc_tuesday_to_wednesday_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存详细数据到JSON
    with open('btc_tuesday_to_wednesday_data.json', 'w', encoding='utf-8') as f:
        json.dump(analyses, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n报告已保存到:")
    print(f"  - btc_tuesday_to_wednesday_report.txt")
    print(f"  - btc_tuesday_to_wednesday_data.json")

if __name__ == "__main__":
    main()
