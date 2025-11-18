#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多空势能场模型API
基于物理学势能场理论的多空力量分析模型
"""

import logging
import requests
import time
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
momentum_field_bp = Blueprint('momentum_field', __name__, url_prefix='/momentum-field')

class MomentumFieldAnalyzer:
    """多空势能场分析器"""
    
    def __init__(self):
        self.supported_symbols = ['HUSDT.P', 'KGEN', 'LA', 'F', 'BANK', 'H']
        self.timeframes = ['5m', '15m', '1h', '4h']
        
    def get_bybit_klines(self, symbol, interval, limit):
        """从Bybit获取K线数据"""
        try:
            # 转换时间周期
            interval_map = {
                '5m': '5',
                '15m': '15', 
                '1h': '60',
                '4h': '240'
            }
            
            bybit_interval = interval_map.get(interval, '60')
            url = f"https://api.bybit.com/v5/market/kline"
            
            params = {
                'category': 'linear',
                'symbol': symbol,
                'interval': bybit_interval,
                'limit': min(limit, 1000)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') == 0:
                klines = data['result']['list']
                return self.convert_bybit_data(klines)
            else:
                logger.error(f"Bybit API错误: {data.get('retMsg', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Bybit获取 {symbol} K线数据失败: {e}")
            return None
    
    def get_gate_klines(self, symbol, interval, limit):
        """从Gate.io获取K线数据"""
        try:
            # 转换时间周期
            interval_map = {
                '5m': '300',
                '15m': '900',
                '1h': '3600', 
                '4h': '14400'
            }
            
            gate_interval = interval_map.get(interval, '3600')
            url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
            
            params = {
                'currency_pair': symbol,
                'interval': gate_interval,
                'limit': min(limit, 1000)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data:
                return self.convert_gate_data(data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Gate.io获取 {symbol} K线数据失败: {e}")
            return None
    
    def get_bitget_klines(self, symbol, interval, limit):
        """从Bitget获取K线数据"""
        try:
            # 转换时间周期
            interval_map = {
                '5m': '5m',
                '15m': '15m',
                '1h': '1H',
                '4h': '4H'
            }
            
            bitget_interval = interval_map.get(interval, '1H')
            url = f"https://api.bitget.com/api/v2/spot/market/candles"
            
            params = {
                'symbol': symbol,
                'granularity': bitget_interval,
                'limit': min(limit, 1000)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '00000':
                return self.convert_bitget_data(data['data'])
            else:
                logger.error(f"Bitget API错误: {data.get('msg', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Bitget获取 {symbol} K线数据失败: {e}")
            return None
    
    def convert_bybit_data(self, klines):
        """转换Bybit数据格式"""
        converted_data = []
        for kline in klines:
            converted_data.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        return converted_data
    
    def convert_gate_data(self, klines):
        """转换Gate.io数据格式"""
        converted_data = []
        for kline in klines:
            converted_data.append({
                'timestamp': int(kline['t']),
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v'])
            })
        return converted_data
    
    def convert_bitget_data(self, klines):
        """转换Bitget数据格式"""
        converted_data = []
        for kline in klines:
            converted_data.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        return converted_data
    
    def generate_mock_data(self, symbol, timeframe):
        """生成模拟数据用于测试"""
        logger.info(f"生成 {symbol} 的模拟数据 (时间周期: {timeframe})")
        
        data = []
        now = int(time.time() * 1000)
        interval_map = {
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000
        }
        
        interval = interval_map.get(timeframe, 60 * 60 * 1000)
        limit = 500
        
        # 根据币种设置不同的起始价格
        base_prices = {
            'HUSDT.P': 100.0,
            'H': 0.1,
            'KGEN': 0.5,
            'LA': 0.1,
            'F': 0.05,
            'BANK': 0.02
        }
        
        base_price = base_prices.get(symbol, 1.0)
        price = base_price
        
        for i in range(limit):
            timestamp = now - (limit - i) * interval
            
            # 生成价格变化 - 增加波动性以便产生更多信号
            change = np.random.normal(0, 0.03)  # 3%标准差的正态分布
            price = price * (1 + change)
            
            # 确保价格不会变成负数
            if price <= 0:
                price = base_price
            
            # 生成OHLC数据
            open_price = price * (1 + np.random.normal(0, 0.005))
            close_price = price
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.01)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.01)))
            
            data.append({
                'timestamp': timestamp,
                'open': round(open_price, 6),
                'high': round(high_price, 6),
                'low': round(low_price, 6),
                'close': round(close_price, 6),
                'volume': np.random.uniform(100000, 1000000)
            })
        
        return data

# 创建分析器实例
analyzer = MomentumFieldAnalyzer()

@momentum_field_bp.route('/api/data', methods=['GET'])
def get_momentum_field_data():
    """获取势能场分析数据"""
    try:
        symbol = request.args.get('symbol', 'HUSDT.P')
        timeframe = request.args.get('timeframe', '5m')
        
        logger.info(f"开始获取{symbol}势能场数据 (时间周期: {timeframe})...")
        
        # 设置限制
        limit_map = {
            '5m': 500,
            '15m': 300,
            '1h': 200,
            '4h': 100
        }
        
        limit = limit_map.get(timeframe, 200)
        
        # 尝试从不同交易所获取数据
        exchanges = [
            ('Bybit', analyzer.get_bybit_klines),
            ('Gate.io', analyzer.get_gate_klines),
            ('Bitget', analyzer.get_bitget_klines)
        ]
        
        best_data = None
        best_source = None
        best_count = 0
        
        for exchange_name, get_func in exchanges:
            try:
                logger.info(f"尝试从{exchange_name}获取数据...")
                raw_data = get_func(symbol, timeframe, limit)
                if raw_data and len(raw_data) > best_count:
                    best_data = raw_data
                    best_source = exchange_name
                    best_count = len(raw_data)
                    logger.info(f"{exchange_name}获取到 {len(raw_data)} 条数据")
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
        
        # 如果所有API都失败，返回模拟数据
        logger.warning(f"所有API都失败，返回{symbol}模拟数据")
        mock_data = analyzer.generate_mock_data(symbol, timeframe)
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
        logger.error(f"获取势能场数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@momentum_field_bp.route('/api/analyze', methods=['POST'])
def analyze_momentum_field():
    """分析势能场模型"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'HUSDT.P')
        timeframe = data.get('timeframe', '5m')
        alpha = data.get('alpha', 0.3)
        beta = data.get('beta', 0.7)
        
        logger.info(f"开始分析{symbol}势能场模型 (α={alpha}, β={beta})...")
        
        # 获取价格数据
        price_data = analyzer.get_bybit_klines(symbol, timeframe, 500)
        if not price_data:
            price_data = analyzer.generate_mock_data(symbol, timeframe)
        
        # 计算势能场
        results = calculate_momentum_field_analysis(price_data, alpha, beta)
        
        return jsonify({
            'success': True,
            'results': results,
            'symbol': symbol,
            'timeframe': timeframe
        })
        
    except Exception as e:
        logger.error(f"势能场分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def calculate_momentum_field_analysis(price_data, alpha, beta):
    """计算势能场分析结果"""
    try:
        # 转换为DataFrame便于计算
        df = pd.DataFrame(price_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 1. 识别关键中枢
        key_levels = identify_key_levels(df)
        
        # 2. 计算势能函数
        potential_energy = []
        for i in range(len(df)):
            current_price = df.iloc[i]['close']
            
            # 计算趋势动能
            trend_momentum = calculate_trend_momentum(df, i)
            
            # 计算关键位引力
            key_level_attraction = calculate_key_level_attraction(current_price, key_levels)
            
            # 势能函数 Φ(P,t) = α * 趋势动能 + β * 关键位引力
            energy = alpha * trend_momentum + beta * key_level_attraction
            
            potential_energy.append({
                'timestamp': df.iloc[i]['timestamp'].timestamp() * 1000,
                'price': current_price,
                'potential_energy': energy,
                'trend_momentum': trend_momentum,
                'key_level_attraction': key_level_attraction
            })
        
        # 3. 计算势能梯度
        gradients = []
        for i in range(1, len(potential_energy)):
            gradient = potential_energy[i]['potential_energy'] - potential_energy[i-1]['potential_energy']
            gradients.append({
                'timestamp': potential_energy[i]['timestamp'],
                'gradient': gradient
            })
        
        # 4. 生成交易信号
        threshold = calculate_gradient_threshold(gradients)
        signals = generate_trading_signals(gradients, threshold)
        
        # 5. 计算统计信息
        statistics = calculate_statistics(potential_energy, gradients, signals)
        
        return {
            'potential_energy': potential_energy,
            'gradients': gradients,
            'key_levels': key_levels,
            'signals': signals,
            'statistics': statistics
        }
        
    except Exception as e:
        logger.error(f"势能场计算失败: {e}")
        return None

def identify_key_levels(df):
    """识别关键中枢"""
    key_levels = []
    window_size = min(20, len(df) // 10)
    
    for i in range(window_size, len(df) - window_size):
        current_price = df.iloc[i]['close']
        is_key_level = True
        
        # 检查是否为局部极值
        for j in range(i - window_size, i + window_size + 1):
            if j != i and abs(df.iloc[j]['close'] - current_price) < current_price * 0.01:
                is_key_level = False
                break
        
        if is_key_level:
            strength = calculate_key_level_strength(df, i, window_size)
            key_levels.append({
                'price': current_price,
                'timestamp': df.iloc[i]['timestamp'].timestamp() * 1000,
                'strength': strength
            })
    
    return key_levels

def calculate_trend_momentum(df, index):
    """计算趋势动能"""
    if index < 5:
        return 0
    
    current_price = df.iloc[index]['close']
    past_price = df.iloc[index - 5]['close']
    price_change = (current_price - past_price) / past_price
    
    # 考虑成交量权重
    volume_weight = df.iloc[index]['volume']
    avg_volume = df.iloc[max(0, index-10):index+1]['volume'].mean()
    volume_ratio = volume_weight / avg_volume if avg_volume > 0 else 1
    
    return price_change * volume_ratio

def calculate_key_level_attraction(current_price, key_levels):
    """计算关键位引力"""
    total_attraction = 0
    
    for key_level in key_levels:
        distance = abs(current_price - key_level['price']) / key_level['price']
        attraction = key_level['strength'] / (1 + distance * 10)
        total_attraction += attraction
    
    return total_attraction

def calculate_gradient_threshold(gradients):
    """计算势能梯度阈值"""
    gradient_values = [abs(g['gradient']) for g in gradients]
    mean = np.mean(gradient_values)
    std = np.std(gradient_values)
    
    # 降低阈值，使其更容易产生信号
    return mean + 0.5 * std  # 从2倍标准差降低到0.5倍

def generate_trading_signals(gradients, threshold):
    """生成交易信号"""
    signals = []
    
    for gradient in gradients:
        grad_value = gradient['gradient']
        
        if grad_value > threshold:
            signals.append({
                'timestamp': gradient['timestamp'],
                'type': 'BUY',
                'strength': grad_value / threshold,
                'signal': '多头突破'
            })
        elif grad_value < -threshold:
            signals.append({
                'timestamp': gradient['timestamp'],
                'type': 'SELL',
                'strength': abs(grad_value) / threshold,
                'signal': '空头突破'
            })
    
    return signals

def calculate_key_level_strength(df, index, window_size):
    """计算关键位强度"""
    start = max(0, index - window_size)
    end = min(len(df), index + window_size + 1)
    volume_sum = df.iloc[start:end]['volume'].sum()
    count = end - start
    
    return volume_sum / count if count > 0 else 1

def calculate_statistics(potential_energy, gradients, signals):
    """计算统计信息"""
    energies = [p['potential_energy'] for p in potential_energy]
    grad_values = [g['gradient'] for g in gradients]
    
    return {
        'avg_potential_energy': np.mean(energies),
        'max_potential_energy': np.max(energies),
        'min_potential_energy': np.min(energies),
        'avg_gradient': np.mean(grad_values),
        'max_gradient': np.max(grad_values),
        'min_gradient': np.min(grad_values),
        'signal_count': len(signals),
        'buy_signals': len([s for s in signals if s['type'] == 'BUY']),
        'sell_signals': len([s for s in signals if s['type'] == 'SELL'])
    }
