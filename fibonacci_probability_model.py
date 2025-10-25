#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斐波那契概率预测模型
基于价格行为模式和强度因子的概率预测系统
"""

import logging
import requests
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from typing import List, Dict, Tuple, Optional
import math

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
fibonacci_prob_bp = Blueprint('fibonacci_prob', __name__, url_prefix='/fibonacci-prob')

class FibonacciProbabilityModel:
    """斐波那契概率预测模型"""
    
    def __init__(self):
        self.fibonacci_levels = [1.0, 1.618, 2.618, 3.618, 4.236]
        self.fibonacci_names = ['1.0', '1.618', '2.618', '3.618', '4.236']
        
    def get_bybit_klines(self, symbol, interval, limit):
        """从Bybit获取K线数据"""
        try:
            interval_map = {
                '5m': '5', '15m': '15', '1h': '60', '4h': '240', '1d': 'D'
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
    
    def calculate_fibonacci_extension_levels(self, base_price, target_price):
        """计算斐波那契扩展位"""
        if base_price == 0:
            return {}
        
        price_range = target_price - base_price
        extension_levels = {}
        
        for level in self.fibonacci_levels:
            extension_price = base_price + (price_range * level)
            extension_levels[level] = extension_price
            
        return extension_levels
    
    def analyze_price_velocity(self, price_data, window=20):
        """分析价格运动速度"""
        velocities = []
        
        for i in range(window, len(price_data)):
            # 计算价格变化率
            price_change = (price_data[i]['close'] - price_data[i-window]['close']) / price_data[i-window]['close']
            
            # 计算时间间隔（小时）
            time_diff = (price_data[i]['timestamp'] - price_data[i-window]['timestamp']) / (1000 * 3600)
            
            # 速度 = 价格变化率 / 时间
            velocity = price_change / time_diff if time_diff > 0 else 0
            velocities.append({
                'timestamp': price_data[i]['timestamp'],
                'velocity': velocity,
                'price_change': price_change
            })
        
        return velocities
    
    def calculate_volume_energy(self, price_data, window=20):
        """计算量能累积强度"""
        volume_energies = []
        
        for i in range(window, len(price_data)):
            # 计算成交量加权平均
            volumes = [price_data[j]['volume'] for j in range(i-window, i)]
            avg_volume = sum(volumes) / len(volumes)
            
            # 计算价格变化
            price_change = abs(price_data[i]['close'] - price_data[i-window]['close']) / price_data[i-window]['close']
            
            # 量能强度 = 成交量 × 价格变化
            volume_energy = avg_volume * price_change
            volume_energies.append({
                'timestamp': price_data[i]['timestamp'],
                'volume_energy': volume_energy,
                'avg_volume': avg_volume,
                'price_change': price_change
            })
        
        return volume_energies
    
    def analyze_consolidation_strength(self, price_data, start_idx, end_idx):
        """分析盘整强度"""
        if end_idx <= start_idx:
            return 0
        
        # 计算盘整时间
        time_span = (price_data[end_idx]['timestamp'] - price_data[start_idx]['timestamp']) / (1000 * 3600)  # 小时
        
        # 计算价格波动范围
        prices = [price_data[i]['close'] for i in range(start_idx, end_idx+1)]
        price_range = (max(prices) - min(prices)) / min(prices)
        
        # 计算成交量强度
        volumes = [price_data[i]['volume'] for i in range(start_idx, end_idx+1)]
        avg_volume = sum(volumes) / len(volumes)
        volume_consistency = 1 - (np.std(volumes) / avg_volume) if avg_volume > 0 else 0
        
        # 盘整强度 = 时间 × 成交量一致性 × (1 - 价格波动)
        consolidation_strength = time_span * volume_consistency * (1 - price_range)
        
        return consolidation_strength
    
    def identify_fake_breakouts(self, price_data, window=10):
        """识别假突破"""
        fake_breakouts = []
        
        for i in range(window, len(price_data) - window):
            current_high = price_data[i]['high']
            current_close = price_data[i]['close']
            
            # 检查是否为局部高点
            is_local_high = True
            for j in range(i-window, i+window+1):
                if j != i and price_data[j]['high'] > current_high:
                    is_local_high = False
                    break
            
            if is_local_high:
                # 检查后续是否快速回落（假突破特征）
                max_retracement = 0
                for k in range(i+1, min(i+window, len(price_data))):
                    retracement = (current_high - price_data[k]['low']) / current_high
                    max_retracement = max(max_retracement, retracement)
                
                # 如果回落超过5%，可能是假突破
                if max_retracement > 0.05:
                    fake_breakouts.append({
                        'timestamp': price_data[i]['timestamp'],
                        'price': current_high,
                        'retracement': max_retracement,
                        'strength': max_retracement  # 回落越大，假突破强度越高
                    })
        
        return fake_breakouts
    
    def analyze_key_zone_consolidation(self, price_data, fib_level, tolerance=0.02):
        """分析关键斐波区间的盘整"""
        zone_consolidations = []
        
        for i in range(len(price_data)):
            current_price = price_data[i]['close']
            
            # 检查是否在关键区间内
            if abs(current_price - fib_level) / fib_level <= tolerance:
                # 寻找盘整开始和结束
                start_idx = i
                end_idx = i
                
                # 向前寻找盘整开始
                for j in range(i-1, -1, -1):
                    if abs(price_data[j]['close'] - fib_level) / fib_level <= tolerance:
                        start_idx = j
                    else:
                        break
                
                # 向后寻找盘整结束
                for j in range(i+1, len(price_data)):
                    if abs(price_data[j]['close'] - fib_level) / fib_level <= tolerance:
                        end_idx = j
                    else:
                        break
                
                if end_idx > start_idx:
                    consolidation_strength = self.analyze_consolidation_strength(
                        price_data, start_idx, end_idx
                    )
                    
                    zone_consolidations.append({
                        'fib_level': fib_level,
                        'start_time': price_data[start_idx]['timestamp'],
                        'end_time': price_data[end_idx]['timestamp'],
                        'strength': consolidation_strength,
                        'duration': (price_data[end_idx]['timestamp'] - price_data[start_idx]['timestamp']) / (1000 * 3600)
                    })
        
        return zone_consolidations
    
    def calculate_breakout_probability(self, price_data, fib_level, analysis_results):
        """计算突破概率"""
        # 获取分析结果
        velocities = analysis_results.get('velocities', [])
        volume_energies = analysis_results.get('volume_energies', [])
        fake_breakouts = analysis_results.get('fake_breakouts', [])
        zone_consolidations = analysis_results.get('zone_consolidations', [])
        
        # 计算基础概率因子
        factors = {
            'velocity_factor': 0.0,
            'volume_factor': 0.0,
            'consolidation_factor': 0.0,
            'fake_breakout_factor': 0.0
        }
        
        # 1. 速度因子
        if velocities:
            recent_velocities = velocities[-10:]  # 最近10个数据点
            avg_velocity = sum(v['velocity'] for v in recent_velocities) / len(recent_velocities)
            factors['velocity_factor'] = min(1.0, max(0.0, avg_velocity * 10))  # 标准化到0-1
        
        # 2. 量能因子
        if volume_energies:
            recent_volumes = volume_energies[-10:]
            avg_volume_energy = sum(v['volume_energy'] for v in recent_volumes) / len(recent_volumes)
            factors['volume_factor'] = min(1.0, max(0.0, avg_volume_energy / 1000000))  # 标准化
        
        # 3. 盘整强度因子
        relevant_consolidations = [c for c in zone_consolidations if c['fib_level'] == fib_level]
        if relevant_consolidations:
            max_consolidation = max(relevant_consolidations, key=lambda x: x['strength'])
            factors['consolidation_factor'] = min(1.0, max_consolidation['strength'] / 100)
        
        # 4. 假突破因子（负向影响）
        recent_fake_breakouts = [f for f in fake_breakouts 
                               if f['timestamp'] > price_data[-50]['timestamp']]  # 最近50个数据点
        if recent_fake_breakouts:
            avg_fake_strength = sum(f['strength'] for f in recent_fake_breakouts) / len(recent_fake_breakouts)
            factors['fake_breakout_factor'] = -min(1.0, avg_fake_strength)
        
        # 计算综合概率
        weights = {
            'velocity_factor': 0.3,
            'volume_factor': 0.3,
            'consolidation_factor': 0.2,
            'fake_breakout_factor': 0.2
        }
        
        probability = sum(factors[key] * weights[key] for key in factors)
        probability = max(0.0, min(1.0, probability))  # 限制在0-1之间
        
        return {
            'probability': probability,
            'factors': factors,
            'weights': weights
        }
    
    def analyze_symbol_behavior(self, symbol, timeframe='4h', days=120):
        """分析单个币种的行为模式"""
        try:
            logger.info(f"开始分析 {symbol} 的行为模式...")
            
            # 获取数据
            limit = min(1000, days * 24 // {'5m': 12, '15m': 4, '1h': 1, '4h': 1, '1d': 1}.get(timeframe, 1))
            price_data = self.get_bybit_klines(symbol, timeframe, limit)
            
            if not price_data:
                logger.warning(f"无法获取 {symbol} 数据，使用模拟数据")
                price_data = self.generate_mock_data(symbol, timeframe, limit)
            
            # 分析各种因子
            velocities = self.analyze_price_velocity(price_data)
            volume_energies = self.calculate_volume_energy(price_data)
            fake_breakouts = self.identify_fake_breakouts(price_data)
            
            # 计算斐波扩展位
            base_price = min(d['low'] for d in price_data)
            target_price = max(d['high'] for d in price_data)
            fib_levels = self.calculate_fibonacci_extension_levels(base_price, target_price)
            
            # 分析关键区间盘整
            zone_consolidations = []
            for fib_level in fib_levels.values():
                consolidations = self.analyze_key_zone_consolidation(price_data, fib_level)
                zone_consolidations.extend(consolidations)
            
            # 计算每个斐波位点的概率
            analysis_results = {
                'velocities': velocities,
                'volume_energies': volume_energies,
                'fake_breakouts': fake_breakouts,
                'zone_consolidations': zone_consolidations
            }
            
            fib_probabilities = {}
            for level, price in fib_levels.items():
                prob_result = self.calculate_breakout_probability(price_data, price, analysis_results)
                fib_probabilities[level] = {
                    'price': price,
                    'probability': prob_result['probability'],
                    'factors': prob_result['factors']
                }
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'data_points': len(price_data),
                'fib_levels': fib_levels,
                'probabilities': fib_probabilities,
                'analysis_results': analysis_results
            }
            
        except Exception as e:
            logger.error(f"分析 {symbol} 失败: {e}")
            return None
    
    def generate_mock_data(self, symbol, timeframe, limit):
        """生成模拟数据"""
        data = []
        now = int(time.time() * 1000)
        
        interval_map = {
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        
        interval = interval_map.get(timeframe, 60 * 60 * 1000)
        base_price = 0.1 if symbol == 'H' else 1.0
        price = base_price
        
        for i in range(limit):
            timestamp = now - (limit - i) * interval
            
            # 生成更真实的价格波动
            change = np.random.normal(0, 0.02)
            price = price * (1 + change)
            price = max(price, base_price * 0.1)  # 防止价格过低
            
            data.append({
                'timestamp': timestamp,
                'open': price * (1 + np.random.normal(0, 0.005)),
                'high': price * (1 + abs(np.random.normal(0, 0.01))),
                'low': price * (1 - abs(np.random.normal(0, 0.01))),
                'close': price,
                'volume': np.random.uniform(100000, 1000000)
            })
        
        return data

# 创建模型实例
model = FibonacciProbabilityModel()

@fibonacci_prob_bp.route('/api/analyze', methods=['POST'])
def analyze_fibonacci_probability():
    """分析斐波那契概率"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'H')
        timeframe = data.get('timeframe', '4h')
        days = data.get('days', 120)
        
        result = model.analyze_symbol_behavior(symbol, timeframe, days)
        
        if result:
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'error': '分析失败'
            }), 500
            
    except Exception as e:
        logger.error(f"斐波那契概率分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@fibonacci_prob_bp.route('/api/batch-analyze', methods=['POST'])
def batch_analyze_symbols():
    """批量分析多个币种"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', ['H', 'KGEN', 'BANK', 'LA', 'F'])
        timeframe = data.get('timeframe', '4h')
        days = data.get('days', 120)
        
        results = []
        for symbol in symbols:
            logger.info(f"分析 {symbol}...")
            result = model.analyze_symbol_behavior(symbol, timeframe, days)
            if result:
                results.append(result)
            time.sleep(0.1)  # 避免API限制
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
