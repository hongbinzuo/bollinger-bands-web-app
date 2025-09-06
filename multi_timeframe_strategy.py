import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class MultiTimeframeStrategy:
    def __init__(self):
        self.timeframes = ['4h', '8h', '12h', '1d', '3d', '1w']
        self.ema_periods = [144, 233, 377, 610]
        self.bb_period = 20  # 布林带周期
        self.bb_std = 2      # 布林带标准差
        
        # 时间框架对应的止盈时间框架
        self.take_profit_timeframes = {
            '4h': '3m',   # 4小时对应3分钟
            '8h': '5m',   # 8小时对应5分钟
            '12h': '10m', # 12小时对应10分钟
            '1d': '15m',  # 1天对应15分钟
            '3d': '30m',  # 3天对应30分钟
            '1w': '1h'    # 1周对应1小时
        }
        
        # 记录每个币种每个时间框架的EMA使用情况
        self.ema_usage = {}
        
    def get_klines_data(self, symbol: str, interval: str, limit: int = 1000) -> pd.DataFrame:
        """获取K线数据 - 优先使用Gate.io API"""
        import time
        
        try:
            # 首先尝试Gate.io API
            gate_result = self._get_gate_klines(symbol, interval, limit)
            if not gate_result.empty:
                return gate_result
            
            # Gate.io失败时，尝试币安期货API作为备用
            logger.info(f"Gate.io获取失败，尝试币安期货API: {symbol} {interval}")
            binance_result = self._get_binance_futures_klines(symbol, interval, limit)
            if not binance_result.empty:
                return binance_result
            
            # 最后尝试币安现货API
            logger.info(f"币安期货API失败，尝试币安现货API: {symbol} {interval}")
            return self._get_binance_spot_klines(symbol, interval, limit)
                
        except Exception as e:
            logger.error(f"获取{symbol} {interval}数据异常: {e}")
            return pd.DataFrame()
    
    def _get_gate_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """使用Gate.io API获取K线数据"""
        import time
        
        try:
            # 转换币种格式：BTCUSDT -> BTC_USDT
            gate_symbol = symbol.replace('USDT', '_USDT')
            
            # 转换时间间隔格式
            interval_map = {
                '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
                '1d': '1d', '3d': '3d', '1w': '1w'
            }
            gate_interval = interval_map.get(interval, interval)
            
            url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': gate_symbol,
                'interval': gate_interval,
                'limit': min(limit, 1000)  # Gate.io限制最大1000
            }
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            })
            
            for attempt in range(3):
                try:
                    if attempt > 0:
                        time.sleep(1)
                    
                    response = session.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if not data:
                            logger.warning(f"Gate.io返回空数据: {symbol} {interval}")
                            continue
                        
                        # Gate.io数据格式转换 - 检查实际数据列数
                        logger.info(f"Gate.io返回数据列数: {len(data[0]) if data else 0}")
                        logger.info(f"Gate.io返回数据示例: {data[0] if data else 'None'}")
                        
                        # Gate.io实际返回格式：[timestamp, volume, close, high, low, open, amount, count]
                        if len(data[0]) == 8:
                            df = pd.DataFrame(data, columns=[
                                'timestamp', 'volume', 'close', 'high', 'low', 'open', 'amount', 'count'
                            ])
                        elif len(data[0]) == 6:
                            df = pd.DataFrame(data, columns=[
                                'timestamp', 'volume', 'close', 'high', 'low', 'open'
                            ])
                        else:
                            # 如果列数不匹配，尝试直接使用索引访问
                            logger.warning(f"列数不匹配，尝试直接索引访问")
                            df = pd.DataFrame(data)
                            # 手动设置列名
                            if len(data[0]) >= 6:
                                df.columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open'] + [f'col_{i}' for i in range(6, len(data[0]))]
                            else:
                                logger.error(f"Gate.io数据格式异常，列数: {len(data[0])}")
                                continue
                        
                        # 检查列名是否存在
                        logger.info(f"DataFrame列名: {list(df.columns)}")
                        
                        # 转换数据类型
                        if 'timestamp' in df.columns:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        else:
                            logger.error("timestamp列不存在")
                            continue
                            
                        # 确保所有必需的列都存在
                        required_columns = ['open', 'high', 'low', 'close', 'volume']
                        for col in required_columns:
                            if col in df.columns:
                                df[col] = df[col].astype(float)
                            else:
                                logger.error(f"必需列 {col} 不存在")
                                continue
                        
                        # 重新排列列顺序
                        df = df[['open', 'high', 'low', 'close', 'volume']]
                        df.set_index('timestamp', inplace=True)
                        
                        logger.info(f"Gate.io成功获取 {symbol} {interval} 数据: {len(df)} 条")
                        return df
                    else:
                        logger.warning(f"Gate.io获取{symbol} {interval}失败: {response.status_code}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Gate.io网络请求异常: {e}")
                    continue
            
            logger.error(f"Gate.io获取{symbol} {interval}数据最终失败")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Gate.io获取数据异常: {e}")
            return pd.DataFrame()
    
    def _get_binance_futures_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """使用币安期货API获取K线数据（备用）"""
        import time
        
        try:
            url = f"https://fapi.binance.com/fapi/v1/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            for attempt in range(2):  # 减少重试次数
                try:
                    if attempt > 0:
                        time.sleep(2)
                    
                    response = session.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if not data:
                            continue
                            
                        df = pd.DataFrame(data, columns=[ 
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                            'taker_buy_quote', 'ignore'
                        ])
                        
                        # 转换数据类型
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df['open'] = df['open'].astype(float)
                        df['high'] = df['high'].astype(float)
                        df['low'] = df['low'].astype(float)
                        df['close'] = df['close'].astype(float)
                        df['volume'] = df['volume'].astype(float)
                        
                        df = df[['open', 'high', 'low', 'close', 'volume']]
                        df.set_index('timestamp', inplace=True)
                        
                        logger.info(f"币安期货API成功获取 {symbol} {interval} 数据: {len(df)} 条")
                        return df
                    else:
                        logger.warning(f"币安期货API获取{symbol} {interval}失败: {response.status_code}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"币安期货API网络请求异常: {e}")
                    continue
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"币安期货API获取数据异常: {e}")
            return pd.DataFrame()
    
    def _get_binance_spot_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """使用币安现货API获取K线数据（最后备用）"""
        import time
        
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                # 转换数据类型
                df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                df = df[['open', 'high', 'low', 'close', 'volume']]
                df.set_index('timestamp', inplace=True)
                
                logger.info(f"币安现货API成功获取 {symbol} {interval} 数据: {len(df)} 条")
                return df
            else:
                logger.error(f"币安现货API也失败: {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"币安现货API获取数据异常: {e}")
            return pd.DataFrame()
    
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """计算EMA指标（纯Python实现）"""
        alpha = 2.0 / (period + 1)
        ema = pd.Series(index=prices.index, dtype=float)
        ema.iloc[0] = prices.iloc[0]
        
        for i in range(1, len(prices)):
            ema.iloc[i] = alpha * prices.iloc[i] + (1 - alpha) * ema.iloc[i-1]
        
        return ema
    
    def calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算EMA指标"""
        for period in self.ema_periods:
            df[f'ema{period}'] = self.calculate_ema(df['close'], period)
        return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: float = 2) -> pd.DataFrame:
        """计算布林带（纯Python实现）"""
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (rolling_std * std)
        df['bb_lower'] = df['bb_middle'] - (rolling_std * std)
        return df
    
    def is_bullish_trend(self, df: pd.DataFrame) -> bool:
        """判断是否为多头趋势（EMA144 > EMA233）"""
        if len(df) < 2:
            return False
        
        current_ema144 = df['ema144'].iloc[-1]
        current_ema233 = df['ema233'].iloc[-1]
        
        return current_ema144 > current_ema233
    
    def is_bearish_trend(self, df: pd.DataFrame) -> bool:
        """判断是否为空头趋势（EMA144 < EMA233）"""
        if len(df) < 2:
            return False
        
        current_ema144 = df['ema144'].iloc[-1]
        current_ema233 = df['ema233'].iloc[-1]
        
        return current_ema144 < current_ema233
    
    def find_ema_pullback_levels(self, df: pd.DataFrame, trend: str) -> List[Dict]:
        """改进：加入趋势确认和量能过滤的回踩信号"""
        if len(df) < 2:
            return []
        
        current_price = df['close'].iloc[-1]
        available_levels = []

        # 确认趋势
        if trend == 'bullish' and self.is_bullish_trend(df):
            # 多头趋势：价格回踩到EMA下方附近
            for period in self.ema_periods:
                ema_col = f'ema{period}'
                if ema_col not in df.columns:
                    continue
                
                ema_value = df[ema_col].iloc[-1]
                
                # 设置动态的回踩条件
                price_range = ema_value * 1.02  # 允许2%的误差
                if current_price <= price_range:  # 价格在2%范围内回踩
                    # 增加量能确认
                    if df['volume'].iloc[-1] > df['volume'].rolling(window=20).mean().iloc[-1]:
                        available_levels.append({
                            'ema_period': period,
                            'ema_value': ema_value,
                            'type': 'long',
                            'entry_price': ema_value
                        })
        
        elif trend == 'bearish' and self.is_bearish_trend(df):
            # 空头趋势：价格回踩到EMA上方附近
            for period in self.ema_periods:
                ema_col = f'ema{period}'
                if ema_col not in df.columns:
                    continue
                
                ema_value = df[ema_col].iloc[-1]
                
                # 设置动态的回踩条件
                price_range = ema_value * 0.98  # 允许2%的误差
                if current_price >= price_range:  # 价格在2%范围内回踩
                    # 增加量能确认
                    if df['volume'].iloc[-1] > df['volume'].rolling(window=20).mean().iloc[-1]:
                        available_levels.append({
                            'ema_period': period,
                            'ema_value': ema_value,
                            'type': 'short',
                            'entry_price': ema_value
                        })
        
        return available_levels
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """分析单个币种的所有时间框架"""
        results = []
        
        for timeframe in self.timeframes:
            try:
                # 获取K线数据
                df = self.get_klines_data(symbol, timeframe, 1000)
                if df.empty or len(df) < 200:
                    results.append({
                        'timeframe': timeframe,
                        'status': 'error',
                        'message': f'数据不足: {len(df)} 条'
                    })
                    continue
                
                # 计算技术指标
                df = self.calculate_emas(df)
                df = self.calculate_bollinger_bands(df)
                
                # 判断趋势
                if self.is_bullish_trend(df):
                    trend = 'bullish'
                    trend_strength = 'strong' if df['ema144'].iloc[-1] > df['ema233'].iloc[-1] * 1.01 else 'weak'
                elif self.is_bearish_trend(df):
                    trend = 'bearish'
                    trend_strength = 'strong' if df['ema144'].iloc[-1] < df['ema233'].iloc[-1] * 0.99 else 'weak'
                else:
                    trend = 'neutral'
                    trend_strength = 'weak'
                
                # 寻找回踩机会
                pullback_levels = self.find_ema_pullback_levels(df, trend)
                
                # 计算止盈目标
                take_profit_timeframe = self.take_profit_timeframes.get(timeframe, '15m')
                tp_df = self.get_klines_data(symbol, take_profit_timeframe, 200)
                take_profit_price = None
                if not tp_df.empty:
                    tp_df = self.calculate_bollinger_bands(tp_df)
                    take_profit_price = tp_df['bb_middle'].iloc[-1] if 'bb_middle' in tp_df.columns else None
                
                results.append({
                    'timeframe': timeframe,
                    'status': 'success',
                    'trend': trend,
                    'trend_strength': trend_strength,
                    'current_price': df['close'].iloc[-1],
                    'ema144': df['ema144'].iloc[-1],
                    'ema233': df['ema233'].iloc[-1],
                    'pullback_levels': pullback_levels,
                    'take_profit_timeframe': take_profit_timeframe,
                    'take_profit_price': take_profit_price,
                    'signal_count': len(pullback_levels)
                })
                
            except Exception as e:
                logger.error(f"分析{symbol} {timeframe}失败: {e}")
                results.append({
                    'timeframe': timeframe,
                    'status': 'error',
                    'message': str(e)
                })
        
        return {
            'symbol': symbol,
            'results': results,
            'total_timeframes': len(self.timeframes),
            'successful_timeframes': sum(1 for r in results if r['status'] == 'success')
        }
    
    def analyze_multiple_symbols(self, symbols: List[str]) -> Dict:
        """分析多个币种 - 添加请求间隔控制"""
        import time
        all_results = {}
        
        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"开始分析币种: {symbol} ({i+1}/{len(symbols)})")
                
                # 添加请求间隔，避免API频率限制
                if i > 0:
                    delay = 0.5  # 每个请求间隔0.5秒
                    time.sleep(delay)
                
                result = self.analyze_symbol(symbol)
                all_results[symbol] = result['results']
                
                # 每10个币种后增加额外延迟
                if (i + 1) % 10 == 0:
                    logger.info(f"已处理 {i+1} 个币种，休息2秒...")
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"分析币种{symbol}失败: {e}")
                all_results[symbol] = [{
                    'timeframe': 'all',
                    'status': 'error',
                    'message': str(e)
                }]
        
        return all_results
    
    def analyze_all_timeframes(self, symbol: str) -> List[Dict]:
        """分析单个币种的所有时间框架（API兼容方法）"""
        result = self.analyze_symbol(symbol)
        return result['results']
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证币种是否存在"""
        try:
            df = self.get_klines_data(symbol, '1d', 10)
            return not df.empty
        except Exception as e:
            logger.error(f"验证币种{symbol}失败: {e}")
            return False
