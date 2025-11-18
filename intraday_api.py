from flask import Blueprint, request, jsonify
import logging
from intraday_analyzer import intraday_analyzer
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

# 创建日内交易蓝图
intraday_bp = Blueprint('intraday', __name__, url_prefix='/intraday')

@intraday_bp.route('/health', methods=['GET'])
def health():
    """日内交易模块健康检查"""
    return jsonify({
        'status': 'healthy',
        'module': 'intraday_trading',
        'timestamp': datetime.now().isoformat(),
        'supported_timeframes': intraday_analyzer.timeframes,
        'priority_timeframes': intraday_analyzer.priority_timeframes
    })

@intraday_bp.route('/analyze_symbol', methods=['POST'])
def analyze_symbol():
    """分析单个币种的所有时间周期"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        force_refresh = data.get('force_refresh', False)
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': '请提供币种符号'
            }), 400
        
        # 确保币种以USDT结尾
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        logger.info(f"开始分析币种: {symbol}")
        
        # 分析所有时间周期
        result = intraday_analyzer.analyze_symbol_all_timeframes(symbol, force_refresh)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"分析币种失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intraday_bp.route('/analyze_timeframe', methods=['POST'])
def analyze_timeframe():
    """分析单个币种在特定时间周期的信号"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        timeframe = data.get('timeframe', '').strip().lower()
        force_refresh = data.get('force_refresh', False)
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': '请提供币种符号'
            }), 400
        
        if not timeframe:
            return jsonify({
                'success': False,
                'error': '请提供时间周期'
            }), 400
        
        if timeframe not in intraday_analyzer.timeframes:
            return jsonify({
                'success': False,
                'error': f'不支持的时间周期: {timeframe}。支持的时间周期: {intraday_analyzer.timeframes}'
            }), 400
        
        # 确保币种以USDT结尾
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        logger.info(f"开始分析币种: {symbol} 时间周期: {timeframe}")
        
        # 分析特定时间周期
        result = intraday_analyzer.analyze_symbol_timeframe(symbol, timeframe, force_refresh)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"分析币种时间周期失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intraday_bp.route('/analyze_multiple', methods=['POST'])
def analyze_multiple():
    """批量分析多个币种"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        timeframes = data.get('timeframes', intraday_analyzer.priority_timeframes)
        force_refresh = data.get('force_refresh', False)
        
        if not symbols:
            return jsonify({
                'success': False,
                'error': '请提供币种列表'
            }), 400
        
        # 验证时间周期
        for tf in timeframes:
            if tf not in intraday_analyzer.timeframes:
                return jsonify({
                    'success': False,
                    'error': f'不支持的时间周期: {tf}。支持的时间周期: {intraday_analyzer.timeframes}'
                }), 400
        
        results = []
        
        for i, symbol in enumerate(symbols):
            try:
                symbol = symbol.strip().upper()
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
                
                logger.info(f"处理 {symbol} ({i+1}/{len(symbols)})")
                
                # 分析指定时间周期
                symbol_results = {}
                for timeframe in timeframes:
                    result = intraday_analyzer.analyze_symbol_timeframe(symbol, timeframe, force_refresh)
                    symbol_results[timeframe] = result
                
                results.append({
                    'symbol': symbol,
                    'timeframes': symbol_results,
                    'analysis_date': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"处理 {symbol} 时出错: {e}")
                continue
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'timeframes_analyzed': timeframes
        })
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intraday_bp.route('/get_signals', methods=['POST'])
def get_signals():
    """获取信号汇总（优先显示15m和1h信号）"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        force_refresh = data.get('force_refresh', False)
        
        if not symbols:
            return jsonify({
                'success': False,
                'error': '请提供币种列表'
            }), 400
        
        signals = []
        
        for i, symbol in enumerate(symbols):
            try:
                symbol = symbol.strip().upper()
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
                
                logger.info(f"获取信号 {symbol} ({i+1}/{len(symbols)})")
                
                # 只分析优先时间周期
                priority_results = {}
                for timeframe in intraday_analyzer.priority_timeframes:
                    result = intraday_analyzer.analyze_symbol_timeframe(symbol, timeframe, force_refresh)
                    priority_results[timeframe] = result
                
                # 计算综合信号
                signal_types = []
                for tf in intraday_analyzer.priority_timeframes:
                    if tf in priority_results and priority_results[tf]['status'] == '✓ 成功':
                        signal_types.append(priority_results[tf]['signal_type'])
                
                # 综合信号逻辑
                if len(signal_types) >= 2:
                    if signal_types[0] == signal_types[1]:
                        overall_signal = signal_types[0]
                        signal_consistency = '一致'
                    else:
                        overall_signal = 'mixed'
                        signal_consistency = '不一致'
                elif len(signal_types) == 1:
                    overall_signal = signal_types[0]
                    signal_consistency = '单一'
                else:
                    overall_signal = 'unknown'
                    signal_consistency = '无信号'
                
                signals.append({
                    'symbol': symbol,
                    'overall_signal': overall_signal,
                    'signal_consistency': signal_consistency,
                    'priority_signals': priority_results,
                    'analysis_date': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"获取 {symbol} 信号时出错: {e}")
                continue
        
        return jsonify({
            'success': True,
            'signals': signals,
            'total': len(signals),
            'priority_timeframes': intraday_analyzer.priority_timeframes
        })
        
    except Exception as e:
        logger.error(f"获取信号失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intraday_bp.route('/clear_cache', methods=['POST'])
def clear_cache():
    """清除日内交易缓存"""
    try:
        intraday_analyzer.clear_cache()
        return jsonify({
            'success': True,
            'message': '日内交易缓存已清除'
        })
        
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intraday_bp.route('/get_timeframes', methods=['GET'])
def get_timeframes():
    """获取支持的时间周期列表"""
    return jsonify({
        'success': True,
        'timeframes': intraday_analyzer.timeframes,
        'priority_timeframes': intraday_analyzer.priority_timeframes
    })

@intraday_bp.route('/get_symbol_signals', methods=['POST'])
def get_symbol_signals():
    """获取单个币种的所有时间周期信号（用于详细分析）"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        force_refresh = data.get('force_refresh', False)
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': '请提供币种符号'
            }), 400
        
        # 确保币种以USDT结尾
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        logger.info(f"获取 {symbol} 所有时间周期信号")
        
        # 分析所有时间周期
        result = intraday_analyzer.analyze_symbol_all_timeframes(symbol, force_refresh)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"获取币种信号失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intraday_bp.route('/get_chart_data', methods=['POST'])
def get_chart_data():
    """获取图表数据（多时间周期EMA）"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        base_timeframe = data.get('base_timeframe', '5m')
        limit = data.get('limit', 200)
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': '请提供币种符号'
            }), 400
        
        # 确保币种以USDT结尾
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        # 验证基础时间周期
        if base_timeframe not in intraday_analyzer.timeframes:
            return jsonify({
                'success': False,
                'error': f'不支持的基础时间周期: {base_timeframe}'
            }), 400
        
        logger.info(f"获取 {symbol} 图表数据，基础时间周期: {base_timeframe}")
        
        # 获取图表数据
        result = intraday_analyzer.get_chart_data(symbol, base_timeframe, limit)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取图表数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
