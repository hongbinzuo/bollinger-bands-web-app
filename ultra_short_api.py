from flask import Blueprint, request, jsonify
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import sqlite3
import os
import json

logger = logging.getLogger(__name__)

# 创建Blueprint
ultra_short_bp = Blueprint('ultra_short', __name__, url_prefix='/ultra_short')

# 数据库路径
DB_PATH = os.getenv('SQLITE_PATH', 'bollinger_strategy.db')

class UltraShortStrategy:
    """超短线BTC信号策略"""
    
    def __init__(self):
        self.gate_url = "https://api.gateio.ws/api/v4"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.symbol = "BTC_USDT"  # Gate.io格式
        self.stop_loss_points = 150  # 固定止损点数
        self.max_position_pct = 0.05  # 最大仓位5%
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 创建超短线信号表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ultra_short_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_timeframe TEXT,
                    direction_timeframe TEXT,
                    bollinger_lower REAL,
                    support_level REAL,
                    stop_loss REAL,
                    take_profit_price REAL,
                    risk_reward_ratio REAL,
                    signal_strength TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_status ON ultra_short_signals(symbol, status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON ultra_short_signals(created_at)')
            
            # 创建历史信号记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ultra_short_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    exit_reason TEXT,
                    pnl REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (signal_id) REFERENCES ultra_short_signals(id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("超短线信号数据库表初始化成功")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def _normalize_symbol(self, symbol: str) -> str:
        """标准化币种名称为Gate.io格式"""
        symbol = symbol.upper().strip()
        if symbol == "BTC" or symbol == "BTCUSDT":
            return "BTC_USDT"
        return symbol
    
    def get_klines(self, symbol: str, interval: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        try:
            gate_symbol = self._normalize_symbol(symbol)
            
            interval_map = {
                '1m': '1m', '2m': '1m', '3m': '3m', '5m': '5m',
                '15m': '15m', '1h': '1h', '4h': '4h', '12h': '12h', '1d': '1d', '1w': '1w'
            }
            gate_interval = interval_map.get(interval)
            if not gate_interval:
                gate_interval = interval
            
            url = f"{self.gate_url}/spot/candlesticks"
            params = {
                'currency_pair': gate_symbol,
                'interval': gate_interval,
                'limit': min(limit, 1000)
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list) or not data:
                return None
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            if len(data[0]) >= 6:
                df.columns = ['timestamp', 'volume', 'close', 'high', 'low', 'open'] + [f'col_{i}' for i in range(6, len(data[0]))]
            else:
                return None
            
            # 转换数据类型
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='s')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
            
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败 {symbol} {interval}: {e}")
            return None
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: float = 2) -> pd.DataFrame:
        """计算布林带"""
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std)
        return df
    
    def calculate_ema(self, df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """计算EMA"""
        for period in periods:
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        return df
    
    def is_bullish_trend(self, df: pd.DataFrame) -> bool:
        """判断1h级别是否为多头趋势（EMA89 > EMA144 > EMA233）"""
        required_emas = ['ema89', 'ema144', 'ema233']
        if not all(ema in df.columns for ema in required_emas) or len(df) < 1:
            return False
        latest = df.iloc[-1]
        return latest['ema89'] > latest['ema144'] > latest['ema233']
    
    def find_support_levels(self, symbol: str) -> List[float]:
        """识别支撑位：最近一周的1h/4h密集成交区"""
        try:
            support_levels = []
            
            # 获取最近一周的1h和4h数据
            for timeframe in ['1h', '4h']:
                df = self.get_klines(symbol, timeframe, limit=168 if timeframe == '1h' else 42)
                if df is None or len(df) < 20:
                    continue
                
                # 使用成交量加权价格（VWAP）识别密集成交区
                df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
                df['vwap'] = (df['typical_price'] * df['volume']).rolling(window=20).sum() / df['volume'].rolling(window=20).sum()
                
                # 识别价格密集区域（价格在一定范围内的K线数量）
                price_range = df['close'].max() - df['close'].min()
                bin_size = price_range / 20  # 分成20个区间
                
                # 计算每个价格区间的成交量
                bins = np.arange(df['close'].min(), df['close'].max() + bin_size, bin_size)
                df['price_bin'] = pd.cut(df['close'], bins=bins)
                volume_by_bin = df.groupby('price_bin')['volume'].sum()
                
                # 找出成交量最大的3个区间作为支撑位
                top_bins = volume_by_bin.nlargest(3)
                for bin_idx, volume in top_bins.items():
                    if pd.notna(bin_idx):
                        support_price = bin_idx.mid  # 区间的中点
                        support_levels.append(round(support_price, 2))
            
            # 去重并排序
            support_levels = sorted(list(set(support_levels)), reverse=True)
            return support_levels[:5]  # 返回前5个支撑位
            
        except Exception as e:
            logger.error(f"识别支撑位失败: {e}")
            return []
    
    def check_signal(self, symbol: str = "BTC") -> Optional[Dict]:
        """检查是否有信号"""
        try:
            # 1. 获取1h数据，判断方向
            df_1h = self.get_klines(symbol, '1h', limit=200)
            if df_1h is None or len(df_1h) < 100:
                return None
            
            # 计算EMA
            df_1h = self.calculate_ema(df_1h, [89, 144, 233])
            df_1h = df_1h.dropna()
            
            if len(df_1h) < 1:
                return None
            
            # 检查是否为多头趋势
            if not self.is_bullish_trend(df_1h):
                return None
            
            # 2. 获取1-5min数据，检查布林带下轨
            entry_timeframes = ['1m', '2m', '3m', '5m']
            for entry_tf in entry_timeframes:
                df_short = self.get_klines(symbol, entry_tf, limit=100)
                if df_short is None or len(df_short) < 20:
                    continue
                
                # 计算布林带
                df_short = self.calculate_bollinger_bands(df_short, period=20, std=2)
                df_short = df_short.dropna()
                
                if len(df_short) < 1:
                    continue
                
                latest = df_short.iloc[-1]
                current_price = latest['close']
                bb_lower = latest['bb_lower']
                bb_middle = latest['bb_middle']
                
                # 检查价格是否接近下轨（在99%-100.5%下轨之间）
                if bb_lower > 0:
                    price_ratio = current_price / bb_lower
                    if 0.99 <= price_ratio <= 1.005:  # 接近下轨
                        # 获取支撑位
                        support_levels = self.find_support_levels(symbol)
                        support_level = support_levels[0] if support_levels else None
                        
                        # 计算止损和止盈（2:1盈亏比）
                        stop_loss = current_price - self.stop_loss_points
                        take_profit_price = current_price + (self.stop_loss_points * 2)  # 止损150点，止盈300点
                        risk_reward = 2.0
                        
                        # 生成信号
                        signal = {
                            'symbol': symbol,
                            'signal_type': 'long',
                            'entry_price': round(current_price, 2),
                            'entry_timeframe': entry_tf,
                            'direction_timeframe': '1h',
                            'bollinger_lower': round(bb_lower, 2),
                            'support_level': round(support_level, 2) if support_level else None,
                            'stop_loss': round(stop_loss, 2),
                            'take_profit_price': round(take_profit_price, 2),
                            'risk_reward_ratio': risk_reward,
                            'signal_strength': 'high' if support_level and current_price >= support_level * 0.99 else 'medium',
                            'current_price': round(current_price, 2),
                            'bb_middle': round(bb_middle, 2),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        return signal
            
            return None
            
        except Exception as e:
            logger.error(f"检查信号失败: {e}", exc_info=True)
            return None
    
    def save_signal(self, signal: Dict) -> int:
        """保存信号到数据库"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ultra_short_signals 
                (symbol, signal_type, entry_price, entry_timeframe, direction_timeframe,
                 bollinger_lower, support_level, stop_loss, take_profit_price,
                 risk_reward_ratio, signal_strength, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal['symbol'],
                signal['signal_type'],
                signal['entry_price'],
                signal['entry_timeframe'],
                signal['direction_timeframe'],
                signal['bollinger_lower'],
                signal.get('support_level'),
                signal['stop_loss'],
                signal['take_profit_price'],
                signal['risk_reward_ratio'],
                signal['signal_strength'],
                'active'
            ))
            
            signal_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return signal_id
            
        except Exception as e:
            logger.error(f"保存信号失败: {e}")
            return 0
    
    def get_active_signals(self) -> List[Dict]:
        """获取所有活跃信号"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM ultra_short_signals 
                WHERE status = 'active' 
                ORDER BY created_at DESC
            ''')
            
            rows = cursor.fetchall()
            signals = []
            for row in rows:
                signal = dict(row)
                signals.append(signal)
            
            conn.close()
            return signals
            
        except Exception as e:
            logger.error(f"获取活跃信号失败: {e}")
            return []
    
    def get_history_signals(self, limit: int = 50) -> List[Dict]:
        """获取历史信号"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM ultra_short_signals 
                WHERE status != 'active' 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            signals = []
            for row in rows:
                signal = dict(row)
                signals.append(signal)
            
            conn.close()
            return signals
            
        except Exception as e:
            logger.error(f"获取历史信号失败: {e}")
            return []


# 创建策略实例
strategy = UltraShortStrategy()


# API路由
@ultra_short_bp.route('/check_signal', methods=['GET', 'POST'])
def check_signal():
    """检查当前是否有信号"""
    try:
        symbol = request.args.get('symbol', 'BTC') or request.json.get('symbol', 'BTC') if request.is_json else 'BTC'
        signal = strategy.check_signal(symbol)
        
        if signal:
            # 保存信号
            signal_id = strategy.save_signal(signal)
            signal['id'] = signal_id
            
            return jsonify({
                'success': True,
                'has_signal': True,
                'signal': signal
            })
        else:
            return jsonify({
                'success': True,
                'has_signal': False,
                'signal': None
            })
            
    except Exception as e:
        logger.error(f"检查信号API失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ultra_short_bp.route('/get_klines', methods=['GET', 'POST'])
def get_klines():
    """获取K线数据（用于图表显示）"""
    try:
        data = request.json if request.is_json else {}
        symbol = data.get('symbol', 'BTC')
        interval = data.get('interval', '1m')
        limit = data.get('limit', 200)
        
        df = strategy.get_klines(symbol, interval, limit)
        
        if df is None or df.empty:
            return jsonify({'success': False, 'error': '无法获取K线数据'}), 404
        
        # 转换为JSON格式
        klines = []
        for idx, row in df.iterrows():
            klines.append({
                'time': int(idx.timestamp()),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })
        
        return jsonify({
            'success': True,
            'klines': klines,
            'symbol': symbol,
            'interval': interval
        })
        
    except Exception as e:
        logger.error(f"获取K线数据API失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ultra_short_bp.route('/get_price_info', methods=['GET', 'POST'])
def get_price_info():
    """获取价格和指标信息（用于左侧监控面板）"""
    try:
        data = request.json if request.is_json else {}
        symbol = data.get('symbol', 'BTC')
        
        result = {}
        
        # 1. 获取当前标记价格
        try:
            gate_symbol = strategy._normalize_symbol(symbol)
            ticker_url = f"{strategy.gate_url}/spot/tickers"
            ticker_response = strategy.session.get(ticker_url, params={'currency_pair': gate_symbol}, timeout=10)
            if ticker_response.status_code == 200:
                ticker_data = ticker_response.json()
                if ticker_data and len(ticker_data) > 0:
                    result['current_price'] = float(ticker_data[0].get('last', 0))
        except Exception as e:
            logger.error(f"获取当前价格失败: {e}")
            result['current_price'] = None
        
        # 2. 获取1-5min下轨均值（最新值）
        entry_timeframes = ['1m', '2m', '3m', '5m']
        bb_lower_values = []
        for tf in entry_timeframes:
            df_short = strategy.get_klines(symbol, tf, limit=100)
            if df_short is not None and not df_short.empty:
                df_short = strategy.calculate_bollinger_bands(df_short, period=20, std=2)
                df_short = df_short.dropna()
                if not df_short.empty:
                    latest = df_short.iloc[-1]
                    if pd.notna(latest['bb_lower']):
                        bb_lower_values.append(float(latest['bb_lower']))
        
        if bb_lower_values:
            result['bb_lower_avg'] = round(sum(bb_lower_values) / len(bb_lower_values), 2)
        else:
            result['bb_lower_avg'] = None
        
        # 3. 获取1h布林带（最新值：下轨、中轨、上轨）
        df_1h = strategy.get_klines(symbol, '1h', limit=200)
        if df_1h is not None and not df_1h.empty:
            df_1h = strategy.calculate_bollinger_bands(df_1h, period=20, std=2)
            df_1h = df_1h.dropna()
            if not df_1h.empty:
                latest_1h = df_1h.iloc[-1]
                result['bb_1h_lower'] = round(float(latest_1h['bb_lower']), 2) if pd.notna(latest_1h['bb_lower']) else None
                result['bb_1h_middle'] = round(float(latest_1h['bb_middle']), 2) if pd.notna(latest_1h['bb_middle']) else None
                result['bb_1h_upper'] = round(float(latest_1h['bb_upper']), 2) if pd.notna(latest_1h['bb_upper']) else None
            else:
                result['bb_1h_lower'] = None
                result['bb_1h_middle'] = None
                result['bb_1h_upper'] = None
        else:
            result['bb_1h_lower'] = None
            result['bb_1h_middle'] = None
            result['bb_1h_upper'] = None
        
        # 4. 获取1h EMA200（最新值）
        df_1h_ema = strategy.get_klines(symbol, '1h', limit=200)
        if df_1h_ema is not None and not df_1h_ema.empty:
            df_1h_ema = strategy.calculate_ema(df_1h_ema, [200])
            df_1h_ema = df_1h_ema.dropna()
            if not df_1h_ema.empty and 'ema200' in df_1h_ema.columns:
                latest_ema = df_1h_ema.iloc[-1]
                result['ema200_1h'] = round(float(latest_ema['ema200']), 2) if pd.notna(latest_ema['ema200']) else None
            else:
                result['ema200_1h'] = None
        else:
            result['ema200_1h'] = None
        
        # 5. 获取日线高、低点
        df_1d = strategy.get_klines(symbol, '1d', limit=30)
        if df_1d is not None and not df_1d.empty:
            result['daily_high'] = round(float(df_1d['high'].max()), 2)
            result['daily_low'] = round(float(df_1d['low'].min()), 2)
        else:
            result['daily_high'] = None
            result['daily_low'] = None
        
        # 6. 获取周线高、低点
        df_1w = strategy.get_klines(symbol, '1w', limit=10)
        if df_1w is not None and not df_1w.empty:
            result['weekly_high'] = round(float(df_1w['high'].max()), 2)
            result['weekly_low'] = round(float(df_1w['low'].min()), 2)
        else:
            result['weekly_high'] = None
            result['weekly_low'] = None
        
        # 7. 获取买入条件状态
        signal_info = strategy.check_signal(symbol)
        if signal_info:
            result['buy_conditions'] = {
                'trend_1h': '多头' if signal_info.get('signal_type') == 'long' else '非多头',
                'price_near_lower': True,
                'support_level': signal_info.get('support_level'),
                'signal_strength': signal_info.get('signal_strength', 'medium')
            }
        else:
            # 检查趋势
            df_1h_check = strategy.get_klines(symbol, '1h', limit=200)
            is_bullish = False
            if df_1h_check is not None and len(df_1h_check) >= 100:
                df_1h_check = strategy.calculate_ema(df_1h_check, [89, 144, 233])
                df_1h_check = df_1h_check.dropna()
                if len(df_1h_check) >= 1:
                    is_bullish = strategy.is_bullish_trend(df_1h_check)
            
            # 检查价格是否接近下轨
            price_near_lower = False
            if result.get('current_price') and result.get('bb_lower_avg'):
                ratio = result['current_price'] / result['bb_lower_avg']
                price_near_lower = 0.99 <= ratio <= 1.005
            
            result['buy_conditions'] = {
                'trend_1h': '多头' if is_bullish else '非多头',
                'price_near_lower': price_near_lower,
                'support_level': None,
                'signal_strength': None
            }
        
        return jsonify({
            'success': True,
            'data': result,
            'symbol': symbol
        })
        
    except Exception as e:
        logger.error(f"获取价格信息API失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ultra_short_bp.route('/get_indicators', methods=['GET', 'POST'])
def get_indicators():
    """获取所有指标数据（1h布林带、1-5min下轨均值、1h EMA200、1h ZigZag低点）"""
    try:
        data = request.json if request.is_json else {}
        symbol = data.get('symbol', 'BTC')
        
        result = {}
        
        # 1. 获取1h布林带（只返回下轨）
        df_1h = strategy.get_klines(symbol, '1h', limit=200)
        if df_1h is not None and not df_1h.empty:
            df_1h = strategy.calculate_bollinger_bands(df_1h, period=20, std=2)
            df_1h = df_1h.dropna()
            if not df_1h.empty:
                bb_1h = []
                for idx, row in df_1h.iterrows():
                    if pd.notna(row['bb_lower']):
                        bb_1h.append({
                            'time': int(idx.timestamp()),
                            'lower': float(row['bb_lower'])
                        })
                result['bb_1h'] = bb_1h
        
        # 2. 获取1-5min布林带下轨，计算均值
        entry_timeframes = ['1m', '2m', '3m', '5m']
        bb_lower_means = []
        for tf in entry_timeframes:
            df_short = strategy.get_klines(symbol, tf, limit=100)
            if df_short is not None and not df_short.empty:
                df_short = strategy.calculate_bollinger_bands(df_short, period=20, std=2)
                df_short = df_short.dropna()
                if not df_short.empty:
                    bb_lower_data = []
                    for idx, row in df_short.iterrows():
                        if pd.notna(row['bb_lower']):
                            bb_lower_data.append({
                                'time': int(idx.timestamp()),
                                'value': float(row['bb_lower'])
                            })
                    if bb_lower_data:
                        bb_lower_means.append({
                            'timeframe': tf,
                            'data': bb_lower_data
                        })
        
        # 计算1-5min下轨的均值（按时间对齐）
        if bb_lower_means:
            # 获取所有时间点
            all_times = set()
            for tf_data in bb_lower_means:
                for point in tf_data['data']:
                    all_times.add(point['time'])
            
            # 按时间计算均值
            bb_lower_avg = []
            for time in sorted(all_times):
                values = []
                for tf_data in bb_lower_means:
                    # 找到该时间点的值
                    for point in tf_data['data']:
                        if point['time'] == time:
                            values.append(point['value'])
                            break
                if len(values) > 0:
                    avg_value = sum(values) / len(values)
                    bb_lower_avg.append({
                        'time': time,
                        'value': avg_value
                    })
            result['bb_lower_avg'] = bb_lower_avg
        
        # 3. 获取1h ZigZag低点（简化实现，使用pivotlow逻辑，只返回最近3个）
        df_1h_zigzag = strategy.get_klines(symbol, '1h', limit=200)
        if df_1h_zigzag is not None and not df_1h_zigzag.empty:
            # 使用pivotlow识别低点
            zigzag_lows = []
            depth = 12
            for i in range(depth, len(df_1h_zigzag) - depth):
                current_low = df_1h_zigzag.iloc[i]['low']
                # 检查是否是pivot low
                is_pivot = True
                for j in range(i - depth, i):
                    if df_1h_zigzag.iloc[j]['low'] < current_low:
                        is_pivot = False
                        break
                for j in range(i + 1, i + depth + 1):
                    if df_1h_zigzag.iloc[j]['low'] < current_low:
                        is_pivot = False
                        break
                
                if is_pivot:
                    idx = df_1h_zigzag.index[i]
                    zigzag_lows.append({
                        'time': int(idx.timestamp()),
                        'value': float(current_low)
                    })
            # 只返回最近3个低点
            zigzag_lows = sorted(zigzag_lows, key=lambda x: x['time'], reverse=True)[:3]
            result['zigzag_lows_1h'] = zigzag_lows
        
        return jsonify({
            'success': True,
            'indicators': result,
            'symbol': symbol
        })
        
    except Exception as e:
        logger.error(f"获取指标数据API失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ultra_short_bp.route('/get_support_levels', methods=['GET', 'POST'])
def get_support_levels():
    """获取支撑位"""
    try:
        data = request.json if request.is_json else {}
        symbol = data.get('symbol', 'BTC')
        
        support_levels = strategy.find_support_levels(symbol)
        
        return jsonify({
            'success': True,
            'support_levels': support_levels,
            'symbol': symbol
        })
        
    except Exception as e:
        logger.error(f"获取支撑位API失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ultra_short_bp.route('/get_active_signals', methods=['GET'])
def get_active_signals():
    """获取所有活跃信号"""
    try:
        signals = strategy.get_active_signals()
        return jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals)
        })
    except Exception as e:
        logger.error(f"获取活跃信号API失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ultra_short_bp.route('/get_history_signals', methods=['GET'])
def get_history_signals():
    """获取历史信号"""
    try:
        limit = request.args.get('limit', 50, type=int)
        signals = strategy.get_history_signals(limit)
        return jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals)
        })
    except Exception as e:
        logger.error(f"获取历史信号API失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



