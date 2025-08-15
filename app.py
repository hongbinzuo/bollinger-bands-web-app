from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
from typing import List, Dict
import json
import os
from io import StringIO

app = Flask(__name__)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BollingerBandsAnalyzer:
    def __init__(self):
        """初始化布林带分析器"""
        # Binance API
        self.binance_url = "https://api.binance.com/api/v3"
        # Gate.io API
        self.gate_url = "https://api.gateio.ws/api/v4"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_binance_klines(self, symbol: str, interval: str = '12h', limit: int = 100) -> pd.DataFrame:
        """从Binance获取K线数据"""
        try:
            url = f"{self.binance_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 创建DataFrame
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 转换数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 只保留需要的列
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Binance获取 {symbol} K线数据失败: {e}")
            return pd.DataFrame()
    
    def get_gate_klines(self, symbol: str, interval: str = '12h', limit: int = 100) -> pd.DataFrame:
        """从Gate.io获取K线数据"""
        try:
            # Gate.io的interval格式转换
            interval_map = {
                '12h': '12h',
                '4h': '4h',
                '1d': '1d'
            }
            gate_interval = interval_map.get(interval, '12h')
            
            url = f"{self.gate_url}/spot/candlesticks"
            params = {
                'currency_pair': symbol,
                'interval': gate_interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return pd.DataFrame()
            
            # 创建DataFrame - Gate.io返回8个字段
            df = pd.DataFrame(data, columns=[
                'timestamp', 'volume', 'close', 'high', 'low', 'open', 'extra1', 'extra2'
            ])
            
            # 转换数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            # 重新排列列顺序
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Gate.io获取 {symbol} K线数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> Dict:
        """计算布林带"""
        try:
            if len(df) < period:
                return None
            
            # 计算移动平均线（中轨）
            middle_band = df['close'].rolling(window=period).mean()
            
            # 计算标准差
            std = df['close'].rolling(window=period).std()
            
            # 计算上轨和下轨
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            # 获取最新值
            current_price = df['close'].iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            return {
                'current_price': current_price,
                'middle_band': current_middle,
                'upper_band': current_upper,
                'lower_band': current_lower
            }
            
        except Exception as e:
            logger.error(f"计算布林带失败: {e}")
            return None
    
    def calculate_order_price(self, current_price: float, middle_band: float, upper_band: float, lower_band: float) -> str:
        """计算挂单价格"""
        try:
            # 如果当前币价在中轨和下轨之间，则挂单价格=下轨
            if lower_band <= current_price <= middle_band:
                return f"{lower_band:.6f}"
            
            # 如果当前币价在中轨与（中轨*1.02）的区间，则挂单价格=下轨
            upper_threshold = middle_band * 1.02
            if middle_band <= current_price <= upper_threshold:
                return f"{lower_band:.6f}"
            
            # 如果价格在上轨与中轨之间则挂单价格=中轨
            elif middle_band <= current_price <= upper_band:
                return f"{middle_band:.6f}"
            
            # 如果价格在下轨下方，则挂单价格=已破下轨
            elif current_price < lower_band:
                return "已破下轨"
            
            # 其他情况挂单价格=中轨
            else:
                return f"{middle_band:.6f}"
            
        except Exception as e:
            logger.error(f"计算挂单价格失败: {e}")
            return "计算失败"
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """分析单个币种"""
        try:
            logger.info(f"分析 {symbol}")
            
            # 首先尝试Binance
            df = self.get_binance_klines(symbol, '12h', 100)
            
            if df.empty:
                # 如果Binance失败，尝试Gate.io
                logger.info(f"Binance获取失败，尝试Gate.io...")
                gate_symbol = symbol.replace('USDT', '_USDT')
                df = self.get_gate_klines(gate_symbol, '12h', 100)
                data_source = "Gate.io"
            else:
                data_source = "Binance"
            
            if df.empty:
                return {
                    'symbol': symbol,
                    'current_price': None,
                    'middle_band': None,
                    'lower_band': None,
                    'order_price': None,
                    'status': '✗ 失败',
                    'data_source': 'None'
                }
            
            # 计算布林带
            bb_data = self.calculate_bollinger_bands(df)
            
            if bb_data is None:
                return {
                    'symbol': symbol,
                    'current_price': None,
                    'middle_band': None,
                    'lower_band': None,
                    'order_price': None,
                    'status': '✗ 计算失败',
                    'data_source': data_source
                }
            
            # 计算挂单价格
            order_price = self.calculate_order_price(
                bb_data['current_price'],
                bb_data['middle_band'],
                bb_data['upper_band'],
                bb_data['lower_band']
            )
            
            return {
                'symbol': symbol,
                'current_price': bb_data['current_price'],
                'middle_band': bb_data['middle_band'],
                'lower_band': bb_data['lower_band'],
                'order_price': order_price,
                'status': '✓ 成功',
                'data_source': data_source
            }
            
        except Exception as e:
            logger.error(f"分析 {symbol} 时出错: {e}")
            return {
                'symbol': symbol,
                'current_price': None,
                'middle_band': None,
                'lower_band': None,
                'order_price': None,
                'status': '✗ 错误',
                'data_source': 'None'
            }

# 全局分析器实例
analyzer = BollingerBandsAnalyzer()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """分析币种"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'error': '请提供币种列表'}), 400
        
        # 添加USDT后缀
        symbols_with_usdt = [f"{symbol}USDT" for symbol in symbols]
        
        results = []
        for i, symbol in enumerate(symbols_with_usdt):
            try:
                logger.info(f"处理 {symbol} ({i+1}/{len(symbols_with_usdt)})")
                
                result = analyzer.analyze_symbol(symbol)
                results.append(result)
                
                # 延迟控制
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"处理 {symbol} 时出错: {e}")
                continue
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        logger.error(f"分析请求失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_csv', methods=['POST'])
def download_csv():
    """下载CSV文件"""
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': '没有数据可下载'}), 400
        
        # 创建CSV数据
        csv_data = []
        for result in results:
            symbol = result['symbol'].replace('USDT', '')  # 去掉USDT后缀
            current_price = result['current_price']
            middle_band = result['middle_band']
            lower_band = result['lower_band']
            order_price = result['order_price']
            status = result['status']
            data_source = result['data_source']
            
            if current_price is not None and middle_band is not None and lower_band is not None and order_price is not None:
                csv_data.append({
                    '币种': symbol,
                    '当前价格': f"{current_price:.6f}",
                    '中轨': f"{middle_band:.6f}",
                    '下轨': f"{lower_band:.6f}",
                    '挂单价格': order_price,
                    '状态': status,
                    '数据源': data_source
                })
            else:
                csv_data.append({
                    '币种': symbol,
                    '当前价格': '获取失败',
                    '中轨': '获取失败',
                    '下轨': '获取失败',
                    '挂单价格': '获取失败',
                    '状态': status,
                    '数据源': data_source
                })
        
        # 创建DataFrame并转换为CSV
        df = pd.DataFrame(csv_data)
        csv_string = df.to_csv(index=False, encoding='utf-8-sig')
        
        # 创建文件对象
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bollinger_bands_analysis_{timestamp}.csv"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'csv_data': csv_string
        })
        
    except Exception as e:
        logger.error(f"下载CSV失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # 创建templates目录
    os.makedirs('templates', exist_ok=True)
    
    # 运行应用
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
