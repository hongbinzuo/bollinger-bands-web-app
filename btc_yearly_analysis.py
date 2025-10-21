#!/usr/bin/env python3
print("=== BTC周二反弹策略年度分析器 ===")

import requests
from datetime import datetime, timedelta
import json

def get_btc_yearly_data():
    print("正在获取BTC一年数据...")
    
    # 获取一年的数据，使用4小时K线减少数据量
    api_config = {
        'category': 'linear', 
        'symbol': 'BTCUSDT', 
        'interval': '240',  # 4小时K线
        'limit': 2190  # 一年约2190个4小时K线
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

def analyze_tuesday_sessions_yearly(klines):
    print("\n分析周二时段...")
    
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
    
    # 筛选周二数据
    tuesday_data = [d for d in data_points if d['datetime'].weekday() == 1]
    print(f"找到 {len(tuesday_data)} 条周二数据")
    
    if not tuesday_data:
        print("无周二数据")
        return None
    
    # 按日期分组
    tuesday_by_date = {}
    for d in tuesday_data:
        date_key = d['datetime'].date()
        if date_key not in tuesday_by_date:
            tuesday_by_date[date_key] = []
        tuesday_by_date[date_key].append(d)
    
    print(f"周二日期数量: {len(tuesday_by_date)}")
    print(f"周二日期: {sorted(list(tuesday_by_date.keys()))}")
    
    # 分析各时段
    sessions = {
        'asia': (0, 8),      # 亚盘: 00:00-08:00 UTC
        'europe': (8, 16),    # 欧盘: 08:00-16:00 UTC
        'us': (16, 24)       # 美盘: 16:00-24:00 UTC
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
                
                # 计算反弹幅度
                max_recovery = ((high_price - open_price) / open_price) * 100
                max_drawdown = ((low_price - open_price) / open_price) * 100
                net_change = ((close_price - open_price) / open_price) * 100
                
                # 判断是否在1-1.5%范围内
                target_achieved = 1.0 <= max_recovery <= 1.5
                
                session_analyses.append({
                    'date': str(date),
                    'max_recovery_pct': max_recovery,
                    'max_drawdown_pct': max_drawdown,
                    'net_change_pct': net_change,
                    'target_achieved': target_achieved,
                    'open_price': open_price,
                    'high_price': high_price,
                    'low_price': low_price,
                    'close_price': close_price
                })
                
                status = "✅" if target_achieved else "❌"
                print(f"  {date}: 反弹 {max_recovery:.2f}%, 回撤 {max_drawdown:.2f}%, 净变化 {net_change:.2f}% {status}")
        
        if session_analyses:
            total_sessions = len(session_analyses)
            target_achieved = sum(1 for s in session_analyses if s['target_achieved'])
            success_rate = (target_achieved / total_sessions) * 100
            avg_recovery = sum(s['max_recovery_pct'] for s in session_analyses) / total_sessions
            avg_drawdown = sum(s['max_drawdown_pct'] for s in session_analyses) / total_sessions
            avg_net_change = sum(s['net_change_pct'] for s in session_analyses) / total_sessions
            
            # 计算最大和最小反弹
            max_recovery = max(s['max_recovery_pct'] for s in session_analyses)
            min_recovery = min(s['max_recovery_pct'] for s in session_analyses)
            
            results[session_name] = {
                'total_sessions': total_sessions,
                'target_achieved': target_achieved,
                'success_rate': success_rate,
                'avg_recovery': avg_recovery,
                'avg_drawdown': avg_drawdown,
                'avg_net_change': avg_net_change,
                'max_recovery': max_recovery,
                'min_recovery': min_recovery,
                'analyses': session_analyses
            }
            
            print(f"  {session_name.upper()} 统计:")
            print(f"    总时段数: {total_sessions}")
            print(f"    目标达成: {target_achieved} ({success_rate:.1f}%)")
            print(f"    平均反弹: {avg_recovery:.2f}%")
            print(f"    平均回撤: {avg_drawdown:.2f}%")
            print(f"    平均净变化: {avg_net_change:.2f}%")
            print(f"    最大反弹: {max_recovery:.2f}%")
            print(f"    最小反弹: {min_recovery:.2f}%")
    
    return results

def generate_detailed_report(results):
    """生成详细报告"""
    if not results:
        return "无分析结果"
    
    report = []
    report.append("=" * 60)
    report.append("BTC周二反弹策略年度分析报告")
    report.append("=" * 60)
    
    # 总体统计
    total_sessions = sum(stats['total_sessions'] for stats in results.values())
    total_achieved = sum(stats['target_achieved'] for stats in results.values())
    overall_success_rate = (total_achieved / total_sessions) * 100 if total_sessions > 0 else 0
    
    report.append(f"\n总体统计:")
    report.append(f"  总周二时段数: {total_sessions}")
    report.append(f"  目标达成次数: {total_achieved}")
    report.append(f"  整体成功率: {overall_success_rate:.1f}%")
    
    # 各时段详细分析
    for session_name, stats in results.items():
        report.append(f"\n{session_name.upper()}时段详细分析:")
        report.append(f"  总时段数: {stats['total_sessions']}")
        report.append(f"  目标达成: {stats['target_achieved']} ({stats['success_rate']:.1f}%)")
        report.append(f"  平均反弹: {stats['avg_recovery']:.2f}%")
        report.append(f"  平均回撤: {stats['avg_drawdown']:.2f}%")
        report.append(f"  平均净变化: {stats['avg_net_change']:.2f}%")
        report.append(f"  最大反弹: {stats['max_recovery']:.2f}%")
        report.append(f"  最小反弹: {stats['min_recovery']:.2f}%")
        
        # 显示具体案例
        target_cases = [s for s in stats['analyses'] if s['target_achieved']]
        if target_cases:
            report.append(f"  目标达成案例:")
            for case in target_cases[:5]:  # 显示前5个案例
                report.append(f"    {case['date']}: 反弹 {case['max_recovery_pct']:.2f}%")
    
    # 找出最佳时段
    if results:
        best_session = max(results.items(), key=lambda x: x[1]['success_rate'])
        report.append(f"\n最佳时段: {best_session[0].upper()}")
        report.append(f"成功率: {best_session[1]['success_rate']:.1f}%")
        report.append(f"平均反弹: {best_session[1]['avg_recovery']:.2f}%")
        
        # 策略建议
        report.append(f"\n策略建议:")
        if best_session[1]['success_rate'] > 50:
            report.append(f"✅ {best_session[0].upper()}时段表现优异，建议重点关注")
        elif best_session[1]['success_rate'] > 30:
            report.append(f"⚠️ {best_session[0].upper()}时段表现一般，可适度关注")
        else:
            report.append(f"❌ 所有时段表现不佳，策略需要重新评估")
    
    return "\n".join(report)

def main():
    # 获取数据
    klines = get_btc_yearly_data()
    
    if not klines:
        print("无法获取数据")
        return
    
    # 分析周二
    results = analyze_tuesday_sessions_yearly(klines)
    
    if not results:
        print("无法分析数据")
        return
    
    # 生成详细报告
    report = generate_detailed_report(results)
    print("\n" + report)
    
    # 保存报告到文件
    with open('btc_tuesday_yearly_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存详细数据到JSON
    with open('btc_tuesday_yearly_data.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n报告已保存到:")
    print(f"  - btc_tuesday_yearly_report.txt")
    print(f"  - btc_tuesday_yearly_data.json")

if __name__ == "__main__":
    main()
