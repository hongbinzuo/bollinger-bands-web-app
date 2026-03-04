from flask import Blueprint, jsonify, request
import requests
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone

options_bp = Blueprint('options', __name__, url_prefix='/options')
logger = logging.getLogger(__name__)


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


@options_bp.route('/get_options', methods=['GET'])
def get_options():
    """获取BTC期权列表"""
    try:
        symbol = request.args.get('symbol', 'BTC')

        # Deribit API endpoint
        url = "https://www.deribit.com/api/v2/public/get_instruments"
        params = {'currency': symbol, 'kind': 'option', 'expired': 'false'}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('result'):
            raw_options = data['result']
            usdc_options = [o for o in raw_options if _is_usdc_option_name(o.get('instrument_name', ''))]
            options = usdc_options if usdc_options else raw_options
            option_market = 'USDC' if usdc_options else 'ALL'

            # 提取唯一的到期日和执行价格
            expiry_dates = sorted(list(set([opt['expiration_timestamp'] for opt in options])))
            periods = ['1h', '4h', '1d']  # 固定时间周期
            strikes = {}

            for opt in options:
                expiry = opt['expiration_timestamp']
                if expiry not in strikes:
                    strikes[expiry] = []
                strike = opt['strike']
                if strike not in strikes[expiry]:
                    strikes[expiry].append(strike)

            # 排序执行价格
            for expiry in strikes:
                strikes[expiry] = sorted(strikes[expiry])

            return jsonify({
                'success': True,
                'expiry_dates': expiry_dates,
                'periods': periods,
                'strikes': strikes,
                'options': options,
                'option_market': option_market
            })
        else:
            return jsonify({'success': False, 'error': 'API返回错误'})

    except Exception as e:
        logger.error(f"获取期权数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@options_bp.route('/get_option_data', methods=['POST'])
def get_option_data():
    """获取特定期权的详细数据"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC')
        expiry = data.get('expiry')
        strike = data.get('strike')
        option_type = data.get('type', 'CALL')

        url = "https://api.coincall.com/open/option/query/option-list"
        params = {'underlying': symbol}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get('code') == 0:
            options = result.get('data', [])

            # 筛选匹配的期权
            filtered = [opt for opt in options
                       if opt['expiryDate'] == expiry
                       and opt['strikePrice'] == strike
                       and opt['optionType'] == option_type]

            if filtered:
                option = filtered[0]
                return jsonify({
                    'success': True,
                    'data': {
                        'strike': option['strikePrice'],
                        'expiry': option['expiryDate'],
                        'type': option['optionType'],
                        'mark_price': option.get('markPrice', 0),
                        'bid': option.get('bidPrice', 0),
                        'ask': option.get('askPrice', 0),
                        'volume': option.get('volume24h', 0),
                        'open_interest': option.get('openInterest', 0),
                        'iv': option.get('impliedVolatility', 0)
                    }
                })
            else:
                return jsonify({'success': False, 'error': '未找到匹配的期权'})
        else:
            return jsonify({'success': False, 'error': 'API返回错误'})

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
        price_unit = _detect_price_unit_by_name(used_instrument)
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

        # 计算EMA均线
        ema_data = {}
        for period in ema_periods:
            df[f'ema{period}'] = df['close'].ewm(span=period).mean()
            ema_data[f'ema{period}'] = df[['time', f'ema{period}']].dropna().to_dict('records')

        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * std
        df['bb_lower'] = df['bb_middle'] - 2 * std

        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['signal'] = df['macd'].ewm(span=9).mean()
        df['histogram'] = df['macd'] - df['signal']

        # KDJ
        low_min = df['low'].rolling(9).min()
        high_max = df['high'].rolling(9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        df['k'] = rsv.ewm(com=2).mean()
        df['d'] = df['k'].ewm(com=2).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']

        result = {
            'success': True,
            'instrument': used_instrument,
            'fallback_used': fallback_used,
            'price_unit': price_unit,
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

