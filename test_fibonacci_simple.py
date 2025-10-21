#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试斐波规律研究API
"""

import requests
import json

def test_fibonacci_api():
    """测试斐波规律研究API"""
    base_url = "https://bollinger-bands-web-app-production.up.railway.app"
    
    print("🧪 测试斐波规律研究API...")
    
    # 测试API端点
    api_url = f"{base_url}/fibonacci/api/light-data"
    params = {
        'symbol': 'LIGHT',
        'timeframe': '1h'
    }
    
    try:
        print(f"📡 请求URL: {api_url}")
        print(f"📊 参数: {params}")
        
        response = requests.get(api_url, params=params, timeout=30)
        
        print(f"📈 响应状态码: {response.status_code}")
        print(f"📋 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ JSON解析成功")
                print(f"📊 数据键: {list(data.keys())}")
                if data.get('success'):
                    print(f"🎯 成功: {data.get('count', 0)}条数据, 来源: {data.get('source', 'Unknown')}")
                else:
                    print(f"❌ API错误: {data.get('error', 'Unknown error')}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"📄 响应内容: {response.text[:500]}...")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"📄 响应内容: {response.text[:500]}...")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    print("\n🎯 测试完成！")

if __name__ == "__main__":
    test_fibonacci_api()
