#!/usr/bin/env python3
"""
测试页面访问
"""

import requests
import time

def test_page_access():
    """测试页面访问"""
    print("=== 测试页面访问 ===")
    
    # 等待应用启动
    print("等待应用启动...")
    time.sleep(3)
    
    # 测试主页
    try:
        response = requests.get('http://localhost:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ 主页访问正常")
        else:
            print(f"❌ 主页访问异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 主页访问失败: {e}")
    
    # 测试多时间框架测试页面
    try:
        response = requests.get('http://localhost:5000/test_multi_timeframe.html', timeout=5)
        if response.status_code == 200:
            print("✅ 多时间框架测试页面访问正常")
            print(f"页面大小: {len(response.text)} 字符")
        else:
            print(f"❌ 多时间框架测试页面访问异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 多时间框架测试页面访问失败: {e}")
    
    # 测试健康检查
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查正常: {data['status']}")
        else:
            print(f"❌ 健康检查异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")

if __name__ == "__main__":
    test_page_access()

