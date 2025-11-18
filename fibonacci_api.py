#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斐波规律研究API
获取LIGHT币种数据用于斐波那契分析
"""

import requests
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
fibonacci_bp = Blueprint('fibonacci', __name__, url_prefix='/fibonacci')

def get_bitget_klines(symbol, interval, limit):
    """从Bitget获取K线数据"""
    try:
        # 时间周期映射
        granularity_map = {
            '15': '15m',
            '60': '1H', 
            '240': '4H',
            '1440': '1D'
        }
        
        granularity = granularity_map.get(interval, '1H')
        
        url = "https://api.bitget.com/api/spot/v1/market/candles"
        params = {
            'symbol': symbol,
            'granularity': granularity,
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') == '00000':
            klines = data.get('data', [])
            logger.info(f"从Bitget获取到 {len(klines)} 条{symbol}数据")
            return klines
        else:
            logger.error(f"Bitget API错误: {data.get('msg')}")
            return None
            
    except Exception as e:
        logger.error(f"从Bitget获取{symbol}数据失败: {e}")
        return None

def get_bybit_klines(symbol, interval, limit):
    """从Bybit获取K线数据"""
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('retCode') == 0:
            klines = data.get('result', {}).get('list', [])
            logger.info(f"从Bybit获取到 {len(klines)} 条{symbol}数据")
            return klines
        else:
            logger.error(f"Bybit API错误: {data.get('retMsg')}")
            return None
            
    except Exception as e:
        logger.error(f"从Bybit获取{symbol}数据失败: {e}")
        return None

def get_gate_klines(symbol, interval, limit):
    """从Gate.io获取K线数据"""
    try:
        # Gate.io时间周期映射
        gate_interval_map = {
            '15': '15m',
            '60': '1h',
            '240': '4h', 
            '1440': '1d',
            '10080': '1w'
        }
        
        gate_interval = gate_interval_map.get(interval, '1h')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': symbol,
            'interval': gate_interval,
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            logger.info(f"从Gate.io获取到 {len(data)} 条{symbol}数据")
            return data
        else:
            logger.error(f"Gate.io API错误: {data}")
            return None
            
    except Exception as e:
        logger.error(f"从Gate.io获取{symbol}数据失败: {e}")
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

def convert_gate_data(klines):
    """转换Gate.io数据格式"""
    converted_data = []
    for kline in klines:
        try:
            # Gate.io格式: [timestamp, volume, close, high, low, open]
            converted_data.append({
                'timestamp': int(kline[0]) * 1000,  # Gate.io返回秒，需要转毫秒
                'open': float(kline[5]),
                'high': float(kline[3]),
                'low': float(kline[4]),
                'close': float(kline[2]),
                'volume': float(kline[1])
            })
        except (ValueError, IndexError) as e:
            logger.warning(f"跳过无效数据: {kline}, 错误: {e}")
            continue
    
    return converted_data

@fibonacci_bp.route('/api/light-data', methods=['GET'])
def get_light_data():
    """获取币种数据API"""
    try:
        symbol = request.args.get('symbol', 'LIGHT')
        timeframe = request.args.get('timeframe', '1h')
        
        logger.info(f"开始获取{symbol}数据 (时间周期: {timeframe})...")
        
        # 根据时间周期设置不同的参数
        interval_map = {
            '15m': '15',
            '1h': '60', 
            '4h': '240',
            '1d': '1440',
            '1w': '10080'  # 周线
        }
        
        limit_map = {
            '15m': 672,   # 7天
            '1h': 168,    # 7天
            '4h': 168,    # 28天
            '1d': 365,    # 1年
            '1w': 104     # 2年
        }
        
        interval = interval_map.get(timeframe, '60')
        limit = limit_map.get(timeframe, 168)
        
        # 构建交易对符号
        symbol_pair = f"{symbol}USDT"
        
        # 尝试从多个交易所获取数据，选择历史最长的
        exchanges = [
            ('Bitget', get_bitget_klines, convert_bitget_data),
            ('Bybit', get_bybit_klines, convert_bybit_data),
            ('Gate', get_gate_klines, convert_gate_data)
        ]
        
        best_data = None
        best_source = None
        best_count = 0
        
        for exchange_name, get_func, convert_func in exchanges:
            try:
                logger.info(f"尝试从{exchange_name}获取数据...")
                raw_data = get_func(symbol_pair, interval, limit)
                if raw_data:
                    converted_data = convert_func(raw_data)
                    if converted_data and len(converted_data) > best_count:
                        best_data = converted_data
                        best_source = exchange_name
                        best_count = len(converted_data)
                        logger.info(f"{exchange_name}获取到 {len(converted_data)} 条数据")
            except Exception as e:
                logger.warning(f"{exchange_name}获取失败: {e}")
                continue
        
        if best_data:
            logger.info(f"选择{best_source}作为数据源，共{best_count}条数据")
            return jsonify({
                'success': True,
                'data': best_data,
                'source': best_source,
                'symbol': symbol,
                'timeframe': timeframe,
                'count': best_count
            })
        
        # 如果都失败了，返回模拟数据
        logger.warning(f"所有API都失败，返回{symbol}模拟数据")
        mock_data = generate_mock_data(symbol, timeframe)
        return jsonify({
            'success': True,
            'data': mock_data,
            'source': 'Mock',
            'symbol': symbol,
            'timeframe': timeframe,
            'count': len(mock_data),
            'warning': '使用模拟数据，实际交易请谨慎'
        })
        
    except Exception as e:
        logger.error(f"获取{symbol}数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_mock_data(symbol, timeframe):
    """生成模拟数据用于演示"""
    import random
    from datetime import datetime, timedelta
    
    # 根据币种设置不同的基础价格
    base_prices = {
        'LIGHT': 1.8, 'KGEN': 0.5, 'XPIN': 2.1, 'BLESS': 0.8, 'BAS': 0.3,
        'RIVER': 1.2, 'BANK': 0.4, 'ALCH': 0.6, 'STO': 1.5, 'USELESS': 0.1,
        'AIA': 0.7, 'RATS': 0.2, 'SKYAI': 1.0, 'H': 0.9, 'VFY': 0.3
    }
    
    # 根据时间周期设置数据点数和时间间隔
    timeframe_config = {
        '15m': {'count': 672, 'interval': timedelta(minutes=15)},   # 7天
        '1h': {'count': 168, 'interval': timedelta(hours=1)},       # 7天
        '4h': {'count': 168, 'interval': timedelta(hours=4)},       # 28天
        '1d': {'count': 365, 'interval': timedelta(days=1)}         # 1年
    }
    
    config = timeframe_config.get(timeframe, timeframe_config['1h'])
    base_price = base_prices.get(symbol, 1.0)
    
    mock_data = []
    current_time = datetime.now() - config['interval'] * config['count']
    
    for i in range(config['count']):
        # 模拟价格波动
        price_change = random.uniform(-0.05, 0.05)  # ±5%波动
        base_price *= (1 + price_change)
        
        # 确保价格在合理范围内
        base_price = max(0.01, min(10.0, base_price))
        
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
        
        current_time += config['interval']
    
    return mock_data

@fibonacci_bp.route('/research', methods=['GET'])
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
