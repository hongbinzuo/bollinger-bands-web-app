#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试多时间框架数据格式
检查前端和后端数据格式是否匹配
"""

import requests
import json

def test_api_response():
    """测试API响应数据格式"""
    print("🔍 测试多时间框架API数据格式")
    print("=" * 50)
    
    # 测试获取币种列表
    try:
        response = requests.get('http://localhost:5000/multi_timeframe/get_top_symbols')
        data = response.json()
        
        print("✅ 获取币种列表成功")
        print(f"📊 币种数量: {data.get('count', 0)}")
        print(f"📋 前5个币种: {data.get('symbols', [])[:5]}")
        print()
        
    except Exception as e:
        print(f"❌ 获取币种列表失败: {e}")
        return
    
    # 测试分析币种
    try:
        test_symbols = ['BTCUSDT', 'ETHUSDT']
        payload = {'symbols': test_symbols}
        
        response = requests.post(
            'http://localhost:5000/multi_timeframe/analyze_multiple_symbols',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        data = response.json()
        
        print("✅ 分析币种成功")
        print(f"📊 请求币种数: {data.get('symbols_requested', 0)}")
        print(f"📊 处理币种数: {data.get('symbols_processed', 0)}")
        print(f"📊 总信号数: {data.get('total_signals', 0)}")
        print(f"📊 成功信号数: {data.get('successful_signals', 0)}")
        print()
        
        # 检查信号数据格式
        signals = data.get('signals', [])
        if signals:
            print("🔍 信号数据格式检查:")
            print(f"📋 信号数量: {len(signals)}")
            
            # 检查第一个信号的数据结构
            first_signal = signals[0]
            print(f"📋 第一个信号数据结构:")
            for key, value in first_signal.items():
                print(f"  {key}: {type(value).__name__} = {value}")
            
            print()
            
            # 检查前端期望的字段
            expected_fields = [
                'symbol', 'timeframe', 'trend', 'signal_type', 
                'entry_price', 'take_profit', 'profit_pct', 
                'signal_time', 'ema_period'
            ]
            
            print("🔍 前端期望字段检查:")
            for field in expected_fields:
                if field in first_signal:
                    print(f"  ✅ {field}: {first_signal[field]}")
                else:
                    print(f"  ❌ 缺少字段: {field}")
            
            print()
            
            # 检查信号类型
            signal_types = set()
            for signal in signals:
                signal_types.add(signal.get('signal_type', 'unknown'))
            
            print(f"📊 信号类型统计: {signal_types}")
            
            # 检查趋势类型
            trends = set()
            for signal in signals:
                trends.add(signal.get('trend', 'unknown'))
            
            print(f"📊 趋势类型统计: {trends}")
            
        else:
            print("❌ 没有信号数据")
            
    except Exception as e:
        print(f"❌ 分析币种失败: {e}")
        import traceback
        traceback.print_exc()

def test_frontend_expected_format():
    """测试前端期望的数据格式"""
    print("\n🔍 前端期望的数据格式")
    print("=" * 50)
    
    # 模拟前端期望的信号格式
    expected_signal = {
        'symbol': 'BTCUSDT',
        'timeframe': '4h',
        'trend': 'bullish',
        'signal_type': 'long',
        'entry_price': 50000.0,
        'take_profit': 52000.0,
        'profit_pct': 4.0,
        'signal_time': '2025-09-07 14:30:00',
        'ema_period': 144
    }
    
    print("📋 前端期望的信号格式:")
    for key, value in expected_signal.items():
        print(f"  {key}: {type(value).__name__} = {value}")
    
    print("\n🔍 前端JavaScript处理逻辑:")
    print("  - signal.symbol: 币种名称")
    print("  - signal.timeframe: 时间框架")
    print("  - signal.trend: 趋势 (bullish/bearish/neutral)")
    print("  - signal.signal_type: 信号类型 (long/short)")
    print("  - signal.entry_price: 入场价格")
    print("  - signal.take_profit: 止盈价格")
    print("  - signal.profit_pct: 收益率百分比")
    print("  - signal.signal_time: 信号时间")
    print("  - signal.ema_period: EMA周期")

if __name__ == "__main__":
    test_api_response()
    test_frontend_expected_format()
