import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os
import pickle

logger = logging.getLogger(__name__)

class IntradayAnalyzer:
    """日内交易分析器"""
    
    def __init__(self):
        """初始化日内交易分析器"""
        # Binance API
        self.binance_url = "https://api.binance.com/api/v3"
        # Gate.io API
        self.gate_url = "https://api.gateio.ws/api/v4"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 支持的时间周期
        self.timeframes = ['1m', '3m', '5m', '15m', '1h', '2h', '4h', '6h', '8h']
        
        # 优先时间周期（主要信号）
        self.priority_timeframes = ['15m', '1h']
        
        # 缓存目录
        self.cache_dir = "cache"
        self.intraday_cache_file = os.path.join(self.cache_dir, "intraday_cache.pkl")
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_klines_data(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """获取K线数据"""
        try:
            # 首先尝试Binance
            df = self._get_binance_klines(symbol, interval, limit)
            
            if df.empty:
                # 如果Binance失败，尝试Gate.io
                logger.info(f"Binance获取失败，尝试Gate.io...")
                gate_symbol = symbol.replace('USDT', '_USDT')
                df = self._get_gate_klines(gate_symbol, interval, limit)
            
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} {interval} K线数据失败: {e}")
            return pd.DataFrame()
    
    def _get_binance_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
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
            logger.error(f"Binance获取 {symbol} {interval} K线数据失败: {e}")
            return pd.DataFrame()
    
    def _get_gate_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """从Gate.io获取K线数据"""
        try:
            # Gate.io的interval格式转换
            interval_map = {
                '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m',
                '1h': '1h', '2h': '2h', '4h': '4h',
                '6h': '6h', '8h': '8h'
            }
            gate_interval = interval_map.get(interval, '1h')
            
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
            logger.error(f"Gate.io获取 {symbol} {interval} K线数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_ema(self, data: pd.Series, period: int = 365) -> pd.Series:
        """计算指数移动平均线"""
        try:
            return data.ewm(span=period, adjust=False).mean()
        except Exception as e:
            logger.error(f"计算EMA失败: {e}")
            return pd.Series()
    
    def calculate_ema89(self, data: pd.Series) -> pd.Series:
        """计算89周期指数移动平均线"""
        try:
            return data.ewm(span=89, adjust=False).mean()
        except Exception as e:
            logger.error(f"计算EMA89失败: {e}")
            return pd.Series()
    
    def calculate_ema144(self, data: pd.Series) -> pd.Series:
        """计算144周期指数移动平均线"""
        try:
            return data.ewm(span=144, adjust=False).mean()
        except Exception as e:
            logger.error(f"计算EMA144失败: {e}")
            return pd.Series()
    
    def calculate_ema233(self, data: pd.Series) -> pd.Series:
        """计算233周期指数移动平均线"""
        try:
            return data.ewm(span=233, adjust=False).mean()
        except Exception as e:
            logger.error(f"计算EMA233失败: {e}")
            return pd.Series()
    
    def calculate_ma(self, data: pd.Series, period: int = 365) -> pd.Series:
        """计算简单移动平均线"""
        try:
            return data.rolling(window=period).mean()
        except Exception as e:
            logger.error(f"计算MA失败: {e}")
            return pd.Series()
    
    def calculate_ma89(self, data: pd.Series) -> pd.Series:
        """计算89周期简单移动平均线"""
        try:
            return data.rolling(window=89).mean()
        except Exception as e:
            logger.error(f"计算MA89失败: {e}")
            return pd.Series()
    
    def calculate_ma144(self, data: pd.Series) -> pd.Series:
        """计算144周期简单移动平均线"""
        try:
            return data.rolling(window=144).mean()
        except Exception as e:
            logger.error(f"计算MA144失败: {e}")
            return pd.Series()
    
    def calculate_ma233(self, data: pd.Series) -> pd.Series:
        """计算233周期简单移动平均线"""
        try:
            return data.rolling(window=233).mean()
        except Exception as e:
            logger.error(f"计算MA233失败: {e}")
            return pd.Series()
    
    def calculate_ma365(self, data: pd.Series) -> pd.Series:
        """计算365周期简单移动平均线"""
        try:
            return data.rolling(window=365).mean()
        except Exception as e:
            logger.error(f"计算MA365失败: {e}")
            return pd.Series()
    
    def detect_cross_points(self, prices: pd.Series, indicators: dict, tolerance: float = 0.001) -> dict:
        """检测交叉点位（误差在千分之1以内）"""
        try:
            cross_points = {
                'price_crosses': [],  # 价格与均线交叉
                'indicator_crosses': []  # 均线与均线交叉
            }
            
            # 检测价格与各均线的交叉
            for indicator_name, indicator_data in indicators.items():
                if indicator_data is None or len(indicator_data) < 2:
                    continue
                    
                for i in range(1, len(prices)):
                    if pd.isna(prices.iloc[i]) or pd.isna(prices.iloc[i-1]) or \
                       pd.isna(indicator_data.iloc[i]) or pd.isna(indicator_data.iloc[i-1]):
                        continue
                    
                    # 检查是否发生交叉
                    price_prev = prices.iloc[i-1]
                    price_curr = prices.iloc[i]
                    ind_prev = indicator_data.iloc[i-1]
                    ind_curr = indicator_data.iloc[i]
                    
                    # 计算交叉点
                    if (price_prev <= ind_prev and price_curr >= ind_curr) or \
                       (price_prev >= ind_prev and price_curr <= ind_curr):
                        
                        # 计算精确交叉点
                        cross_price = self._calculate_cross_price(
                            price_prev, price_curr, ind_prev, ind_curr
                        )
                        
                        # 验证误差是否在容忍范围内
                        if self._validate_cross_accuracy(cross_price, price_curr, ind_curr, tolerance):
                            cross_points['price_crosses'].append({
                                'timestamp': prices.index[i],
                                'price': cross_price,
                                'indicator': indicator_name,
                                'type': 'golden_cross' if price_curr > ind_curr else 'death_cross',
                                'index': i
                            })
            
            # 检测均线与均线的交叉
            indicator_names = list(indicators.keys())
            for i in range(len(indicator_names)):
                for j in range(i + 1, len(indicator_names)):
                    ind1_name = indicator_names[i]
                    ind2_name = indicator_names[j]
                    ind1_data = indicators[ind1_name]
                    ind2_data = indicators[ind2_name]
                    
                    if ind1_data is None or ind2_data is None or len(ind1_data) < 2:
                        continue
                    
                    for k in range(1, len(ind1_data)):
                        if pd.isna(ind1_data.iloc[k]) or pd.isna(ind1_data.iloc[k-1]) or \
                           pd.isna(ind2_data.iloc[k]) or pd.isna(ind2_data.iloc[k-1]):
                            continue
                        
                        ind1_prev = ind1_data.iloc[k-1]
                        ind1_curr = ind1_data.iloc[k]
                        ind2_prev = ind2_data.iloc[k-1]
                        ind2_curr = ind2_data.iloc[k]
                        
                        # 检查是否发生交叉
                        if (ind1_prev <= ind2_prev and ind1_curr >= ind2_curr) or \
                           (ind1_prev >= ind2_prev and ind1_curr <= ind2_curr):
                            
                            # 计算精确交叉点
                            cross_price = self._calculate_cross_price(
                                ind1_prev, ind1_curr, ind2_prev, ind2_curr
                            )
                            
                            # 验证误差是否在容忍范围内
                            if self._validate_cross_accuracy(cross_price, ind1_curr, ind2_curr, tolerance):
                                cross_points['indicator_crosses'].append({
                                    'timestamp': ind1_data.index[k],
                                    'price': cross_price,
                                    'indicator1': ind1_name,
                                    'indicator2': ind2_name,
                                    'type': 'golden_cross' if ind1_curr > ind2_curr else 'death_cross',
                                    'index': k
                                })
            
            return cross_points
            
        except Exception as e:
            logger.error(f"检测交叉点位失败: {e}")
            return {'price_crosses': [], 'indicator_crosses': []}
    
    def _calculate_cross_price(self, y1_prev: float, y1_curr: float, y2_prev: float, y2_curr: float) -> float:
        """计算两条线的精确交叉点价格"""
        try:
            # 使用线性插值计算交叉点
            # 假设时间间隔为1，计算交叉点的y值
            if abs(y1_curr - y1_prev - (y2_curr - y2_prev)) < 1e-10:
                # 平行线，返回当前值
                return (y1_curr + y2_curr) / 2
            
            # 计算交叉点
            t = (y2_prev - y1_prev) / ((y1_curr - y1_prev) - (y2_curr - y2_prev))
            cross_price = y1_prev + t * (y1_curr - y1_prev)
            
            return cross_price
            
        except Exception as e:
            logger.error(f"计算交叉点价格失败: {e}")
            return (y1_curr + y2_curr) / 2
    
    def _validate_cross_accuracy(self, cross_price: float, val1: float, val2: float, tolerance: float) -> bool:
        """验证交叉点精度是否在容忍范围内"""
        try:
            # 计算交叉点与两条线的距离
            dist1 = abs(cross_price - val1) / val1 if val1 != 0 else float('inf')
            dist2 = abs(cross_price - val2) / val2 if val2 != 0 else float('inf')
            
            # 检查是否在容忍范围内
            return dist1 <= tolerance and dist2 <= tolerance
            
        except Exception as e:
            logger.error(f"验证交叉点精度失败: {e}")
            return False
    
    def calculate_anchor_point(self, ema: float, ma: float) -> float:
        """计算锚点（EMA365和MA365的中间值）"""
        try:
            return (ema + ma) / 2
        except Exception as e:
            logger.error(f"计算锚点失败: {e}")
            return 0.0
    
    def generate_signal(self, current_price: float, anchor_point: float) -> Dict:
        """生成交易信号"""
        try:
            if current_price > anchor_point:
                signal = "多头"
                signal_type = "long"
                strength = "强" if (current_price - anchor_point) / anchor_point > 0.02 else "中"
            elif current_price < anchor_point:
                signal = "空头"
                signal_type = "short"
                strength = "强" if (anchor_point - current_price) / anchor_point > 0.02 else "中"
            else:
                signal = "空头"
                signal_type = "short"
                strength = "弱"
            
            # 计算偏离度
            deviation = abs(current_price - anchor_point) / anchor_point * 100
            
            return {
                'signal': signal,
                'signal_type': signal_type,
                'strength': strength,
                'deviation': round(deviation, 2),
                'current_price': current_price,
                'anchor_point': anchor_point
            }
            
        except Exception as e:
            logger.error(f"生成信号失败: {e}")
            return {
                'signal': '未知',
                'signal_type': 'unknown',
                'strength': '弱',
                'deviation': 0.0,
                'current_price': current_price,
                'anchor_point': anchor_point
            }
    
    def analyze_symbol_timeframe(self, symbol: str, timeframe: str, force_refresh: bool = False) -> Dict:
        """分析单个币种在特定时间周期的信号"""
        try:
            logger.info(f"分析 {symbol} {timeframe}")
            
            # 检查缓存
            if not force_refresh:
                cached_result = self.get_cached_result(symbol, timeframe)
                if cached_result:
                    logger.info(f"使用缓存数据: {symbol} {timeframe}")
                    return cached_result
            
            # 获取K线数据
            df = self.get_klines_data(symbol, timeframe, 500)
            
            if df.empty or len(df) < 365:
                result = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'current_price': None,
                    'ema365': None,
                    'ma365': None,
                    'anchor_point': None,
                    'signal': '数据不足',
                    'signal_type': 'unknown',
                    'strength': '弱',
                    'deviation': 0.0,
                    'status': '✗ 数据不足',
                    'cache_date': datetime.now().isoformat()
                }
                self.save_to_cache(symbol, timeframe, result)
                return result
            
            # 计算技术指标
            ema365 = self.calculate_ema(df['close'], 365)
            ma365 = self.calculate_ma(df['close'], 365)
            
            if ema365.empty or ma365.empty:
                result = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'current_price': None,
                    'ema365': None,
                    'ma365': None,
                    'anchor_point': None,
                    'signal': '计算失败',
                    'signal_type': 'unknown',
                    'strength': '弱',
                    'deviation': 0.0,
                    'status': '✗ 计算失败',
                    'cache_date': datetime.now().isoformat()
                }
                self.save_to_cache(symbol, timeframe, result)
                return result
            
            # 获取最新值
            current_price = df['close'].iloc[-1]
            current_ema365 = ema365.iloc[-1]
            current_ma365 = ma365.iloc[-1]
            
            # 计算锚点
            anchor_point = self.calculate_anchor_point(current_ema365, current_ma365)
            
            # 生成信号
            signal_data = self.generate_signal(current_price, anchor_point)
            
            result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': round(current_price, 6),
                'ema365': round(current_ema365, 6),
                'ma365': round(current_ma365, 6),
                'anchor_point': round(anchor_point, 6),
                'signal': signal_data['signal'],
                'signal_type': signal_data['signal_type'],
                'strength': signal_data['strength'],
                'deviation': signal_data['deviation'],
                'status': '✓ 成功',
                'cache_date': datetime.now().isoformat()
            }
            
            # 保存到缓存
            self.save_to_cache(symbol, timeframe, result)
            return result
            
        except Exception as e:
            logger.error(f"分析 {symbol} {timeframe} 时出错: {e}")
            result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': None,
                'ema365': None,
                'ma365': None,
                'anchor_point': None,
                'signal': '错误',
                'signal_type': 'unknown',
                'strength': '弱',
                'deviation': 0.0,
                'status': '✗ 错误',
                'cache_date': datetime.now().isoformat()
            }
            self.save_to_cache(symbol, timeframe, result)
            return result
    
    def analyze_symbol_all_timeframes(self, symbol: str, force_refresh: bool = False) -> Dict:
        """分析单个币种在所有时间周期的信号"""
        try:
            results = {}
            
            for timeframe in self.timeframes:
                result = self.analyze_symbol_timeframe(symbol, timeframe, force_refresh)
                results[timeframe] = result
                
                # 延迟控制，避免API限制
                time.sleep(0.1)
            
            # 计算综合信号（基于优先时间周期）
            priority_signals = []
            for tf in self.priority_timeframes:
                if tf in results and results[tf]['status'] == '✓ 成功':
                    priority_signals.append(results[tf]['signal_type'])
            
            # 综合信号逻辑
            if len(priority_signals) >= 2:
                if priority_signals[0] == priority_signals[1]:
                    overall_signal = priority_signals[0]
                else:
                    overall_signal = 'mixed'  # 信号不一致
            elif len(priority_signals) == 1:
                overall_signal = priority_signals[0]
            else:
                overall_signal = 'unknown'
            
            return {
                'symbol': symbol,
                'overall_signal': overall_signal,
                'timeframes': results,
                'priority_timeframes': self.priority_timeframes,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"分析 {symbol} 所有时间周期时出错: {e}")
            return {
                'symbol': symbol,
                'overall_signal': 'unknown',
                'timeframes': {},
                'priority_timeframes': self.priority_timeframes,
                'analysis_date': datetime.now().isoformat()
            }
    
    def get_cached_result(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """获取缓存结果"""
        try:
            if not os.path.exists(self.intraday_cache_file):
                return None
            
            with open(self.intraday_cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in cache_data:
                cached_result = cache_data[cache_key]
                cache_date = datetime.fromisoformat(cached_result['cache_date'])
                current_time = datetime.now()
                
                # 检查缓存是否过期（5分钟）
                if (current_time - cache_date).total_seconds() < 300:
                    return cached_result
            
            return None
            
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            return None
    
    def save_to_cache(self, symbol: str, timeframe: str, result: Dict):
        """保存结果到缓存"""
        try:
            cache_data = {}
            if os.path.exists(self.intraday_cache_file):
                with open(self.intraday_cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
            
            cache_key = f"{symbol}_{timeframe}"
            cache_data[cache_key] = result
            
            with open(self.intraday_cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
                
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def get_chart_data(self, symbol: str, base_timeframe: str = '5m', limit: int = 200) -> Dict:
        """获取图表数据（多时间周期EMA）"""
        try:
            logger.info(f"获取 {symbol} 图表数据，基础时间周期: {base_timeframe}")
            
            # 获取基础时间周期的K线数据
            df_base = self.get_klines_data(symbol, base_timeframe, limit)
            
            if df_base.empty or len(df_base) < 100:
                return {
                    'success': False,
                    'error': '基础数据不足',
                    'symbol': symbol,
                    'timeframe': base_timeframe
                }
            
            # 计算基础时间周期的所有EMA和MA
            ema89 = self.calculate_ema89(df_base['close'])
            ema144 = self.calculate_ema144(df_base['close'])
            ema233 = self.calculate_ema233(df_base['close'])
            ema365 = self.calculate_ema(df_base['close'], 365)
            
            ma89 = self.calculate_ma89(df_base['close'])
            ma144 = self.calculate_ma144(df_base['close'])
            ma233 = self.calculate_ma233(df_base['close'])
            ma365 = self.calculate_ma365(df_base['close'])
            
            # 准备基础数据
            base_data = {
                'timestamps': df_base.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'prices': df_base['close'].tolist(),
                'ema89': ema89.tolist(),
                'ema144': ema144.tolist(),
                'ema233': ema233.tolist(),
                'ema365': ema365.tolist(),
                'ma89': ma89.tolist(),
                'ma144': ma144.tolist(),
                'ma233': ma233.tolist(),
                'ma365': ma365.tolist()
            }
            
            # 检测交叉点位
            indicators = {
                'EMA89': ema89,
                'EMA144': ema144,
                'EMA233': ema233,
                'EMA365': ema365,
                'MA89': ma89,
                'MA144': ma144,
                'MA233': ma233,
                'MA365': ma365
            }
            
            cross_points = self.detect_cross_points(df_base['close'], indicators)
            
            # 格式化交叉点位数据
            formatted_cross_points = {
                'price_crosses': [],
                'indicator_crosses': []
            }
            
            # 格式化价格与均线交叉点
            for cross in cross_points['price_crosses']:
                formatted_cross_points['price_crosses'].append({
                    'timestamp': cross['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'price': round(cross['price'], 2),
                    'indicator': cross['indicator'],
                    'type': cross['type'],
                    'index': cross['index']
                })
            
            # 格式化均线与均线交叉点
            for cross in cross_points['indicator_crosses']:
                formatted_cross_points['indicator_crosses'].append({
                    'timestamp': cross['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'price': round(cross['price'], 2),
                    'indicator1': cross['indicator1'],
                    'indicator2': cross['indicator2'],
                    'type': cross['type'],
                    'index': cross['index']
                })
            
            # 获取其他时间周期的EMA365数据
            other_timeframes = ['1m', '2m', '3m']
            timeframe_data = {}
            
            for tf in other_timeframes:
                try:
                    df_tf = self.get_klines_data(symbol, tf, limit * 2)  # 获取更多数据点
                    
                    if not df_tf.empty and len(df_tf) >= 100:
                        ema365_tf = self.calculate_ema(df_tf['close'], 365)
                        
                        # 对齐时间戳（取最近的数据点）
                        aligned_data = []
                        for base_ts in df_base.index:
                            # 找到最接近的时间点
                            closest_idx = df_tf.index.get_indexer([base_ts], method='nearest')[0]
                            if closest_idx >= 0:
                                aligned_data.append(ema365_tf.iloc[closest_idx])
                            else:
                                aligned_data.append(None)
                        
                        timeframe_data[tf] = aligned_data
                    else:
                        timeframe_data[tf] = [None] * len(df_base)
                        
                except Exception as e:
                    logger.error(f"获取 {tf} 数据失败: {e}")
                    timeframe_data[tf] = [None] * len(df_base)
            
            result = {
                'success': True,
                'symbol': symbol,
                'base_timeframe': base_timeframe,
                'base_data': base_data,
                'timeframe_data': timeframe_data,
                'cross_points': formatted_cross_points,
                'data_count': len(df_base),
                'cache_date': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取图表数据失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'timeframe': base_timeframe
            }
    
    def clear_cache(self):
        """清除缓存"""
        try:
            if os.path.exists(self.intraday_cache_file):
                os.remove(self.intraday_cache_file)
                logger.info("日内交易缓存已清除")
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")

# 全局日内交易分析器实例
intraday_analyzer = IntradayAnalyzer()
