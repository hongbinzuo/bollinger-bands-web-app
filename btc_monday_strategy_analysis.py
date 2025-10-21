#!/usr/bin/env python3
print("=== BTC周一策略验证分析器 ===")

import requests
from datetime import datetime, timedelta
import json

def get_btc_extended_data():
    print("正在获取BTC扩展数据...")
    
    # 获取更多历史数据，使用4小时K线
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

def analyze_monday_strategy(klines):
    print("\n分析周一策略...")
    
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
    
    # 找到所有周一
    monday_dates = []
    for date in sorted(daily_data.keys()):
        if date.weekday() == 0:  # 周一
            monday_dates.append(date)
    
    print(f"找到 {len(monday_dates)} 个周一交易日")
    
    if not monday_dates:
        print("无周一交易日")
        return None
    
    # 分析每个周一
    analyses = []
    
    for monday_date in monday_dates:
        print(f"\n分析 {monday_date} (周一):")
        
        # 周一数据
        monday_data = daily_data[monday_date]
        monday_data.sort(key=lambda x: x['datetime'])
        
        # 计算周一的表现
        monday_open = monday_data[0]['open']
        monday_close = monday_data[-1]['close']
        monday_high = max(d['high'] for d in monday_data)
        monday_low = min(d['low'] for d in monday_data)
        
        # 计算周一涨跌幅
        monday_change = ((monday_close - monday_open) / monday_open) * 100
        
        # 分析后续表现（周二到周五）
        next_days_analysis = analyze_next_days_performance(monday_date, daily_data, monday_close)
        
        # 判断策略信号
        strategy_signals = analyze_strategy_signals(monday_change, monday_high, monday_low, monday_open, next_days_analysis)
        
        analysis = {
            'monday_date': str(monday_date),
            'monday_open': monday_open,
            'monday_close': monday_close,
            'monday_high': monday_high,
            'monday_low': monday_low,
            'monday_change_pct': monday_change,
            'next_days_analysis': next_days_analysis,
            'strategy_signals': strategy_signals
        }
        
        analyses.append(analysis)
        
        print(f"  周一开盘: ${monday_open:.2f}")
        print(f"  周一收盘: ${monday_close:.2f}")
        print(f"  周一涨跌: {monday_change:.2f}%")
        print(f"  策略信号: {strategy_signals['signal_type']}")
        print(f"  后续表现: {next_days_analysis['overall_performance']}")
    
    return analyses

def analyze_next_days_performance(monday_date, daily_data, monday_close):
    """分析周二到周五的表现"""
    
    next_days = []
    for i in range(1, 5):  # 周二到周五
        next_date = monday_date + timedelta(days=i)
        if next_date in daily_data:
            next_days.append(next_date)
    
    if not next_days:
        return {'overall_performance': '无后续数据', 'max_gain': 0, 'max_loss': 0, 'final_change': 0}
    
    # 计算后续最高点和最低点
    max_price = monday_close
    min_price = monday_close
    
    for date in next_days:
        day_data = daily_data[date]
        day_high = max(d['high'] for d in day_data)
        day_low = min(d['low'] for d in day_data)
        max_price = max(max_price, day_high)
        min_price = min(min_price, day_low)
    
    # 计算最终价格（周五收盘）
    final_date = next_days[-1]
    final_data = daily_data[final_date]
    final_close = final_data[-1]['close']
    
    max_gain = ((max_price - monday_close) / monday_close) * 100
    max_loss = ((min_price - monday_close) / monday_close) * 100
    final_change = ((final_close - monday_close) / monday_close) * 100
    
    # 判断整体表现
    if final_change > 2:
        performance = "强势上涨"
    elif final_change > 0:
        performance = "温和上涨"
    elif final_change > -2:
        performance = "温和下跌"
    else:
        performance = "强势下跌"
    
    return {
        'overall_performance': performance,
        'max_gain': max_gain,
        'max_loss': max_loss,
        'final_change': final_change,
        'next_days_count': len(next_days)
    }

def analyze_strategy_signals(monday_change, monday_high, monday_low, monday_open, next_days_analysis):
    """分析策略信号"""
    
    # 策略1: 如果周一上涨，很可能反转下跌
    if monday_change > 1:  # 周一上涨超过1%
        if next_days_analysis['final_change'] < -1:  # 后续下跌超过1%
            signal_type = "反转下跌信号 ✅"
            signal_accuracy = True
        else:
            signal_type = "反转下跌信号 ❌"
            signal_accuracy = False
    elif monday_change < -1:  # 周一下跌超过1%
        if next_days_analysis['final_change'] > 1:  # 后续上涨超过1%
            signal_type = "底部反弹信号 ✅"
            signal_accuracy = True
        else:
            signal_type = "底部反弹信号 ❌"
            signal_accuracy = False
    else:
        signal_type = "无明确信号"
        signal_accuracy = None
    
    return {
        'signal_type': signal_type,
        'signal_accuracy': signal_accuracy,
        'monday_pump': monday_change > 1,
        'monday_dump': monday_change < -1,
        'reversal_confirmed': monday_change > 1 and next_days_analysis['final_change'] < -1,
        'bottom_confirmed': monday_change < -1 and next_days_analysis['final_change'] > 1
    }

def generate_detailed_report_monday(analyses):
    """生成详细报告"""
    if not analyses:
        return "无分析结果"
    
    report = []
    report.append("=" * 70)
    report.append("BTC周一策略验证分析报告")
    report.append("=" * 70)
    
    # 总体统计
    total_mondays = len(analyses)
    
    # 统计策略信号
    reversal_signals = [a for a in analyses if a['strategy_signals']['monday_pump']]
    bottom_signals = [a for a in analyses if a['strategy_signals']['monday_dump']]
    
    reversal_accurate = sum(1 for a in reversal_signals if a['strategy_signals']['reversal_confirmed'])
    bottom_accurate = sum(1 for a in bottom_signals if a['strategy_signals']['bottom_confirmed'])
    
    reversal_success_rate = (reversal_accurate / len(reversal_signals)) * 100 if reversal_signals else 0
    bottom_success_rate = (bottom_accurate / len(bottom_signals)) * 100 if bottom_signals else 0
    
    report.append(f"\n总体统计:")
    report.append(f"  总周一交易日: {total_mondays}")
    report.append(f"  反转信号总数: {len(reversal_signals)}")
    report.append(f"  底部信号总数: {len(bottom_signals)}")
    report.append(f"  反转信号准确率: {reversal_success_rate:.1f}% ({reversal_accurate}/{len(reversal_signals)})")
    report.append(f"  底部信号准确率: {bottom_success_rate:.1f}% ({bottom_accurate}/{len(bottom_signals)})")
    
    # 与原始策略对比
    original_reversal_rate = 64  # 原始策略声称64%反转
    original_bottom_rate = 36   # 原始策略声称36%底部
    
    report.append(f"\n与原始策略对比:")
    report.append(f"  原始策略声称: 64%反转下跌, 36%底部信号")
    report.append(f"  实际验证结果: {reversal_success_rate:.1f}%反转准确率, {bottom_success_rate:.1f}%底部准确率")
    
    if reversal_success_rate > 50:
        report.append(f"  ✅ 反转信号表现良好")
    else:
        report.append(f"  ❌ 反转信号表现不佳")
    
    if bottom_success_rate > 30:
        report.append(f"  ✅ 底部信号表现良好")
    else:
        report.append(f"  ❌ 底部信号表现不佳")
    
    # 详细案例分析
    report.append(f"\n详细案例分析:")
    
    # 反转信号案例
    if reversal_signals:
        report.append(f"\n反转信号案例 (周一上涨后反转):")
        for i, analysis in enumerate(reversal_signals[:5], 1):  # 显示前5个
            report.append(f"  案例 {i}: {analysis['monday_date']}")
            report.append(f"    周一涨跌: {analysis['monday_change_pct']:.2f}%")
            report.append(f"    后续表现: {analysis['next_days_analysis']['overall_performance']}")
            report.append(f"    最终变化: {analysis['next_days_analysis']['final_change']:.2f}%")
            report.append(f"    信号准确: {'✅' if analysis['strategy_signals']['reversal_confirmed'] else '❌'}")
    
    # 底部信号案例
    if bottom_signals:
        report.append(f"\n底部信号案例 (周一下跌后反弹):")
        for i, analysis in enumerate(bottom_signals[:5], 1):  # 显示前5个
            report.append(f"  案例 {i}: {analysis['monday_date']}")
            report.append(f"    周一涨跌: {analysis['monday_change_pct']:.2f}%")
            report.append(f"    后续表现: {analysis['next_days_analysis']['overall_performance']}")
            report.append(f"    最终变化: {analysis['next_days_analysis']['final_change']:.2f}%")
            report.append(f"    信号准确: {'✅' if analysis['strategy_signals']['bottom_confirmed'] else '❌'}")
    
    # 策略建议
    report.append(f"\n策略建议:")
    overall_accuracy = (reversal_accurate + bottom_accurate) / total_mondays * 100
    
    if overall_accuracy > 60:
        report.append(f"✅ 策略整体表现优异，准确率 {overall_accuracy:.1f}%")
    elif overall_accuracy > 40:
        report.append(f"⚠️ 策略整体表现一般，准确率 {overall_accuracy:.1f}%")
    else:
        report.append(f"❌ 策略整体表现不佳，准确率 {overall_accuracy:.1f}%，需要重新评估")
    
    return "\n".join(report)

def main():
    # 获取数据
    klines = get_btc_extended_data()
    
    if not klines:
        print("无法获取数据")
        return
    
    # 分析周一策略
    analyses = analyze_monday_strategy(klines)
    
    if not analyses:
        print("无法分析数据")
        return
    
    # 生成详细报告
    report = generate_detailed_report_monday(analyses)
    print("\n" + report)
    
    # 保存报告到文件
    with open('btc_monday_strategy_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存详细数据到JSON
    with open('btc_monday_strategy_data.json', 'w', encoding='utf-8') as f:
        json.dump(analyses, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n报告已保存到:")
    print(f"  - btc_monday_strategy_report.txt")
    print(f"  - btc_monday_strategy_data.json")

if __name__ == "__main__":
    main()
