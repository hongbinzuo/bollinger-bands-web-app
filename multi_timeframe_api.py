"""
多时间框架策略API接口
"""

from flask import Blueprint, request, jsonify
import logging
from multi_timeframe_strategy import MultiTimeframeStrategy
import json

# 创建蓝图
multi_timeframe_bp = Blueprint('multi_timeframe', __name__, url_prefix='/multi_timeframe')

# 创建策略实例
strategy = MultiTimeframeStrategy()

logger = logging.getLogger(__name__)

@multi_timeframe_bp.route('/analyze_symbol', methods=['POST'])
def analyze_symbol():
    """分析单个币种的所有时间框架"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'error': '请提供币种'}), 400
        
        # 确保币种以USDT结尾
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        logger.info(f"开始分析币种: {symbol}")
        
        # 分析所有时间框架
        results = strategy.analyze_all_timeframes(symbol)
        
        # 统计结果
        success_count = sum(1 for r in results if r['status'] == 'success')
        total_count = len(results)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'total_timeframes': total_count,
            'successful_signals': success_count,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"分析币种失败: {e}")
        return jsonify({'error': str(e)}), 500

@multi_timeframe_bp.route('/analyze_multiple_symbols', methods=['POST'])
def analyze_multiple_symbols():
    """分析多个币种"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'error': '请提供币种列表'}), 400
        
        # 处理币种格式
        processed_symbols = []
        for symbol in symbols:
            symbol = symbol.upper()
            if not symbol.endswith('USDT'):
                symbol += 'USDT'
            processed_symbols.append(symbol)
        
        logger.info(f"开始分析 {len(processed_symbols)} 个币种")
        
        # 分析所有币种（包含验证）
        all_results = strategy.analyze_multiple_symbols(processed_symbols)
        
        # 统计结果
        total_signals = 0
        successful_signals = 0
        valid_symbols = len(all_results)
        
        for symbol, results in all_results.items():
            for result in results:
                total_signals += 1
                if result['status'] == 'success':
                    successful_signals += 1
        
        return jsonify({
            'success': True,
            'total_symbols': len(processed_symbols),
            'valid_symbols': valid_symbols,
            'total_signals': total_signals,
            'successful_signals': successful_signals,
            'results': all_results
        })
        
    except Exception as e:
        logger.error(f"分析多个币种失败: {e}")
        return jsonify({'error': str(e)}), 500

@multi_timeframe_bp.route('/get_top_symbols', methods=['GET'])
def get_top_symbols():
    """获取前100个币种"""
    try:
        import requests
        
        # 使用重试机制获取币安期货前100个币种
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        for attempt in range(3):
            try:
                response = session.get('https://fapi.binance.com/fapi/v1/ticker/24hr', timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    
                    # 按交易量排序
                    sorted_data = sorted(data, key=lambda x: float(x['volume']), reverse=True)
                    
                    # 过滤稳定币
                    stablecoins = {'USDT', 'USDC', 'BUSD', 'TUSD', 'USDP', 'DAI', 'FRAX', 'LUSD', 'SUSD', 'GUSD', 'HUSD', 'USDN', 'USDK', 'USDJ', 'USDS'}
                    
                    filtered_symbols = []
                    for item in sorted_data[:200]:  # 取前200个，然后过滤
                        symbol = item['symbol']
                        if symbol.endswith('USDT') and not any(coin in symbol for coin in stablecoins):
                            filtered_symbols.append(symbol)
                            if len(filtered_symbols) >= 100:  # 取前100个
                                break
                    
                    return jsonify({
                        'success': True,
                        'symbols': filtered_symbols,
                        'count': len(filtered_symbols)
                    })
                else:
                    logger.warning(f"获取币种失败: {response.status_code}, 重试 {attempt + 1}/3")
                    if attempt < 2:
                        import time
                        time.sleep(1)
                    continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"网络请求异常: {e}, 重试 {attempt + 1}/3")
                if attempt < 2:
                    import time
                    time.sleep(2)
                continue
        
        # 如果网络请求失败，返回默认币种列表
        default_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT',
            'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'ATOMUSDT', 'ETCUSDT', 'XLMUSDT', 'BCHUSDT', 'FILUSDT', 'TRXUSDT',
            'APTUSDT', 'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FTMUSDT', 'HBARUSDT', 'MANAUSDT', 'SANDUSDT', 'AXSUSDT',
            'THETAUSDT', 'EGLDUSDT', 'FLOWUSDT', 'XTZUSDT', 'EOSUSDT', 'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'YFIUSDT', 'SNXUSDT',
            'CRVUSDT', '1INCHUSDT', 'SUSHIUSDT', 'ALPHAUSDT', 'ZENUSDT', 'SKLUSDT', 'GRTUSDT', 'BATUSDT', 'ZECUSDT', 'DASHUSDT'
        ]
        
        return jsonify({
            'success': True,
            'symbols': default_symbols,
            'count': len(default_symbols),
            'note': '使用默认币种列表（网络请求失败）'
        })
            
    except Exception as e:
        logger.error(f"获取币种失败: {e}")
        return jsonify({'error': str(e)}), 500

@multi_timeframe_bp.route('/get_strategy_info', methods=['GET'])
def get_strategy_info():
    """获取策略信息"""
    return jsonify({
        'success': True,
        'strategy_name': '多时间框架趋势跟踪策略',
        'timeframes': strategy.timeframes,
        'ema_periods': strategy.ema_periods,
        'take_profit_mapping': strategy.take_profit_timeframes,
        'description': {
            'trend_detection': 'EMA144/233多头排列判断趋势',
            'entry_condition': '价格回踩EMA144/233/377/610',
            'take_profit': '使用对应时间框架的布林中轨',
            'ema_usage_limit': '每个EMA级别只用一次'
        }
    })

@multi_timeframe_bp.route('/validate_symbol', methods=['POST'])
def validate_symbol():
    """验证币种是否存在"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'error': '请提供币种'}), 400
        
        # 确保币种以USDT结尾
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        # 验证币种
        is_valid = strategy.validate_symbol(symbol)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'is_valid': is_valid,
            'message': f'{symbol} {"存在" if is_valid else "不存在"}'
        })
        
    except Exception as e:
        logger.error(f"验证币种失败: {e}")
        return jsonify({'error': str(e)}), 500

@multi_timeframe_bp.route('/clear_ema_usage', methods=['POST'])
def clear_ema_usage():
    """清除EMA使用记录"""
    try:
        strategy.ema_usage = {}
        return jsonify({
            'success': True,
            'message': 'EMA使用记录已清除'
        })
    except Exception as e:
        logger.error(f"清除EMA使用记录失败: {e}")
        return jsonify({'error': str(e)}), 500
