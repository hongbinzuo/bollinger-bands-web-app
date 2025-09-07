from flask import Blueprint, request, jsonify
import logging
import requests
import time
from typing import List, Dict, Any

# Assuming the first file is named 'multi_timeframe_strategy.py'
from multi_timeframe_strategy import MultiTimeframeStrategy

# --- Blueprint and Global Instances ---
multi_timeframe_bp = Blueprint('multi_timeframe', __name__, url_prefix='/multi_timeframe')

# Create a single strategy instance for the application
# Note: In a multi-worker production environment (e.g., Gunicorn), each worker
# will have its own instance. State stored in `strategy.ema_usage` will not be shared.
# For shared state, consider using a database or a cache like Redis.
strategy = MultiTimeframeStrategy()
logger = logging.getLogger(__name__)

# --- Helper Function for Code Reusability ---
def _process_symbol(symbol: str) -> str:
    """
    Standardizes a symbol string to the required format (uppercase, ends with USDT).
    """
    if not isinstance(symbol, str) or not symbol:
        return ""
    processed = symbol.upper().strip()
    if not processed.endswith('USDT'):
        processed += 'USDT'
    return processed

# --- API Endpoints ---

@multi_timeframe_bp.route('/analyze_symbol', methods=['POST'])
def analyze_symbol():
    """Analyzes all timeframes for a single symbol."""
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({'error': 'Request body must be JSON with a "symbol" key.'}), 400

        symbol = _process_symbol(data['symbol'])
        if not symbol:
            return jsonify({'error': 'Symbol cannot be empty.'}), 400
        
        logger.info(f"Received request to analyze symbol: {symbol}")
        
        results = strategy.analyze_all_timeframes(symbol)
        
        success_count = sum(1 for r in results if r.get('status') == 'success')
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'total_timeframes_analyzed': len(results),
            'successful_timeframes': success_count,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error analyzing symbol {data.get('symbol', '')}: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.', 'details': str(e)}), 500

@multi_timeframe_bp.route('/analyze_multiple_symbols', methods=['POST'])
def analyze_multiple_symbols():
    """Analyzes multiple symbols."""
    try:    
        data = request.get_json()
        if not data or 'symbols' not in data or not isinstance(data['symbols'], list):
            return jsonify({'error': 'Request body must be JSON with a "symbols" key containing a list.'}), 400

        symbols_list = data.get('symbols', [])
        if not symbols_list:
            return jsonify({'error': 'The "symbols" list cannot be empty.'}), 400
        
        processed_symbols = [_process_symbol(s) for s in symbols_list if s]
        
        logger.info(f"Received request to analyze {len(processed_symbols)} symbols.")
        
        all_results = strategy.analyze_multiple_symbols(processed_symbols)
        
        # 【已优化】使用更清晰的变量名进行统计
        total_analyses = 0
        successful_analyses = 0
        all_signals = []
        
        for symbol, results in all_results.items():
            total_analyses += len(results)
            for result in results:
                if result.get('status') == 'success':
                    successful_analyses += 1
                    # 将信号转换为前端期望的格式
                    for signal in result.get('all_signals', []):
                        formatted_signal = {
                            'symbol': symbol,
                            'timeframe': result['timeframe'],
                            'trend': result['trend'],
                            'signal_type': signal.get('signal', 'unknown'),
                            'entry_price': signal.get('entry_price', result['current_price']),
                            'take_profit': result.get('take_profit_price', 0),
                            'profit_pct': 0,  # 暂时设为0，需要计算
                            'signal_time': result.get('signal_time', ''),
                            'ema_period': signal.get('ema_period', ''),
                            'signal_data': signal  # 保留原始信号数据
                        }
                        all_signals.append(formatted_signal)
        
        return jsonify({
            'success': True,
            'symbols_requested': len(processed_symbols),
            'symbols_processed': len(all_results),
            'total_timeframe_analyses': total_analyses,
            'successful_timeframe_analyses': successful_analyses,
            'total_signals': len(all_signals),
            'successful_signals': len(all_signals),
            'results': all_results,
            'signals': all_signals  # 添加前端期望的信号格式
        })
        
    except Exception as e:
        logger.error(f"Error analyzing multiple symbols: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.', 'details': str(e)}), 500

@multi_timeframe_bp.route('/get_top_symbols', methods=['GET'])
def get_top_symbols():
    """Gets the top 500 symbols by 24h volume from Gate.io."""
    default_symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT',
        'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'ATOMUSDT', 'ETCUSDT', 'XLMUSDT', 'BCHUSDT', 'FILUSDT', 'TRXUSDT'
    ]
    
    try:
        # 使用Gate.io API获取24小时交易数据
        url = 'https://api.gateio.ws/api/v4/spot/tickers'
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError("Gate.io API returned empty data.")
        
        # Gate.io数据格式: [{"currency_pair": "BTC_USDT", "last": "50000", "lowest_ask": "50001", "highest_bid": "49999", "change_percentage": "2.5", "base_volume": "1000", "quote_volume": "50000000", "high_24h": "51000", "low_24h": "49000"}]
        
        # 按quote_volume排序，过滤USDT交易对
        usdt_pairs = []
        for item in data:
            currency_pair = item.get('currency_pair', '')
            if currency_pair.endswith('_USDT'):
                # 转换格式: BTC_USDT -> BTCUSDT
                base_asset = currency_pair.replace('_USDT', '')
                symbol = f"{base_asset}USDT"
                
                # 过滤稳定币
                stablecoin_bases = {'USDC', 'BUSD', 'TUSD', 'USDP', 'DAI', 'FDUSD'}
                
                # 过滤杠杆代币 (3L, 3S, 5L, 5S)
                leverage_tokens = ['3L', '3S', '5L', '5S']
                is_leverage_token = any(base_asset.endswith(token) for token in leverage_tokens)
                
                if base_asset not in stablecoin_bases and not is_leverage_token:
                    quote_volume = float(item.get('quote_volume', 0))
                    usdt_pairs.append({
                        'symbol': symbol,
                        'quote_volume': quote_volume,
                        'currency_pair': currency_pair
                    })
        
        # 按交易量降序排序
        sorted_pairs = sorted(usdt_pairs, key=lambda x: x['quote_volume'], reverse=True)
        
        # 取前500个
        filtered_symbols = [pair['symbol'] for pair in sorted_pairs[:500]]
        
        logger.info(f"Successfully fetched and filtered {len(filtered_symbols)} symbols from Gate.io.")
        return jsonify({
            'success': True,
            'source': 'Gate.io API',
            'count': len(filtered_symbols),
            'symbols': filtered_symbols
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch symbols from Gate.io API: {e}. Using default list.")
        return jsonify({
            'success': True,
            'source': 'Default List (Gate.io API Failed)',
            'count': len(default_symbols),
            'symbols': default_symbols
        })
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_top_symbols: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.', 'details': str(e)}), 500


@multi_timeframe_bp.route('/get_strategy_info', methods=['GET'])
def get_strategy_info():
    """Returns information about the strategy configuration."""
    return jsonify({
        'success': True,
        'strategy_name': 'Multi-Timeframe EMA Pullback Strategy',
        'timeframes': strategy.timeframes,
        'ema_periods': strategy.ema_periods,
        'take_profit_mapping': strategy.take_profit_timeframes,
        'description': {
            'trend_detection': 'EMA144 > EMA233 for bullish trend, and vice-versa for bearish.',
            'entry_condition': 'Price pulls back to one of the key EMA levels (144, 233, 377, 610) with volume confirmation.',
            'take_profit': 'Calculated based on the Bollinger Bands middle line of a smaller, corresponding timeframe.',
        }
    })

@multi_timeframe_bp.route('/validate_symbol', methods=['POST'])
def validate_symbol_endpoint():
    """Validates if a symbol exists and has data."""
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({'error': 'Request body must be JSON with a "symbol" key.'}), 400

        symbol = _process_symbol(data['symbol'])
        if not symbol:
            return jsonify({'error': 'Symbol cannot be empty.'}), 400

        is_valid = strategy.validate_symbol(symbol)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'is_valid': is_valid,
            'message': f'Symbol {symbol} is {"valid and has data" if is_valid else "invalid or has no data"}.'
        })
        
    except Exception as e:
        logger.error(f"Error validating symbol {data.get('symbol', '')}: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.', 'details': str(e)}), 500

@multi_timeframe_bp.route('/clear_ema_usage', methods=['POST'])
def clear_ema_usage():
    """
    Clears the in-memory EMA usage record.
    Note: This is not effective in a multi-worker production environment.
    """
    try:
        strategy.ema_usage = {}
        logger.info("In-memory EMA usage record has been cleared.")
        return jsonify({
            'success': True,
            'message': 'EMA usage record has been cleared for this worker process.'
        })
    except Exception as e:
        logger.error(f"Failed to clear EMA usage record: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.', 'details': str(e)}), 500

