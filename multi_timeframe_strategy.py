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
