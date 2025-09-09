#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端集成测试脚本
测试前端HTML页面、JavaScript功能和数据展示
"""

import requests
import json
import time
from datetime import datetime

def test_frontend_endpoints():
    """测试前端相关的API端点"""
    print("🔍 测试前端API端点")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # 测试主页
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ 主页访问成功")
            print(f"📄 页面大小: {len(response.text)} 字符")
        else:
            print(f"❌ 主页访问失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 主页访问异常: {e}")
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ 健康检查成功")
            print(f"📊 状态: {data.get('status')}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
    
    # 测试多时间框架测试页面
    try:
        response = requests.get(f"{base_url}/test_multi_timeframe_frontend.html")
        if response.status_code == 200:
            print("✅ 多时间框架测试页面访问成功")
        else:
            print(f"❌ 多时间框架测试页面访问失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 多时间框架测试页面访问异常: {e}")

def test_multi_timeframe_api_integration():
    """测试多时间框架API集成"""
    print("\n🔍 测试多时间框架API集成")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # 测试获取币种列表
    try:
        response = requests.get(f"{base_url}/multi_timeframe/get_top_symbols")
        if response.status_code == 200:
            data = response.json()
            print("✅ 获取币种列表成功")
            print(f"📊 币种数量: {data.get('count', 0)}")
            print(f"📋 前5个币种: {data.get('symbols', [])[:5]}")
        else:
            print(f"❌ 获取币种列表失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取币种列表异常: {e}")
    
    # 测试分析单个币种
    try:
        payload = {"symbol": "BTCUSDT"}
        response = requests.post(
            f"{base_url}/multi_timeframe/analyze_symbol",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ 分析单个币种成功")
            print(f"📊 成功时间框架: {data.get('successful_timeframes', 0)}")
            print(f"📊 总时间框架: {data.get('total_timeframes_analyzed', 0)}")
        else:
            print(f"❌ 分析单个币种失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 分析单个币种异常: {e}")
    
    # 测试分析多个币种
    try:
        payload = {"symbols": ["BTCUSDT", "ETHUSDT"]}
        response = requests.post(
            f"{base_url}/multi_timeframe/analyze_multiple_symbols",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ 分析多个币种成功")
            print(f"📊 总信号数: {data.get('total_signals', 0)}")
            print(f"📊 成功信号数: {data.get('successful_signals', 0)}")
        else:
            print(f"❌ 分析多个币种失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 分析多个币种异常: {e}")
    
    # 测试币种验证
    try:
        payload = {"symbol": "BTCUSDT"}
        response = requests.post(
            f"{base_url}/multi_timeframe/validate_symbol",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ 币种验证成功")
            print(f"📊 币种有效: {data.get('is_valid', False)}")
        else:
            print(f"❌ 币种验证失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 币种验证异常: {e}")

def test_data_format_compatibility():
    """测试数据格式兼容性"""
    print("\n🔍 测试数据格式兼容性")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    try:
        # 获取分析结果
        payload = {"symbols": ["BTCUSDT"]}
        response = requests.post(
            f"{base_url}/multi_timeframe/analyze_multiple_symbols",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            signals = data.get('signals', [])
            
            if signals:
                print("✅ 数据格式检查")
                first_signal = signals[0]
                
                # 检查前端期望的字段
                expected_fields = [
                    'symbol', 'timeframe', 'trend', 'signal_type',
                    'entry_price', 'take_profit', 'profit_pct',
                    'signal_time', 'ema_period'
                ]
                
                print("📋 字段完整性检查:")
                for field in expected_fields:
                    if field in first_signal:
                        value = first_signal[field]
                        print(f"  ✅ {field}: {type(value).__name__} = {value}")
                    else:
                        print(f"  ❌ 缺少字段: {field}")
                
                # 检查数据类型
                print("\n📊 数据类型检查:")
                type_checks = {
                    'symbol': str,
                    'timeframe': str,
                    'trend': str,
                    'signal_type': str,
                    'entry_price': (int, float),
                    'take_profit': (int, float),
                    'profit_pct': (int, float),
                    'signal_time': str,
                    'ema_period': (str, int)
                }
                
                for field, expected_type in type_checks.items():
                    if field in first_signal:
                        actual_type = type(first_signal[field])
                        if isinstance(first_signal[field], expected_type):
                            print(f"  ✅ {field}: 类型正确 ({actual_type.__name__})")
                        else:
                            print(f"  ⚠️  {field}: 类型不匹配 (期望: {expected_type}, 实际: {actual_type.__name__})")
                
            else:
                print("❌ 没有信号数据")
        else:
            print(f"❌ 获取数据失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 数据格式检查异常: {e}")

def test_error_handling():
    """测试错误处理"""
    print("\n🔍 测试错误处理")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # 测试无效币种
    try:
        payload = {"symbol": "INVALID_SYMBOL_123"}
        response = requests.post(
            f"{base_url}/multi_timeframe/analyze_symbol",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ 无效币种处理成功")
            print(f"📊 成功时间框架: {data.get('successful_timeframes', 0)}")
        else:
            print(f"❌ 无效币种处理失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 无效币种处理异常: {e}")
    
    # 测试空请求
    try:
        payload = {}
        response = requests.post(
            f"{base_url}/multi_timeframe/analyze_symbol",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 400:
            print("✅ 空请求错误处理正确")
        else:
            print(f"⚠️  空请求处理: {response.status_code}")
    except Exception as e:
        print(f"❌ 空请求处理异常: {e}")

def test_performance():
    """测试性能"""
    print("\n🔍 测试性能")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # 测试单个币种分析性能
    try:
        start_time = time.time()
        payload = {"symbol": "BTCUSDT"}
        response = requests.post(
            f"{base_url}/multi_timeframe/analyze_symbol",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        end_time = time.time()
        
        if response.status_code == 200:
            duration = end_time - start_time
            print(f"✅ 单个币种分析性能: {duration:.2f}秒")
            
            if duration < 15:
                print("  🚀 性能优秀 (< 15秒)")
            elif duration < 30:
                print("  ⚡ 性能良好 (< 30秒)")
            else:
                print("  ⚠️  性能需要优化 (> 30秒)")
        else:
            print(f"❌ 性能测试失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 性能测试异常: {e}")

def main():
    """主测试函数"""
    print("🚀 前端集成测试开始")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. 测试前端端点
        test_frontend_endpoints()
        
        # 2. 测试多时间框架API集成
        test_multi_timeframe_api_integration()
        
        # 3. 测试数据格式兼容性
        test_data_format_compatibility()
        
        # 4. 测试错误处理
        test_error_handling()
        
        # 5. 测试性能
        test_performance()
        
        print("\n" + "=" * 60)
        print("🎉 前端集成测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

