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
        for symbol, results in all_results.items():
            total_analyses += len(results)
            successful_analyses += sum(1 for r in results if r.get('status') == 'success')
        
        return jsonify({
            'success': True,
            'symbols_requested': len(processed_symbols),
            'symbols_processed': len(all_results),
            'total_timeframe_analyses': total_analyses,
            'successful_timeframe_analyses': successful_analyses,
            'results': all_results
        })
        
    except Exception as e:
        logger.error(f"Error analyzing multiple symbols: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.', 'details': str(e)}), 500

@multi_timeframe_bp.route('/get_top_symbols', methods=['GET'])
def get_top_symbols():
    """Gets the top 500 symbols by 24h volume from Binance Futures."""
    default_symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT',
        'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'ATOMUSDT', 'ETCUSDT', 'XLMUSDT', 'BCHUSDT', 'FILUSDT', 'TRXUSDT'
    ]
    
    try:
        url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError("API returned empty data.")
        
        # Sort by quote asset volume for a more accurate measure of market activity
        sorted_data = sorted(data, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
        
        # 【已优化】使用更精确的稳定币过滤逻辑
        stablecoin_bases = {'USDC', 'BUSD', 'TUSD', 'USDP', 'DAI', 'FDUSD'}
        
        filtered_symbols = []
        for item in sorted_data:
            symbol = item.get('symbol', '')
            # Filter out non-USDT pairs and stablecoin pairs
            if symbol.endswith('USDT'):
                base_asset = symbol[:-4] # e.g., 'BTCUSDT' -> 'BTC'
                if base_asset not in stablecoin_bases:
                    filtered_symbols.append(symbol)
            if len(filtered_symbols) >= 500:
                break
        
        logger.info(f"Successfully fetched and filtered {len(filtered_symbols)} symbols from Binance.")
        return jsonify({
            'success': True,
            'source': 'Binance Futures API',
            'count': len(filtered_symbols),
            'symbols': filtered_symbols
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch symbols from Binance API: {e}. Using default list.")
        return jsonify({
            'success': True,
            'source': 'Default List (API Failed)',
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

