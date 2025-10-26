#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时斐波那契扩展位分析系统
实时判断币种是否在斐波扩展阶段，定位当前点位，分析阻力支撑概率
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
realtime_fib_bp = Blueprint('realtime_fib', __name__, url_prefix='/realtime-fib')

class RealtimeFibonacciAnalyzer:
    """实时斐波那契扩展位分析器"""
    
    def __init__(self):
        self.fibonacci_levels = [0.618, 1.0, 1.618, 2.618, 3.618, 4.236]
        self.fibonacci_names = ['0.618', '1.0', '1.618', '2.618', '3.618', '4.236']
        
    def get_gate_klines(self, symbol, interval, limit):
        """从Gate.io获取K线数据"""
        try:
            # Gate.io使用时间字符串格式
            interval_map = {
                '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h'
            }
            gate_interval = interval_map.get(interval, '1h')
            
            # 格式化币种符号：BTCUSDT -> BTC_USDT
            formatted_symbol = symbol
            if symbol.endswith('USDT') and not '_' in symbol:
                formatted_symbol = symbol[:-4] + '_USDT'
            
            url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': formatted_symbol,
                'interval': gate_interval,
                'limit': min(limit, 1000)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            if klines:
                return self.convert_gate_data(klines)
            return None
                
        except Exception as e:
            logger.error(f"Gate.io获取 {symbol} K线数据失败: {e}")
            return None
    
    def get_bitget_klines(self, symbol, interval, limit):
        """从Bitget获取K线数据"""
        try:
            interval_map = {
                '5m': '5m', '15m': '15m', '1h': '1H', '4h': '4H'
            }
            bitget_interval = interval_map.get(interval, '1H')
            
            # Bitget需要合约格式：BTCUSDT -> BTCUSDT_UMCBL
            formatted_symbol = symbol + '_UMCBL'
            
            url = f"https://api.bitget.com/api/mix/v1/market/candles"
            params = {
                'symbol': formatted_symbol,
                'granularity': bitget_interval,
                'limit': min(limit, 1000),
                'productType': 'umcbl'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '00000':
                klines = data.get('data', [])
                return self.convert_bitget_data(klines)
            return None
                
        except Exception as e:
            logger.error(f"Bitget获取 {symbol} K线数据失败: {e}")
            return None
    
    def get_bybit_klines(self, symbol, interval, limit):
        """从Bybit获取K线数据"""
        try:
            interval_map = {
                '5m': '5', '15m': '15', '1h': '60', '4h': '240'
            }
            bybit_interval = interval_map.get(interval, '60')
            
            # Bybit符号格式：BTCUSDT -> BTCUSDT
            formatted_symbol = symbol
            
            url = f"https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'linear',
                'symbol': formatted_symbol,
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
    
    def convert_gate_data(self, klines):
        """转换Gate.io数据格式"""
        if not klines or not isinstance(klines, list):
            logger.error("Gate.io数据格式错误: klines为空或非列表")
            return None
            
        converted_data = []
        for kline in klines:
            if not kline or len(kline) < 6:
                logger.error(f"Gate.io单条K线数据格式错误: {kline}")
                continue
            # Gate.io返回的格式: [timestamp(秒), volume, close, high, low, open]
            # 需要转换为毫秒时间戳
            try:
                converted_data.append({
                    'timestamp': int(kline[0]) * 1000,  # Gate.io返回秒级时间戳，转为毫秒
                    'open': float(kline[5]),
                    'high': float(kline[3]),
                    'low': float(kline[4]),
                    'close': float(kline[2]),
                    'volume': float(kline[1])
                })
            except (ValueError, IndexError) as e:
                logger.error(f"Gate.io数据转换错误: {e}, kline={kline}")
                continue
        
        if not converted_data:
            logger.error("Gate.io数据转换后为空")
            return None
            
        return converted_data
    
    def convert_bitget_data(self, klines):
        """转换Bitget数据格式"""
        if not klines or not isinstance(klines, list):
            logger.error("Bitget数据格式错误: klines为空或非列表")
            return None
            
        converted_data = []
        for kline in klines:
            if not kline or len(kline) < 6:
                logger.error(f"Bitget单条K线数据格式错误: {kline}")
                continue
            # Bitget返回格式: [timestamp, open, high, low, close, volume]
            try:
                converted_data.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            except (ValueError, IndexError) as e:
                logger.error(f"Bitget数据转换错误: {e}, kline={kline}")
                continue
        
        if not converted_data:
            logger.error("Bitget数据转换后为空")
            return None
            
        return converted_data
    
    def convert_bybit_data(self, klines):
        """转换Bybit数据格式"""
        if not klines or not isinstance(klines, list):
            logger.error("Bybit数据格式错误: klines为空或非列表")
            return None
            
        converted_data = []
        for kline in klines:
            if not kline or len(kline) < 6:
                logger.error(f"Bybit单条K线数据格式错误: {kline}")
                continue
            try:
                converted_data.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            except (ValueError, IndexError) as e:
                logger.error(f"Bybit数据转换错误: {e}, kline={kline}")
                continue
        
        if not converted_data:
            logger.error("Bybit数据转换后为空")
            return None
            
        return converted_data
    
    def identify_fibonacci_base_levels(self, price_data):
        """识别斐波那契基准位（历史高点和低点）"""
        df = pd.DataFrame(price_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp')
        
        # 找到历史高点
        historical_high = df['high'].max()
        high_idx = df['high'].idxmax()
        high_date = df.loc[high_idx, 'timestamp']
        
        # 找到历史低点（在高点之后）
        if high_idx < len(df) - 1:
            low_data = df.iloc[high_idx:]
            historical_low = low_data['low'].min()
            low_idx = low_data['low'].idxmin()
            low_date = df.loc[low_idx, 'timestamp']
        else:
            historical_low = df['low'].min()
            low_idx = df['low'].idxmin()
            low_date = df.loc[low_idx, 'timestamp']
        
        return {
            'historical_high': historical_high,
            'high_date': high_date,
            'high_timestamp': int(high_date.timestamp() * 1000),
            'historical_low': historical_low,
            'low_date': low_date,
            'low_timestamp': int(low_date.timestamp() * 1000)
        }
    
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
    
    def analyze_recent_price_volume_changes(self, price_data, hours=4):
        """分析近期价格和量能变化"""
        df = pd.DataFrame(price_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp')
        
        # 获取最近N小时的数据
        now = datetime.now()
        cutoff_time = now - timedelta(hours=hours)
        recent_data = df[df['timestamp'] >= cutoff_time]
        
        if len(recent_data) < 2:
            return None
        
        # 计算价格变化
        start_price = recent_data.iloc[0]['close']
        end_price = recent_data.iloc[-1]['close']
        price_change = (end_price - start_price) / start_price
        
        # 计算价格变化速度（每小时）
        time_hours = (recent_data.iloc[-1]['timestamp'] - recent_data.iloc[0]['timestamp']).total_seconds() / 3600
        price_velocity = price_change / time_hours if time_hours > 0 else 0
        
        # 计算量能变化
        avg_volume = recent_data['volume'].mean()
        volume_volatility = recent_data['volume'].std() / avg_volume if avg_volume > 0 else 0
        
        # 计算量能加权价格变化
        volume_weighted_change = 0
        total_volume = 0
        for i in range(1, len(recent_data)):
            price_change_i = (recent_data.iloc[i]['close'] - recent_data.iloc[i-1]['close']) / recent_data.iloc[i-1]['close']
            volume_i = recent_data.iloc[i]['volume']
            volume_weighted_change += price_change_i * volume_i
            total_volume += volume_i
        
        volume_weighted_change = volume_weighted_change / total_volume if total_volume > 0 else 0
        
        # 计算多空强度
        bullish_strength = 0
        bearish_strength = 0
        
        for i in range(1, len(recent_data)):
            current = recent_data.iloc[i]
            previous = recent_data.iloc[i-1]
            
            if current['close'] > previous['close']:
                # 多头强度 = 涨幅 × 成交量
                strength = ((current['close'] - previous['close']) / previous['close']) * current['volume']
                bullish_strength += strength
            else:
                # 空头强度 = 跌幅 × 成交量
                strength = ((previous['close'] - current['close']) / previous['close']) * current['volume']
                bearish_strength += strength
        
        total_strength = bullish_strength + bearish_strength
        bullish_ratio = bullish_strength / total_strength if total_strength > 0 else 0.5
        
        return {
            'price_change': price_change,
            'price_velocity': price_velocity,
            'volume_volatility': volume_volatility,
            'volume_weighted_change': volume_weighted_change,
            'bullish_strength': bullish_strength,
            'bearish_strength': bearish_strength,
            'bullish_ratio': bullish_ratio,
            'time_hours': time_hours,
            'data_points': len(recent_data)
        }
    
    def locate_current_fibonacci_position(self, current_price, fib_levels):
        """定位当前价格在斐波扩展位中的位置"""
        # 找到最接近的斐波位点
        closest_level = None
        min_distance = float('inf')
        
        for level, price in fib_levels.items():
            distance = abs(current_price - price)
            if distance < min_distance:
                min_distance = distance
                closest_level = level
        
        # 确定当前价格相对于斐波位点的位置
        if closest_level is None:
            return None
        
        closest_price = fib_levels[closest_level]
        position_ratio = (current_price - closest_price) / closest_price
        
        # 找到上方和下方的关键位点
        sorted_levels = sorted(fib_levels.items(), key=lambda x: x[1])
        current_index = None
        
        for i, (level, price) in enumerate(sorted_levels):
            if level == closest_level:
                current_index = i
                break
        
        if current_index is None:
            return None
        
        # 上方和下方的位点
        upper_levels = []
        lower_levels = []
        
        for i, (level, price) in enumerate(sorted_levels):
            if i > current_index:
                upper_levels.append((level, price))
            elif i < current_index:
                lower_levels.append((level, price))
        
        return {
            'closest_level': closest_level,
            'closest_price': closest_price,
            'distance_ratio': position_ratio,
            'upper_levels': upper_levels,
            'lower_levels': lower_levels,
            'is_above_closest': current_price > closest_price
        }
    
    def calculate_resistance_support_probability(self, current_price, fib_levels, recent_analysis):
        """计算阻力/支撑概率"""
        probabilities = {}
        
        for level, price in fib_levels.items():
            # 基础概率计算
            distance_ratio = abs(current_price - price) / price
            
            # 基于距离的概率
            distance_prob = max(0, 1 - distance_ratio * 10)  # 距离越近概率越高
            
            # 基于近期变化的概率
            if recent_analysis:
                price_velocity = recent_analysis['price_velocity']
                bullish_ratio = recent_analysis['bullish_ratio']
                
                # 如果价格在斐波位点上方且上涨，阻力概率高
                if current_price > price and price_velocity > 0:
                    resistance_prob = 0.7 + (price_velocity * 10)
                    support_prob = 0.3
                # 如果价格在斐波位点下方且下跌，支撑概率高
                elif current_price < price and price_velocity < 0:
                    support_prob = 0.7 + (abs(price_velocity) * 10)
                    resistance_prob = 0.3
                else:
                    # 基于多空强度比例
                    resistance_prob = 0.5 + (bullish_ratio - 0.5) * 0.4
                    support_prob = 0.5 + (0.5 - bullish_ratio) * 0.4
            else:
                resistance_prob = 0.5
                support_prob = 0.5
            
            # 综合概率
            resistance_prob = min(0.9, max(0.1, resistance_prob * distance_prob))
            support_prob = min(0.9, max(0.1, support_prob * distance_prob))
            
            probabilities[level] = {
                'price': price,
                'resistance_probability': resistance_prob,
                'support_probability': support_prob,
                'distance_ratio': distance_ratio
            }
        
        return probabilities
    
    def analyze_realtime_fibonacci(self, symbol, timeframe='1h'):
        """实时斐波那契分析"""
        try:
            logger.info(f"开始实时分析 {symbol} 的斐波扩展位...")
            
            # 获取数据
            limit = 200  # 获取足够的历史数据
            price_data = None
            data_source = None
            
            # 尝试从Bybit获取数据
            price_data = self.get_bybit_klines(symbol, timeframe, limit)
            if price_data:
                data_source = "Bybit"
            else:
                # 尝试从Gate.io获取数据
                price_data = self.get_gate_klines(symbol, timeframe, limit)
                if price_data:
                    data_source = "Gate.io"
                else:
                    # 尝试从Bitget获取数据
                    price_data = self.get_bitget_klines(symbol, timeframe, limit)
                    if price_data:
                        data_source = "Bitget"
            
            if not price_data:
                logger.warning(f"无法从所有交易所获取 {symbol} 数据，使用模拟数据")
                try:
                    price_data = self.generate_mock_data(symbol, timeframe, limit)
                    data_source = "模拟数据"
                except Exception as e:
                    logger.error(f"生成模拟数据失败: {e}")
                    return None
            
            # 识别斐波基准位
            try:
                base_levels = self.identify_fibonacci_base_levels(price_data)
                historical_high = base_levels['historical_high']
                historical_low = base_levels['historical_low']
            except Exception as e:
                logger.error(f"识别斐波基准位失败: {e}")
                return None
            
            # 计算斐波扩展位
            try:
                fib_levels = self.calculate_fibonacci_extension_levels(historical_low, historical_high)
            except Exception as e:
                logger.error(f"计算斐波扩展位失败: {e}")
                return None
            
            # 获取当前价格
            current_price = price_data[-1]['close']
            
            # 分析近期变化
            recent_analysis = self.analyze_recent_price_volume_changes(price_data, hours=4)
            
            # 定位当前斐波位置
            fib_position = self.locate_current_fibonacci_position(current_price, fib_levels)
            
            # 计算阻力支撑概率
            resistance_support_probs = self.calculate_resistance_support_probability(
                current_price, fib_levels, recent_analysis
            )
            
            # 判断是否在斐波扩展阶段
            is_in_fib_extension = self.is_in_fibonacci_extension_phase(
                current_price, fib_levels, recent_analysis
            )
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'data_source': data_source,
                'current_price': current_price,
                'historical_high': historical_high,
                'historical_low': historical_low,
                'fib_levels': fib_levels,
                'fib_position': fib_position,
                'recent_analysis': recent_analysis,
                'resistance_support_probs': resistance_support_probs,
                'is_in_fib_extension': is_in_fib_extension,
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"实时斐波分析失败: {e}")
            return None
    
    def is_in_fibonacci_extension_phase(self, current_price, fib_levels, recent_analysis):
        """判断是否在斐波扩展阶段"""
        if not fib_levels or not recent_analysis:
            return False
        
        # 检查当前价格是否在斐波扩展位附近
        in_fib_range = False
        for level, price in fib_levels.items():
            distance_ratio = abs(current_price - price) / price
            if distance_ratio < 0.05:  # 5%范围内
                in_fib_range = True
                break
        
        # 检查是否有明显的趋势
        has_trend = abs(recent_analysis['price_velocity']) > 0.01  # 每小时变化超过1%
        
        # 检查量能是否配合
        has_volume_confirmation = recent_analysis['volume_volatility'] > 0.5
        
        return in_fib_range and has_trend and has_volume_confirmation
    
    def generate_mock_data(self, symbol, timeframe, limit):
        """生成模拟数据"""
        data = []
        now = int(time.time() * 1000)
        
        interval_map = {
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000
        }
        
        interval = interval_map.get(timeframe, 60 * 60 * 1000)
        base_price = 0.1 if symbol == 'H' else 1.0
        price = base_price
        
        for i in range(limit):
            timestamp = now - (limit - i) * interval
            
            # 生成更真实的价格波动
            change = np.random.normal(0, 0.02)
            price = price * (1 + change)
            price = max(price, base_price * 0.1)
            
            data.append({
                'timestamp': timestamp,
                'open': price * (1 + np.random.normal(0, 0.005)),
                'high': price * (1 + abs(np.random.normal(0, 0.01))),
                'low': price * (1 - abs(np.random.normal(0, 0.01))),
                'close': price,
                'volume': np.random.uniform(100000, 1000000)
            })
        
        return data

# 创建分析器实例
analyzer = RealtimeFibonacciAnalyzer()

@realtime_fib_bp.route('/api/analyze', methods=['POST'])
def analyze_realtime_fibonacci():
    """实时斐波那契分析API"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'H')
        timeframe = data.get('timeframe', '1h')
        
        logger.info(f"收到实时斐波分析请求: symbol={symbol}, timeframe={timeframe}")
        
        result = analyzer.analyze_realtime_fibonacci(symbol, timeframe)
        
        if result:
            logger.info(f"实时斐波分析成功: symbol={symbol}")
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            logger.error(f"实时斐波分析返回None: symbol={symbol}")
            return jsonify({
                'success': False,
                'error': '分析失败'
            }), 500
            
    except Exception as e:
        import traceback
        logger.error(f"实时斐波分析异常: {e}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
