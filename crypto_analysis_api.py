# -*- coding: utf-8 -*-
"""
热点币种分析API
"""

from flask import Blueprint, jsonify
import logging
import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# 创建热点币种分析蓝图
crypto_analysis_bp = Blueprint('crypto_analysis', __name__, url_prefix='/crypto_analysis')

class CryptoAnalyzer:
    def __init__(self):
        """初始化加密货币分析器"""
        self.gate_url = "https://api.gateio.ws/api/v4"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 加载币种列表
        self.symbols_file = os.path.join('coin_analyze', 'crypto_symbols_350.txt')
        self.symbols = self.load_symbols()
    
    def load_symbols(self):
        """从文件加载350个币种"""
        try:
            with open(self.symbols_file, 'r', encoding='utf-8') as f:
                symbols = [line.strip().replace('USDT', '') for line in f if line.strip()]
            logger.info(f"成功加载 {len(symbols)} 个币种")
            return symbols
        except Exception as e:
            logger.error(f"加载币种列表失败: {e}")
            return []
    
    def get_gate_price(self, symbol):
        """从Gate.io获取价格数据"""
        try:
            currency_pair = f"{symbol}_USDT"
            url = f"{self.gate_url}/spot/tickers"
            params = {'currency_pair': currency_pair}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    ticker = data[0]
                    return {
                        'symbol': symbol,
                        'price': float(ticker.get('last', 0)),
                        'change_24h': float(ticker.get('change_percentage', 0)),
                        'volume': float(ticker.get('base_volume', 0)),
                        'high_24h': float(ticker.get('high_24h', 0)),
                        'low_24h': float(ticker.get('low_24h', 0)),
                        'quote_volume': float(ticker.get('quote_volume', 0)),
                        'source': 'Gate.io'
                    }
        except Exception as e:
            logger.debug(f"获取 {symbol} 价格失败: {e}")
        return None
    
    def analyze_coins(self, progress_callback=None):
        """分析所有币种"""
        logger.info(f"开始分析 {len(self.symbols)} 个币种")
        
        results = []
        success_count = 0
        
        for i, symbol in enumerate(self.symbols, 1):
            if progress_callback:
                progress_callback(i, len(self.symbols), symbol)
            
            # 获取价格数据
            price_data = self.get_gate_price(symbol)
            time.sleep(0.2)  # Gate.io限速控制
            
            if price_data:
                results.append(price_data)
                success_count += 1
                logger.debug(f"[{i}/{len(self.symbols)}] {symbol}: ${price_data['price']:.6f} ({price_data['change_24h']:+.2f}%)")
            else:
                # 失败的币种也添加，但标记为无效
                results.append({
                    'symbol': symbol,
                    'price': 0,
                    'change_24h': 0,
                    'volume': 0,
                    'high_24h': 0,
                    'low_24h': 0,
                    'quote_volume': 0,
                    'source': 'Failed'
                })
        
        logger.info(f"分析完成: 成功 {success_count}/{len(self.symbols)}")
        return results
    
    def generate_analysis_result(self, coin_data_list):
        """生成分析结果"""
        df = pd.DataFrame(coin_data_list)
        df_valid = df[df['price'] > 0]
        
        # 基本统计
        total_coins = len(df)
        successful_coins = len(df_valid)
        success_rate = (successful_coins / total_coins * 100) if total_coins > 0 else 0
        
        # 涨跌分析
        positive = len(df_valid[df_valid['change_24h'] > 0])
        negative = len(df_valid[df_valid['change_24h'] < 0])
        
        # 统计指标
        stats = {}
        if len(df_valid) > 0:
            stats = {
                'avg_change': float(df_valid['change_24h'].mean()),
                'max_gain': float(df_valid['change_24h'].max()),
                'max_loss': float(df_valid['change_24h'].min()),
                'median_change': float(df_valid['change_24h'].median()),
                'total_volume': float(df_valid['volume'].sum()),
                'avg_volume': float(df_valid['volume'].mean())
            }
        
        # TOP涨幅榜
        top_gainers = []
        if len(df_valid) > 0:
            top_gainers = df_valid.nlargest(20, 'change_24h').to_dict('records')
        
        # TOP跌幅榜
        top_losers = []
        if len(df_valid) > 0:
            top_losers = df_valid.nsmallest(20, 'change_24h').to_dict('records')
        
        # TOP交易量
        top_volume = []
        if len(df_valid) > 0:
            top_volume = df_valid.nlargest(20, 'volume').to_dict('records')
        
        # 涨跌分布
        distribution = {
            'up_10_plus': len(df_valid[df_valid['change_24h'] >= 10]),
            'up_5_10': len(df_valid[(df_valid['change_24h'] >= 5) & (df_valid['change_24h'] < 10)]),
            'up_0_5': len(df_valid[(df_valid['change_24h'] >= 0) & (df_valid['change_24h'] < 5)]),
            'down_0_5': len(df_valid[(df_valid['change_24h'] >= -5) & (df_valid['change_24h'] < 0)]),
            'down_5_10': len(df_valid[(df_valid['change_24h'] >= -10) & (df_valid['change_24h'] < -5)]),
            'down_10_plus': len(df_valid[df_valid['change_24h'] < -10])
        }
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_coins': total_coins,
                'successful_coins': successful_coins,
                'success_rate': round(success_rate, 2),
                'positive_coins': positive,
                'negative_coins': negative,
                'positive_rate': round((positive / successful_coins * 100) if successful_coins > 0 else 0, 2)
            },
            'statistics': stats,
            'top_gainers': top_gainers,
            'top_losers': top_losers,
            'top_volume': top_volume,
            'distribution': distribution,
            'all_coins': coin_data_list
        }

# 创建全局分析器实例
analyzer = CryptoAnalyzer()

@crypto_analysis_bp.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'module': 'crypto_analysis',
        'timestamp': datetime.now().isoformat(),
        'total_symbols': len(analyzer.symbols)
    })

@crypto_analysis_bp.route('/analyze', methods=['GET'])
def analyze():
    """分析所有币种"""
    try:
        logger.info("开始分析热点币种...")
        
        # 执行分析
        coin_data = analyzer.analyze_coins()
        
        # 生成结果
        result = analyzer.generate_analysis_result(coin_data)
        
        logger.info(f"分析完成: {result['summary']['successful_coins']}/{result['summary']['total_coins']} 个币种")
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crypto_analysis_bp.route('/get_symbols', methods=['GET'])
def get_symbols():
    """获取所有币种列表"""
    try:
        return jsonify({
            'success': True,
            'symbols': analyzer.symbols,
            'count': len(analyzer.symbols)
        })
    except Exception as e:
        logger.error(f"获取币种列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

