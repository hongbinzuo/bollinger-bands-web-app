#!/usr/bin/env python3
"""
多时间框架策略诊断脚本
"""

import requests
import json
import time
from datetime import datetime

def log(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_api_endpoint(url, method="GET", data=None, timeout=30):
    """测试API端点"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        return False, "连接错误"
    except Exception as e:
        return False, str(e)

def diagnose_multi_timeframe():
    """诊断多时间框架策略"""
    log("开始多时间框架策略诊断")
    
    # 1. 测试基础连接
    log("1. 测试基础连接")
    success, result = test_api_endpoint("http://localhost:5000/health")
    if success:
        log(f"✅ 健康检查通过: {result['status']}")
    else:
        log(f"❌ 健康检查失败: {result}", "ERROR")
        return
    
    # 2. 测试获取币种列表
    log("2. 测试获取币种列表")
    success, result = test_api_endpoint("http://localhost:5000/multi_timeframe/get_top_symbols")
    if success:
        if result.get('success'):
            symbols = result.get('symbols', [])
            log(f"✅ 成功获取 {len(symbols)} 个币种")
            log(f"前5个币种: {symbols[:5]}")
            
            # 检查是否包含稳定币
            stablecoins = ['USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'DAIUSDT']
            found_stablecoins = [s for s in symbols if s in stablecoins]
            if found_stablecoins:
                log(f"⚠️  发现稳定币: {found_stablecoins}", "WARNING")
            else:
                log("✅ 已成功排除稳定币")
        else:
            log(f"❌ 获取币种失败: {result.get('error', '未知错误')}", "ERROR")
            return
    else:
        log(f"❌ 获取币种异常: {result}", "ERROR")
        return
    
    # 3. 测试单个币种分析
    log("3. 测试单个币种分析")
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    for symbol in test_symbols:
        log(f"分析币种: {symbol}")
        success, result = test_api_endpoint(
            "http://localhost:5000/multi_timeframe/analyze_symbol",
            method="POST",
            data={"symbol": symbol},
            timeout=60
        )
        
        if success:
            if result.get('success'):
                successful_timeframes = result.get('successful_timeframes', 0)
                total_timeframes = result.get('total_timeframes_analyzed', 0)
                log(f"✅ {symbol} 分析成功: {successful_timeframes}/{total_timeframes} 个时间框架")
                
                # 统计信号
                total_signals = 0
                for timeframe_result in result.get('results', []):
                    if timeframe_result.get('status') == 'success':
                        signal_count = len(timeframe_result.get('all_signals', []))
                        total_signals += signal_count
                        timeframe = timeframe_result.get('timeframe', 'unknown')
                        trend = timeframe_result.get('trend', 'unknown')
                        log(f"  {timeframe}: {signal_count} 个信号, 趋势: {trend}")
                
                log(f"  {symbol} 总信号数: {total_signals}")
                
                if total_signals == 0:
                    log(f"⚠️  {symbol} 没有生成任何信号", "WARNING")
                
            else:
                log(f"❌ {symbol} 分析失败: {result.get('error', '未知错误')}", "ERROR")
        else:
            log(f"❌ {symbol} 分析异常: {result}", "ERROR")
    
    # 4. 测试多币种分析
    log("4. 测试多币种分析")
    success, result = test_api_endpoint(
        "http://localhost:5000/multi_timeframe/analyze_multiple_symbols",
        method="POST",
        data={"symbols": test_symbols},
        timeout=120
    )
    
    if success:
        if result.get('success'):
            total_signals = result.get('total_signals', 0)
            log(f"✅ 多币种分析成功: {total_signals} 个信号")
            
            # 分析信号分布
            signals = result.get('signals', [])
            if signals:
                signal_by_symbol = {}
                signal_by_timeframe = {}
                signal_by_type = {}
                
                for signal in signals:
                    symbol = signal.get('symbol', 'unknown')
                    timeframe = signal.get('timeframe', 'unknown')
                    signal_type = signal.get('signal_type', 'unknown')
                    
                    signal_by_symbol[symbol] = signal_by_symbol.get(symbol, 0) + 1
                    signal_by_timeframe[timeframe] = signal_by_timeframe.get(timeframe, 0) + 1
                    signal_by_type[signal_type] = signal_by_type.get(signal_type, 0) + 1
                
                log(f"信号分布:")
                log(f"  按币种: {signal_by_symbol}")
                log(f"  按时间框架: {signal_by_timeframe}")
                log(f"  按信号类型: {signal_by_type}")
                
                # 显示前10个信号
                log("前10个信号:")
                for i, signal in enumerate(signals[:10]):
                    log(f"  {i+1}. {signal.get('symbol')} {signal.get('timeframe')} {signal.get('signal_type')} 收益率:{signal.get('profit_pct')}%")
            else:
                log("⚠️  多币种分析没有生成任何信号", "WARNING")
        else:
            log(f"❌ 多币种分析失败: {result.get('error', '未知错误')}", "ERROR")
    else:
        log(f"❌ 多币种分析异常: {result}", "ERROR")
    
    # 5. 测试策略信息
    log("5. 测试策略信息")
    success, result = test_api_endpoint("http://localhost:5000/multi_timeframe/get_strategy_info")
    if success:
        if result.get('success'):
            log("✅ 策略信息获取成功")
            log(f"策略名称: {result.get('strategy_name', 'N/A')}")
            log(f"时间框架: {result.get('timeframes', [])}")
            log(f"EMA周期: {result.get('ema_periods', [])}")
        else:
            log(f"❌ 获取策略信息失败: {result.get('error', '未知错误')}", "ERROR")
    else:
        log(f"❌ 获取策略信息异常: {result}", "ERROR")
    
    log("诊断完成")

if __name__ == "__main__":
    diagnose_multi_timeframe()

