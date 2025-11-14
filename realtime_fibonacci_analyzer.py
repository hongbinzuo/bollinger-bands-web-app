#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时斐波分析（重写版）
- 数据源：Gate.io 或 Bybit（默认 Gate.io）
- 扫描前 N（最多1000）个交易对，排除稳定币
- 识别最近斐波高/低点，计算当前价格所在的斐波位置（0-1区间及>1扩展位）
- 提供单币分析与批量扫描接口
"""

import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

realtime_fib_bp = Blueprint('realtime_fib', __name__, url_prefix='/realtime-fib')


# ----------------------------- 核心数据结构 -----------------------------

FIB_LEVELS = [
    0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.414, 1.618, 2.0, 2.618, 3.618, 4.236
]

STABLECOIN_BASES = {
    'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USDD', 'EURS', 'EURT', 'GUSD', 'UST', 'PAX'
}


@dataclass
class Swing:
    low: float
    low_ts: int
    high: float
    high_ts: int
    trend: str  # 'up' or 'down'


class RealtimeFibonacciV2:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    # ----------------------------- 工具函数 -----------------------------
    def _ok(self, x) -> bool:
        try:
            return x is not None and not (isinstance(x, float) and (np.isnan(x) or np.isinf(x)))
        except Exception:
            return False

    # ----------------------------- 交易对列表 -----------------------------
    def get_gate_top_symbols(self, limit: int = 1000) -> List[str]:
        url = 'https://api.gateio.ws/api/v4/spot/tickers'
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            pairs: List[Tuple[str, float]] = []
            for item in data:
                cp = item.get('currency_pair', '')  # e.g., BTC_USDT
                if not cp or '_USDT' not in cp:
                    continue
                base = cp.split('_')[0]
                if base.upper() in STABLECOIN_BASES:
                    continue
                # 排除杠杆/奇异代币
                base_up = base.upper()
                if any(k in base_up for k in ['3L', '3S', '5L', '5S', 'BULL', 'BEAR']):
                    continue
                qv = float(item.get('quote_volume', 0) or 0)
                symbol = f"{base.upper()}USDT"
                pairs.append((symbol, qv))
            pairs.sort(key=lambda x: x[1], reverse=True)
            return [s for s, _ in pairs[: min(limit, 1000)]]
        except Exception as e:
            logger.error(f"Gate.io 获取交易对失败: {e}")
            # 兜底：常见主流币
            return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']

    def get_bybit_top_symbols(self, limit: int = 1000) -> List[str]:
        url = 'https://api.bybit.com/v5/market/tickers'
        params = {'category': 'spot'}
        try:
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get('retCode') != 0:
                raise RuntimeError(data.get('retMsg'))
            items = data.get('result', {}).get('list', [])
            pairs: List[Tuple[str, float]] = []
            for it in items:
                symbol = it.get('symbol', '')  # e.g., BTCUSDT
                if not symbol.endswith('USDT'):
                    continue
                base = symbol[:-4]
                if base.upper() in STABLECOIN_BASES:
                    continue
                if any(k in base.upper() for k in ['3L', '3S', '5L', '5S', 'BULL', 'BEAR']):
                    continue
                qv = float(it.get('turnover24h', 0) or 0)
                pairs.append((symbol, qv))
            pairs.sort(key=lambda x: x[1], reverse=True)
            return [s for s, _ in pairs[: min(limit, 1000)]]
        except Exception as e:
            logger.error(f"Bybit 获取交易对失败: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']

    # ----------------------------- 行情数据 -----------------------------
    def get_klines_gate(self, symbol: str, interval: str = '1d', limit: int = 300) -> Optional[pd.DataFrame]:
        try:
            cp = symbol
            if symbol.endswith('USDT') and '_' not in symbol:
                cp = f"{symbol[:-4]}_USDT"
            url = 'https://api.gateio.ws/api/v4/spot/candlesticks'
            params = {'currency_pair': cp, 'interval': interval, 'limit': min(limit, 1000)}
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            raw = r.json()  # [t, vol, close, high, low, open, ...]
            if not raw:
                return None
            df = pd.DataFrame(raw, columns=['t', 'vol', 'close', 'high', 'low', 'open', 'x1', 'x2'])
            for col in ['open', 'high', 'low', 'close', 'vol']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['t'] = pd.to_datetime(pd.to_numeric(df['t'], errors='coerce'), unit='s')
            df = df[['t', 'open', 'high', 'low', 'close', 'vol']].dropna()
            return df.sort_values('t').reset_index(drop=True)
        except Exception as e:
            logger.debug(f"Gate kline 失败 {symbol}: {e}")
            return None

    def get_klines_bybit(self, symbol: str, interval: str = 'D', limit: int = 300) -> Optional[pd.DataFrame]:
        try:
            url = 'https://api.bybit.com/v5/market/kline'
            params = {'category': 'spot', 'symbol': symbol, 'interval': interval, 'limit': min(limit, 1000)}
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get('retCode') != 0:
                return None
            rows = data.get('result', {}).get('list', [])
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=['t', 'open', 'high', 'low', 'close', 'vol', 'turnover'])
            for col in ['open', 'high', 'low', 'close', 'vol']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['t'] = pd.to_datetime(pd.to_numeric(df['t'], errors='coerce'), unit='ms')
            df = df[['t', 'open', 'high', 'low', 'close', 'vol']].dropna()
            return df.sort_values('t').reset_index(drop=True)
        except Exception as e:
            logger.debug(f"Bybit kline 失败 {symbol}: {e}")
            return None

    # ----------------------------- 斐波计算 -----------------------------
    def find_recent_swing(self, df: pd.DataFrame, pivot: int = 5, max_lookback: int = 300) -> Optional[Swing]:
        """用局部极值寻找最近一对高低点。pivot=5 表示两侧各5根K线确认。"""
        if df is None or df.empty:
            return None
        highs = df['high'].values
        lows = df['low'].values
        idxs_high: List[int] = []
        idxs_low: List[int] = []
        n = len(df)
        start = max(0, n - max_lookback)
        for i in range(start + pivot, n - pivot):
            if highs[i] == np.nanmax(highs[i - pivot:i + pivot + 1]):
                idxs_high.append(i)
            if lows[i] == np.nanmin(lows[i - pivot:i + pivot + 1]):
                idxs_low.append(i)
        if not idxs_high or not idxs_low:
            # 退化为窗口最高/最低
            h_idx = int(np.nanargmax(highs[start:])) + start
            l_idx = int(np.nanargmin(lows[start:])) + start
            if l_idx < h_idx:
                return Swing(low=float(lows[l_idx]), low_ts=int(df['t'].iloc[l_idx].timestamp() * 1000),
                             high=float(highs[h_idx]), high_ts=int(df['t'].iloc[h_idx].timestamp() * 1000),
                             trend='up')
            else:
                return Swing(low=float(lows[l_idx]), low_ts=int(df['t'].iloc[l_idx].timestamp() * 1000),
                             high=float(highs[h_idx]), high_ts=int(df['t'].iloc[h_idx].timestamp() * 1000),
                             trend='down')
        # 从最近的极值向前找到一对先低后高或先高后低
        i_high = idxs_high[-1]
        # 找到该高点之前最近的低点
        prior_lows = [i for i in idxs_low if i < i_high]
        if prior_lows:
            i_low = prior_lows[-1]
            tr = 'up'
        else:
            # 没有低点在前，则找高点之后的低点，趋势为下
            after_lows = [i for i in idxs_low if i > i_high]
            if not after_lows:
                return None
            i_low = after_lows[0]
            tr = 'down'
        return Swing(low=float(lows[i_low]), low_ts=int(df['t'].iloc[i_low].timestamp() * 1000),
                     high=float(highs[i_high]), high_ts=int(df['t'].iloc[i_high].timestamp() * 1000),
                     trend=tr)

    def compute_fib_map(self, low: float, high: float) -> Dict[float, float]:
        if not self._ok(low) or not self._ok(high) or high <= 0 or low <= 0 or high == low:
            return {}
        rng = high - low
        return {lvl: low + rng * lvl for lvl in FIB_LEVELS}

    def locate_position(self, price: float, low: float, high: float) -> Dict:
        if not self._ok(price) or not self._ok(low) or not self._ok(high) or high == low:
            return {}
        rng = high - low
        ratio = (price - low) / rng
        # 找最近的标准位
        nearest = min(FIB_LEVELS, key=lambda lv: abs(ratio - lv))
        nearest_price = low + rng * nearest
        # 上下方位点（各取3个）
        upper = sorted([lv for lv in FIB_LEVELS if lv > ratio])[:3]
        lower = sorted([lv for lv in FIB_LEVELS if lv <= ratio], reverse=True)[:3]
        return {
            'ratio': float(ratio),
            'nearest_level': float(nearest),
            'nearest_price': float(nearest_price),
            'upper_levels': [[float(lv), float(low + rng * lv)] for lv in upper],
            'lower_levels': [[float(lv), float(low + rng * lv)] for lv in lower]
        }

    # ----------------------------- 单币与批量分析 -----------------------------
    def analyze_one(self, symbol: str, timeframe: str = '1d', source: str = 'gate') -> Optional[Dict]:
        df = None
        if source == 'bybit':
            interval = {'1d': 'D', '4h': '240', '1h': '60'}.get(timeframe, 'D')
            df = self.get_klines_bybit(symbol, interval=interval)
        else:
            interval = timeframe if timeframe in {'1d', '4h', '1h'} else '1d'
            df = self.get_klines_gate(symbol, interval=interval)
        if df is None or len(df) < 20:
            return None
        swing = self.find_recent_swing(df)
        if swing is None:
            return None
        current_price = float(df['close'].iloc[-1])
        # 统一采用 low->high 作为基准，若趋势为 down 且 low_index>high_index 可交换
        low, high = swing.low, swing.high
        if swing.trend == 'down' and swing.high_ts < swing.low_ts:
            # 先高后低，交换
            low, high = swing.low, swing.high  # 值保持不变，但 ratio 解释为可能<0
        fib_map = self.compute_fib_map(low, high)
        pos = self.locate_position(current_price, low, high)
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'source': source,
            'current_price': current_price,
            'recent_low': low,
            'recent_low_ts': swing.low_ts,
            'recent_high': high,
            'recent_high_ts': swing.high_ts,
            'trend': swing.trend,
            'fib_levels': fib_map,
            'position': pos
        }

    def scan_symbols(
        self,
        symbols: List[str],
        timeframe: str = '1d',
        source: str = 'gate',
        max_workers: int = 8,
        batch_size: int = 50,
        throttle_sec: float = 0.2,
    ) -> List[Dict]:
        """分批并发扫描，批间节流，降低被限频概率。"""
        results: List[Dict] = []
        n = len(symbols)
        if n == 0:
            return results
        batch_size = max(1, min(batch_size, 200))
        max_workers = max(1, min(max_workers, 32))
        for i in range(0, n, batch_size):
            chunk = symbols[i:i + batch_size]
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = {ex.submit(self.analyze_one, s, timeframe, source): s for s in chunk}
                for fut in as_completed(futures):
                    try:
                        r = fut.result()
                        if r:
                            results.append(r)
                    except Exception as e:
                        logger.debug(f"扫描 {futures[fut]} 失败: {e}")
            # 批次之间稍作等待
            if i + batch_size < n and throttle_sec > 0:
                try:
                    import time as _t
                    _t.sleep(throttle_sec)
                except Exception:
                    pass
        return results


# 实例化
engine = RealtimeFibonacciV2()


# ----------------------------- HTTP 接口 -----------------------------

@realtime_fib_bp.route('/api/top_symbols', methods=['GET'])
def api_top_symbols():
    source = request.args.get('source', 'gate').lower()
    limit = int(request.args.get('limit', 1000))
    if source == 'bybit':
        syms = engine.get_bybit_top_symbols(limit)
    else:
        syms = engine.get_gate_top_symbols(limit)
    return jsonify({'success': True, 'source': source, 'count': len(syms), 'symbols': syms})


@realtime_fib_bp.route('/api/scan', methods=['POST'])
def api_scan():
    data = request.get_json(silent=True) or {}
    source = (data.get('source') or 'gate').lower()
    limit = int(data.get('limit', 1000))
    timeframe = data.get('timeframe', '1d')
    # 并发与限速参数
    max_workers = int(data.get('max_workers', 8))
    batch_size = int(data.get('batch_size', 50))
    throttle_sec = float(data.get('throttle_sec', 0.2))
    # 分页与排序/筛选
    page = max(1, int(data.get('page', 1)))
    page_size = max(1, min(200, int(data.get('page_size', 50))))
    sort_by = (data.get('sort_by') or 'ratio').lower()  # ratio/current_price/nearest_level
    sort_dir = (data.get('sort_dir') or 'desc').lower()  # asc/desc
    only_extension = bool(data.get('only_extension', False))  # ratio>=1
    min_ratio = data.get('min_ratio')
    try:
        min_ratio = float(min_ratio) if min_ratio is not None else None
    except Exception:
        min_ratio = None
    # 获取交易对列表
    symbols = engine.get_bybit_top_symbols(limit) if source == 'bybit' else engine.get_gate_top_symbols(limit)
    # 扫描
    results = engine.scan_symbols(
        symbols,
        timeframe=timeframe,
        source=source,
        max_workers=max_workers,
        batch_size=batch_size,
        throttle_sec=throttle_sec,
    )
    # 简化列表返回字段，便于前端表格展示
    list_rows = []
    for r in results:
        pos = r.get('position') or {}
        list_rows.append({
            'symbol': r['symbol'],
            'timeframe': r['timeframe'],
            'trend': r['trend'],
            'current_price': r['current_price'],
            'recent_low': r['recent_low'],
            'recent_high': r['recent_high'],
            'ratio': pos.get('ratio'),
            'nearest_level': pos.get('nearest_level'),
            'nearest_price': pos.get('nearest_price')
        })
    # 筛选（仅扩展位 / 最小比例）
    filtered = []
    for row in list_rows:
        r = row.get('ratio')
        if r is None:
            continue
        if only_extension and r < 1.0:
            continue
        if min_ratio is not None and r < min_ratio:
            continue
        filtered.append(row)
    # 排序
    key_funcs = {
        'ratio': lambda x: (x.get('ratio') is not None, x.get('ratio') or -1),
        'current_price': lambda x: x.get('current_price') or 0,
        'nearest_level': lambda x: x.get('nearest_level') or 0,
    }
    key_fn = key_funcs.get(sort_by, key_funcs['ratio'])
    reverse = (sort_dir != 'asc')
    filtered.sort(key=key_fn, reverse=reverse)
    # 分页
    total = len(filtered)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    page = min(page, max(1, total_pages) if total_pages > 0 else 1)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = filtered[start:end]
    return jsonify({
        'success': True,
        'source': source,
        'timeframe': timeframe,
        'total': total,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
        },
        'rows': page_rows
    })


@realtime_fib_bp.route('/api/analyze', methods=['POST'])
def api_analyze_one():
    data = request.get_json(silent=True) or {}
    symbol = data.get('symbol', 'BTCUSDT').upper()
    timeframe = data.get('timeframe', '1d')
    source = (data.get('source') or 'gate').lower()
    res = engine.analyze_one(symbol, timeframe=timeframe, source=source)
    if not res:
        return jsonify({'success': False, 'error': '分析失败或无数据'}), 500
    return jsonify({'success': True, 'result': res})
