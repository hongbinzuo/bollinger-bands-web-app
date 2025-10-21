#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斐波规律研究API
获取LIGHT币种数据用于斐波那契分析
"""

import requests
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
fibonacci_bp = Blueprint('fibonacci', __name__)

def get_light_data_from_bitget():
    """从Bitget获取LIGHT价格数据"""
    try:
        # Bitget API获取K线数据
        url = "https://api.bitget.com/api/spot/v1/market/candles"
        params = {
            'symbol': 'LIGHTUSDT',
            'granularity': '1H',  # 1小时K线
            'limit': 168  # 7天数据
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') == '00000':
            klines = data.get('data', [])
            logger.info(f"从Bitget获取到 {len(klines)} 条LIGHT数据")
            return klines
        else:
            logger.error(f"Bitget API错误: {data.get('msg')}")
            return None
            
    except Exception as e:
        logger.error(f"从Bitget获取LIGHT数据失败: {e}")
        return None

def get_light_data_from_bybit():
    """从Bybit获取LIGHT价格数据"""
    try:
        # Bybit API获取K线数据
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': 'LIGHTUSDT',
            'interval': '60',  # 1小时K线
            'limit': 168  # 7天数据
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('retCode') == 0:
            klines = data.get('result', {}).get('list', [])
            logger.info(f"从Bybit获取到 {len(klines)} 条LIGHT数据")
            return klines
        else:
            logger.error(f"Bybit API错误: {data.get('retMsg')}")
            return None
            
    except Exception as e:
        logger.error(f"从Bybit获取LIGHT数据失败: {e}")
        return None

def convert_bitget_data(klines):
    """转换Bitget数据格式"""
    converted_data = []
    for kline in klines:
        try:
            # Bitget格式: [timestamp, open, high, low, close, volume, quote_volume]
            converted_data.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        except (ValueError, IndexError) as e:
            logger.warning(f"跳过无效数据: {kline}, 错误: {e}")
            continue
    
    return converted_data

def convert_bybit_data(klines):
    """转换Bybit数据格式"""
    converted_data = []
    for kline in klines:
        try:
            # Bybit格式: [timestamp, open, high, low, close, volume, turnover]
            converted_data.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        except (ValueError, IndexError) as e:
            logger.warning(f"跳过无效数据: {kline}, 错误: {e}")
            continue
    
    return converted_data

@fibonacci_bp.route('/api/light-data', methods=['GET'])
def get_light_data():
    """获取LIGHT币种数据API"""
    try:
        logger.info("开始获取LIGHT数据...")
        
        # 首先尝试从Bitget获取
        bitget_data = get_light_data_from_bitget()
        if bitget_data:
            converted_data = convert_bitget_data(bitget_data)
            if converted_data:
                logger.info(f"成功从Bitget获取 {len(converted_data)} 条LIGHT数据")
                return jsonify({
                    'success': True,
                    'data': converted_data,
                    'source': 'Bitget',
                    'count': len(converted_data)
                })
        
        # 如果Bitget失败，尝试Bybit
        logger.info("Bitget获取失败，尝试Bybit...")
        bybit_data = get_light_data_from_bybit()
        if bybit_data:
            converted_data = convert_bybit_data(bybit_data)
            if converted_data:
                logger.info(f"成功从Bybit获取 {len(converted_data)} 条LIGHT数据")
                return jsonify({
                    'success': True,
                    'data': converted_data,
                    'source': 'Bybit',
                    'count': len(converted_data)
                })
        
        # 如果都失败了，返回模拟数据
        logger.warning("所有API都失败，返回模拟数据")
        mock_data = generate_mock_light_data()
        return jsonify({
            'success': True,
            'data': mock_data,
            'source': 'Mock',
            'count': len(mock_data),
            'warning': '使用模拟数据，实际交易请谨慎'
        })
        
    except Exception as e:
        logger.error(f"获取LIGHT数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_mock_light_data():
    """生成模拟LIGHT数据用于演示"""
    import random
    from datetime import datetime, timedelta
    
    mock_data = []
    base_price = 1.8
    current_time = datetime.now() - timedelta(days=7)
    
    for i in range(168):  # 7天 * 24小时
        # 模拟价格波动
        price_change = random.uniform(-0.05, 0.05)  # ±5%波动
        base_price *= (1 + price_change)
        
        # 确保价格在合理范围内
        base_price = max(1.0, min(3.0, base_price))
        
        high = base_price * (1 + random.uniform(0, 0.02))
        low = base_price * (1 - random.uniform(0, 0.02))
        open_price = base_price * (1 + random.uniform(-0.01, 0.01))
        close_price = base_price
        
        mock_data.append({
            'timestamp': int(current_time.timestamp() * 1000),
            'open': round(open_price, 4),
            'high': round(high, 4),
            'low': round(low, 4),
            'close': round(close_price, 4),
            'volume': random.uniform(1000, 10000)
        })
        
        current_time += timedelta(hours=1)
    
    return mock_data

@fibonacci_bp.route('/fibonacci-research', methods=['GET'])
def fibonacci_research_page():
    """斐波规律研究页面"""
    from flask import render_template
    return render_template('fibonacci_research.html')

if __name__ == "__main__":
    # 测试API
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(fibonacci_bp)
    
    with app.test_client() as client:
        response = client.get('/api/light-data')
        print("API响应:", response.get_json())
