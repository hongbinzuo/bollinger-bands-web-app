import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

yoyo_bp = Blueprint('yoyo', __name__, url_prefix='/yoyo')

SUPPORTED_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'LTCUSDT', 'BCHUSDT', 'XRPUSDT',
    'LINKUSDT', 'SUIUSDT', 'TAOUSDT', 'UNIUSDT', 'ADAUSDT', 'AAVEUSDT'
]

SUPPORTED_TIMEFRAMES = {
    '1h': '1h',
    '4h': '4h',
    '1d': '1d',
}

CACHE_DIR = 'cache'
LAST_SIGNAL_FILE = os.path.join(CACHE_DIR, 'yoyo_last_signals.json')

_session = requests.Session()
_session.headers.update({'User-Agent': 'Mozilla/5.0'})


def _ensure_cache_dir() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def _load_last_signals() -> Dict[str, Dict[str, object]]:
    _ensure_cache_dir()
    if not os.path.exists(LAST_SIGNAL_FILE):
        return {}
    try:
        with open(LAST_SIGNAL_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_last_signals(data: Dict[str, Dict[str, object]]) -> None:
    _ensure_cache_dir()
    try:
        with open(LAST_SIGNAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save last signals: {e}")


def _normalize_symbol(symbol: str) -> str:
    sym = (symbol or '').upper().strip()
    if not sym:
        return ''
    if not sym.endswith('USDT'):
        sym += 'USDT'
    return sym


def _gate_symbol(symbol: str) -> str:
    sym = _normalize_symbol(symbol)
    if sym.endswith('USDT'):
        return f"{sym[:-4]}_USDT"
    return sym


def _get_gate_klines(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    try:
        url = 'https://api.gateio.ws/api/v4/spot/candlesticks'
        params = {
            'currency_pair': _gate_symbol(symbol),
            'interval': interval,
            'limit': min(int(limit), 1000)
        }
        resp = _session.get(url, params=params, timeout=12)
        resp.raise_for_status()
        raw = resp.json()
        if not raw:
            return None
        df = pd.DataFrame(raw, columns=[
            'timestamp', 'volume', 'close', 'high', 'low', 'open', 'extra1', 'extra2'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp'], errors='coerce'), unit='s', utc=True)
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
        return df.sort_values('timestamp').reset_index(drop=True)
    except Exception as e:
        logger.error(f"Gate.io kline fetch failed for {symbol} {interval}: {e}")
        return None


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    if len(series) == 0:
        return np.array([])
    return pd.Series(series).ewm(span=period, adjust=False).mean().to_numpy()


def _barssince(condition: List[bool]) -> np.ndarray:
    result = []
    last = None
    for cond in condition:
        if cond:
            last = 0
            result.append(0)
        else:
            if last is None:
                result.append(np.nan)
            else:
                last += 1
                result.append(last)
    return np.array(result, dtype=float)


def _is_finite(value: float) -> bool:
    return value is not None and np.isfinite(value)


def _safe_lt(a: float, b: float) -> bool:
    return _is_finite(a) and _is_finite(b) and a < b


def _safe_gt(a: float, b: float) -> bool:
    return _is_finite(a) and _is_finite(b) and a > b


def _safe_le(a: float, b: float) -> bool:
    return _is_finite(a) and _is_finite(b) and a <= b


def _safe_ge(a: float, b: float) -> bool:
    return _is_finite(a) and _is_finite(b) and a >= b


def _compute_yoyo_signals(df: pd.DataFrame, s: int = 12, p: int = 26, m: int = 9) -> Dict[str, object]:
    close = df['close'].to_numpy()
    n = len(close)
    if n == 0:
        return {'signals': [], 'latest': []}

    diff = _ema(close, s) - _ema(close, p)
    dea = _ema(diff, m)
    macd = (diff - dea) * 2

    cond_down = [False] * n
    cond_up = [False] * n
    for i in range(1, n):
        if _is_finite(macd[i - 1]) and _is_finite(macd[i]):
            cond_down[i] = macd[i - 1] >= 0 and macd[i] < 0
            cond_up[i] = macd[i - 1] <= 0 and macd[i] > 0

    n1_raw = _barssince(cond_down)
    mm1_raw = _barssince(cond_up)

    n1 = []
    mm1 = []
    for i in range(n):
        v1 = 0 if np.isnan(n1_raw[i]) else max(0, n1_raw[i] - 1)
        v2 = 0 if np.isnan(mm1_raw[i]) else max(0, mm1_raw[i] - 1)
        n1.append(int(min(v1, 50)))
        mm1.append(int(min(v2, 50)))

    n1_plus_1 = [min(v + 1, 55) for v in n1]
    mm1_plus_1 = [min(v + 1, 55) for v in mm1]
    n1_idx = n1_plus_1
    mm1_idx = mm1_plus_1

    cc1 = np.full(n, np.nan)
    difl1 = np.full(n, np.nan)
    ch1 = np.full(n, np.nan)
    difh1 = np.full(n, np.nan)

    for i in range(n):
        w1 = n1_plus_1[i]
        s1 = max(0, i - w1 + 1)
        cc1[i] = np.nanmin(close[s1:i + 1])
        difl1[i] = np.nanmin(diff[s1:i + 1])

        w2 = mm1_plus_1[i]
        s2 = max(0, i - w2 + 1)
        ch1[i] = np.nanmax(close[s2:i + 1])
        difh1[i] = np.nanmax(diff[s2:i + 1])

    def _shift_series(src: np.ndarray, offsets: List[int]) -> np.ndarray:
        out = np.full(n, np.nan)
        for i in range(n):
            idx = offsets[i]
            if 0 <= idx <= 55 and i - idx >= 0:
                out[i] = src[i - idx]
        return out

    cc2 = _shift_series(cc1, mm1_idx)
    cc3 = _shift_series(cc2, mm1_idx)
    difl2 = _shift_series(difl1, mm1_idx)
    difl3 = _shift_series(difl2, mm1_idx)
    ch2 = _shift_series(ch1, n1_idx)
    ch3 = _shift_series(ch2, n1_idx)
    difh2 = _shift_series(difh1, n1_idx)
    difh3 = _shift_series(difh2, n1_idx)

    aaa = [False] * n
    bbb = [False] * n
    ccc = [False] * n
    lll = [False] * n
    xxx = [False] * n
    jjj = [False] * n
    blbl = [False] * n
    dxdx = [False] * n

    zjdb = [False] * n
    gxdb = [False] * n
    dbbl = [False] * n
    dbl = [False] * n
    dblxs = [False] * n
    dbjg = [False] * n
    dbjgxc = [False] * n
    dbjgb = [False] * n

    djgxx = [False] * n
    djxx = [False] * n

    zzzzz = [False] * n
    yyyyy = [False] * n
    wwwww = [False] * n

    for i in range(n):
        macd_prev = macd[i - 1] if i >= 1 else np.nan
        diff_prev = diff[i - 1] if i >= 1 else np.nan

        aaa[i] = (
            _safe_lt(cc1[i], cc2[i])
            and _safe_gt(difl1[i], difl2[i])
            and _is_finite(macd_prev) and macd_prev < 0
            and _is_finite(diff[i]) and diff[i] < 0
        )
        bbb[i] = (
            _safe_lt(cc1[i], cc3[i])
            and _safe_lt(difl1[i], difl2[i])
            and _safe_gt(difl1[i], difl3[i])
            and _is_finite(macd_prev) and macd_prev < 0
            and _is_finite(diff[i]) and diff[i] < 0
        )
        ccc[i] = (aaa[i] or bbb[i]) and _is_finite(diff[i]) and diff[i] < 0
        lll[i] = (not ccc[i - 1]) and ccc[i] if i >= 1 else ccc[i]

        aaa_prev = aaa[i - 1] if i >= 1 else False
        bbb_prev = bbb[i - 1] if i >= 1 else False
        ccc_prev = ccc[i - 1] if i >= 1 else False
        diff_le_dea = _is_finite(diff[i]) and _is_finite(dea[i]) and diff[i] < dea[i]

        xxx[i] = (
            (aaa_prev and _safe_le(difl1[i], difl2[i]) and diff_le_dea)
            or (bbb_prev and _safe_le(difl1[i], difl3[i]) and diff_le_dea)
        )

        jjj[i] = (
            ccc_prev
            and _is_finite(diff_prev)
            and _is_finite(diff[i])
            and abs(diff_prev) >= (abs(diff[i]) * 1.01)
        )

        jjj_prev = jjj[i - 1] if i >= 1 else False
        blbl[i] = (
            jjj_prev
            and ccc[i]
            and _is_finite(diff_prev)
            and _is_finite(diff[i])
            and (abs(diff_prev) * 1.01 <= abs(diff[i]))
        )
        dxdx[i] = (not jjj_prev) and jjj[i]

        jjj_count = sum(1 for k in range(max(0, i - 23), i + 1) if jjj[k])
        mm1_offset = mm1_idx[i]
        jjj_mm1_plus_1 = jjj[i - mm1_offset] if i - mm1_offset >= 0 else False
        mm1_offset_raw = mm1[i]
        jjj_mm1 = jjj[i - mm1_offset_raw] if i - mm1_offset_raw >= 0 else False

        close_lt_cc2 = _safe_lt(close[i], cc2[i])
        close_lt_cc1 = _safe_lt(close[i], cc1[i])
        lll_prev = lll[i - 1] if i >= 1 else False
        djgxx[i] = (
            (close_lt_cc2 or close_lt_cc1)
            and (jjj_mm1_plus_1 or jjj_mm1)
            and (not lll_prev)
            and jjj_count >= 1
        )

        djgxx_count = sum(1 for k in range(max(0, i - 2), i) if djgxx[k])
        djxx[i] = djgxx_count < 1 and djgxx[i]

        macd_pos = _is_finite(macd_prev) and macd_prev > 0
        diff_pos = _is_finite(diff[i]) and diff[i] > 0
        zjdb[i] = (
            _safe_gt(ch1[i], ch2[i])
            and _safe_lt(difh1[i], difh2[i])
            and macd_pos
            and diff_pos
        )
        gxdb[i] = (
            _safe_gt(ch1[i], ch3[i])
            and _safe_gt(difh1[i], difh2[i])
            and _safe_lt(difh1[i], difh3[i])
            and macd_pos
            and diff_pos
        )
        dbbl[i] = (zjdb[i] or gxdb[i]) and diff_pos
        dbbl_prev = dbbl[i - 1] if i >= 1 else False
        diff_gt_dea = _is_finite(diff[i]) and _is_finite(dea[i]) and diff[i] > dea[i]
        dbl[i] = (not dbbl_prev) and dbbl[i] and diff_gt_dea

        zjdb_prev = zjdb[i - 1] if i >= 1 else False
        gxdb_prev = gxdb[i - 1] if i >= 1 else False
        dblxs[i] = (
            (zjdb_prev and _safe_ge(difh1[i], difh2[i]) and diff_gt_dea)
            or (gxdb_prev and _safe_ge(difh1[i], difh3[i]) and diff_gt_dea)
        )

        dbjg[i] = (
            dbbl_prev
            and _is_finite(diff_prev)
            and _is_finite(diff[i])
            and diff_prev >= (diff[i] * 1.01)
        )
        dbjg_prev = dbjg[i - 1] if i >= 1 else False
        dbjgxc[i] = (not dbjg_prev) and dbjg[i]
        dbjgb[i] = (
            dbjg_prev
            and dbbl[i]
            and _is_finite(diff_prev)
            and _is_finite(diff[i])
            and (diff_prev * 1.01 <= diff[i])
        )

        dbjg_count = sum(1 for k in range(max(0, i - 22), i + 1) if dbjg[k])
        n1_offset = n1_idx[i]
        dbjg_n1_plus_1 = dbjg[i - n1_offset] if i - n1_offset >= 0 else False
        n1_offset_raw = n1[i]
        dbjg_n1 = dbjg[i - n1_offset_raw] if i - n1_offset_raw >= 0 else False

        close_gt_ch2 = _safe_gt(close[i], ch2[i])
        close_gt_ch1 = _safe_gt(close[i], ch1[i])
        dbl_prev = dbl[i - 1] if i >= 1 else False
        zzzzz[i] = (
            (close_gt_ch2 or close_gt_ch1)
            and (dbjg_n1_plus_1 or dbjg_n1)
            and (not dbl_prev)
            and dbjg_count >= 1
        )

        zzzzz_count = sum(1 for k in range(max(0, i - 2), i) if zzzzz[k])
        yyyyy[i] = zzzzz_count < 1 and zzzzz[i]
        wwwww[i] = (dblxs[i] or yyyyy[i]) and (not dbbl[i])

    signals = []
    latest = []
    for i in range(n):
        ts = int(df['timestamp'].iloc[i].timestamp())
        if dxdx[i]:
            signals.append({'time': ts, 'signal': 'buy'})
        if dbjgxc[i]:
            signals.append({'time': ts, 'signal': 'sell'})

    if n > 0:
        last_ts = int(df['timestamp'].iloc[-1].timestamp())
        if dxdx[-1]:
            latest.append({'time': last_ts, 'signal': 'buy'})
        if dbjgxc[-1]:
            latest.append({'time': last_ts, 'signal': 'sell'})

    return {'signals': signals, 'latest': latest}


def _telegram_enabled() -> bool:
    return bool(os.getenv('TELEGRAM_BOT_TOKEN')) and bool(os.getenv('TELEGRAM_CHAT_ID'))


def _send_telegram_message(text: str) -> None:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        _session.post(url, data={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


def _format_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def _maybe_send_latest_signal(symbol: str, timeframe: str, latest_signals: List[Dict[str, object]], close_price: float) -> None:
    if not latest_signals or not _telegram_enabled():
        return
    key = f"{symbol}|{timeframe}"
    last_state = _load_last_signals()
    latest_time = latest_signals[0]['time']
    latest_types = sorted([s['signal'] for s in latest_signals])
    last_entry = last_state.get(key, {})
    if last_entry.get('time') == latest_time and last_entry.get('signals') == latest_types:
        return

    signal_text = ", ".join(latest_types).upper()
    message = f"YOYO signal {signal_text} - {symbol} {timeframe} @ {close_price:.6f} ({_format_ts(latest_time)})"
    _send_telegram_message(message)

    last_state[key] = {'time': latest_time, 'signals': latest_types}
    _save_last_signals(last_state)


@yoyo_bp.route('/api/chart', methods=['POST'])
def yoyo_chart():
    try:
        payload = request.get_json(silent=True) or {}
        symbol = _normalize_symbol(payload.get('symbol') or '')
        timeframe = (payload.get('timeframe') or '1h').strip()
        display_limit = int(payload.get('display_limit') or 90)
        raw_limit = int(payload.get('limit') or 200)

        if symbol not in SUPPORTED_SYMBOLS:
            return jsonify({'success': False, 'error': 'Unsupported symbol'}), 400
        if timeframe not in SUPPORTED_TIMEFRAMES:
            return jsonify({'success': False, 'error': 'Unsupported timeframe'}), 400

        df = _get_gate_klines(symbol, SUPPORTED_TIMEFRAMES[timeframe], raw_limit)
        if df is None or df.empty:
            return jsonify({'success': False, 'error': 'No kline data'}), 502

        signals_payload = _compute_yoyo_signals(df)
        signals = signals_payload['signals']
        latest_signals = signals_payload['latest']

        display_limit = max(30, min(display_limit, 300))
        df_display = df.tail(display_limit).reset_index(drop=True)
        display_times = set(int(ts.timestamp()) for ts in df_display['timestamp'])
        filtered_signals = [s for s in signals if s['time'] in display_times]

        last_close = float(df['close'].iloc[-1])
        _maybe_send_latest_signal(symbol, timeframe, latest_signals, last_close)

        candles = [
            {
                'time': int(row.timestamp.timestamp()),
                'open': float(row.open),
                'high': float(row.high),
                'low': float(row.low),
                'close': float(row.close),
            }
            for row in df_display.itertuples(index=False)
        ]

        return jsonify({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'candles': candles,
            'signals': filtered_signals,
            'latest_signals': latest_signals
        })
    except Exception as e:
        logger.error(f"Yoyo chart failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@yoyo_bp.route('/api/symbols', methods=['GET'])
def yoyo_symbols():
    return jsonify({'success': True, 'symbols': SUPPORTED_SYMBOLS})
