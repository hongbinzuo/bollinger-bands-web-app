from flask import Blueprint, jsonify, request
import requests
import logging
import pandas as pd
import numpy as np
import os
import time
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime, timezone

options_bp = Blueprint('options', __name__, url_prefix='/options')
logger = logging.getLogger(__name__)

COINCALL_BASE_URL = os.getenv('COINCALL_BASE_URL', 'https://api.coincall.com').rstrip('/')
COINCALL_API_KEY = os.getenv('COINCALL_API_KEY', '').strip()
COINCALL_API_SECRET = os.getenv('COINCALL_API_SECRET', '').strip()
COINCALL_SIGN_OPEN = str(os.getenv('COINCALL_SIGN_OPEN', '1')).strip() not in {'0', 'false', 'False'}
try:
    COINCALL_TIMEOUT = int(os.getenv('COINCALL_TIMEOUT', '10') or 10)
except Exception:
    COINCALL_TIMEOUT = 10
OPTIONS_MARKET_SOURCE = str(os.getenv('OPTIONS_MARKET_SOURCE', 'coincall')).strip().lower()
_COINCALL_CACHE = {
    'instruments': {},  # key -> {'expire_at': float, 'value': list}
    'chain': {},        # key -> {'expire_at': float, 'value': list}
}


def _cache_get(bucket: str, key: str):
    item = _COINCALL_CACHE.get(bucket, {}).get(key)
    if not item:
        return None
    if time.time() >= float(item.get('expire_at', 0)):
        _COINCALL_CACHE[bucket].pop(key, None)
        return None
    return item.get('value')


def _cache_set(bucket: str, key: str, value, ttl_seconds: int):
    _COINCALL_CACHE.setdefault(bucket, {})[key] = {
        'expire_at': time.time() + max(1, int(ttl_seconds)),
        'value': value
    }


def _coincall_index_symbol(symbol: str) -> str:
    base = str(symbol or '').upper().strip()
    if not base:
        return 'BTCUSD'
    return f'{base}USD'


def _coincall_option_type_char(name: str) -> str:
    n = str(name or '').upper()
    if n.endswith('-C'):
        return 'C'
    if n.endswith('-P'):
        return 'P'
    return ''


def _coincall_sign_headers(method: str, path: str, params: dict | None):
    if not COINCALL_API_KEY or not COINCALL_API_SECRET:
        return {}
    query = urlencode(sorted((params or {}).items()), doseq=True)
    uri = path if not query else f'{path}?{query}'
    ts = str(int(time.time() * 1000))
    payload = f'{ts}{method.upper()}{uri}'
    sign = hmac.new(COINCALL_API_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return {
        'COINCALL-API-KEY': COINCALL_API_KEY,
        'COINCALL-TIMESTAMP': ts,
        'COINCALL-SIGN': sign
    }


def _coincall_get(path: str, params: dict | None = None):
    """访问Coincall接口，返回 (json, err)。"""
    url = f'{COINCALL_BASE_URL}{path}'
    headers = {}
    if COINCALL_SIGN_OPEN:
        headers.update(_coincall_sign_headers('GET', path, params))
    try:
        resp = requests.get(url, params=params or {}, headers=headers, timeout=COINCALL_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return None, str(e)

    if isinstance(payload, dict) and payload.get('code') == 0:
        return payload, ''
    if isinstance(payload, dict):
        msg = payload.get('msg') or payload.get('message') or payload.get('error') or 'Coincall请求失败'
        return payload, str(msg)
    return payload, 'Coincall响应格式异常'


def _fetch_coincall_instruments(symbol: str, use_cache: bool = True):
    base = str(symbol or '').upper().strip() or 'BTC'
    cache_key = base
    if use_cache:
        cached = _cache_get('instruments', cache_key)
        if isinstance(cached, list) and cached:
            return cached, ''

    payload, err = _coincall_get(f'/open/option/getInstruments/{base}')
    if err:
        return [], err
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return [], 'Coincall instruments格式异常'
    _cache_set('instruments', cache_key, data, ttl_seconds=30)
    return data, ''


def _find_coincall_option_symbol(
    symbol: str,
    expiry_ms: int,
    strike_value: float,
    option_char: str,
    instruments: list | None = None
) -> str:
    options = instruments or []
    if not options:
        options, _ = _fetch_coincall_instruments(symbol)
    if not options:
        return ''

    target_char = option_char.upper()
    try:
        target_expiry = int(expiry_ms)
    except Exception:
        target_expiry = None
    try:
        target_strike = float(strike_value)
    except Exception:
        target_strike = None

    exact_name = ''
    fallback = []
    for item in options:
        if not isinstance(item, dict):
            continue
        name = str(item.get('symbolName') or '')
        if not name:
            continue
        if _coincall_option_type_char(name) != target_char:
            continue

        expiry = item.get('expirationTimestamp')
        strike = item.get('strike')
        try:
            expiry_i = int(expiry)
            strike_f = float(strike)
        except Exception:
            continue
        if target_expiry is not None and target_strike is not None:
            if expiry_i == target_expiry and abs(strike_f - target_strike) < 1e-9:
                exact_name = name
                break
            fallback.append((abs(expiry_i - target_expiry), abs(strike_f - target_strike), name))

    if exact_name:
        return exact_name
    if not fallback:
        return ''
    fallback.sort(key=lambda x: (x[0], x[1]))
    return fallback[0][2]


def _fetch_coincall_kline(option_name: str, period: str, start_time: int, end_time: int):
    params = {
        'period': period,
        'start': int(start_time),
        'end': int(end_time),
        'limit': 1000
    }
    payload, err = _coincall_get(f'/open/option/market/kline/history/v1/{option_name}', params=params)
    if err:
        return [], err
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return [], 'Coincall K线格式异常'
    return data, ''


def _fetch_coincall_chain(symbol: str, expiry_ms: int, use_cache: bool = True):
    index = _coincall_index_symbol(symbol)
    cache_key = f'{index}:{int(expiry_ms)}'
    if use_cache:
        cached = _cache_get('chain', cache_key)
        if isinstance(cached, list):
            return cached, ''

    payload, err = _coincall_get(f'/open/option/get/v1/{index}', params={'endTime': int(expiry_ms)})
    if err:
        return [], err
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return [], 'Coincall chain格式异常'
    _cache_set('chain', cache_key, data, ttl_seconds=8)
    return data, ''


def _pick_coincall_quote(chain_rows: list, strike_value: float, option_char: str) -> dict:
    target_char = option_char.upper()
    best = {}
    best_dist = float('inf')
    for item in chain_rows:
        if not isinstance(item, dict):
            continue
        try:
            strike = float(item.get('strike'))
        except Exception:
            continue
        dist = abs(strike - float(strike_value))
        if target_char == 'C':
            quote = item.get('callOption') or {}
        else:
            quote = item.get('putOption') or {}
        if quote and dist < best_dist:
            best = quote
            best_dist = dist
            if dist < 1e-9:
                break
    return best if isinstance(best, dict) else {}


def _build_deribit_instrument_name(symbol: str, expiry_ms: int, strike_value: float, option_char: str) -> str:
    """构建Deribit期权合约名（日期不补零，如 5MAR26）"""
    expiry_date = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)
    date_str = f"{expiry_date.day}{expiry_date.strftime('%b%y').upper()}"
    return f'{symbol}-{date_str}-{int(strike_value)}-{option_char}'


def _rank_fallback_instruments(
    options: list,
    target_expiry_ms: int,
    target_strike: float,
    option_char: str,
) -> list:
    """Deribit兜底候选：同方向(C/P)按到期日和执行价最近排序"""
    if not isinstance(options, list):
        return []

    target_option_type = 'call' if option_char == 'C' else 'put'
    candidates = []

    for item in options:
        if not isinstance(item, dict):
            continue
        name = str(item.get('instrument_name') or '')
        expiry = item.get('expiration_timestamp')
        strike = item.get('strike')
        option_type = str(item.get('option_type') or '').lower()
        if not name or expiry is None or strike is None:
            continue
        if option_type and option_type != target_option_type:
            continue
        try:
            expiry_diff = abs(int(expiry) - target_expiry_ms)
            strike_diff = abs(float(strike) - target_strike)
            candidates.append((expiry_diff, strike_diff, name))
        except Exception:
            continue

    if not candidates:
        return []
    candidates.sort(key=lambda x: (x[0], x[1]))
    ranked = []
    for _, _, name in candidates:
        if name not in ranked:
            ranked.append(name)
    return ranked


def _fetch_deribit_kline(instrument_name: str, resolution: str, start_time: int, end_time: int):
    """请求Deribit K线，返回 (result_json, error_message)"""
    url = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
    params = {
        'instrument_name': instrument_name,
        'start_timestamp': start_time,
        'end_timestamp': end_time,
        'resolution': resolution
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as e:
        return None, str(e)

    if payload.get('error'):
        return payload, payload['error'].get('message', 'Deribit请求失败')
    if not isinstance(payload.get('result'), dict):
        return payload, 'Deribit返回缺少result'
    return payload, ''


def _fetch_deribit_ticker(instrument_name: str) -> dict:
    """获取Deribit ticker快照（含last/mark/bid/ask）。失败返回空dict。"""
    try:
        resp = requests.get(
            "https://www.deribit.com/api/v2/public/ticker",
            params={"instrument_name": instrument_name},
            timeout=10
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get('error'):
            return {}
        result = payload.get('result')
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def _fetch_deribit_mark_history(instrument_name: str, start_time: int, end_time: int) -> tuple:
    """获取Deribit标记价格历史，返回 (DataFrame[time, mark], error_message)。"""
    url = "https://www.deribit.com/api/v2/public/get_mark_price_history"
    params = {
        "instrument_name": instrument_name,
        "start_timestamp": start_time,
        "end_timestamp": end_time
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return pd.DataFrame(columns=['time', 'mark']), str(e)

    if payload.get('error'):
        return pd.DataFrame(columns=['time', 'mark']), payload['error'].get('message', 'Deribit请求失败')

    result = payload.get('result')
    rows = []
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                ts = item.get('timestamp', item.get('time', item.get('tick')))
                mark = item.get('mark_price', item.get('markPrice', item.get('value')))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                ts, mark = item[0], item[1]
            else:
                continue
            rows.append((ts, mark))
    elif isinstance(result, dict):
        ticks = result.get('ticks')
        marks = result.get('mark_price', result.get('mark_prices', result.get('close')))
        if isinstance(ticks, list) and isinstance(marks, list):
            for ts, mark in zip(ticks, marks):
                rows.append((ts, mark))

    if not rows:
        return pd.DataFrame(columns=['time', 'mark']), '无标记价格历史'

    df = pd.DataFrame(rows, columns=['time', 'mark'])
    df['time'] = pd.to_numeric(df['time'], errors='coerce')
    df['mark'] = pd.to_numeric(df['mark'], errors='coerce')
    df = df.dropna(subset=['time', 'mark']).sort_values('time').drop_duplicates(subset=['time'])
    if df.empty:
        return pd.DataFrame(columns=['time', 'mark']), '无标记价格历史'
    return df, ''


def _payload_has_rows(payload: dict) -> bool:
    """判断Deribit返回是否包含有效K线"""
    if not isinstance(payload, dict):
        return False
    result = payload.get('result')
    if not isinstance(result, dict):
        return False
    ticks = result.get('ticks')
    return isinstance(ticks, list) and len(ticks) > 0


def _is_usdc_option_name(name: str) -> bool:
    return '_USDC-' in str(name or '').upper()


def _detect_price_unit_by_name(name: str) -> str:
    return 'USDC' if _is_usdc_option_name(name) else 'NATIVE'


def _fetch_deribit_perp_last_price(symbol: str) -> float:
    """获取永续最新价（用于无法拉到历史时的兜底换算）"""
    try:
        resp = requests.get(
            "https://www.deribit.com/api/v2/public/ticker",
            params={"instrument_name": f"{symbol}-PERPETUAL"},
            timeout=10
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get('error'):
            return 0.0
        result = payload.get('result') or {}
        return float(result.get('last_price') or 0.0)
    except Exception:
        return 0.0


def _fetch_underlying_close_series(symbol: str, resolution: str, start_time: int, end_time: int) -> pd.DataFrame:
    """获取标的永续close序列（毫秒时间戳）。"""
    base = str(symbol or '').upper().strip()
    perp_payload, perp_err = _fetch_deribit_kline(f"{base}-PERPETUAL", resolution, start_time, end_time)
    if perp_err or not _payload_has_rows(perp_payload):
        return pd.DataFrame(columns=['time', 'u_close'])
    result = perp_payload['result']
    under = pd.DataFrame({
        'time': pd.to_numeric(result.get('ticks', []), errors='coerce'),
        'u_close': pd.to_numeric(result.get('close', []), errors='coerce'),
    }).dropna().sort_values('time')
    return under


def _convert_price_columns_to_usdc(
    df: pd.DataFrame,
    price_cols: list,
    symbol: str,
    resolution: str,
    start_time: int,
    end_time: int,
) -> tuple:
    """将指定价格列从币本位转换为USDC(≈USD)。"""
    base = str(symbol or '').upper().strip()
    if base not in {'BTC', 'ETH'}:
        return df, 'NATIVE'

    work = df.copy()
    work['time'] = pd.to_numeric(work['time'], errors='coerce')
    for col in price_cols:
        work[col] = pd.to_numeric(work[col], errors='coerce')
    work = work.dropna(subset=['time'] + price_cols).sort_values('time')
    if work.empty:
        return work, 'NATIVE'

    under = _fetch_underlying_close_series(base, resolution, start_time, end_time)
    if not under.empty:
        merged = pd.merge_asof(work, under, on='time', direction='nearest')
        merged['u_close'] = pd.to_numeric(merged['u_close'], errors='coerce').ffill().bfill()
        merged = merged.dropna(subset=['u_close'])
        if not merged.empty:
            for col in price_cols:
                merged[col] = merged[col] * merged['u_close']
            return merged[work.columns], 'USDC~'

    perp_last = _fetch_deribit_perp_last_price(base)
    if perp_last > 0:
        for col in price_cols:
            work[col] = work[col] * perp_last
        return work, 'USDC~'

    return work, 'NATIVE'


def _convert_native_option_to_usdc(
    df: pd.DataFrame,
    symbol: str,
    resolution: str,
    start_time: int,
    end_time: int,
) -> tuple:
    """
    将Deribit币本位期权价格换算为USDC(≈USD)。
    优先使用同时间的永续OHLC逐列换算，其次使用永续最新价近似换算。
    """
    return _convert_price_columns_to_usdc(
        df=df,
        price_cols=['open', 'high', 'low', 'close'],
        symbol=symbol,
        resolution=resolution,
        start_time=start_time,
        end_time=end_time,
    )


def _safe_float(value):
    try:
        v = float(value)
        if np.isfinite(v):
            return v
    except Exception:
        return None
    return None


def _normalize_interval_and_resolution(interval: str) -> tuple:
    """将前端周期映射到Deribit分辨率；4h使用1h拉取后端聚合"""
    normalized = str(interval or '1h').strip().lower()
    if normalized == '4h':
        return '4h', '60'
    if normalized == '1d':
        return '1d', '1D'
    return '1h', '60'


def _post_process_klines(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """统一时间为秒级时间戳；4h由1h聚合而来"""
    out = df.copy()
    out['time'] = pd.to_numeric(out['time'], errors='coerce')
    out = out.dropna(subset=['time', 'open', 'high', 'low', 'close', 'volume'])
    if out.empty:
        return out

    if interval == '4h':
        out['dt'] = pd.to_datetime(out['time'], unit='ms', utc=True)
        out = out.set_index('dt')
        out = out[['open', 'high', 'low', 'close', 'volume']].resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        if out.empty:
            return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        out['time'] = (out.index.view('int64') // 10 ** 9).astype('int64')
        out = out.reset_index(drop=True)
    else:
        out['time'] = (out['time'] // 1000).astype('int64')

    return out[['time', 'open', 'high', 'low', 'close', 'volume']].sort_values('time')


def _coincall_period(interval: str) -> str:
    normalized = str(interval or '1h').strip().lower()
    if normalized in {'1h', '4h', '1d'}:
        return normalized
    if normalized in {'h', '60'}:
        return '1h'
    if normalized in {'d', '1day'}:
        return '1d'
    return '1h'


def _compute_option_indicators(df: pd.DataFrame, ema_periods: list, requested_price_source: str, effective_price_source: str):
    """
    基于已清洗K线计算指标与价格快照。
    """
    out = df.copy()
    out['indicator_price'] = pd.to_numeric(out['close'], errors='coerce')
    if out['indicator_price'].isna().all():
        return None

    ema_data = {}
    for period in ema_periods:
        out[f'ema{period}'] = out['indicator_price'].ewm(span=period).mean()
        ema_data[f'ema{period}'] = out[['time', f'ema{period}']].dropna().to_dict('records')

    out['bb_middle'] = out['indicator_price'].rolling(20).mean()
    std = out['indicator_price'].rolling(20).std()
    out['bb_upper'] = out['bb_middle'] + 2 * std
    out['bb_lower'] = out['bb_middle'] - 2 * std

    ema12 = out['indicator_price'].ewm(span=12).mean()
    ema26 = out['indicator_price'].ewm(span=26).mean()
    out['macd'] = ema12 - ema26
    out['signal'] = out['macd'].ewm(span=9).mean()
    out['histogram'] = out['macd'] - out['signal']

    low_min = out['low'].rolling(9).min()
    high_max = out['high'].rolling(9).max()
    denom = (high_max - low_min).replace(0, np.nan)
    rsv = (out['indicator_price'] - low_min) / denom * 100
    out['k'] = rsv.ewm(com=2).mean()
    out['d'] = out['k'].ewm(com=2).mean()
    out['j'] = 3 * out['k'] - 2 * out['d']

    selected_price = _safe_float(out['indicator_price'].iloc[-1]) if not out.empty else None
    close_price = _safe_float(out['close'].iloc[-1]) if not out.empty else None
    if selected_price is None:
        selected_price = close_price

    return {
        'df': out,
        'current_price': selected_price,
        'close_price': close_price,
        'price_source_requested': requested_price_source,
        'effective_price_source': effective_price_source,
        'indicators': {
            **ema_data,
            'bb_upper': out[['time', 'bb_upper']].dropna().to_dict('records'),
            'bb_middle': out[['time', 'bb_middle']].dropna().to_dict('records'),
            'bb_lower': out[['time', 'bb_lower']].dropna().to_dict('records'),
            'macd': out[['time', 'macd', 'signal', 'histogram']].dropna().to_dict('records'),
            'kdj': out[['time', 'k', 'd', 'j']].dropna().to_dict('records')
        }
    }


def _build_coincall_kline_response(
    symbol: str,
    interval: str,
    expiry_ms: int,
    strike_value: float,
    option_char: str,
    ema_periods: list,
    requested_price_source: str,
):
    """
    Coincall数据通路：返回(result_dict, err_msg, status_code)
    """
    normalized_interval, _ = _normalize_interval_and_resolution(interval)
    coincall_period = _coincall_period(normalized_interval)

    end_time = int(time.time() * 1000)
    start_time = end_time - (500 * 3600 * 1000)

    instruments, inst_err = _fetch_coincall_instruments(symbol)
    if inst_err:
        return None, f'Coincall instruments错误: {inst_err}', 502
    if not instruments:
        return None, 'Coincall无可用期权合约', 404

    used_instrument = _find_coincall_option_symbol(
        symbol=symbol,
        expiry_ms=expiry_ms,
        strike_value=strike_value,
        option_char=option_char,
        instruments=instruments
    )
    if not used_instrument:
        return None, 'Coincall未找到匹配合约', 404

    rows, kline_err = _fetch_coincall_kline(used_instrument, coincall_period, start_time, end_time)
    if kline_err:
        return None, f'Coincall K线错误: {kline_err}', 400
    if not rows:
        return None, '无K线数据', 404

    df = pd.DataFrame([{
        'time': item.get('time'),
        'open': item.get('open'),
        'high': item.get('high'),
        'low': item.get('low'),
        'close': item.get('close'),
        'volume': item.get('volume')
    } for item in rows if isinstance(item, dict)])
    if df.empty:
        return None, 'K线数据为空', 404

    for col in ['time', 'open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['time', 'open', 'high', 'low', 'close', 'volume']).sort_values('time')
    df = df.drop_duplicates(subset=['time'])
    if df.empty:
        return None, 'K线数据为空', 404

    df = _post_process_klines(df, normalized_interval)
    if df.empty:
        return None, '无K线数据', 404

    effective_price_source = 'close'
    source_note = ''
    # Coincall当前公开口径只有一套历史K线，mark请求使用近似模式，避免全量扫描被误过滤。
    if requested_price_source == 'mark':
        effective_price_source = 'mark_proxy'
        source_note = 'Coincall暂无独立历史mark，使用K线口径近似'

    calc = _compute_option_indicators(df, ema_periods, requested_price_source, effective_price_source)
    if not calc:
        return None, '指标计算失败', 500

    chain_rows, chain_err = _fetch_coincall_chain(symbol, expiry_ms)
    quote = _pick_coincall_quote(chain_rows or [], strike_value, option_char) if not chain_err else {}
    ticker_last = _safe_float(quote.get('lastPrice'))
    ticker_mark = _safe_float(quote.get('markPrice'))
    best_bid = _safe_float(quote.get('bid'))
    best_ask = _safe_float(quote.get('ask'))

    mid_price = None
    spread_pct = None
    if best_bid is not None and best_ask is not None and best_bid > 0 and best_ask > 0:
        mid_price = (best_bid + best_ask) / 2.0
        if mid_price > 0:
            spread_pct = (best_ask - best_bid) / mid_price * 100.0

    response = {
        'success': True,
        'market_source': 'coincall',
        'instrument': used_instrument,
        'fallback_used': False,
        'price_unit': 'USDT',
        'price_source_requested': requested_price_source,
        'effective_price_source': calc['effective_price_source'],
        'source_note': source_note,
        'current_price': calc['current_price'],
        'current_prices': {
            'selected': calc['current_price'],
            'close': calc['close_price'],
            'mark': ticker_mark,
            'last': ticker_last,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'mid': mid_price,
            'spread_pct': spread_pct
        },
        'klines': calc['df'][['time', 'open', 'high', 'low', 'close', 'volume']].to_dict('records'),
        'indicators': calc['indicators']
    }
    return response, '', 200


@options_bp.route('/get_options', methods=['GET'])
def get_options():
    """获取期权元信息（优先Coincall，失败回退Deribit）。"""
    try:
        symbol = str(request.args.get('symbol', 'BTC')).upper().strip() or 'BTC'

        # 1) 优先Coincall（用户反馈Deribit覆盖不足）
        coincall_options, coincall_err = _fetch_coincall_instruments(symbol)
        if not coincall_err and coincall_options:
            options = []
            strikes = {}
            expiry_set = set()
            for item in coincall_options:
                if not isinstance(item, dict):
                    continue
                name = str(item.get('symbolName') or '')
                expiry = item.get('expirationTimestamp')
                strike = item.get('strike')
                option_char = _coincall_option_type_char(name)
                if not name or expiry is None or strike is None or option_char not in {'C', 'P'}:
                    continue
                try:
                    expiry_i = int(expiry)
                    strike_f = float(strike)
                except Exception:
                    continue
                option_type = 'call' if option_char == 'C' else 'put'
                options.append({
                    'instrument_name': name,
                    'expiration_timestamp': expiry_i,
                    'strike': strike_f,
                    'option_type': option_type,
                    'source': 'coincall'
                })
                expiry_set.add(expiry_i)
                strikes.setdefault(expiry_i, [])
                if strike_f not in strikes[expiry_i]:
                    strikes[expiry_i].append(strike_f)

            expiry_dates = sorted(expiry_set)
            for expiry in strikes:
                strikes[expiry] = sorted(strikes[expiry])

            return jsonify({
                'success': True,
                'expiry_dates': expiry_dates,
                'periods': ['1h', '4h', '1d'],
                'strikes': strikes,
                'options': options,
                'option_market': 'COINCALL',
                'expiry_coverage': {
                    'all_count': len(expiry_dates),
                    'usdc_count': len(expiry_dates),
                    'coverage_pct': 100.0 if expiry_dates else 0.0,
                    'missing_count': 0,
                    'missing_expiry_dates': []
                }
            })

        # 2) Coincall失败时回退Deribit（保留旧逻辑）
        if coincall_err:
            logger.warning(f'Coincall get_options失败，回退Deribit: {coincall_err}')
        url = "https://www.deribit.com/api/v2/public/get_instruments"
        params = {'currency': symbol, 'kind': 'option', 'expired': 'false'}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('result'):
            return jsonify({'success': False, 'error': coincall_err or 'API返回错误'})

        raw_options = data['result']
        usdc_options = [o for o in raw_options if _is_usdc_option_name(o.get('instrument_name', ''))]
        options = usdc_options if usdc_options else raw_options
        option_market = 'USDC' if usdc_options else 'ALL'

        raw_expiry_dates = sorted(list(set([opt['expiration_timestamp'] for opt in raw_options if opt.get('expiration_timestamp') is not None])))
        usdc_expiry_dates = sorted(list(set([opt['expiration_timestamp'] for opt in usdc_options if opt.get('expiration_timestamp') is not None])))
        usdc_expiry_set = set(usdc_expiry_dates)
        missing_expiry_dates = [ts for ts in raw_expiry_dates if ts not in usdc_expiry_set]
        all_count = len(raw_expiry_dates)
        usdc_count = len(usdc_expiry_dates)
        coverage_pct = (usdc_count / all_count * 100.0) if all_count > 0 else 0.0

        expiry_dates = sorted(list(set([opt['expiration_timestamp'] for opt in options])))
        periods = ['1h', '4h', '1d']
        strikes = {}

        for opt in options:
            expiry = opt['expiration_timestamp']
            if expiry not in strikes:
                strikes[expiry] = []
            strike = opt['strike']
            if strike not in strikes[expiry]:
                strikes[expiry].append(strike)

        for expiry in strikes:
            strikes[expiry] = sorted(strikes[expiry])

        return jsonify({
            'success': True,
            'expiry_dates': expiry_dates,
            'periods': periods,
            'strikes': strikes,
            'options': options,
            'option_market': option_market,
            'expiry_coverage': {
                'all_count': all_count,
                'usdc_count': usdc_count,
                'coverage_pct': coverage_pct,
                'missing_count': len(missing_expiry_dates),
                'missing_expiry_dates': missing_expiry_dates
            }
        })
    except Exception as e:
        logger.error(f"获取期权数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@options_bp.route('/get_option_data', methods=['POST'])
def get_option_data():
    """获取特定期权的详细数据"""
    try:
        data = request.json or {}
        symbol = str(data.get('symbol', 'BTC')).upper().strip() or 'BTC'
        expiry = data.get('expiry')
        strike = data.get('strike')
        option_type = str(data.get('type', 'CALL')).strip().upper()
        option_char = 'C' if option_type == 'CALL' else 'P'

        if expiry is None or strike is None:
            return jsonify({'success': False, 'error': '缺少expiry或strike参数'}), 400

        try:
            expiry_ms = int(expiry)
            strike_value = float(strike)
        except Exception:
            return jsonify({'success': False, 'error': 'expiry或strike格式错误'}), 400

        chain_rows, chain_err = _fetch_coincall_chain(symbol, expiry_ms, use_cache=False)
        if chain_err:
            return jsonify({'success': False, 'error': f'Coincall错误: {chain_err}'}), 502

        quote = _pick_coincall_quote(chain_rows, strike_value, option_char)
        if not quote:
            return jsonify({'success': False, 'error': '未找到匹配的期权'}), 404

        return jsonify({
            'success': True,
            'data': {
                'strike': strike_value,
                'expiry': expiry_ms,
                'type': option_type,
                'mark_price': _safe_float(quote.get('markPrice')) or 0,
                'bid': _safe_float(quote.get('bid')) or 0,
                'ask': _safe_float(quote.get('ask')) or 0,
                'last_price': _safe_float(quote.get('lastPrice')) or 0,
                'volume': _safe_float(quote.get('volume')) or 0,
                'open_interest': _safe_float(quote.get('openInterest')) or 0,
                'iv': _safe_float(quote.get('markIv')) or 0,
                'symbol': quote.get('symbol') or quote.get('displayName') or ''
            }
        })

    except Exception as e:
        logger.error(f"获取期权详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@options_bp.route('/get_kline_data', methods=['POST'])
def get_kline_data():
    """获取期权K线数据和技术指标"""
    try:
        data = request.get_json(silent=True) or {}
        symbol = str(data.get('symbol', 'BTC')).upper().strip()
        interval = data.get('interval', '1h')
        expiry = data.get('expiry')
        strike = data.get('strike')
        option_type = str(data.get('option_type', 'call')).strip().lower()
        ema_periods = data.get('ema_periods', [13, 21, 34, 55, 89, 144, 233])
        prefer_usdc = bool(data.get('prefer_usdc', True))
        requested_price_source = str(data.get('price_source', 'close')).strip().lower()
        if requested_price_source not in {'close', 'mark'}:
            requested_price_source = 'close'
        market_source = str(data.get('market_source', OPTIONS_MARKET_SOURCE)).strip().lower()
        if market_source not in {'coincall', 'deribit', 'auto'}:
            market_source = OPTIONS_MARKET_SOURCE if OPTIONS_MARKET_SOURCE in {'coincall', 'deribit', 'auto'} else 'coincall'

        if not symbol:
            return jsonify({'success': False, 'error': '缺少symbol参数'}), 400
        if expiry is None or strike is None:
            return jsonify({'success': False, 'error': '缺少expiry或strike参数'}), 400
        try:
            expiry_ms = int(expiry)
            strike_value = float(strike)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'expiry或strike格式错误'}), 400

        option_char = option_type[:1].upper()
        if option_char not in {'C', 'P'}:
            return jsonify({'success': False, 'error': 'option_type必须为call或put'}), 400

        safe_periods = []
        for p in ema_periods if isinstance(ema_periods, list) else []:
            try:
                pv = int(p)
                if 1 <= pv <= 500:
                    safe_periods.append(pv)
            except Exception:
                continue
        ema_periods = safe_periods or [13, 21, 34, 55, 89, 144, 233]

        # 优先Coincall（用户场景中Deribit很多合约无K线/无mark）
        if market_source in {'coincall', 'auto'}:
            cc_result, cc_err, cc_status = _build_coincall_kline_response(
                symbol=symbol,
                interval=interval,
                expiry_ms=expiry_ms,
                strike_value=strike_value,
                option_char=option_char,
                ema_periods=ema_periods,
                requested_price_source=requested_price_source
            )
            if cc_result:
                return jsonify(cc_result)
            if market_source == 'coincall':
                return jsonify({'success': False, 'error': cc_err}), cc_status
            logger.warning(f'Coincall get_kline_data失败，回退Deribit: {cc_err}')

        interval, resolution = _normalize_interval_and_resolution(interval)

        import time
        end_time = int(time.time() * 1000)
        start_time = end_time - (500 * 3600 * 1000)

        date_obj = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)
        date_str = f"{date_obj.day}{date_obj.strftime('%b%y').upper()}"
        instrument_candidates = []
        if prefer_usdc:
            instrument_candidates.append(f"{symbol}_USDC-{date_str}-{int(strike_value)}-{option_char}")
        instrument_candidates.append(_build_deribit_instrument_name(symbol, expiry_ms, strike_value, option_char))

        result = None
        err_msg = 'no data'
        used_instrument = instrument_candidates[0]
        for candidate in instrument_candidates:
            cand_result, cand_err = _fetch_deribit_kline(candidate, resolution, start_time, end_time)
            if cand_err:
                err_msg = cand_err
                continue
            if not _payload_has_rows(cand_result):
                err_msg = '无K线数据'
                continue
            result = cand_result
            err_msg = ''
            used_instrument = candidate
            break

        instrument_name = used_instrument
        fallback_tried = 0
        fallback_used = False
        need_fallback = bool(err_msg) or (result is not None and not _payload_has_rows(result))
        if need_fallback:
            # Deribit报错或无成交K线时兜底：拉取可交易期权并按最近候选依次尝试
            try:
                inst_resp = requests.get(
                    "https://www.deribit.com/api/v2/public/get_instruments",
                    params={'currency': symbol, 'kind': 'option', 'expired': 'false'},
                    timeout=10
                )
                inst_resp.raise_for_status()
                inst_data = inst_resp.json()
                pool = inst_data.get('result', [])
                if prefer_usdc:
                    usdc_pool = [o for o in pool if _is_usdc_option_name(o.get('instrument_name', ''))]
                    if usdc_pool:
                        pool = usdc_pool
                fallback_names = _rank_fallback_instruments(
                    pool,
                    target_expiry_ms=expiry_ms,
                    target_strike=strike_value,
                    option_char=option_char
                )
                for fallback_name in fallback_names[:30]:
                    if fallback_name == instrument_name:
                        continue
                    fallback_tried += 1
                    second_result, second_err = _fetch_deribit_kline(
                        fallback_name, resolution, start_time, end_time
                    )
                    if second_err:
                        continue
                    if not _payload_has_rows(second_result):
                        continue
                    result = second_result
                    used_instrument = fallback_name
                    err_msg = ''
                    fallback_used = True
                    break
            except Exception:
                pass

        if err_msg:
            return jsonify({
                'success': False,
                'error': f'Deribit API错误: {err_msg}',
                'instrument': instrument_name,
                'fallback_tried': fallback_tried
            }), 400

        if not _payload_has_rows(result):
            return jsonify({
                'success': False,
                'error': '无K线数据',
                'instrument': instrument_name,
                'fallback_tried': fallback_tried
            }), 404

        kline_data = result['result']
        required_keys = ['ticks', 'open', 'high', 'low', 'close', 'volume']
        if not all(isinstance(kline_data.get(k), list) for k in required_keys):
            return jsonify({'success': False, 'error': 'K线数据格式异常'}), 500
        if not kline_data['ticks']:
            return jsonify({'success': False, 'error': '无K线数据'})

        df = pd.DataFrame({
            'time': kline_data['ticks'],
            'open': kline_data['open'],
            'high': kline_data['high'],
            'low': kline_data['low'],
            'close': kline_data['close'],
            'volume': kline_data['volume']
        })
        instrument_native = _detect_price_unit_by_name(used_instrument) == 'NATIVE'
        price_unit = 'NATIVE' if instrument_native else 'USDC'
        if instrument_native:
            df, price_unit = _convert_native_option_to_usdc(
                df=df,
                symbol=symbol,
                resolution=resolution,
                start_time=start_time,
                end_time=end_time,
            )
        for col in ['time', 'open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['time', 'open', 'high', 'low', 'close', 'volume'])
        if df.empty:
            return jsonify({'success': False, 'error': 'K线数据为空'}), 500

        df = _post_process_klines(df, interval)
        if df.empty:
            return jsonify({
                'success': False,
                'error': '无K线数据',
                'instrument': used_instrument,
                'fallback_tried': fallback_tried
            }), 404

        effective_price_source = 'close'
        df['indicator_price'] = pd.to_numeric(df['close'], errors='coerce')
        source_note = ''

        if requested_price_source == 'mark':
            mark_df, mark_err = _fetch_deribit_mark_history(used_instrument, start_time, end_time)
            if not mark_err and not mark_df.empty:
                if instrument_native:
                    mark_df, mark_unit = _convert_price_columns_to_usdc(
                        df=mark_df,
                        price_cols=['mark'],
                        symbol=symbol,
                        resolution=resolution,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    if mark_unit == 'NATIVE' and price_unit != 'NATIVE':
                        # 主K线已换算成功但mark换算失败时，放弃mark来源，避免单位混淆
                        mark_df = pd.DataFrame(columns=['time', 'mark'])
                mark_df['time'] = pd.to_numeric(mark_df['time'], errors='coerce')
                mark_df['mark'] = pd.to_numeric(mark_df['mark'], errors='coerce')
                mark_df = mark_df.dropna(subset=['time', 'mark']).sort_values('time')
                if not mark_df.empty:
                    mark_df['time'] = (mark_df['time'] // 1000).astype('int64')
                    mark_df['dt'] = pd.to_datetime(mark_df['time'], unit='s', utc=True)
                    mark_df = mark_df.set_index('dt')
                    if interval == '4h':
                        mark_df = mark_df[['time', 'mark']].resample('4h').last().dropna()
                    elif interval == '1d':
                        mark_df = mark_df[['time', 'mark']].resample('1D').last().dropna()
                    else:
                        mark_df = mark_df[['time', 'mark']]
                    if not mark_df.empty:
                        mark_df = mark_df.reset_index(drop=True).sort_values('time')
                        aligned = pd.merge_asof(
                            df[['time']].sort_values('time'),
                            mark_df[['time', 'mark']],
                            on='time',
                            direction='nearest'
                        )
                        aligned['mark'] = pd.to_numeric(aligned['mark'], errors='coerce').ffill().bfill()
                        if aligned['mark'].notna().sum() >= max(10, int(len(df) * 0.3)):
                            df['indicator_price'] = aligned['mark'].values
                            effective_price_source = 'mark'
            if effective_price_source != 'mark':
                source_note = '标记价格不可用，已回退成交价'

        df['indicator_price'] = pd.to_numeric(df['indicator_price'], errors='coerce')
        if df['indicator_price'].isna().all():
            df['indicator_price'] = pd.to_numeric(df['close'], errors='coerce')
            effective_price_source = 'close'
            source_note = '价格源异常，已回退成交价'

        # 计算EMA均线
        ema_data = {}
        for period in ema_periods:
            df[f'ema{period}'] = df['indicator_price'].ewm(span=period).mean()
            ema_data[f'ema{period}'] = df[['time', f'ema{period}']].dropna().to_dict('records')

        # 布林带
        df['bb_middle'] = df['indicator_price'].rolling(20).mean()
        std = df['indicator_price'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * std
        df['bb_lower'] = df['bb_middle'] - 2 * std

        # MACD
        ema12 = df['indicator_price'].ewm(span=12).mean()
        ema26 = df['indicator_price'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['signal'] = df['macd'].ewm(span=9).mean()
        df['histogram'] = df['macd'] - df['signal']

        # KDJ
        low_min = df['low'].rolling(9).min()
        high_max = df['high'].rolling(9).max()
        rsv = (df['indicator_price'] - low_min) / (high_max - low_min) * 100
        df['k'] = rsv.ewm(com=2).mean()
        df['d'] = df['k'].ewm(com=2).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']

        ticker = _fetch_deribit_ticker(used_instrument)
        ticker_last = _safe_float(ticker.get('last_price'))
        ticker_mark = _safe_float(ticker.get('mark_price'))
        best_bid = _safe_float(ticker.get('best_bid_price'))
        best_ask = _safe_float(ticker.get('best_ask_price'))

        if price_unit == 'USDC~':
            fx = _fetch_deribit_perp_last_price(symbol)
            if fx > 0:
                if ticker_last is not None:
                    ticker_last = ticker_last * fx
                if ticker_mark is not None:
                    ticker_mark = ticker_mark * fx
                if best_bid is not None:
                    best_bid = best_bid * fx
                if best_ask is not None:
                    best_ask = best_ask * fx

        mid_price = None
        spread_pct = None
        if best_bid is not None and best_ask is not None and best_bid > 0 and best_ask > 0:
            mid_price = (best_bid + best_ask) / 2.0
            if mid_price > 0:
                spread_pct = (best_ask - best_bid) / mid_price * 100.0

        selected_price = _safe_float(df['indicator_price'].iloc[-1]) if not df.empty else None
        close_price = _safe_float(df['close'].iloc[-1]) if not df.empty else None
        if selected_price is None:
            selected_price = close_price

        result = {
            'success': True,
            'market_source': 'deribit',
            'instrument': used_instrument,
            'fallback_used': fallback_used,
            'price_unit': price_unit,
            'price_source_requested': requested_price_source,
            'effective_price_source': effective_price_source,
            'source_note': source_note,
            'current_price': selected_price,
            'current_prices': {
                'selected': selected_price,
                'close': close_price,
                'mark': ticker_mark,
                'last': ticker_last,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid': mid_price,
                'spread_pct': spread_pct
            },
            'klines': df[['time', 'open', 'high', 'low', 'close', 'volume']].to_dict('records'),
            'indicators': {
                **ema_data,
                'bb_upper': df[['time', 'bb_upper']].dropna().to_dict('records'),
                'bb_middle': df[['time', 'bb_middle']].dropna().to_dict('records'),
                'bb_lower': df[['time', 'bb_lower']].dropna().to_dict('records'),
                'macd': df[['time', 'macd', 'signal', 'histogram']].dropna().to_dict('records'),
                'kdj': df[['time', 'k', 'd', 'j']].dropna().to_dict('records')
            }
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取K线数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

