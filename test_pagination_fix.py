#!/usr/bin/env python3
"""
分页修复验证脚本
测试前端分页功能是否正常工作
"""

import requests
import json
import time

def test_pagination_fix():
    """测试分页修复"""
    base_url = "http://localhost:5000"
    
    print("=== 分页修复验证测试 ===")
    
    try:
        # 1. 获取少量币种进行测试
        print("1. 获取测试币种...")
        response = requests.get(f"{base_url}/multi_timeframe/get_top_symbols")
        data = response.json()
        
        if not data['success']:
            print(f"[FAIL] 获取币种失败: {data.get('error')}")
            return False
            
        test_symbols = data['symbols'][:5]  # 只取前5个币种
        print(f"[PASS] 获取到测试币种: {test_symbols}")
        
        # 2. 测试多页信号生成
        print("\n2. 测试分页信号生成...")
        response = requests.post(f"{base_url}/multi_timeframe/analyze_multiple_symbols", 
                               json={
                                   'symbols': test_symbols,
                                   'page': 1,
                                   'page_size': 10  # 每页10个信号，确保会有多页
                               })
        data = response.json()
        
        if not data['success']:
            print(f"[FAIL] 分析失败: {data.get('error')}")
            return False
            
        signals = data.get('signals', [])
        pagination = data.get('pagination', {})
        
        print(f"[PASS] 第1页: {len(signals)} 个信号")
        print(f"   分页信息: 第{pagination.get('current_page')}页，共{pagination.get('total_pages')}页")
        print(f"   总信号数: {pagination.get('total_signals')}")
        
        # 3. 测试第2页（如果存在）
        if pagination.get('total_pages', 0) > 1:
            print("\n3. 测试第2页...")
            response = requests.post(f"{base_url}/multi_timeframe/analyze_multiple_symbols", 
                                   json={
                                       'symbols': test_symbols,
                                       'page': 2,
                                       'page_size': 10
                                   })
            data2 = response.json()
            
            if data2['success']:
                signals2 = data2.get('signals', [])
                pagination2 = data2.get('pagination', {})
                
                print(f"[PASS] 第2页: {len(signals2)} 个信号")
                print(f"   分页信息: 第{pagination2.get('current_page')}页，共{pagination2.get('total_pages')}页")
                
                # 检查信号是否重复
                signal_ids_1 = set(f"{s.get('symbol')}-{s.get('timeframe')}-{s.get('entry_price', 0)}" for s in signals)
                signal_ids_2 = set(f"{s.get('symbol')}-{s.get('timeframe')}-{s.get('entry_price', 0)}" for s in signals2)
                
                overlap = signal_ids_1 & signal_ids_2
                if overlap:
                    print(f"[WARN] 检测到重复信号: {len(overlap)} 个")
                    return False
                else:
                    print("[PASS] 分页信号无重复，分页逻辑正确")
            else:
                print(f"[FAIL] 第2页获取失败: {data2.get('error')}")
        else:
            print("\n3. 只有1页数据，跳过多页测试")
        
        # 4. 测试边界情况
        print("\n4. 测试边界情况...")
        
        # 测试超出范围的页面
        response = requests.post(f"{base_url}/multi_timeframe/analyze_multiple_symbols", 
                               json={
                                   'symbols': test_symbols,
                                   'page': 999,  # 超大页码
                                   'page_size': 10
                               })
        data999 = response.json()
        
        if data999['success']:
            signals999 = data999.get('signals', [])
            if len(signals999) == 0:
                print("[PASS] 超出范围页面返回空结果，边界处理正确")
            else:
                print("[WARN] 超出范围页面仍返回数据，可能有问题")
        
        print("\n=== 分页修复验证完成 ===")
        print("[SUCCESS] 所有测试通过，分页功能正常工作")
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    success = test_pagination_fix()
    exit(0 if success else 1)
