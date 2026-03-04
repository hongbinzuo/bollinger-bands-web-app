from flask import Blueprint, jsonify, request
import requests
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone

options_bp = Blueprint('options', __name__, url_prefix='/options')
logger = logging.getLogger(__name__)

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
            options = data['result']

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
                'options': options
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

        # 构建期权合约名称
        expiry_date = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)
        date_str = expiry_date.strftime('%d%b%y').upper()
        instrument_name = f'{symbol}-{date_str}-{int(strike_value)}-{option_char}'

        # 从Deribit获取期权K线数据
        url = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"

        resolution_map = {'1h': '60', '4h': '240', '1d': '1D'}
        resolution = resolution_map.get(interval, '60')

        import time
        end_time = int(time.time() * 1000)
        start_time = end_time - (500 * 3600 * 1000)

        params = {
            'instrument_name': instrument_name,
            'start_timestamp': start_time,
            'end_timestamp': end_time,
            'resolution': resolution
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get('error'):
            api_msg = result['error'].get('message', 'Deribit请求失败')
            return jsonify({'success': False, 'error': f'Deribit API错误: {api_msg}'}), 400
        if not isinstance(result.get('result'), dict):
            return jsonify({'success': False, 'error': '无K线数据'})

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
        for col in ['time', 'open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['time', 'open', 'high', 'low', 'close', 'volume'])
        if df.empty:
            return jsonify({'success': False, 'error': 'K线数据为空'}), 500

        df = df.sort_values('time')

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

