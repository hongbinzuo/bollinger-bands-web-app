#!/usr/bin/env python3
"""
测试500个币种功能
"""

import requests
import json
import time
from datetime import datetime

def log(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_500_symbols():
    """测试500个币种功能"""
    log("开始测试500个币种功能")
    
    # 等待应用启动
    time.sleep(3)
    
    # 1. 测试获取币种列表
    log("1. 测试获取币种列表")
    try:
        response = requests.get('http://localhost:5000/multi_timeframe/get_top_symbols', timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                log(f"✅ 成功获取 {data['count']} 个币种")
                log(f"前10个币种: {data['symbols'][:10]}")
                
                # 检查是否达到500个
                if data['count'] >= 500:
                    log("✅ 币种数量达到500个")
                else:
                    log(f"⚠️  币种数量只有 {data['count']} 个，未达到500个", "WARNING")
                
                return data['symbols']
            else:
                log(f"❌ 获取币种失败: {data.get('error', '未知错误')}", "ERROR")
                return []
        else:
            log(f"❌ HTTP错误: {response.status_code}", "ERROR")
            return []
    except Exception as e:
        log(f"❌ 获取币种异常: {e}", "ERROR")
        return []
    
    # 2. 测试分页功能
    log("2. 测试分页功能")
    if symbols:
        test_symbols = symbols[:20]  # 只取前20个测试
        
        try:
            response = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                                   json={
                                       'symbols': test_symbols,
                                       'page': 1,
                                       'page_size': 5
                                   }, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    pagination = data.get('pagination', {})
                    log(f"✅ 分页测试成功")
                    log(f"当前页: {pagination.get('current_page', 'N/A')}")
                    log(f"总页数: {pagination.get('total_pages', 'N/A')}")
                    log(f"页面大小: {pagination.get('page_size', 'N/A')}")
                    log(f"总币种数: {pagination.get('total_symbols', 'N/A')}")
                    log(f"当前页信号数: {data.get('total_signals', 0)}")
                else:
                    log(f"❌ 分页测试失败: {data.get('error', '未知错误')}", "ERROR")
            else:
                log(f"❌ HTTP错误: {response.status_code}", "ERROR")
        except Exception as e:
            log(f"❌ 分页测试异常: {e}", "ERROR")
    
    # 3. 测试多线程性能
    log("3. 测试多线程性能")
    if symbols:
        test_symbols = symbols[:10]  # 只取前10个测试性能
        
        start_time = time.time()
        try:
            response = requests.post('http://localhost:5000/multi_timeframe/analyze_multiple_symbols', 
                                   json={
                                       'symbols': test_symbols,
                                       'page': 1,
                                       'page_size': 10
                                   }, timeout=120)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    log(f"✅ 多线程性能测试成功")
                    log(f"分析 {len(test_symbols)} 个币种耗时: {duration:.2f} 秒")
                    log(f"平均每个币种: {duration/len(test_symbols):.2f} 秒")
                    log(f"总信号数: {data.get('total_signals', 0)}")
                else:
                    log(f"❌ 多线程性能测试失败: {data.get('error', '未知错误')}", "ERROR")
            else:
                log(f"❌ HTTP错误: {response.status_code}", "ERROR")
        except Exception as e:
            log(f"❌ 多线程性能测试异常: {e}", "ERROR")
    
    log("测试完成")

if __name__ == "__main__":
    test_500_symbols()

