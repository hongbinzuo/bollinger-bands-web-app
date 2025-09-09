#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端数据格式兼容性
"""

import requests
import json

def test_frontend_data_format():
    try:
        # 测试API响应
        response = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                                json={'symbols': ['BTCUSDT']},
                                headers={'Content-Type': 'application/json'})
        
        data = response.json()
        print('=== API响应测试 ===')
        print(f'状态码: {response.status_code}')
        print(f'成功: {data.get("success")}')
        print(f'总信号数: {data.get("total_signals")}')
        print(f'成功信号数: {data.get("successful_signals")}')
        
        signals = data.get('signals', [])
        print(f'信号数组长度: {len(signals)}')
        
        if signals:
            print('\n=== 第一个信号数据格式 ===')
            first_signal = signals[0]
            print('信号字段:')
            for key, value in first_signal.items():
                print(f'  {key}: {type(value).__name__} = {value}')
            
            # 检查前端期望的字段
            print('\n=== 前端期望字段检查 ===')
            expected_fields = [
                'symbol', 'timeframe', 'trend', 'signal_type', 
                'entry_price', 'take_profit', 'profit_pct', 
                'signal_time', 'ema_period'
            ]
            
            missing_fields = []
            for field in expected_fields:
                if field not in first_signal:
                    missing_fields.append(field)
                else:
                    value = first_signal[field]
                    print(f'  ✅ {field}: {type(value).__name__} = {value}')
            
            if missing_fields:
                print(f'  ❌ 缺少字段: {missing_fields}')
            
            # 检查数据类型问题
            print('\n=== 数据类型检查 ===')
            type_issues = []
            
            # 检查数值类型
            numeric_fields = ['entry_price', 'take_profit', 'profit_pct']
            for field in numeric_fields:
                if field in first_signal:
                    value = first_signal[field]
                    if not isinstance(value, (int, float)):
                        type_issues.append(f'{field} 不是数值类型: {type(value)}')
            
            # 检查字符串类型
            string_fields = ['symbol', 'timeframe', 'trend', 'signal_type', 'signal_time']
            for field in string_fields:
                if field in first_signal:
                    value = first_signal[field]
                    if not isinstance(value, str):
                        type_issues.append(f'{field} 不是字符串类型: {type(value)}')
            
            if type_issues:
                print('  ❌ 数据类型问题:')
                for issue in type_issues:
                    print(f'    - {issue}')
            else:
                print('  ✅ 数据类型正确')
            
            # 检查特殊值
            print('\n=== 特殊值检查 ===')
            if first_signal.get('profit_pct') is None:
                print('  ⚠️  profit_pct 为 None')
            if first_signal.get('take_profit') is None:
                print('  ⚠️  take_profit 为 None')
            if first_signal.get('signal_time') == '':
                print('  ⚠️  signal_time 为空字符串')
            if first_signal.get('ema_period') is None:
                print('  ⚠️  ema_period 为 None')
        
        # 测试JSON序列化
        print('\n=== JSON序列化测试 ===')
        try:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            print('  ✅ JSON序列化成功')
            print(f'  JSON长度: {len(json_str)} 字符')
        except Exception as e:
            print(f'  ❌ JSON序列化失败: {e}')
        
    except Exception as e:
        print(f'测试失败: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_frontend_data_format()
