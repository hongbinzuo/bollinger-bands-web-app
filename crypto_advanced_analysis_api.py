# -*- coding: utf-8 -*-
"""
高级加密货币分析API - 支持历史数据、项目信息、资金流向分析
"""

from flask import Blueprint, request, jsonify
import logging
import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

# 创建高级分析蓝图
crypto_advanced_bp = Blueprint('crypto_advanced', __name__, url_prefix='/crypto_advanced')

class AdvancedCryptoAnalyzer:
    def __init__(self):
        """初始化高级加密货币分析器"""
        self.gate_url = "https://api.gateio.ws/api/v4"
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 加载币种列表
        self.symbols_file = os.path.join('coin_analyze', 'crypto_symbols_350.txt')
        self.symbols = self.load_symbols()
        
        # CoinGecko币种映射缓存
        self.coingecko_id_cache = {}
    
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
    
    def get_historical_klines(self, symbol, start_date, end_date=None, interval='1d'):
        """
        获取历史K线数据
        
        Args:
            symbol: 币种符号（如BTC）
            start_date: 开始日期（datetime对象或字符串 'YYYY-MM-DD'）
            end_date: 结束日期（默认为今天）
            interval: 时间间隔（'1d', '1h', '4h'等）
        
        Returns:
            DataFrame包含历史价格数据
        """
        try:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date is None:
                end_date = datetime.now()
            elif isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 转换为时间戳
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            
            currency_pair = f"{symbol}_USDT"
            url = f"{self.gate_url}/spot/candlesticks"
            
            all_data = []
            current_ts = start_ts
            
            # Gate.io每次最多返回1000条数据，需要分批获取
            interval_seconds = self._interval_to_seconds(interval)
            batch_size = 1000
            
            while current_ts < end_ts:
                params = {
                    'currency_pair': currency_pair,
                    'interval': interval,
                    'from': current_ts,
                    'to': min(current_ts + batch_size * interval_seconds, end_ts)
                }
                
                response = self.session.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        all_data.extend(data)
                        current_ts = int(data[-1][0]) + interval_seconds
                    else:
                        break
                elif response.status_code == 400:
                    logger.debug(f"币种 {symbol} 可能不存在或交易对不可用")
                    break
                else:
                    logger.debug(f"获取 {symbol} 历史数据失败: HTTP {response.status_code}")
                    break
                
                time.sleep(0.2)  # 限速
            
            if not all_data:
                return pd.DataFrame()
            
            # 转换为DataFrame
            # Gate.io返回格式: [timestamp, volume, close, high, low, open, amount, ...]
            # 先创建DataFrame不指定列名，然后选择需要的列
            df_raw = pd.DataFrame(all_data)
            
            # 确保至少有6列
            if len(df_raw.columns) < 6:
                logger.error(f"获取 {symbol} 历史数据列数不足: {len(df_raw.columns)} 列")
                return pd.DataFrame()
            
            # 提取前6列并重命名
            df = df_raw.iloc[:, :6].copy()
            df.columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open']
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df = df.sort_values('timestamp')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"成功获取 {symbol} 从 {start_date} 到 {end_date} 的 {len(df)} 条数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 历史K线失败: {e}")
            return pd.DataFrame()
    
    def _interval_to_seconds(self, interval):
        """转换时间间隔为秒数"""
        interval_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '8h': 28800,
            '1d': 86400,
            '7d': 604800
        }
        return interval_map.get(interval, 86400)
    
    def calculate_gain_since_date(self, symbol, start_date):
        """
        计算从指定日期到现在的涨幅
        
        Args:
            symbol: 币种符号
            start_date: 开始日期
        
        Returns:
            dict: 包含涨幅信息
        """
        try:
            df = self.get_historical_klines(symbol, start_date)
            
            if df.empty or len(df) < 2:
                return None
            
            start_price = df.iloc[0]['close']
            end_price = df.iloc[-1]['close']
            gain_ratio = (end_price / start_price) if start_price > 0 else 0
            gain_percent = (gain_ratio - 1) * 100
            
            return {
                'symbol': symbol,
                'start_date': df.index[0].strftime('%Y-%m-%d'),
                'end_date': df.index[-1].strftime('%Y-%m-%d'),
                'start_price': float(start_price),
                'end_price': float(end_price),
                'gain_ratio': float(gain_ratio),
                'gain_percent': float(gain_percent),
                'max_price': float(df['high'].max()),
                'min_price': float(df['low'].min()),
                'total_volume': float(df['volume'].sum()),
                'avg_volume': float(df['volume'].mean())
            }
            
        except Exception as e:
            logger.error(f"计算 {symbol} 涨幅失败: {e}")
            return None
    
    def get_coingecko_id(self, symbol):
        """获取CoinGecko币种ID"""
        if symbol in self.coingecko_id_cache:
            return self.coingecko_id_cache[symbol]
        
        try:
            url = f"{self.coingecko_url}/search"
            params = {'query': symbol}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                coins = data.get('coins', [])
                if coins and len(coins) > 0:
                    coin_id = coins[0]['id']
                    self.coingecko_id_cache[symbol] = coin_id
                    return coin_id
                else:
                    logger.debug(f"CoinGecko未收录 {symbol}")
            else:
                logger.debug(f"CoinGecko搜索 {symbol} 失败: {response.status_code}")
        except Exception as e:
            logger.debug(f"获取 {symbol} CoinGecko ID失败: {e}")
        
        # 缓存失败结果，避免重复查询
        self.coingecko_id_cache[symbol] = None
        return None
    
    def get_project_info(self, symbol):
        """
        获取项目详细信息（CoinGecko）
        
        Returns:
            dict: 包含项目名称、描述、分类、链接、市值排名等
        """
        try:
            coin_id = self.get_coingecko_id(symbol)
            if not coin_id:
                return None
            
            url = f"{self.coingecko_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'true',
                'developer_data': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # 基本信息
                info = {
                    'symbol': symbol,
                    'name': data.get('name', ''),
                    'description': data.get('description', {}).get('en', '')[:500],  # 限制长度
                    'categories': data.get('categories', [])[:5],  # 技术赛道
                    'market_cap_rank': data.get('market_cap_rank', 999),
                    
                    # 链接信息
                    'homepage': data.get('links', {}).get('homepage', [None])[0],
                    'whitepaper': data.get('links', {}).get('whitepaper', ''),
                    'github': data.get('links', {}).get('repos_url', {}).get('github', [None])[0],
                    'twitter': data.get('links', {}).get('twitter_screen_name', ''),
                    
                    # 市场数据
                    'market_cap': data.get('market_data', {}).get('market_cap', {}).get('usd', 0),
                    'total_volume': data.get('market_data', {}).get('total_volume', {}).get('usd', 0),
                    'circulating_supply': data.get('market_data', {}).get('circulating_supply', 0),
                    'total_supply': data.get('market_data', {}).get('total_supply', 0),
                    
                    # 社区数据
                    'twitter_followers': data.get('community_data', {}).get('twitter_followers', 0),
                    'reddit_subscribers': data.get('community_data', {}).get('reddit_subscribers', 0),
                    'telegram_users': data.get('community_data', {}).get('telegram_channel_user_count', 0),
                    
                    # 开发者数据
                    'github_forks': data.get('developer_data', {}).get('forks', 0),
                    'github_stars': data.get('developer_data', {}).get('stars', 0),
                    'github_subscribers': data.get('developer_data', {}).get('subscribers', 0),
                    'github_total_issues': data.get('developer_data', {}).get('total_issues', 0),
                    'github_closed_issues': data.get('developer_data', {}).get('closed_issues', 0),
                    'github_commits_4w': data.get('developer_data', {}).get('commit_count_4_weeks', 0),
                }
                
                return info
                
        except Exception as e:
            logger.error(f"获取 {symbol} 项目信息失败: {e}")
        
        return None
    
    def analyze_money_flow(self, symbol, start_date, end_date=None):
        """
        分析资金流向（基于成交量和价格变化）
        
        Returns:
            DataFrame: 每日资金流向数据
        """
        try:
            df = self.get_historical_klines(symbol, start_date, end_date, '1d')
            
            if df.empty:
                return None
            
            # 计算资金流向指标
            df['price_change'] = df['close'].pct_change()
            df['volume_change'] = df['volume'].pct_change()
            
            # 资金流向 = 成交量 × 价格变化
            # 正值表示资金流入，负值表示资金流出
            df['money_flow'] = df['volume'] * df['close'] * df['price_change']
            
            # 累计资金流向
            df['cumulative_flow'] = df['money_flow'].cumsum()
            
            # OBV (On Balance Volume) - 能量潮指标
            df['obv'] = (np.sign(df['price_change']) * df['volume']).cumsum()
            
            # 资金流强度
            df['flow_strength'] = abs(df['money_flow']) / df['volume']
            
            return df[['close', 'volume', 'price_change', 'money_flow', 'cumulative_flow', 'obv', 'flow_strength']]
            
        except Exception as e:
            logger.error(f"分析 {symbol} 资金流向失败: {e}")
            return None

# 创建全局分析器实例
advanced_analyzer = AdvancedCryptoAnalyzer()

@crypto_advanced_bp.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'module': 'crypto_advanced_analysis',
        'timestamp': datetime.now().isoformat(),
        'total_symbols': len(advanced_analyzer.symbols)
    })

@crypto_advanced_bp.route('/analyze_period', methods=['POST'])
def analyze_period():
    """
    分析指定时间段的币种表现
    
    请求参数:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (可选，默认今天)
        min_gain_ratio: 最小涨幅倍数 (如3表示3倍，可选)
        include_project_info: 是否包含项目信息 (默认false)
        include_money_flow: 是否包含资金流向 (默认false)
    """
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        min_gain_ratio = data.get('min_gain_ratio', 1.0)
        include_project_info = data.get('include_project_info', False)
        include_money_flow = data.get('include_money_flow', False)
        
        if not start_date:
            return jsonify({
                'success': False,
                'error': '请提供start_date参数'
            }), 400
        
        logger.info(f"开始分析时间段: {start_date} 到 {end_date or '今天'}")
        
        results = []
        failed_records = []  # 记录失败的币种
        symbols = advanced_analyzer.symbols  # 分析所有350个币种
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"[{i}/{len(symbols)}] 分析 {symbol}...")
                
                # 计算涨幅
                gain_info = advanced_analyzer.calculate_gain_since_date(symbol, start_date)
                
                if gain_info is None:
                    # 记录无法获取历史数据的币种
                    failed_records.append({
                        'symbol': symbol,
                        'reason': '无法获取历史数据',
                        'detail': '可能币种不存在或交易对不可用'
                    })
                elif gain_info['gain_ratio'] >= min_gain_ratio:
                    result = gain_info
                    project_info_failed = False
                    money_flow_failed = False
                    
                    # 获取项目信息
                    if include_project_info:
                        try:
                            project_info = advanced_analyzer.get_project_info(symbol)
                            if project_info:
                                result['project_info'] = project_info
                            else:
                                project_info_failed = True
                            time.sleep(1.5)  # CoinGecko限速
                        except Exception as e:
                            logger.debug(f"获取 {symbol} 项目信息失败: {e}")
                            project_info_failed = True
                    
                    # 获取资金流向
                    if include_money_flow:
                        try:
                            flow_data = advanced_analyzer.analyze_money_flow(symbol, start_date, end_date)
                            if flow_data is not None and not flow_data.empty:
                                result['money_flow'] = {
                                    'latest_flow': float(flow_data['money_flow'].iloc[-1]),
                                    'cumulative_flow': float(flow_data['cumulative_flow'].iloc[-1]),
                                    'avg_daily_volume': float(flow_data['volume'].mean()),
                                    'obv': float(flow_data['obv'].iloc[-1])
                                }
                            else:
                                money_flow_failed = True
                        except Exception as e:
                            logger.debug(f"分析 {symbol} 资金流向失败: {e}")
                            money_flow_failed = True
                    
                    results.append(result)
                    
                    # 记录部分失败的信息
                    if project_info_failed or money_flow_failed:
                        fail_parts = []
                        if project_info_failed:
                            fail_parts.append('项目信息')
                        if money_flow_failed:
                            fail_parts.append('资金流向')
                        
                        failed_records.append({
                            'symbol': symbol,
                            'reason': '部分数据获取失败',
                            'detail': f"无法获取: {', '.join(fail_parts)}"
                        })
                
            except Exception as e:
                logger.warning(f"分析 {symbol} 失败，跳过: {e}")
                failed_records.append({
                    'symbol': symbol,
                    'reason': '分析异常',
                    'detail': str(e)
                })
            
            time.sleep(0.3)  # 限速
        
        # 排序
        results.sort(key=lambda x: x['gain_ratio'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'start_date': start_date,
                'end_date': end_date or datetime.now().strftime('%Y-%m-%d'),
                'min_gain_ratio': min_gain_ratio,
                'total_analyzed': len(symbols),
                'qualified_count': len(results),
                'failed_count': len(failed_records),
                'results': results,
                'failed_records': failed_records  # 添加失败记录
            }
        })
        
    except Exception as e:
        logger.error(f"时间段分析失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crypto_advanced_bp.route('/get_historical_chart', methods=['POST'])
def get_historical_chart():
    """
    获取历史图表数据
    
    请求参数:
        symbol: 币种符号
        start_date: 开始日期
        end_date: 结束日期 (可选)
        interval: 时间间隔 (默认'1d')
    """
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        interval = data.get('interval', '1d')
        
        if not symbol or not start_date:
            return jsonify({
                'success': False,
                'error': '请提供symbol和start_date参数'
            }), 400
        
        df = advanced_analyzer.get_historical_klines(symbol, start_date, end_date, interval)
        
        if df.empty:
            return jsonify({
                'success': False,
                'error': f'未能获取 {symbol} 的历史数据'
            }), 404
        
        # 转换为前端图表格式
        chart_data = {
            'labels': df.index.strftime('%Y-%m-%d').tolist(),
            'prices': df['close'].tolist(),
            'volumes': df['volume'].tolist(),
            'highs': df['high'].tolist(),
            'lows': df['low'].tolist()
        }
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': chart_data
        })
        
    except Exception as e:
        logger.error(f"获取历史图表数据失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crypto_advanced_bp.route('/get_money_flow_chart', methods=['POST'])
def get_money_flow_chart():
    """
    获取资金流向图表数据
    
    请求参数:
        symbol: 币种符号
        start_date: 开始日期
        end_date: 结束日期 (可选)
    """
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not symbol or not start_date:
            return jsonify({
                'success': False,
                'error': '请提供symbol和start_date参数'
            }), 400
        
        df = advanced_analyzer.analyze_money_flow(symbol, start_date, end_date)
        
        if df is None or df.empty:
            return jsonify({
                'success': False,
                'error': f'未能分析 {symbol} 的资金流向'
            }), 404
        
        # 转换为前端图表格式
        chart_data = {
            'labels': df.index.strftime('%Y-%m-%d').tolist(),
            'money_flow': df['money_flow'].tolist(),
            'cumulative_flow': df['cumulative_flow'].tolist(),
            'obv': df['obv'].tolist(),
            'volumes': df['volume'].tolist(),
            'prices': df['close'].tolist()
        }
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': chart_data
        })
        
    except Exception as e:
        logger.error(f"获取资金流向图表数据失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

