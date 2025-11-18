#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理和性能测试脚本
测试网络异常、数据异常、API限制、响应时间、并发处理等
"""

import requests
import time
import threading
import json
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

def test_network_error_handling():
    """测试网络错误处理"""
    print("🔍 测试网络错误处理")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试超时处理
    print("📊 测试超时处理:")
    try:
        # 模拟超时情况（设置极短的超时时间）
        original_timeout = requests.Session().timeout
        start_time = time.time()
        
        # 使用正常超时时间测试
        df = strategy.get_klines_data('BTCUSDT', '4h', 10)
        end_time = time.time()
        
        if not df.empty:
            print(f"  ✅ 正常请求成功: {end_time - start_time:.2f}秒")
        else:
            print("  ❌ 正常请求失败")
            
    except Exception as e:
        print(f"  ❌ 超时测试异常: {e}")
    
    # 测试无效URL处理
    print("\n📊 测试API错误处理:")
    try:
        # 测试无效币种
        df = strategy.get_klines_data('INVALID_SYMBOL_123', '4h', 10)
        if df.empty:
            print("  ✅ 无效币种处理正确")
        else:
            print("  ⚠️  无效币种意外返回数据")
    except Exception as e:
        print(f"  ✅ 无效币种异常处理: {type(e).__name__}")
    
    # 测试无效时间框架
    try:
        df = strategy.get_klines_data('BTCUSDT', 'invalid_tf', 10)
        if df.empty:
            print("  ✅ 无效时间框架处理正确")
        else:
            print("  ⚠️  无效时间框架意外返回数据")
    except Exception as e:
        print(f"  ✅ 无效时间框架异常处理: {type(e).__name__}")

def test_api_rate_limiting():
    """测试API频率限制处理"""
    print("\n🔍 测试API频率限制处理")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试快速连续请求
    print("📊 测试快速连续请求:")
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
    start_time = time.time()
    success_count = 0
    
    for i, symbol in enumerate(symbols):
        try:
            df = strategy.get_klines_data(symbol, '4h', 10)
            if not df.empty:
                success_count += 1
            print(f"  📊 {symbol}: {'✅' if not df.empty else '❌'}")
            
            # 添加小延迟避免频率限制
            if i < len(symbols) - 1:
                time.sleep(0.5)
                
        except Exception as e:
            print(f"  ❌ {symbol}: {type(e).__name__}")
    
    end_time = time.time()
    print(f"  📊 成功率: {success_count}/{len(symbols)} ({success_count/len(symbols)*100:.1f}%)")
    print(f"  ⏱️  总耗时: {end_time - start_time:.2f}秒")

def test_data_validation():
    """测试数据验证"""
    print("\n🔍 测试数据验证")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试空数据处理
    print("📊 测试空数据处理:")
    try:
        # 模拟空数据情况
        empty_df = strategy.get_klines_data('NONEXISTENT_SYMBOL', '4h', 10)
        if empty_df.empty:
            print("  ✅ 空数据正确处理")
            
            # 测试在空数据上计算指标
            try:
                result = strategy.calculate_emas(empty_df)
                if result.empty:
                    print("  ✅ 空数据指标计算正确处理")
                else:
                    print("  ⚠️  空数据指标计算意外返回数据")
            except Exception as e:
                print(f"  ✅ 空数据指标计算异常处理: {type(e).__name__}")
        else:
            print("  ⚠️  空数据意外返回数据")
    except Exception as e:
        print(f"  ✅ 空数据异常处理: {type(e).__name__}")
    
    # 测试数据格式验证
    print("\n📊 测试数据格式验证:")
    try:
        df = strategy.get_klines_data('BTCUSDT', '4h', 10)
        if not df.empty:
            # 检查必要列是否存在
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if not missing_columns:
                print("  ✅ 数据格式验证通过")
            else:
                print(f"  ❌ 缺少必要列: {missing_columns}")
            
            # 检查数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            type_issues = []
            
            for col in numeric_columns:
                if col in df.columns:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        type_issues.append(f"{col}不是数值类型")
            
            if not type_issues:
                print("  ✅ 数据类型验证通过")
            else:
                print(f"  ❌ 数据类型问题: {type_issues}")
        else:
            print("  ❌ 无法获取测试数据")
    except Exception as e:
        print(f"  ❌ 数据格式验证异常: {e}")

def test_performance_single_request():
    """测试单请求性能"""
    print("\n🔍 测试单请求性能")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试不同币种的性能
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
    performance_results = []
    
    for symbol in test_symbols:
        try:
            start_time = time.time()
            df = strategy.get_klines_data(symbol, '4h', 100)
            end_time = time.time()
            
            duration = end_time - start_time
            performance_results.append({
                'symbol': symbol,
                'duration': duration,
                'success': not df.empty,
                'data_points': len(df) if not df.empty else 0
            })
            
            status = "✅" if not df.empty else "❌"
            print(f"  📊 {symbol}: {status} {duration:.2f}秒 ({len(df) if not df.empty else 0}条数据)")
            
        except Exception as e:
            print(f"  ❌ {symbol}: 异常 - {type(e).__name__}")
            performance_results.append({
                'symbol': symbol,
                'duration': 0,
                'success': False,
                'data_points': 0
            })
    
    # 性能统计
    successful_requests = [r for r in performance_results if r['success']]
    if successful_requests:
        avg_duration = sum(r['duration'] for r in successful_requests) / len(successful_requests)
        min_duration = min(r['duration'] for r in successful_requests)
        max_duration = max(r['duration'] for r in successful_requests)
        
        print(f"\n📊 性能统计:")
        print(f"  ✅ 成功请求: {len(successful_requests)}/{len(test_symbols)}")
        print(f"  ⏱️  平均耗时: {avg_duration:.2f}秒")
        print(f"  🚀 最快请求: {min_duration:.2f}秒")
        print(f"  🐌 最慢请求: {max_duration:.2f}秒")
        
        if avg_duration < 5:
            print("  🎯 性能评级: 优秀")
        elif avg_duration < 10:
            print("  🎯 性能评级: 良好")
        elif avg_duration < 20:
            print("  🎯 性能评级: 一般")
        else:
            print("  🎯 性能评级: 需要优化")

def test_concurrent_requests():
    """测试并发请求处理"""
    print("\n🔍 测试并发请求处理")
    print("=" * 50)
    
    strategy = MultiTimeframeStrategy()
    
    # 测试并发请求
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
    
    def fetch_symbol_data(symbol):
        """获取单个币种数据"""
        try:
            start_time = time.time()
            df = strategy.get_klines_data(symbol, '4h', 50)
            end_time = time.time()
            
            return {
                'symbol': symbol,
                'success': not df.empty,
                'duration': end_time - start_time,
                'data_points': len(df) if not df.empty else 0
            }
        except Exception as e:
            return {
                'symbol': symbol,
                'success': False,
                'duration': 0,
                'data_points': 0,
                'error': str(e)
            }
    
    # 串行请求测试
    print("📊 串行请求测试:")
    start_time = time.time()
    serial_results = []
    
    for symbol in test_symbols:
        result = fetch_symbol_data(symbol)
        serial_results.append(result)
        status = "✅" if result['success'] else "❌"
        print(f"  📊 {symbol}: {status} {result['duration']:.2f}秒")
    
    serial_duration = time.time() - start_time
    print(f"  ⏱️  串行总耗时: {serial_duration:.2f}秒")
    
    # 并发请求测试
    print("\n📊 并发请求测试:")
    start_time = time.time()
    concurrent_results = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有任务
        future_to_symbol = {executor.submit(fetch_symbol_data, symbol): symbol for symbol in test_symbols}
        
        # 收集结果
        for future in as_completed(future_to_symbol):
            result = future.result()
            concurrent_results.append(result)
            status = "✅" if result['success'] else "❌"
            print(f"  📊 {result['symbol']}: {status} {result['duration']:.2f}秒")
    
    concurrent_duration = time.time() - start_time
    print(f"  ⏱️  并发总耗时: {concurrent_duration:.2f}秒")
    
    # 性能对比
    if serial_duration > 0 and concurrent_duration > 0:
        speedup = serial_duration / concurrent_duration
        print(f"\n📊 性能对比:")
        print(f"  🚀 加速比: {speedup:.2f}x")
        print(f"  ⏱️  时间节省: {serial_duration - concurrent_duration:.2f}秒")
        
        if speedup > 1.5:
            print("  🎯 并发效果: 优秀")
        elif speedup > 1.2:
            print("  🎯 并发效果: 良好")
        else:
            print("  🎯 并发效果: 一般")

def test_memory_usage():
    """测试内存使用"""
    print("\n🔍 测试内存使用")
    print("=" * 50)
    
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"📊 初始内存使用: {initial_memory:.2f} MB")
        
        strategy = MultiTimeframeStrategy()
        
        # 测试大量数据处理
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
        data_frames = []
        
        for symbol in symbols:
            df = strategy.get_klines_data(symbol, '4h', 200)
            if not df.empty:
                data_frames.append(df)
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"  📊 {symbol}: {current_memory:.2f} MB")
        
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - initial_memory
        
        print(f"\n📊 内存使用统计:")
        print(f"  📈 峰值内存: {peak_memory:.2f} MB")
        print(f"  📊 内存增长: {memory_increase:.2f} MB")
        print(f"  📊 数据框数量: {len(data_frames)}")
        
        if memory_increase < 50:
            print("  🎯 内存使用: 优秀")
        elif memory_increase < 100:
            print("  🎯 内存使用: 良好")
        else:
            print("  🎯 内存使用: 需要优化")
        
        # 清理内存
        del data_frames
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        print(f"  🧹 清理后内存: {final_memory:.2f} MB")
        
    except ImportError:
        print("  ⚠️  psutil未安装，跳过内存测试")
    except Exception as e:
        print(f"  ❌ 内存测试异常: {e}")

def test_api_endpoint_performance():
    """测试API端点性能"""
    print("\n🔍 测试API端点性能")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # 测试不同端点的性能
    endpoints = [
        ('/health', 'GET', None),
        ('/multi_timeframe/get_top_symbols', 'GET', None),
        ('/multi_timeframe/analyze_symbol', 'POST', {'symbol': 'BTCUSDT'}),
        ('/multi_timeframe/validate_symbol', 'POST', {'symbol': 'BTCUSDT'})
    ]
    
    for endpoint, method, payload in endpoints:
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(f"{base_url}{endpoint}", timeout=30)
            else:
                response = requests.post(
                    f"{base_url}{endpoint}",
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"  📊 {endpoint}: {status} {duration:.2f}秒 ({response.status_code})")
            
        except Exception as e:
            print(f"  ❌ {endpoint}: 异常 - {type(e).__name__}")

def main():
    """主测试函数"""
    print("🚀 错误处理和性能测试开始")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. 测试网络错误处理
        test_network_error_handling()
        
        # 2. 测试API频率限制
        test_api_rate_limiting()
        
        # 3. 测试数据验证
        test_data_validation()
        
        # 4. 测试单请求性能
        test_performance_single_request()
        
        # 5. 测试并发请求
        test_concurrent_requests()
        
        # 6. 测试内存使用
        test_memory_usage()
        
        # 7. 测试API端点性能
        test_api_endpoint_performance()
        
        print("\n" + "=" * 60)
        print("🎉 错误处理和性能测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

