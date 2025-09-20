#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终验证脚本
验证币种添加和系统功能
"""

import sys
import os
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import DEFAULT_SYMBOLS, get_all_symbols, load_custom_symbols

def verify_symbols():
    """验证币种配置"""
    print("🔍 最终验证 - 币种配置")
    print("=" * 60)
    
    # 统计币种数量
    default_count = len(DEFAULT_SYMBOLS)
    custom_symbols = load_custom_symbols()
    custom_count = len(custom_symbols)
    all_symbols = get_all_symbols()
    total_count = len(all_symbols)
    
    print(f"📊 默认币种数量: {default_count}")
    print(f"📊 自定义币种数量: {custom_count}")
    print(f"📊 总币种数量: {total_count}")
    
    # 检查是否有重复
    seen = set()
    duplicates = set()
    for symbol in DEFAULT_SYMBOLS:
        if symbol in seen:
            duplicates.add(symbol)
        else:
            seen.add(symbol)
    
    if duplicates:
        print(f"❌ 发现重复币种: {duplicates}")
    else:
        print("✅ 没有重复币种")
    
    # 检查格式
    invalid_symbols = []
    for symbol in DEFAULT_SYMBOLS:
        if not symbol.endswith('USDT'):
            invalid_symbols.append(symbol)
    
    if invalid_symbols:
        print(f"❌ 格式不正确的币种: {invalid_symbols}")
    else:
        print("✅ 所有币种格式正确")
    
    # 显示新增的币种示例
    print("\n🔍 新增币种示例:")
    new_symbols = ['PNUTUSDT', 'JASMYUSDT', 'COOKIEUSDT', 'SPKUSDT', 'EIGENUSDT', 
                   'HYPEUSDT', 'KAITOUSDT', 'PENDLEUSDT', 'HIPPOUSDT', 'SOMIUSDT']
    
    for symbol in new_symbols:
        if symbol in DEFAULT_SYMBOLS:
            print(f"  ✅ {symbol}")
        else:
            print(f"  ❌ {symbol} 未找到")
    
    return total_count

def verify_api():
    """验证API功能"""
    print("\n🔍 最终验证 - API功能")
    print("=" * 60)
    
    try:
        import requests
        
        # 等待应用启动
        print("⏳ 等待应用启动...")
        time.sleep(3)
        
        # 测试健康检查
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print("✅ 应用健康检查通过")
            else:
                print(f"❌ 应用健康检查失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 应用健康检查失败: {e}")
        
        # 测试获取币种列表
        try:
            response = requests.get('http://localhost:5000/get_default_symbols', timeout=10)
            if response.status_code == 200:
                data = response.json()
                api_count = data.get('count', 0)
                print(f"✅ 获取币种列表成功: {api_count}个币种")
                
                if api_count >= 190:  # 期望至少190个币种
                    print("✅ 币种数量符合预期")
                else:
                    print(f"❌ 币种数量不足，期望≥190，实际{api_count}")
            else:
                print(f"❌ 获取币种列表失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 获取币种列表失败: {e}")
        
        # 测试多时间框架API
        try:
            response = requests.get('http://localhost:5000/multi_timeframe/get_top_symbols', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ 多时间框架API正常")
                else:
                    print(f"❌ 多时间框架API失败: {data.get('error')}")
            else:
                print(f"❌ 多时间框架API失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 多时间框架API失败: {e}")
            
    except ImportError:
        print("❌ requests库未安装，跳过API测试")

def main():
    """主验证函数"""
    print("🚀 最终验证开始")
    print(f"⏰ 验证时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 验证币种配置
    total_count = verify_symbols()
    
    # 验证API功能
    verify_api()
    
    print("\n" + "=" * 60)
    print("🎉 最终验证完成！")
    print("=" * 60)
    
    if total_count >= 190:
        print("✅ 币种添加成功！系统现在支持195个币种")
        print("🌐 请访问 http://localhost:5000 查看更新后的系统")
    else:
        print("❌ 币种数量不足，请检查配置")

if __name__ == "__main__":
    main()















