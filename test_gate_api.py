#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GATE.IO API连接
"""

import requests
import json

def test_gate_api():
    """测试GATE.IO API"""
    print("测试GATE.IO API连接...")
    
    try:
        # 测试获取交易对数据
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=10)
        
        print(f"API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"获取到{len(data)}个交易对")
            
            # 筛选USDT交易对
            usdt_pairs = [t for t in data if t['currency_pair'].endswith('_USDT')]
            print(f"USDT交易对数量: {len(usdt_pairs)}")
            
            # 按交易量排序
            usdt_pairs.sort(key=lambda x: float(x.get('base_volume', 0)), reverse=True)
            
            print("前10个USDT交易对:")
            for i, pair in enumerate(usdt_pairs[:10]):
                print(f"  {i+1}. {pair['currency_pair']} - 交易量: {pair.get('base_volume', 'N/A')}")
            
            return [pair['currency_pair'] for pair in usdt_pairs[:50]]
        else:
            print("API请求失败")
            return []
            
    except Exception as e:
        print(f"连接失败: {e}")
        return []

def test_historical_data(symbol):
    """测试获取历史数据"""
    print(f"\n测试获取{symbol}历史数据...")
    
    try:
        # 获取最近7天的日线数据
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': symbol,
            'interval': '1d',
            'from': 1700000000,  # 2023年11月的时间戳
            'to': 1735689600     # 2025年1月的时间戳
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"获取到{len(data)}条K线数据")
            
            if data:
                # 显示最新数据
                latest = data[-1]
                print(f"最新数据: 时间={latest[0]}, 开盘={latest[5]}, 收盘={latest[2]}, 最高={latest[3]}, 最低={latest[4]}")
                return True
            else:
                print("无历史数据")
                return False
        else:
            print(f"获取历史数据失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"获取历史数据失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("GATE.IO API测试")
    print("=" * 60)
    
    # 测试API连接
    symbols = test_gate_api()
    
    if symbols:
        print(f"\n成功获取{len(symbols)}个币种")
        
        # 测试前3个币种的历史数据
        for symbol in symbols[:3]:
            test_historical_data(symbol)
    else:
        print("无法获取币种列表")

if __name__ == "__main__":
    main()
