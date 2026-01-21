import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from flask import Blueprint, jsonify, request

from database import DatabaseManager

logger = logging.getLogger(__name__)
_gunicorn_logger = logging.getLogger('gunicorn.error')
if _gunicorn_logger and _gunicorn_logger.handlers:
    logger.handlers = _gunicorn_logger.handlers
    logger.setLevel(_gunicorn_logger.level)

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
SCHEDULER_LOCK_FILE = os.path.join(CACHE_DIR, 'yoyo_scheduler.lock')
DAILY_BOTTOM_CACHE_FILE = os.path.join(CACHE_DIR, 'daily_bottom_signals.json')
DAILY_BOTTOM_LOCK_FILE = os.path.join(CACHE_DIR, 'daily_bottom_scheduler.lock')

_session = requests.Session()
_session.headers.update({'User-Agent': 'Mozilla/5.0'})
_scheduler_started = False
_daily_bottom_started = False
_daily_bottom_running = False
_db_manager = DatabaseManager()


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


def _is_valid_symbol(symbol: str) -> bool:
    if not symbol:
        return False
    if not symbol.isalnum():
        return False
    return 2 <= len(symbol) <= 15


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


def _get_gate_tickers() -> Optional[List[Dict[str, object]]]:
    try:
        url = 'https://api.gateio.ws/api/v4/spot/tickers'
        resp = _session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else None
    except Exception as e:
        logger.error(f"Gate.io tickers fetch failed: {e}")
        return None


def _filter_usdt_tickers(tickers: List[Dict[str, object]]) -> List[Dict[str, object]]:
    stablecoin_bases = {
        'USDC', 'BUSD', 'TUSD', 'USDP', 'DAI', 'FDUSD', 'USDT', 'USDD', 'FRAX', 'LUSD',
        'GUSD', 'SUSD', 'USDN', 'USTC', 'UST', 'CUSD', 'DUSD', 'VAI', 'RSV', 'USDX',
        'USDJ', 'USDS'
    }
    leverage_tokens = ['3L', '3S', '5L', '5S']
    excluded_patterns = ['BULL', 'BEAR', 'UP', 'DOWN', 'LONG', 'SHORT']

    results = []
    for item in tickers:
        currency_pair = item.get('currency_pair', '')
        if not currency_pair.endswith('_USDT'):
            continue
        base_asset = currency_pair.replace('_USDT', '')
        if base_asset in stablecoin_bases:
            continue
        if any(base_asset.endswith(token) for token in leverage_tokens):
            continue
        if any(pattern in base_asset for pattern in excluded_patterns):
            continue
        try:
            change_pct = float(item.get('change_percentage', 0) or 0)
            last = float(item.get('last', 0) or 0)
            quote_volume = float(item.get('quote_volume', 0) or 0)
        except (TypeError, ValueError):
            continue
        if last <= 0 or quote_volume <= 0:
            continue
        results.append({
            'symbol': f"{base_asset}USDT",
            'change_24h': change_pct,
            'last_price': last,
            'quote_volume': quote_volume
        })
    return results

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
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.fromtimestamp(ts, tz=beijing_tz).strftime('%Y-%m-%d %H:%M 北京时间')


def _maybe_send_latest_signal(
    symbol: str,
    timeframe: str,
    latest_signals: List[Dict[str, object]],
    close_price: float,
    last_state: Optional[Dict[str, Dict[str, object]]] = None,
    persist: bool = True
) -> bool:
    if not latest_signals or not _telegram_enabled():
        return False
    if last_state is None:
        last_state = _load_last_signals()
    key = f"{symbol}|{timeframe}"
    latest_time = latest_signals[0]['time']
    latest_types = sorted([s['signal'] for s in latest_signals])
    last_entry = last_state.get(key, {})
    if last_entry.get('time') == latest_time and last_entry.get('signals') == latest_types:
        return False

    signal_text = ", ".join(latest_types).upper()
    message = (
        f"YOYO signal {signal_text} - {symbol} {timeframe} @ {close_price:.6f} | "
        f"信号时间: {_format_ts(latest_time)}"
    )
    _send_telegram_message(message)

    last_state[key] = {'time': latest_time, 'signals': latest_types}
    if persist:
        _save_last_signals(last_state)
    return True


def _get_recent_1h_signals(symbol: str, hours: int, limit: int) -> Tuple[Optional[Dict[str, object]], Optional[str]]:
    df = _get_gate_klines(symbol, SUPPORTED_TIMEFRAMES['1h'], limit)
    if df is None or df.empty:
        return None, 'No kline data'
    signals_payload = _compute_yoyo_signals(df)
    signals = signals_payload['signals']
    if not signals:
        return {
            'symbol': symbol,
            'signals_recent': [],
            'latest_signal_time': None
        }, None
    now_ts = int(datetime.now(timezone.utc).timestamp())
    cutoff = now_ts - (hours * 3600)
    recent = [s for s in signals if s.get('time', 0) >= cutoff]
    if not recent:
        return {
            'symbol': symbol,
            'signals_recent': [],
            'latest_signal_time': None
        }, None
    latest_time = max(s.get('time', 0) for s in recent)
    return {
        'symbol': symbol,
        'signals_recent': recent,
        'latest_signal_time': latest_time
    }, None


def scan_yoyo_symbols(
    symbols: List[str],
    timeframes: Optional[List[str]] = None,
    limit: int = 300
) -> Tuple[Dict[str, object], int]:
    if not _telegram_enabled():
        return {'success': False, 'error': 'Telegram not configured'}, 400
    if not isinstance(symbols, list):
        return {'success': False, 'error': 'symbols must be a list'}, 400
    if timeframes is None:
        timeframes = list(SUPPORTED_TIMEFRAMES.keys())
    if not isinstance(timeframes, list):
        return {'success': False, 'error': 'timeframes must be a list'}, 400

    limit = max(100, min(int(limit or 300), 1000))

    normalized_symbols = []
    for raw in symbols:
        sym = _normalize_symbol(str(raw))
        if _is_valid_symbol(sym):
            normalized_symbols.append(sym)
    normalized_symbols = list(dict.fromkeys(normalized_symbols))
    if not normalized_symbols:
        return {'success': False, 'error': 'No valid symbols'}, 400

    valid_timeframes = [tf for tf in timeframes if tf in SUPPORTED_TIMEFRAMES]
    if not valid_timeframes:
        return {'success': False, 'error': 'No valid timeframes'}, 400

    last_state = _load_last_signals()
    sent = []
    errors = []

    for symbol in normalized_symbols:
        for timeframe in valid_timeframes:
            df = _get_gate_klines(symbol, SUPPORTED_TIMEFRAMES[timeframe], limit)
            if df is None or df.empty:
                errors.append({'symbol': symbol, 'timeframe': timeframe, 'error': 'No kline data'})
                continue
            signals_payload = _compute_yoyo_signals(df)
            latest_signals = signals_payload['latest']
            if not latest_signals:
                continue
            last_close = float(df['close'].iloc[-1])
            did_send = _maybe_send_latest_signal(
                symbol,
                timeframe,
                latest_signals,
                last_close,
                last_state=last_state,
                persist=False
            )
            if did_send:
                sent.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'signals': [s.get('signal') for s in latest_signals],
                    'time': latest_signals[0].get('time')
                })

    _save_last_signals(last_state)

    return {
        'success': True,
        'symbols': normalized_symbols,
        'timeframes': valid_timeframes,
        'limit': limit,
        'sent_count': len(sent),
        'sent': sent,
        'errors': errors
    }, 200


def _parse_bool_env(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _parse_csv_env(name: str) -> List[str]:
    raw = os.getenv(name, '')
    if not raw:
        return []
    return [item.strip() for item in raw.split(',') if item.strip()]


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return True
    return True


def _acquire_lock(lock_file: str) -> bool:
    _ensure_cache_dir()
    pid = os.getpid()
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(str(pid))
        return True
    except FileExistsError:
        existing_pid = 0
        try:
            with open(lock_file, 'r', encoding='utf-8') as handle:
                existing_pid = int((handle.read() or '').strip() or 0)
        except Exception:
            existing_pid = 0
        if existing_pid and _pid_is_running(existing_pid):
            return False
        try:
            os.remove(lock_file)
        except OSError:
            return False
        return _acquire_lock(lock_file)
    except Exception:
        return False


def _acquire_scheduler_lock() -> bool:
    return _acquire_lock(SCHEDULER_LOCK_FILE)


def _read_scheduler_lock() -> Dict[str, object]:
    if not os.path.exists(SCHEDULER_LOCK_FILE):
        return {'exists': False}
    pid = 0
    try:
        with open(SCHEDULER_LOCK_FILE, 'r', encoding='utf-8') as handle:
            pid = int((handle.read() or '').strip() or 0)
    except Exception:
        pid = 0
    return {
        'exists': True,
        'pid': pid,
        'running': _pid_is_running(pid) if pid else False
    }


def _load_daily_bottom_cache() -> Optional[Dict[str, object]]:
    _ensure_cache_dir()
    if not os.path.exists(DAILY_BOTTOM_CACHE_FILE):
        return None
    try:
        with open(DAILY_BOTTOM_CACHE_FILE, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def _save_daily_bottom_cache(data: Dict[str, object]) -> None:
    _ensure_cache_dir()
    try:
        with open(DAILY_BOTTOM_CACHE_FILE, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save daily bottom cache: {e}")


def _ensure_daily_bottom_tables() -> None:
    create_sql_sqlite = """
    CREATE TABLE IF NOT EXISTS daily_bottom_symbols (
        symbol TEXT PRIMARY KEY,
        market_cap_rank INTEGER,
        market_cap REAL,
        current_price REAL,
        updated_at TEXT
    );
    """
    create_sql_mysql = """
    CREATE TABLE IF NOT EXISTS daily_bottom_symbols (
        symbol VARCHAR(20) PRIMARY KEY,
        market_cap_rank INT,
        market_cap DOUBLE,
        current_price DOUBLE,
        updated_at DATETIME
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with _db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_sql_mysql if _db_manager.db_type == 'mysql' else create_sql_sqlite)
            if _db_manager.db_type != 'mysql':
                conn.commit()
        finally:
            cursor.close()


def _get_marketcap_cache_status() -> Tuple[int, Optional[str]]:
    with _db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) as cnt, MAX(updated_at) as updated_at FROM daily_bottom_symbols")
            row = cursor.fetchone()
            if row is None:
                return 0, None
            if isinstance(row, dict):
                return int(row.get('cnt') or 0), row.get('updated_at')
            return int(row[0] or 0), row[1]
        finally:
            cursor.close()


def _should_refresh_marketcap(limit: int) -> bool:
    count, updated_at = _get_marketcap_cache_status()
    if count < limit:
        return True
    if not updated_at:
        return True
    try:
        if isinstance(updated_at, datetime):
            last_dt = updated_at
        else:
            last_dt = datetime.fromisoformat(str(updated_at))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        else:
            last_dt = last_dt.astimezone(timezone.utc)
        age = datetime.now(timezone.utc) - last_dt
        return age.total_seconds() >= 86400
    except Exception:
        return True


def _refresh_marketcap_symbols(limit: int) -> List[Dict[str, object]]:
    market_list = _get_coingecko_top_marketcap(limit)
    if not market_list:
        return []
    now_dt = datetime.now(timezone.utc)
    now_ts = now_dt.strftime('%Y-%m-%d %H:%M:%S') if _db_manager.db_type == 'mysql' else now_dt.isoformat()
    with _db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM daily_bottom_symbols")
            if _db_manager.db_type == 'mysql':
                insert_sql = (
                    "INSERT INTO daily_bottom_symbols "
                    "(symbol, market_cap_rank, market_cap, current_price, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s)"
                )
                rows = [
                    (item['symbol'], item['market_cap_rank'], item['market_cap'], item['current_price'], now_ts)
                    for item in market_list
                ]
                cursor.executemany(insert_sql, rows)
            else:
                insert_sql = (
                    "INSERT INTO daily_bottom_symbols "
                    "(symbol, market_cap_rank, market_cap, current_price, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)"
                )
                rows = [
                    (item['symbol'], item['market_cap_rank'], item['market_cap'], item['current_price'], now_ts)
                    for item in market_list
                ]
                cursor.executemany(insert_sql, rows)
                conn.commit()
        finally:
            cursor.close()
    return market_list


def _load_marketcap_symbols(limit: int) -> List[Dict[str, object]]:
    _ensure_daily_bottom_tables()
    if _should_refresh_marketcap(limit):
        market_list = _refresh_marketcap_symbols(limit)
        if market_list:
            return market_list
    with _db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT symbol, market_cap_rank, market_cap, current_price FROM daily_bottom_symbols "
                "ORDER BY market_cap_rank ASC LIMIT %s" % (limit,)
                if _db_manager.db_type == 'mysql'
                else "SELECT symbol, market_cap_rank, market_cap, current_price FROM daily_bottom_symbols "
                     "ORDER BY market_cap_rank ASC LIMIT ?",
                (limit,) if _db_manager.db_type != 'mysql' else ()
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                if isinstance(row, dict):
                    results.append({
                        'symbol': row.get('symbol'),
                        'market_cap_rank': row.get('market_cap_rank') or 0,
                        'market_cap': row.get('market_cap') or 0,
                        'current_price': row.get('current_price') or 0
                    })
                else:
                    results.append({
                        'symbol': row[0],
                        'market_cap_rank': row[1] or 0,
                        'market_cap': row[2] or 0,
                        'current_price': row[3] or 0
                    })
            return results
        finally:
            cursor.close()

def _get_coingecko_top_marketcap(limit: int = 1500) -> List[Dict[str, object]]:
    per_page = 250
    pages = (limit + per_page - 1) // per_page
    results = []
    seen = set()

    for page in range(1, pages + 1):
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': per_page,
                'page': page,
                'sparkline': 'false'
            }
            resp = _session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            for item in data:
                symbol = str(item.get('symbol', '')).upper()
                if not symbol or symbol in seen:
                    continue
                seen.add(symbol)
                results.append({
                    'symbol': f"{symbol}USDT",
                    'market_cap_rank': int(item.get('market_cap_rank') or 0),
                    'market_cap': float(item.get('market_cap') or 0),
                    'current_price': float(item.get('current_price') or 0)
                })
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
            time.sleep(0.2)
        except Exception as e:
            logger.error(f"CoinGecko market cap fetch failed on page {page}: {e}")
            break
    return results


def _get_daily_signals(symbol: str, days: int, limit: int) -> Tuple[Optional[Dict[str, object]], Optional[str]]:
    df = _get_gate_klines(symbol, SUPPORTED_TIMEFRAMES['1d'], limit)
    if df is None or df.empty:
        return None, 'No kline data'
    signals_payload = _compute_yoyo_signals(df)
    signals = signals_payload['signals']
    if not signals:
        return None, None
    now_ts = int(datetime.now(timezone.utc).timestamp())
    cutoff = now_ts - (days * 86400)
    recent_signals = [
        s for s in signals
        if s.get('signal') in {'buy', 'sell'} and s.get('time', 0) >= cutoff
    ]
    if not recent_signals:
        return None, None
    latest = max(recent_signals, key=lambda s: s.get('time', 0))
    latest_time = latest.get('time', 0)
    if not latest_time:
        return None, None
    time_to_close = {
        int(row.timestamp.timestamp()): float(row.close)
        for row in df.itertuples(index=False)
    }
    signal_price = time_to_close.get(latest_time)
    if signal_price is None:
        signal_price = float(df['close'].iloc[-1])
    return {
        'symbol': symbol,
        'latest_signal_time': latest_time,
        'latest_signal_price': signal_price,
        'latest_signal_type': latest.get('signal'),
        'signal_count': len(recent_signals)
    }, None


def _scan_daily_bottom_signals(limit: int = 1500, days: int = 14, kline_limit: int = 30) -> Dict[str, object]:
    market_list = _load_marketcap_symbols(limit)
    if not market_list:
        market_list = _get_coingecko_top_marketcap(limit)
    market_map = {item['symbol']: item for item in market_list}
    symbols = [item['symbol'] for item in market_list]

    signals = []
    errors = []
    max_workers = min(6, max(1, len(symbols) // 100))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_get_daily_signals, symbol, days, kline_limit): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                result, err = future.result()
            except Exception as e:
                errors.append({'symbol': symbol, 'error': str(e)})
                continue
            if err:
                errors.append({'symbol': symbol, 'error': err})
                continue
            if not result:
                continue
            market = market_map.get(symbol, {})
            signals.append({
                'symbol': symbol,
                'market_cap_rank': market.get('market_cap_rank', 0),
                'market_cap': market.get('market_cap', 0),
                'current_price': market.get('current_price', 0),
                'latest_signal_time': result['latest_signal_time'],
                'latest_signal_price': result['latest_signal_price'],
                'latest_signal_type': result.get('latest_signal_type', ''),
                'signal_count': result['signal_count']
            })

    return {
        'success': True,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'window_days': days,
        'top_n': limit,
        'scanned_symbols': len(symbols),
        'signals': signals,
        'errors': errors
    }

def _send_startup_latest_signal(symbols: List[str], timeframes: List[str], limit: int) -> None:
    if not _telegram_enabled():
        return
    recent_hours = int(os.getenv('YOYO_STARTUP_SIGNAL_HOURS', '12'))
    recent_hours = max(1, min(recent_hours, 168))
    cutoff_ts = int(datetime.now(timezone.utc).timestamp()) - recent_hours * 3600
    last_state = _load_last_signals()
    sent_count = 0

    for symbol in symbols:
        for timeframe in timeframes:
            df = _get_gate_klines(symbol, SUPPORTED_TIMEFRAMES[timeframe], limit)
            if df is None or df.empty:
                continue
            signals_payload = _compute_yoyo_signals(df)
            signals = signals_payload['signals']
            if not signals:
                continue
            recent_signals = [s for s in signals if s.get('time', 0) >= cutoff_ts]
            if not recent_signals:
                continue
            last_signal = max(recent_signals, key=lambda s: s.get('time', 0))
            last_time = last_signal.get('time', 0)
            if not last_time:
                continue
            latest_types = sorted([s.get('signal') for s in recent_signals if s.get('time') == last_time])
            key = f"{symbol}|{timeframe}"
            last_entry = last_state.get(key, {})
            if last_entry.get('time') == last_time and last_entry.get('signals') == latest_types:
                continue
            last_close = float(df['close'].iloc[-1])
            signal_text = ", ".join(latest_types).upper()
            message = (
                f"YOYO signal {signal_text} - {symbol} {timeframe} @ {last_close:.6f} | "
                f"信号时间: {_format_ts(last_time)}"
            )
            _send_telegram_message(message)
            last_state[key] = {'time': last_time, 'signals': latest_types}
            sent_count += 1

    if sent_count == 0:
        logger.info("YOYO startup: no recent signals found.")
        return
    _save_last_signals(last_state)
    logger.info("YOYO startup: sent %s startup signals.", sent_count)


def _daily_bottom_scheduler_loop(limit: int, days: int, kline_limit: int, interval: int) -> None:
    global _daily_bottom_running
    logger.info(
        "Daily bottom scheduler loop started (top_n=%s, days=%s, interval=%ss)",
        limit,
        days,
        interval
    )
    while True:
        started = time.time()
        if _daily_bottom_running:
            logger.info("Daily bottom scan already running, skipping this cycle.")
        else:
            _daily_bottom_running = True
            try:
                payload = _scan_daily_bottom_signals(limit, days, kline_limit)
                _save_daily_bottom_cache(payload)
                logger.info("Daily bottom scan completed: %s signals", len(payload.get('signals', [])))
            except Exception as e:
                logger.error(f"Daily bottom scan failed: {e}", exc_info=True)
            finally:
                _daily_bottom_running = False
        elapsed = time.time() - started
        sleep_for = max(60, interval - elapsed)
        time.sleep(sleep_for)


def maybe_start_daily_bottom_scheduler() -> bool:
    global _daily_bottom_started
    if _daily_bottom_started:
        return False
    if not _parse_bool_env(os.getenv('DAILY_BOTTOM_SCHEDULER_ENABLED', '1')):
        return False
    if not _acquire_lock(DAILY_BOTTOM_LOCK_FILE):
        logger.info("Daily bottom scheduler lock exists; skipping start.")
        return False

    limit = int(os.getenv('DAILY_BOTTOM_TOP_N', '1500'))
    limit = max(100, min(limit, 1500))
    days = int(os.getenv('DAILY_BOTTOM_SIGNAL_DAYS', '14'))
    days = max(7, min(days, 30))
    kline_limit = int(os.getenv('DAILY_BOTTOM_KLINE_LIMIT', '30'))
    kline_limit = max(20, min(kline_limit, 200))
    interval = int(os.getenv('DAILY_BOTTOM_SCHEDULER_INTERVAL', '28800'))
    interval = max(3600, interval)

    thread = threading.Thread(
        target=_daily_bottom_scheduler_loop,
        args=(limit, days, kline_limit, interval),
        daemon=True
    )
    thread.start()
    _daily_bottom_started = True
    logger.info(
        "Daily bottom scheduler started (top_n=%s, days=%s, interval=%ss)",
        limit,
        days,
        interval
    )
    return True


def _yoyo_scheduler_loop(symbols: List[str], timeframes: List[str], limit: int, interval: int) -> None:
    logger.info(
        "YOYO scheduler loop started (symbols=%s, timeframes=%s, interval=%ss, limit=%s)",
        len(symbols),
        timeframes,
        interval,
        limit
    )
    _send_startup_latest_signal(symbols, timeframes, limit)
    while True:
        started = time.time()
        try:
            result, _ = scan_yoyo_symbols(symbols, timeframes, limit)
            if not result.get('success'):
                logger.warning("YOYO scheduler scan failed: %s", result.get('error'))
            elif result.get('sent_count'):
                logger.info("YOYO scheduler sent %s signals", result.get('sent_count'))
        except Exception as e:
            logger.error(f"YOYO scheduler error: {e}", exc_info=True)
        elapsed = time.time() - started
        sleep_for = max(5, interval - elapsed)
        time.sleep(sleep_for)


def maybe_start_yoyo_scheduler() -> bool:
    global _scheduler_started
    if _scheduler_started:
        return False
    if not _parse_bool_env(os.getenv('YOYO_SCHEDULER_ENABLED')):
        return False
    if not _telegram_enabled():
        logger.warning("YOYO scheduler enabled but Telegram not configured; skipping start.")
        return False
    if not _acquire_scheduler_lock():
        logger.info("YOYO scheduler lock exists; skipping start.")
        return False

    symbols = _parse_csv_env('YOYO_SCHEDULER_SYMBOLS') or SUPPORTED_SYMBOLS
    timeframes = _parse_csv_env('YOYO_SCHEDULER_TIMEFRAMES') or list(SUPPORTED_TIMEFRAMES.keys())
    limit = int(os.getenv('YOYO_SCHEDULER_LIMIT', '300'))
    interval = int(os.getenv('YOYO_SCHEDULER_INTERVAL', '1800'))
    interval = max(15, interval)

    thread = threading.Thread(
        target=_yoyo_scheduler_loop,
        args=(symbols, timeframes, limit, interval),
        daemon=True
    )
    thread.start()
    _scheduler_started = True
    logger.info(
        "YOYO scheduler started (interval=%ss, symbols=%s, timeframes=%s)",
        interval,
        len(symbols),
        timeframes
    )
    return True


@yoyo_bp.route('/api/scheduler_status', methods=['GET'])
def yoyo_scheduler_status():
    return jsonify({
        'success': True,
        'enabled': _parse_bool_env(os.getenv('YOYO_SCHEDULER_ENABLED')),
        'telegram_configured': _telegram_enabled(),
        'scheduler_started': _scheduler_started,
        'lock': _read_scheduler_lock()
    })


@yoyo_bp.route('/api/chart', methods=['POST'])
def yoyo_chart():
    try:
        payload = request.get_json(silent=True) or {}
        symbol = _normalize_symbol(payload.get('symbol') or '')
        timeframe = (payload.get('timeframe') or '1h').strip()
        display_limit = int(payload.get('display_limit') or 1000)
        raw_limit = int(payload.get('limit') or display_limit)

        if not _is_valid_symbol(symbol):
            return jsonify({'success': False, 'error': 'Invalid symbol format'}), 400
        if timeframe not in SUPPORTED_TIMEFRAMES:
            return jsonify({'success': False, 'error': 'Unsupported timeframe'}), 400

        df = _get_gate_klines(symbol, SUPPORTED_TIMEFRAMES[timeframe], raw_limit)
        if df is None or df.empty:
            return jsonify({'success': False, 'error': 'No kline data'}), 502

        signals_payload = _compute_yoyo_signals(df)
        signals = signals_payload['signals']
        latest_signals = signals_payload['latest']

        display_limit = max(30, min(display_limit, 1000))
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


@yoyo_bp.route('/api/scan', methods=['POST'])
def yoyo_scan():
    payload = request.get_json(silent=True) or {}
    symbols = payload.get('symbols') or []
    timeframes = payload.get('timeframes')
    limit = payload.get('limit')
    result, status = scan_yoyo_symbols(symbols, timeframes, limit)
    return jsonify(result), status


@yoyo_bp.route('/api/daily_bottom_signals', methods=['GET'])
def daily_bottom_signals():
    cache = _load_daily_bottom_cache()
    if not cache:
        return jsonify({
            'success': False,
            'error': 'No cached data',
            'running': _daily_bottom_running
        }), 404
    cache['running'] = _daily_bottom_running
    return jsonify(cache)


@yoyo_bp.route('/api/top_movers_signals', methods=['POST'])
def yoyo_top_movers_signals():
    payload = request.get_json(silent=True) or {}
    top_n = int(payload.get('top_n') or 100)
    hours = int(payload.get('hours') or 12)
    include_symbols = payload.get('include_symbols') or []
    limit = int(payload.get('limit') or 300)

    if not isinstance(include_symbols, list):
        return jsonify({'success': False, 'error': 'include_symbols must be a list'}), 400

    top_n = max(10, min(top_n, 200))
    hours = max(1, min(hours, 72))
    limit = max(120, min(limit, 1000))

    tickers = _get_gate_tickers()
    if not tickers:
        return jsonify({'success': False, 'error': 'Failed to fetch tickers'}), 502

    filtered = _filter_usdt_tickers(tickers)
    if not filtered:
        return jsonify({'success': False, 'error': 'No valid tickers found'}), 502

    sorted_by_change = sorted(filtered, key=lambda x: x['change_24h'], reverse=True)
    top_gainers = sorted_by_change[:top_n]
    top_losers = sorted(filtered, key=lambda x: x['change_24h'])[:top_n]

    ticker_map = {item['symbol']: item for item in filtered}

    normalized_includes = []
    for raw in include_symbols:
        sym = _normalize_symbol(str(raw))
        if _is_valid_symbol(sym):
            normalized_includes.append(sym)
    normalized_includes = list(dict.fromkeys(normalized_includes))

    include_missing = [sym for sym in normalized_includes if sym not in ticker_map]
    include_symbols = [sym for sym in normalized_includes if sym in ticker_map]

    gainer_symbols = [item['symbol'] for item in top_gainers]
    loser_symbols = [item['symbol'] for item in top_losers]

    for sym in include_symbols:
        if sym in gainer_symbols or sym in loser_symbols:
            continue
        if ticker_map[sym]['change_24h'] >= 0:
            gainer_symbols.append(sym)
        else:
            loser_symbols.append(sym)

    symbols_to_scan = list(set(gainer_symbols + loser_symbols))
    signals_by_symbol: Dict[str, Dict[str, object]] = {}
    errors = []

    max_workers = min(8, max(1, len(symbols_to_scan)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_get_recent_1h_signals, symbol, hours, limit): symbol
            for symbol in symbols_to_scan
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                result, err = future.result()
            except Exception as e:
                errors.append({'symbol': symbol, 'error': str(e)})
                continue
            if err:
                errors.append({'symbol': symbol, 'error': err})
                continue
            if result is None:
                continue
            signals_by_symbol[symbol] = result

    def _build_list(symbols: List[str]) -> List[Dict[str, object]]:
        output = []
        for sym in symbols:
            sig_info = signals_by_symbol.get(sym)
            if not sig_info or not sig_info.get('signals_recent'):
                continue
            ticker = ticker_map.get(sym)
            if not ticker:
                continue
            recent_signals = sig_info['signals_recent']
            signal_types = sorted({s.get('signal') for s in recent_signals if s.get('signal')})
            output.append({
                'symbol': sym,
                'change_24h': ticker['change_24h'],
                'last_price': ticker['last_price'],
                'signal_count': len(recent_signals),
                'signal_types': signal_types,
                'latest_signal_time': sig_info.get('latest_signal_time'),
                'signals_recent': recent_signals,
                'is_watchlist': sym in include_symbols
            })
        return output

    gainers_with_signals = _build_list(gainer_symbols)
    losers_with_signals = _build_list(loser_symbols)

    return jsonify({
        'success': True,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'top_n': top_n,
        'hours': hours,
        'limit': limit,
        'gainers': gainers_with_signals,
        'losers': losers_with_signals,
        'include_missing': include_missing,
        'errors': errors
    })


@yoyo_bp.route('/api/symbols', methods=['GET'])
def yoyo_symbols():
    return jsonify({'success': True, 'symbols': SUPPORTED_SYMBOLS})


@yoyo_bp.route('/api/test_telegram', methods=['POST'])
def yoyo_test_telegram():
    payload = request.get_json(silent=True) or {}
    symbol = _normalize_symbol(payload.get('symbol') or 'BTCUSDT')
    timeframe = (payload.get('timeframe') or '1h').strip()

    if not _is_valid_symbol(symbol):
        return jsonify({'success': False, 'error': 'Invalid symbol format'}), 400
    if timeframe not in SUPPORTED_TIMEFRAMES:
        return jsonify({'success': False, 'error': 'Unsupported timeframe'}), 400
    if not _telegram_enabled():
        return jsonify({'success': False, 'error': 'Telegram not configured'}), 400

    now_ts = int(datetime.now(timezone.utc).timestamp())
    message = f"YOYO test message - {symbol} {timeframe} | 时间: {_format_ts(now_ts)}"
    _send_telegram_message(message)
    return jsonify({'success': True, 'message': 'Test message sent'})
