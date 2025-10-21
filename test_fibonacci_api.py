#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试斐波规律研究API
"""

import requests
import json

def test_fibonacci_api():
    """测试斐波规律研究API"""
    base_url = "http://localhost:5000"
    
    print("🧪 测试斐波规律研究API...")
    
    # 测试不同币种和时间周期
    test_cases = [
        {'symbol': 'LIGHT', 'timeframe': '1h'},
        {'symbol': 'KGEN', 'timeframe': '4h'},
        {'symbol': 'XPIN', 'timeframe': '1d'},
        {'symbol': 'BLESS', 'timeframe': '15m'}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 测试 {i}: {test_case['symbol']} ({test_case['timeframe']})")
        
        try:
            url = f"{base_url}/api/light-data"
            params = {
                'symbol': test_case['symbol'],
                'timeframe': test_case['timeframe']
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ 成功: {data.get('count', 0)}条数据, 来源: {data.get('source', 'Unknown')}")
                    if data.get('warning'):
                        print(f"⚠️  警告: {data['warning']}")
                else:
                    print(f"❌ 失败: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
    
    print("\n🎯 测试完成！")

if __name__ == "__main__":
    test_fibonacci_api()
