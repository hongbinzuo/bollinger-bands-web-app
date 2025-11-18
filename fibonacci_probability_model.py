#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斐波那契概率预测模型
基于价格行为模式和强度因子的概率预测系统

本次修复/增强要点：
- 数据源：改用 Bybit 现货并自动追加 USDT 后缀；失败时回退到模拟数据。
- 采样：按时间周期换算每日bar数，正确计算limit。
- 摆动点：用最近 swing 高/低点，若最新高点相对前高是假突破则回退到前一 swing 高。
- 稳健性：安全索引、盘整强度非负化、JSON 可序列化日期。
- 概率因子：规范化速度/量能；新增与级别相关的距离因子和趋势对齐因子；权重重平衡。
"""

import logging
import requests
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from typing import List, Dict, Tuple, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
fibonacci_prob_bp = Blueprint('fibonacci_prob', __name__, url_prefix='/fibonacci-prob')

class FibonacciProbabilityModel:
    """斐波那契概率预测模型"""
    
    def __init__(self):
        self.fibonacci_levels = [1.0, 1.618, 2.618, 3.618, 4.236]
        self.fibonacci_names = ['1.0', '1.618', '2.618', '3.618', '4.236']
        # 每天不同周期的bar数
        self._bars_per_day = {
            '5m': 288,
            '15m': 96,
            '1h': 24,
            '4h': 6,
            '1d': 1
        }
        # 概率权重（可被评测脚本覆盖）
        # 初始调优基线权重（可被评测脚本覆盖）
        self.base_weights = {
            'velocity_factor': 0.18,
            'volume_factor': 0.16,
            'consolidation_factor': 0.14,
            'fake_breakout_factor': 0.12,
            'distance_factor': 0.20,
            'trend_alignment_factor': 0.20,
        }
    
    def _get_bars_per_day(self, timeframe: str) -> int:
        return self._bars_per_day.get(timeframe, 24)
        
    def get_bybit_klines(self, symbol, interval, limit):
        """从Bybit获取现货K线数据（失败返回None）"""
        try:
            interval_map = {
                '5m': '5', '15m': '15', '1h': '60', '4h': '240', '1d': 'D'
            }
            bybit_interval = interval_map.get(interval, '60')
            
            url = f"https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'spot',
                'symbol': symbol if symbol.endswith('USDT') else f"{symbol}USDT",
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
    
    def convert_bybit_data(self, klines):
        """转换Bybit数据格式"""
        converted_data = []
        for kline in klines:
            converted_data.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        return converted_data
    
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

    def calculate_fibonacci_down_extension_levels(self, base_price_high, target_price_low):
        """计算向下的斐波扩展位（从高到低延伸）。"""
        if base_price_high == 0:
            return {}
        price_range = base_price_high - target_price_low
        extension_levels = {}
        for level in self.fibonacci_levels:
            extension_price = base_price_high - (price_range * level)
            # 避免负值
            extension_levels[level] = max(0.0, extension_price)
        return extension_levels
    
    def _extract_swings(self, price_data: List[Dict], pivot: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """提取局部极值作为swing高/低点。返回([{'idx','price','ts'}], [...])"""
        n = len(price_data)
        highs = [p['high'] for p in price_data]
        lows = [p['low'] for p in price_data]
        swing_highs: List[Dict] = []
        swing_lows: List[Dict] = []
        for i in range(pivot, n - pivot):
            h = highs[i]
            l = lows[i]
            if all(h >= highs[j] for j in range(i - pivot, i + pivot + 1)):
                swing_highs.append({'idx': i, 'price': h, 'ts': price_data[i]['timestamp']})
            if all(l <= lows[j] for j in range(i - pivot, i + pivot + 1)):
                swing_lows.append({'idx': i, 'price': l, 'ts': price_data[i]['timestamp']})
        return swing_highs, swing_lows

    def _is_false_breakout(self,
                           price_data: List[Dict],
                           swing_high_idx: int,
                           prev_high_price: float,
                           timeframe: str,
                           confirm_days: Tuple[int, int] = (2, 5),
                           lookahead_days: int = 7,
                           up_thresh: float = 0.005,
                           down_thresh: float = 0.03) -> bool:
        """判断某个swing高点是否是相对前高的假突破。
        条件：当前高点高于前高，但随后的走势未创新高，且在2-5天内出现明显回落。
        """
        n = len(price_data)
        bars_per_day = self._get_bars_per_day(timeframe)
        min_bars = max(1, confirm_days[0] * bars_per_day)
        max_bars = max(min_bars, confirm_days[1] * bars_per_day)
        lookahead_bars = max_bars if lookahead_days <= confirm_days[1] else lookahead_days * bars_per_day

        hi_price = price_data[swing_high_idx]['high']
        if hi_price <= prev_high_price:
            # 不是突破，不当作“相对前高的假突破”
            return False

        end = min(n - 1, swing_high_idx + lookahead_bars)

        # 是否在观察期内很快继续创新高（非假突破）
        made_higher_high = any(price_data[k]['high'] > hi_price * (1 + up_thresh)
                               for k in range(swing_high_idx + 1, end + 1))
        if made_higher_high:
            return False

        # 在2-5天窗口内是否出现明显回落（回撤幅度与上影线逻辑结合简化）
        retr_low = min((price_data[k]['low'] for k in range(swing_high_idx + 1, min(n, swing_high_idx + max_bars + 1))),
                       default=price_data[swing_high_idx]['low'])
        retracement = (hi_price - retr_low) / max(hi_price, 1e-12)
        return retracement >= down_thresh

    def identify_historical_high_low(self, price_data: List[Dict], timeframe: str = '4h', pivot: int = 5) -> Dict:
        """使用swing点识别最近的高/低点：若最新swing高点相对前高为假突破则回退到前一高点。
        返回字段仅包含JSON可序列化类型。
        """
        n = len(price_data)
        if n == 0:
            return {
                'historical_high': 0.0,
                'high_timestamp': 0,
                'high_date': None,
                'historical_low': 0.0,
                'low_timestamp': 0,
                'low_date': None
            }

        swing_highs, swing_lows = self._extract_swings(price_data, pivot=pivot)
        if not swing_highs:
            # 兜底：用全局高点/低点
            highs = [p['high'] for p in price_data]
            lows = [p['low'] for p in price_data]
            hi_idx = int(np.argmax(highs))
            lo_idx = int(np.argmin(lows))
            hi_ts = price_data[hi_idx]['timestamp']
            lo_ts = price_data[lo_idx]['timestamp']
            return {
                'historical_high': float(highs[hi_idx]),
                'high_timestamp': int(hi_ts),
                'high_date': datetime.utcfromtimestamp(hi_ts / 1000).isoformat(),
                'historical_low': float(lows[lo_idx]),
                'low_timestamp': int(lo_ts),
                'low_date': datetime.utcfromtimestamp(lo_ts / 1000).isoformat()
            }

        # 从最近swing高点往前找，处理“相对前高的假突破”
        sel_high = swing_highs[-1]
        if len(swing_highs) >= 2:
            k = len(swing_highs) - 1
            while k >= 1:
                cur = swing_highs[k]
                prev = swing_highs[k - 1]
                if self._is_false_breakout(price_data, cur['idx'], prev['price'], timeframe):
                    # 假突破，回退
                    k -= 1
                    sel_high = swing_highs[k]
                    continue
                else:
                    sel_high = cur
                    break

        # 选择高点之前最近的swing低点作为低点，兜底取全局最低（在高点之前）
        preceding_lows = [l for l in swing_lows if l['idx'] <= sel_high['idx']]
        if preceding_lows:
            sel_low = preceding_lows[-1]
        else:
            lows = [p['low'] for p in price_data[: sel_high['idx'] + 1]]
            lo_idx = int(np.argmin(lows)) if lows else 0
            sel_low = {'idx': lo_idx, 'price': price_data[lo_idx]['low'], 'ts': price_data[lo_idx]['timestamp']}

        hi_ts = sel_high['ts']
        lo_ts = sel_low['ts']
        return {
            'historical_high': float(sel_high['price']),
            'high_timestamp': int(hi_ts),
            'high_date': datetime.utcfromtimestamp(hi_ts / 1000).isoformat(),
            'historical_low': float(sel_low['price']),
            'low_timestamp': int(lo_ts),
            'low_date': datetime.utcfromtimestamp(lo_ts / 1000).isoformat()
        }
    
    def analyze_price_velocity(self, price_data, window=20):
        """分析价格运动速度"""
        velocities = []
        
        for i in range(window, len(price_data)):
            # 计算价格变化率
            price_change = (price_data[i]['close'] - price_data[i-window]['close']) / price_data[i-window]['close']
            
            # 计算时间间隔（小时）
            time_diff = (price_data[i]['timestamp'] - price_data[i-window]['timestamp']) / (1000 * 3600)
            
            # 速度 = 价格变化率 / 时间
            velocity = price_change / time_diff if time_diff > 0 else 0
            velocities.append({
                'timestamp': price_data[i]['timestamp'],
                'velocity': velocity,
                'price_change': price_change
            })
        
        return velocities
    
    def calculate_volume_energy(self, price_data, window=20):
        """计算量能累积强度"""
        volume_energies = []
        
        for i in range(window, len(price_data)):
            # 计算成交量加权平均
            volumes = [price_data[j]['volume'] for j in range(i-window, i)]
            avg_volume = sum(volumes) / len(volumes)
            
            # 计算价格变化
            price_change = abs(price_data[i]['close'] - price_data[i-window]['close']) / price_data[i-window]['close']
            
            # 量能强度 = 成交量 × 价格变化
            volume_energy = avg_volume * price_change
            volume_energies.append({
                'timestamp': price_data[i]['timestamp'],
                'volume_energy': volume_energy,
                'avg_volume': avg_volume,
                'price_change': price_change
            })
        
        return volume_energies

    def _compute_indicators(self, price_data: List[Dict], atr_period: int = 14,
                             rsi_period: int = 14, adx_period: int = 14) -> Dict:
        """计算基础技术指标：ATR/RSI/ADX/+DI/-DI（简单SMA版）。
        返回包含全量序列与最后值，便于概率计算和可视化。
        """
        n = len(price_data)
        if n < 2:
            return {
                'atr': [], 'atr_last': 0.0,
                'rsi': [], 'rsi_last': 50.0,
                'adx': [], 'adx_last': 0.0,
                'pdi': [], 'mdi': [], 'pdi_last': 0.0, 'mdi_last': 0.0,
            }
        highs = np.array([p['high'] for p in price_data], dtype=float)
        lows = np.array([p['low'] for p in price_data], dtype=float)
        closes = np.array([p['close'] for p in price_data], dtype=float)

        # TR
        prev_close = np.roll(closes, 1)
        prev_close[0] = closes[0]
        tr = np.maximum(highs - lows, np.maximum(np.abs(highs - prev_close), np.abs(lows - prev_close)))
        # ATR（SMA）
        atr = np.full(n, np.nan)
        if n >= atr_period:
            atr[:atr_period] = np.nan
            for i in range(atr_period, n):
                atr[i] = np.nanmean(tr[i - atr_period + 1:i + 1])
        atr_last = float(atr[~np.isnan(atr)][-1]) if np.any(~np.isnan(atr)) else float(np.nanmean(tr))
        if np.isnan(atr_last) or atr_last <= 0:
            atr_last = 1e-6

        # RSI（SMA）
        rsi = np.full(n, np.nan)
        if n >= rsi_period + 1:
            gains = np.maximum(closes[1:] - closes[:-1], 0.0)
            losses = np.maximum(closes[:-1] - closes[1:], 0.0)
            avg_gain = np.full(n - 1, np.nan)
            avg_loss = np.full(n - 1, np.nan)
            for i in range(rsi_period, n - 1):
                avg_gain[i] = np.nanmean(gains[i - rsi_period:i])
                avg_loss[i] = np.nanmean(losses[i - rsi_period:i])
            rs = np.divide(avg_gain, np.maximum(avg_loss, 1e-12))
            rsi_vals = 100.0 - (100.0 / (1.0 + rs))
            rsi[1:] = rsi_vals
        rsi_last = float(rsi[~np.isnan(rsi)][-1]) if np.any(~np.isnan(rsi)) else 50.0

        # ADX（SMA）
        pdi = np.full(n, np.nan)
        mdi = np.full(n, np.nan)
        adx = np.full(n, np.nan)
        if n >= adx_period + 1:
            up_moves = highs[1:] - highs[:-1]
            down_moves = lows[:-1] - lows[1:]
            plus_dm = np.where((up_moves > down_moves) & (up_moves > 0), up_moves, 0.0)
            minus_dm = np.where((down_moves > up_moves) & (down_moves > 0), down_moves, 0.0)
            tr1 = tr[1:]
            tr_sma = np.full(n - 1, np.nan)
            pdi_s = np.full(n - 1, np.nan)
            mdi_s = np.full(n - 1, np.nan)
            dx = np.full(n - 1, np.nan)
            for i in range(adx_period, n - 1):
                tr_window = np.nanmean(tr1[i - adx_period:i])
                tr_sma[i] = max(tr_window, 1e-12)
                pdi_s[i] = 100.0 * (np.nanmean(plus_dm[i - adx_period:i]) / tr_sma[i])
                mdi_s[i] = 100.0 * (np.nanmean(minus_dm[i - adx_period:i]) / tr_sma[i])
                denom = max(pdi_s[i] + mdi_s[i], 1e-12)
                dx[i] = 100.0 * (abs(pdi_s[i] - mdi_s[i]) / denom)
            # ADX = SMA(DX)
            for i in range(adx_period * 2, n - 1):
                adx[i + 1] = np.nanmean(dx[i - adx_period:i])
            pdi[1:] = pdi_s
            mdi[1:] = mdi_s
        adx_last = float(adx[~np.isnan(adx)][-1]) if np.any(~np.isnan(adx)) else 0.0
        pdi_last = float(pdi[~np.isnan(pdi)][-1]) if np.any(~np.isnan(pdi)) else 0.0
        mdi_last = float(mdi[~np.isnan(mdi)][-1]) if np.any(~np.isnan(mdi)) else 0.0

        return {
            'atr': atr.tolist(), 'atr_last': float(atr_last),
            'rsi': rsi.tolist(), 'rsi_last': float(rsi_last),
            'adx': adx.tolist(), 'adx_last': float(adx_last),
            'pdi': pdi.tolist(), 'mdi': mdi.tolist(),
            'pdi_last': float(pdi_last), 'mdi_last': float(mdi_last),
        }
    
    def analyze_consolidation_strength(self, price_data, start_idx, end_idx):
        """分析盘整强度（非负化处理）"""
        if end_idx <= start_idx:
            return 0.0
        # 时间（小时）
        time_span = (price_data[end_idx]['timestamp'] - price_data[start_idx]['timestamp']) / (1000 * 3600.0)
        prices = [price_data[i]['close'] for i in range(start_idx, end_idx + 1)]
        p_min, p_max = min(prices), max(prices)
        base = max(min(prices), 1e-12)
        volatility = (p_max - p_min) / base
        volumes = [price_data[i]['volume'] for i in range(start_idx, end_idx + 1)]
        avg_volume = sum(volumes) / len(volumes)
        volume_consistency = 0.0
        if avg_volume > 0:
            volume_consistency = max(0.0, 1.0 - (np.std(volumes) / avg_volume))
        stability = max(0.0, 1.0 - volatility)
        consolidation_strength = max(0.0, time_span * volume_consistency * stability)
        return consolidation_strength
    
    def identify_fake_breakouts(self, price_data, historical_high, timeframe: str = '4h', confirm_days: Tuple[int, int] = (2, 5)):
        """识别假突破：接近历史高点的局部高点，随后2-5天内快速回落且长上影线。
        时间窗口按timeframe换算，不再使用固定bar窗口。
        """
        fake_breakouts = []
        # 转换为DataFrame便于分析
        df = pd.DataFrame(price_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp')
        
        # 找到历史高点附近的突破尝试
        high_threshold = historical_high * 0.98  # 接近历史高点的98%
        bars_per_day = self._get_bars_per_day(timeframe)
        min_bars = max(1, confirm_days[0] * bars_per_day)
        max_bars = max(min_bars, confirm_days[1] * bars_per_day)
        
        for i in range(max_bars, len(df) - max_bars):
            current_high = df.iloc[i]['high']
            current_close = df.iloc[i]['close']
            current_timestamp = df.iloc[i]['timestamp']
            
            # 检查是否接近或超过历史高点
            if current_high >= high_threshold:
                # 检查是否为局部高点
                is_local_high = True
                for j in range(max(0, i - max_bars), min(len(df), i + max_bars + 1)):
                    if j != i and df.iloc[j]['high'] > current_high:
                        is_local_high = False
                        break
                
                if is_local_high:
                    # 检查后续是否快速回落（假突破特征）
                    max_retracement = 0
                    retracement_days = 0
                    
                    for k in range(i + 1, min(i + max_bars, len(df))):
                        retracement = (current_high - df.iloc[k]['low']) / current_high
                        if retracement > max_retracement:
                            max_retracement = retracement
                            retracement_days = k - i
                    
                    # 假突破判断条件：
                    # 1. 回落超过3%
                    # 2. 在2-5天内快速回落
                    # 3. 收盘价明显低于最高价（长上影线）
                    shadow_ratio = (current_high - current_close) / current_high
                    
                    if (max_retracement > 0.03 and 
                        retracement_days <= max_bars and 
                        shadow_ratio > 0.02):  # 上影线超过2%
                        
                        fake_breakouts.append({
                            'timestamp': int(current_timestamp.timestamp() * 1000),
                            'price': current_high,
                            'retracement': max_retracement,
                            'shadow_ratio': shadow_ratio,
                            'retracement_days': retracement_days,
                            'strength': max_retracement * shadow_ratio  # 综合强度
                        })
        
        return fake_breakouts
    
    def analyze_key_zone_consolidation(self, price_data, fib_level, tolerance=0.02):
        """分析关键斐波区间的盘整"""
        zone_consolidations = []
        
        for i in range(len(price_data)):
            current_price = price_data[i]['close']
            
            # 检查是否在关键区间内
            if abs(current_price - fib_level) / fib_level <= tolerance:
                # 寻找盘整开始和结束
                start_idx = i
                end_idx = i
                
                # 向前寻找盘整开始
                for j in range(i-1, -1, -1):
                    if abs(price_data[j]['close'] - fib_level) / fib_level <= tolerance:
                        start_idx = j
                    else:
                        break
                
                # 向后寻找盘整结束
                for j in range(i+1, len(price_data)):
                    if abs(price_data[j]['close'] - fib_level) / fib_level <= tolerance:
                        end_idx = j
                    else:
                        break
                
                if end_idx > start_idx:
                    consolidation_strength = self.analyze_consolidation_strength(
                        price_data, start_idx, end_idx
                    )
                    
                    zone_consolidations.append({
                        'fib_level': fib_level,
                        'start_time': price_data[start_idx]['timestamp'],
                        'end_time': price_data[end_idx]['timestamp'],
                        'strength': consolidation_strength,
                        'duration': (price_data[end_idx]['timestamp'] - price_data[start_idx]['timestamp']) / (1000 * 3600)
                    })
        
        return zone_consolidations
    
    def calculate_breakout_probability(self, price_data, fib_level, analysis_results, timeframe: str = '4h'):
        """计算突破概率（含新增距离/趋势对齐因子与稳健归一）"""
        # 获取分析结果
        velocities = analysis_results.get('velocities', [])
        volume_energies = analysis_results.get('volume_energies', [])
        fake_breakouts = analysis_results.get('fake_breakouts', [])
        zone_consolidations = analysis_results.get('zone_consolidations', [])
        indicators = analysis_results.get('indicators', {})
        
        # 计算基础概率因子
        factors = {
            'velocity_factor': 0.0,
            'volume_factor': 0.0,
            'consolidation_factor': 0.0,
            'fake_breakout_factor': 0.0,
            'distance_factor': 0.0,
            'trend_alignment_factor': 0.0,
        }

        # 1. 速度因子
        if velocities:
            recent_velocities = velocities[-10:]  # 最近10个数据点
            avg_velocity = sum(v['velocity'] for v in recent_velocities) / len(recent_velocities)
            abs_all = [abs(v['velocity']) for v in velocities if v and 'velocity' in v]
            q = np.percentile(abs_all, 90) if abs_all else 1e-6
            norm = abs(avg_velocity) / max(q, 1e-6)
            factors['velocity_factor'] = float(max(0.0, min(1.0, norm)))

        # 2. 量能因子
        if volume_energies:
            recent_volumes = volume_energies[-10:]
            avg_volume_energy = sum(v['volume_energy'] for v in recent_volumes) / len(recent_volumes)
            all_vals = [v['volume_energy'] for v in volume_energies if v and 'volume_energy' in v]
            q = np.percentile(all_vals, 90) if all_vals else 1e-6
            norm = avg_volume_energy / max(q, 1e-6)
            factors['volume_factor'] = float(max(0.0, min(1.0, norm)))

        # 3. 盘整强度因子
        relevant_consolidations = [c for c in zone_consolidations if c['fib_level'] == fib_level]
        if relevant_consolidations:
            max_consolidation = max(relevant_consolidations, key=lambda x: x['strength'])
            factors['consolidation_factor'] = float(max(0.0, min(1.0, max_consolidation['strength'] / 100.0)))

        # 4. 假突破因子（负向影响）
        recent_bars = min(len(price_data) - 1, self._get_bars_per_day(timeframe) * 8)  # 近~8天
        anchor_ts = price_data[-recent_bars]['timestamp'] if recent_bars > 0 else price_data[0]['timestamp']
        recent_fake_breakouts = [f for f in fake_breakouts if f['timestamp'] >= anchor_ts]
        if recent_fake_breakouts:
            avg_fake_strength = sum(f.get('strength', 0.0) for f in recent_fake_breakouts) / max(1, len(recent_fake_breakouts))
            factors['fake_breakout_factor'] = -float(min(1.0, max(0.0, avg_fake_strength)))

        # 5. 距离因子（相对ATR的距离，越近越高）
        cur_price = price_data[-1]['close'] if price_data else fib_level
        atr_last = float(indicators.get('atr_last', 0.0) or 0.0)
        if atr_last <= 0:
            # 回退到相对价差
            rel_dist = abs(cur_price - fib_level) / max(fib_level, 1e-12)
            factors['distance_factor'] = float(max(0.0, min(1.0, 1.0 - (rel_dist / 0.25))))
        else:
            rel_dist_atr = abs(cur_price - fib_level) / max(atr_last, 1e-6)
            # 3 ATR 内线性衰减到0
            factors['distance_factor'] = float(max(0.0, min(1.0, 1.0 - (rel_dist_atr / 3.0))))

        # 6. 趋势对齐因子（价格动量+RSI+DI 是否指向目标位）
        if len(price_data) > 1:
            n = min(20, len(price_data) - 1)
            base_price = price_data[-n - 1]['close']
            slope = (cur_price - base_price) / max(base_price, 1e-12)
            direction = 1.0 if fib_level >= cur_price else -1.0
            # 归一化动量，映射到[-1,1]
            slope_term = float(np.tanh(slope / 0.05)) * direction
            # DI 优势 [-1,1]
            pdi = float(indicators.get('pdi_last', 0.0) or 0.0)
            mdi = float(indicators.get('mdi_last', 0.0) or 0.0)
            di_denom = max(pdi + mdi, 1e-6)
            di_term = ((pdi - mdi) / di_denom) * direction
            # RSI 偏离 [-1,1]
            rsi = float(indicators.get('rsi_last', 50.0) or 50.0)
            rsi_term = ((rsi - 50.0) / 50.0) * direction
            z = 0.5 * slope_term + 0.3 * di_term + 0.2 * rsi_term
            factors['trend_alignment_factor'] = float(max(0.0, min(1.0, (z + 1.0) / 2.0)))

        # 计算综合概率
        base_weights = dict(self.base_weights) if hasattr(self, 'base_weights') and self.base_weights else {
            'velocity_factor': 0.2,
            'volume_factor': 0.2,
            'consolidation_factor': 0.15,
            'fake_breakout_factor': 0.15,
            'distance_factor': 0.15,
            'trend_alignment_factor': 0.15,
        }
        # 动态权重：若目标位在当前价之上，更看重趋势与距离
        weights = base_weights.copy()
        # 上/下方向都加大对趋势/距离的重视
        weights['trend_alignment_factor'] += 0.05
        weights['distance_factor'] += 0.05
        weights['volume_factor'] = max(0.05, weights['volume_factor'] - 0.05)
        weights['fake_breakout_factor'] = max(0.05, weights['fake_breakout_factor'] - 0.05)
        # 归一化权重
        sw = sum(weights.values())
        if sw <= 0:
            sw = 1.0
        weights = {k: v / sw for k, v in weights.items()}
        
        probability = sum(factors[key] * weights[key] for key in weights)
        probability = max(0.0, min(1.0, probability))  # 限制在0-1之间
        
        return {
            'probability': probability,
            'factors': factors,
            'weights': weights
        }
    
    def analyze_symbol_behavior(self, symbol, timeframe='4h', days=120):
        """分析单个币种的行为模式 - 基于LIGHT币种优化"""
        try:
            logger.info(f"开始分析 {symbol} 的行为模式...")
            
            # 获取数据
            limit = min(1000, int(days * self._get_bars_per_day(timeframe)))
            price_data = self.get_bybit_klines(symbol, timeframe, limit)
            
            if not price_data:
                logger.warning(f"无法获取 {symbol} 数据，使用模拟数据")
                price_data = self.generate_mock_data(symbol, timeframe, limit)
            
            # 识别历史高点和低点
            historical_data = self.identify_historical_high_low(price_data, timeframe=timeframe)
            historical_high = historical_data['historical_high']
            historical_low = historical_data['historical_low']
            
            logger.info(f"历史高点: {historical_high:.6f} ({historical_data.get('high_date')})")
            logger.info(f"历史低点: {historical_low:.6f} ({historical_data.get('low_date')})")
            
            # 分析各种因子
            velocities = self.analyze_price_velocity(price_data)
            volume_energies = self.calculate_volume_energy(price_data)
            fake_breakouts = self.identify_fake_breakouts(price_data, historical_high, timeframe=timeframe)
            indicators = self._compute_indicators(price_data)
            
            # 计算斐波扩展位：上行（低->高）与下行（高->低）
            fib_levels = self.calculate_fibonacci_extension_levels(historical_low, historical_high)
            down_fib_levels = self.calculate_fibonacci_down_extension_levels(historical_high, historical_low)
            
            # 分析关键区间盘整
            zone_consolidations = []
            for lvl_px in list(fib_levels.values()) + list(down_fib_levels.values()):
                consolidations = self.analyze_key_zone_consolidation(price_data, lvl_px)
                zone_consolidations.extend(consolidations)
            
            # 计算每个斐波位点的概率
            analysis_results = {
                'velocities': velocities,
                'volume_energies': volume_energies,
                'fake_breakouts': fake_breakouts,
                'zone_consolidations': zone_consolidations,
                'historical_data': historical_data,
                'indicators': indicators
            }
            
            fib_probabilities = {}
            for level, price in fib_levels.items():
                prob_result = self.calculate_breakout_probability(price_data, price, analysis_results, timeframe=timeframe)
                fib_probabilities[level] = {
                    'price': price,
                    'probability': prob_result['probability'],
                    'factors': prob_result['factors']
                }
            down_probabilities = {}
            for level, price in down_fib_levels.items():
                prob_result = self.calculate_breakout_probability(price_data, price, analysis_results, timeframe=timeframe)
                down_probabilities[level] = {
                    'price': price,
                    'probability': prob_result['probability'],
                    'factors': prob_result['factors']
                }
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'data_points': len(price_data),
                'fib_levels': fib_levels,
                'down_fib_levels': down_fib_levels,
                'probabilities': fib_probabilities,
                'down_probabilities': down_probabilities,
                'analysis_results': analysis_results,
                'historical_high': historical_high,
                'historical_low': historical_low,
                'fake_breakout_count': len(fake_breakouts)
            }
            
        except Exception as e:
            logger.error(f"分析 {symbol} 失败: {e}")
            return None
    
    def generate_mock_data(self, symbol, timeframe, limit, seed: Optional[int] = None):
        """生成可重复的模拟数据（按 symbol+timeframe 派生种子）。"""
        data = []
        now = int(time.time() * 1000)
        interval_map = {
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 1000 * 60,
            '1d': 24 * 60 * 60 * 1000
        }
        interval = interval_map.get(timeframe, 60 * 60 * 1000)
        # 针对不同symbol/timeframe保持可重复
        if seed is None:
            seed = (abs(hash(f"{symbol}:{timeframe}")) % (2**32))
        rng = np.random.default_rng(seed)
        base_price = 1.0
        price = base_price
        for i in range(limit):
            timestamp = now - (limit - i) * interval
            change = rng.normal(0, 0.02)
            price = max(0.01, price * (1 + change))
            data.append({
                'timestamp': int(timestamp),
                'open': float(price * (1 + rng.normal(0, 0.005))),
                'high': float(price * (1 + abs(rng.normal(0, 0.01)))),
                'low': float(price * (1 - abs(rng.normal(0, 0.01)))),
                'close': float(price),
                'volume': float(rng.uniform(1e5, 1e6))
            })
        return data

# 创建模型实例
model = FibonacciProbabilityModel()

@fibonacci_prob_bp.route('/api/analyze', methods=['POST'])
def analyze_fibonacci_probability():
    """分析斐波那契概率"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'H')
        timeframe = data.get('timeframe', '4h')
        days = data.get('days', 120)
        
        result = model.analyze_symbol_behavior(symbol, timeframe, days)
        
        if result:
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'error': '分析失败'
            }), 500
            
    except Exception as e:
        logger.error(f"斐波那契概率分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@fibonacci_prob_bp.route('/api/batch-analyze', methods=['POST'])
def batch_analyze_symbols():
    """批量分析多个币种"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', ['H', 'KGEN', 'BANK', 'LA', 'F'])
        timeframe = data.get('timeframe', '4h')
        days = data.get('days', 120)
        
        results = []
        for symbol in symbols:
            logger.info(f"分析 {symbol}...")
            result = model.analyze_symbol_behavior(symbol, timeframe, days)
            if result:
                results.append(result)
            time.sleep(0.1)  # 避免API限制
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
