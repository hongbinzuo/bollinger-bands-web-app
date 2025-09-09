#!/usr/bin/env python3
"""
测试前20个币种获取功能
"""

import requests
import json

def test_get_top_20_symbols():
    """测试获取前20个币种"""
    print("=== 测试获取前20个币种 ===")
    try:
        response = requests.get('http://localhost:5000/multi_timeframe/get_top_symbols', timeout=15)
        if response.status_code == 200:
            data = response.json()
            print(f"成功获取 {data['count']} 个币种")
            print(f"数据源: {data['source']}")
            print("前20个币种:")
            for i, symbol in enumerate(data['symbols'], 1):
                print(f"  {i:2d}. {symbol}")
            
            # 检查是否包含稳定币
            stablecoins = ['USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'DAIUSDT', 'FDUSDUSDT']
            found_stablecoins = [s for s in data['symbols'] if s in stablecoins]
            if found_stablecoins:
                print(f"\n⚠️  发现稳定币: {found_stablecoins}")
            else:
                print("\n✅ 已成功排除稳定币")
            
            return data['symbols']
        else:
            print(f"HTTP错误: {response.status_code}")
            return []
    except Exception as e:
        print(f"获取币种列表失败: {e}")
        return []

if __name__ == "__main__":
    test_get_top_20_symbols()

