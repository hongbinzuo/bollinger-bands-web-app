#!/usr/bin/env python3
"""
加密货币价格数据API
支持从Gate.io和Bitget获取实时价格数据
"""

import requests
import json
import time
from datetime import datetime, timedelta
import logging
from flask import Blueprint, jsonify, request

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
crypto_api_bp = Blueprint('crypto_api', __name__)

# API配置
GATE_IO_BASE_URL = "https://api.gateio.ws/api/v4"
BITGET_BASE_URL = "https://api.bitget.com/api/v2"
# BINANCE_BASE_URL = "https://api.binance.com/api/v3"  # 已移除Binance支持
BYBIT_BASE_URL = "https://api.bybit.com/v5"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# 支持的币种 - 扩展到更多交易所
SUPPORTED_SYMBOLS = {
    'COAI': {
        'gateio': 'coai_usdt',
        'bitget': 'COAIUSDT',
        'bybit': 'COAIUSDT'
    },
    'MYX': {
        'gateio': 'myx_usdt',
        'bitget': 'MYXUSDT',
        'bybit': 'MYXUSDT'
    },
    'BAS': {
        'gateio': 'bas_usdt',
        'bitget': 'BASUSDT',
        'bybit': 'BASUSDT'
    },
    'BLESS': {
        'gateio': 'bless_usdt',
        'bitget': 'BLESSUSDT',
        'bybit': 'BLESSUSDT'
    },
    'XPIN': {
        'gateio': 'xpin_usdt',
        'bitget': 'XPINUSDT',
        'bybit': 'XPINUSDT'
    }
}

class CryptoDataProvider:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoChartApp/1.0'
        })
    
    def get_gateio_klines(self, symbol, interval, limit=100):
        """从Gate.io获取K线数据"""
        try:
            url = f"{GATE_IO_BASE_URL}/spot/candlesticks"
            params = {
                'currency_pair': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data or len(data) == 0:
                return []
            
            # 转换数据格式
            klines = []
            for item in data:
                klines.append({
                    'timestamp': int(item[0]),
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5])
                })
            
            return klines
            
        except Exception as e:
            logger.error(f"Gate.io API错误 {symbol}: {e}")
            return []
    
    def get_bitget_klines(self, symbol, interval, limit=100):
        """从Bitget获取K线数据"""
        try:
            url = f"{BITGET_BASE_URL}/spot/market/candles"
            params = {
                'symbol': symbol,
                'granularity': interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != '00000':
                logger.error(f"Bitget API错误: {data.get('msg')}")
                return []
            
            klines_data = data.get('data', [])
            if not klines_data:
                return []
            
            # 转换数据格式
            klines = []
            for item in klines_data:
                klines.append({
                    'timestamp': int(item[0]),
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5])
                })
            
            return klines
            
        except Exception as e:
            logger.error(f"Bitget API错误 {symbol}: {e}")
            return []
    
    # get_binance_klines 方法已移除 - 不再支持Binance
    
    def get_bybit_klines(self, symbol, interval, limit=100):
        """从Bybit获取K线数据"""
        try:
            url = f"{BYBIT_BASE_URL}/market/kline"
            params = {
                'category': 'spot',
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('retCode') != 0:
                logger.error(f"Bybit API错误: {data.get('retMsg')}")
                return []
            
            klines_data = data.get('result', {}).get('list', [])
            if not klines_data:
                return []
            
            # 转换数据格式
            klines = []
            for item in reversed(klines_data):  # Bybit返回的数据是倒序的
                klines.append({
                    'timestamp': int(item[0]),
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5])
                })
            
            return klines
            
        except Exception as e:
            logger.error(f"Bybit API错误 {symbol}: {e}")
            return []
    
    def get_current_price(self, symbol, exchange='gateio'):
        """获取当前价格 - 支持多个交易所（移除Binance）"""
        try:
            if exchange == 'bitget':
                return self._get_bitget_price(symbol)
            elif exchange == 'bybit':
                return self._get_bybit_price(symbol)
            else:  # 默认使用Gate.io
                return self._get_gateio_price(symbol)
                
        except Exception as e:
            logger.error(f"获取价格失败 {symbol}: {e}")
        
        return None
    
    def _get_gateio_price(self, symbol):
        """从Gate.io获取价格"""
        url = f"{GATE_IO_BASE_URL}/spot/tickers"
        params = {'currency_pair': symbol}
        
        response = self.session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data and len(data) > 0:
            ticker = data[0]
            return {
                'price': float(ticker['last']),
                'change_24h': float(ticker['change_percentage']),
                'volume_24h': float(ticker['base_volume']),
                'high_24h': float(ticker['high_24h']),
                'low_24h': float(ticker['low_24h'])
            }
        return None
    
    # _get_binance_price 方法已移除 - 不再支持Binance
    
    def _get_bitget_price(self, symbol):
        """从Bitget获取价格"""
        url = f"{BITGET_BASE_URL}/spot/market/ticker"
        params = {'symbol': symbol}
        
        response = self.session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') == '00000' and data.get('data'):
            ticker = data['data']
            return {
                'price': float(ticker['last']),
                'change_24h': float(ticker['changeRate']) * 100,
                'volume_24h': float(ticker['baseVolume']),
                'high_24h': float(ticker['high24h']),
                'low_24h': float(ticker['low24h'])
            }
        return None
    
    def _get_bybit_price(self, symbol):
        """从Bybit获取价格"""
        url = f"{BYBIT_BASE_URL}/market/tickers"
        params = {
            'category': 'spot',
            'symbol': symbol
        }
        
        response = self.session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data.get('retCode') == 0 and data.get('result', {}).get('list'):
            ticker = data['result']['list'][0]
            return {
                'price': float(ticker['lastPrice']),
                'change_24h': float(ticker['price24hPcnt']) * 100,
                'volume_24h': float(ticker['volume24h']),
                'high_24h': float(ticker['highPrice']),
                'low_24h': float(ticker['lowPrice'])
            }
        return None

# 全局数据提供者实例
data_provider = CryptoDataProvider()

# 时间级别映射
TIMEFRAME_MAP = {
    '15m': '15m',
    '1h': '1h', 
    '4h': '4h',
    '12h': '12h',
    '1d': '1d'
}

@crypto_api_bp.route('/klines', methods=['GET'])
def get_klines():
    """获取K线数据"""
    try:
        symbol = request.args.get('symbol', '').upper()
        timeframe = request.args.get('timeframe', '4h')
        exchange = request.args.get('exchange', 'gateio')  # gateio 或 bitget
        limit = int(request.args.get('limit', 100))
        
        if symbol not in SUPPORTED_SYMBOLS:
            return jsonify({
                'success': False,
                'error': f'不支持的币种: {symbol}'
            }), 400
        
        if timeframe not in TIMEFRAME_MAP:
            return jsonify({
                'success': False,
                'error': f'不支持的时间级别: {timeframe}'
            }), 400
        
        # 获取K线数据 - 支持多交易所
        symbol_config = SUPPORTED_SYMBOLS.get(symbol, {})
        if not symbol_config:
            return jsonify({
                'success': False,
                'error': f'不支持的币种: {symbol}'
            }), 400
        
        # 尝试从多个交易所获取数据
        klines = []
        exchanges_tried = []
        
        # 按优先级尝试交易所 - 优化顺序：首选交易所 -> Gate.io -> Bybit -> Bitget（移除Binance）
        exchange_priority = [exchange] + ['gateio', 'bybit', 'bitget']
        exchange_priority = list(dict.fromkeys(exchange_priority))  # 去重保持顺序
        
        for ex in exchange_priority:
            if ex not in symbol_config:
                continue
                
            symbol_pair = symbol_config[ex]
            exchanges_tried.append(ex)
            
            if ex == 'gateio':
                klines = data_provider.get_gateio_klines(symbol_pair, timeframe, limit)
            elif ex == 'bitget':
                klines = data_provider.get_bitget_klines(symbol_pair, timeframe, limit)
            elif ex == 'bybit':
                klines = data_provider.get_bybit_klines(symbol_pair, timeframe, limit)
            
            if klines:  # 如果获取到数据就停止尝试
                exchange = ex
                break
        
        if not klines:
            return jsonify({
                'success': False,
                'error': f'所有交易所都无法获取数据: {", ".join(exchanges_tried)}'
            }), 500
        
        if not klines:
            return jsonify({
                'success': False,
                'error': '无法获取数据'
            }), 500
        
        # 转换数据格式供前端使用 - 支持K线图
        chart_data = []
        for kline in klines:
            chart_data.append({
                'x': kline['timestamp'] * 1000,  # 转换为毫秒
                'o': kline['open'],    # 开盘价
                'h': kline['high'],    # 最高价
                'l': kline['low'],     # 最低价
                'c': kline['close'],   # 收盘价
                'v': kline['volume']   # 成交量
            })
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'exchange': exchange,
            'data': chart_data,
            'count': len(chart_data)
        })
        
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crypto_api_bp.route('/price', methods=['GET'])
def get_current_prices():
    """获取所有币种的当前价格"""
    try:
        prices = {}
        
        for symbol, symbol_config in SUPPORTED_SYMBOLS.items():
            price_info = None
            # 尝试所有可用的交易所（移除Binance）
            for exchange in ['gateio', 'bybit', 'bitget']:
                if exchange in symbol_config:
                    symbol_pair = symbol_config[exchange]
                    price_info = data_provider.get_current_price(symbol_pair, exchange)
                    if price_info:
                        break  # 成功获取价格就停止尝试
            
            if price_info:
                prices[symbol] = {
                    'symbol': symbol,
                    'price': price_info['price'],
                    'change_24h': price_info['change_24h'],
                    'volume_24h': price_info['volume_24h'],
                    'high_24h': price_info['high_24h'],
                    'low_24h': price_info['low_24h']
                }
            else:
                # 如果所有交易所都获取不到，提供默认值
                prices[symbol] = {
                    'symbol': symbol,
                    'price': 1.0,  # 默认价格
                    'change_24h': 0.0,
                    'volume_24h': 0.0,
                    'high_24h': 1.0,
                    'low_24h': 1.0
                }
        
        return jsonify({
            'success': True,
            'prices': prices,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"获取价格失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crypto_api_bp.route('/symbols', methods=['GET'])
def get_supported_symbols():
    """获取支持的币种列表"""
    return jsonify({
        'success': True,
        'symbols': list(SUPPORTED_SYMBOLS.keys()),
        'exchanges': ['gateio', 'bitget']
    })

@crypto_api_bp.route('/chart', methods=['GET'])
def crypto_chart():
    """加密货币图表页面"""
    from flask import render_template
    return render_template('crypto_charts.html')

if __name__ == '__main__':
    # 测试API
    provider = CryptoDataProvider()
    
    print("测试Gate.io API...")
    klines = provider.get_gateio_klines('btc_usdt', '4h', 10)
    print(f"获取到 {len(klines)} 条K线数据")
    
    if klines:
        print("最新数据:", klines[-1])
    
    print("\n测试价格获取...")
    price = provider.get_current_price('btc_usdt')
    if price:
        print("BTC价格:", price)
