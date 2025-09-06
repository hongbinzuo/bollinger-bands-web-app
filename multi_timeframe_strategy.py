"""
多时间框架趋势跟踪策略
基于EMA144/233/377/610的回踩策略
"""

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
        """获取K线数据"""
        try:
            # 使用币安期货API，增加重试机制
            url = f"https://fapi.binance.com/fapi/v1/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            # 设置更长的超时时间和重试
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            for attempt in range(3):  # 重试3次
                try:
                    response = session.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
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
                        
                        df.set_index('timestamp', inplace=True)
                        return df
                    else:
                        logger.warning(f"获取{symbol} {interval}数据失败: {response.status_code}, 重试 {attempt + 1}/3")
                        if attempt < 2:  # 不是最后一次重试
                            import time
                            time.sleep(1)
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"网络请求异常: {e}, 重试 {attempt + 1}/3")
                    if attempt < 2:
                        import time
                        time.sleep(2)
                    continue
            
            logger.error(f"获取{symbol} {interval}数据最终失败")
            return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取{symbol} {interval}数据异常: {e}")
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
        # 计算移动平均线（中轨）
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        
        # 计算标准差
        rolling_std = df['close'].rolling(window=period).std()
        
        # 计算上轨和下轨
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
        """找到可用的EMA回踩位置"""
        if len(df) < 2:
            return []
        
        current_price = df['close'].iloc[-1]
        available_levels = []
        
        for period in self.ema_periods:
            ema_col = f'ema{period}'
            if ema_col not in df.columns:
                continue
                
            ema_value = df[ema_col].iloc[-1]
            
            # 检查EMA是否已被使用
            symbol_key = f"{df.index[-1].strftime('%Y%m%d')}_{period}"
            if symbol_key in self.ema_usage.get(period, set()):
                continue
            
            # 判断回踩条件
            if trend == 'bullish':
                # 多头趋势：价格回踩到EMA下方附近
                if current_price <= ema_value * 1.02:  # 允许2%的误差
                    available_levels.append({
                        'ema_period': period,
                        'ema_value': ema_value,
                        'type': 'long',
                        'entry_price': ema_value
                    })
            elif trend == 'bearish':
                # 空头趋势：价格回踩到EMA上方附近
                if current_price >= ema_value * 0.98:  # 允许2%的误差
                    available_levels.append({
                        'ema_period': period,
                        'ema_value': ema_value,
                        'type': 'short',
                        'entry_price': ema_value
                    })
        
        return available_levels
    
    def get_take_profit_price(self, symbol: str, timeframe: str) -> float:
        """获取止盈价格（布林中轨）"""
        try:
            take_profit_tf = self.take_profit_timeframes.get(timeframe, '3m')
            df = self.get_klines_data(symbol, take_profit_tf, 100)
            
            if df.empty:
                return 0
            
            df = self.calculate_bollinger_bands(df)
            return df['bb_middle'].iloc[-1]
            
        except Exception as e:
            logger.error(f"获取{symbol} {timeframe}止盈价格失败: {e}")
            return 0
    
    def analyze_symbol_timeframe(self, symbol: str, timeframe: str) -> Dict:
        """分析单个币种单个时间框架"""
        try:
            # 获取主时间框架数据
            df = self.get_klines_data(symbol, timeframe, 1000)
            if df.empty or len(df) < 610:  # 需要足够的数据计算EMA610
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'insufficient_data',
                    'message': f'数据不足: {len(df)}条'
                }
            
            # 计算指标
            df = self.calculate_emas(df)
            
            # 判断趋势
            if self.is_bullish_trend(df):
                trend = 'bullish'
                trend_text = '多头趋势'
            elif self.is_bearish_trend(df):
                trend = 'bearish'
                trend_text = '空头趋势'
            else:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'no_clear_trend',
                    'message': '趋势不明确'
                }
            
            # 找到可用的EMA回踩位置
            pullback_levels = self.find_ema_pullback_levels(df, trend)
            
            if not pullback_levels:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'no_pullback',
                    'message': '无可用回踩位置'
                }
            
            # 选择最佳回踩位置（优先选择EMA144）
            best_level = pullback_levels[0]
            for level in pullback_levels:
                if level['ema_period'] == 144:
                    best_level = level
                    break
            
            # 获取止盈价格
            take_profit = self.get_take_profit_price(symbol, timeframe)
            
            if take_profit == 0:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'no_take_profit',
                    'message': '无法获取止盈价格'
                }
            
            # 计算收益
            entry_price = best_level['entry_price']
            if best_level['type'] == 'long':
                profit = take_profit - entry_price
                profit_pct = (profit / entry_price) * 100
            else:
                profit = entry_price - take_profit
                profit_pct = (profit / entry_price) * 100
            
            # 标记EMA已使用
            if best_level['ema_period'] not in self.ema_usage:
                self.ema_usage[best_level['ema_period']] = set()
            self.ema_usage[best_level['ema_period']].add(f"{df.index[-1].strftime('%Y%m%d')}_{best_level['ema_period']}")
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'success',
                'trend': trend_text,
                'ema_period': best_level['ema_period'],
                'entry_price': round(entry_price, 6),
                'take_profit': round(take_profit, 6),
                'profit_pct': round(profit_pct, 2),
                'signal_type': best_level['type'],
                'current_price': round(df['close'].iloc[-1], 6),
                'ema144': round(df['ema144'].iloc[-1], 6),
                'ema233': round(df['ema233'].iloc[-1], 6),
                'signal_time': df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"分析{symbol} {timeframe}失败: {e}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'error',
                'message': str(e)
            }
    
    def analyze_all_timeframes(self, symbol: str) -> List[Dict]:
        """分析单个币种的所有时间框架"""
        results = []
        for timeframe in self.timeframes:
            result = self.analyze_symbol_timeframe(symbol, timeframe)
            results.append(result)
        return results
    
    def analyze_multiple_symbols(self, symbols: List[str]) -> Dict:
        """分析多个币种"""
        all_results = {}
        
        for symbol in symbols:
            logger.info(f"分析币种: {symbol}")
            results = self.analyze_all_timeframes(symbol)
            all_results[symbol] = results
            
            # 避免请求过于频繁
            import time
            time.sleep(0.1)
        
        return all_results
    
    def format_price(self, price: float) -> str:
        """智能格式化价格显示"""
        if price == 0:
            return "0"
        elif price >= 1:
            return f"{price:.4f}"
        elif price >= 0.01:
            return f"{price:.6f}"
        elif price >= 0.0001:
            return f"{price:.8f}"
        else:
            return f"{price:.10f}"
