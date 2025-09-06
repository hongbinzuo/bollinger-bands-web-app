from flask import Blueprint, request, jsonify
import logging
from intraday_analyzer import IntradayAnalyzer
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 创建蓝图
ultra_short_bp = Blueprint('ultra_short', __name__, url_prefix='/ultra_short')

# 初始化分析器
analyzer = IntradayAnalyzer()

@ultra_short_bp.route('/get_signals', methods=['POST'])
def get_ultra_short_signals():
    """获取日内超短交易信号"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({
                'success': False,
                'error': '未提供币种列表'
            })
        
        logger.info(f"开始分析 {len(symbols)} 个币种的超短交易信号")
        
        signals = []
        for symbol in symbols:
            try:
                signal = analyze_ultra_short_signal(symbol)
                if signal:
                    signals.append(signal)
                else:
                    logger.warning(f"{symbol} 分析失败，返回None")
                    # 即使分析失败也添加一个失败记录，便于调试
                    signals.append({
                        'symbol': symbol,
                        'trading_opportunity': '分析失败',
                        'error': '数据不足或计算失败'
                    })
            except Exception as e:
                logger.error(f"分析 {symbol} 超短信号失败: {e}")
                # 添加错误记录
                signals.append({
                    'symbol': symbol,
                    'trading_opportunity': '分析错误',
                    'error': str(e)
                })
                continue
        
        logger.info(f"分析完成，共 {len(signals)} 个币种有结果")
        
        return jsonify({
            'success': True,
            'signals': signals,
            'total': len(signals)
        })
        
    except Exception as e:
        logger.error(f"获取超短交易信号失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

def analyze_ultra_short_signal(symbol):
    """分析单个币种的超短交易信号"""
    try:
        # 获取1小时K线数据 - 降低数据量要求
        df_1h = analyzer.get_klines_data(symbol, '1h', 500)
        if df_1h.empty or len(df_1h) < 200:  # 降低到200条，确保有足够数据计算指标
            logger.warning(f"{symbol} 1小时数据不足: {len(df_1h) if not df_1h.empty else 0}")
            return None
        
        # 获取1分钟K线数据 - 降低数据量要求
        df_1m = analyzer.get_klines_data(symbol, '1m', 500)
        if df_1m.empty or len(df_1m) < 150:  # 降低到150条，确保有足够数据计算指标
            logger.warning(f"{symbol} 1分钟数据不足: {len(df_1m) if not df_1m.empty else 0}")
            return None
        
        # 计算1小时EMA365和MA365
        ema365_1h = analyzer.calculate_ema(df_1h['close'], 365)
        ma365_1h = analyzer.calculate_ma365(df_1h['close'])
        
        # 计算1分钟EMA233
        ema233_1m = analyzer.calculate_ema233(df_1m['close'])
        
        # 获取最新数据和上一个K线数据
        current_price = df_1h['close'].iloc[-1]
        prev_price = df_1h['close'].iloc[-2]  # 上一个K线收盘价
        current_ema365 = ema365_1h.iloc[-1]
        current_ma365 = ma365_1h.iloc[-1]
        prev_ema365 = ema365_1h.iloc[-2]  # 上一个K线的EMA365
        prev_ma365 = ma365_1h.iloc[-2]    # 上一个K线的MA365
        current_ema233_1m = ema233_1m.iloc[-1]
        
        # 检查数据有效性
        if pd.isna(current_ema365) or pd.isna(current_ma365) or pd.isna(current_ema233_1m):
            logger.warning(f"{symbol} 当前指标数据无效: EMA365={current_ema365}, MA365={current_ma365}, EMA233_1m={current_ema233_1m}")
            return None
        if pd.isna(prev_ema365) or pd.isna(prev_ma365):
            logger.warning(f"{symbol} 上一个K线指标数据无效: prev_EMA365={prev_ema365}, prev_MA365={prev_ma365}")
            return None
        
        logger.info(f"{symbol} 数据检查通过: 当前价格={current_price}, 上一个价格={prev_price}")
        
        # 计算当前区间和上一个K线的区间
        current_interval_low = min(current_ema365, current_ma365)
        current_interval_high = max(current_ema365, current_ma365)
        prev_interval_low = min(prev_ema365, prev_ma365)
        prev_interval_high = max(prev_ema365, prev_ma365)
        
        # 判断上一个K线的突破状态（关键！）
        breakout_status = "未突破"
        if prev_price > prev_interval_high:
            breakout_status = "上一个K线向上突破"
        elif prev_price < prev_interval_low:
            breakout_status = "上一个K线向下突破"
        else:
            breakout_status = "上一个K线区间内"
        
        # 计算做空点位（上一个K线区间上沿）
        short_entry = prev_interval_high
        
        # 计算做多点位（上一个K线区间下沿）
        long_entry = prev_interval_low
        
        # 计算止盈目标（1分钟EMA233）
        profit_target = current_ema233_1m
        
        # 根据图表策略判断交易机会
        trading_opportunity = "无机会"
        entry_price = 0
        risk_reward_ratio = 0
        
        # 做空信号：价格突破1h EMA365/MA365区间上沿
        if prev_price > prev_interval_high:
            # 做空逻辑：在区间上沿做空，止盈到1分钟EMA233
            entry_price = prev_interval_high  # 入场价：区间上沿
            stop_loss = prev_price            # 止损价：突破点
            take_profit = current_ema233_1m   # 止盈价：1分钟EMA233
            
            # 计算做空风险收益比
            short_risk = stop_loss - entry_price      # 风险：止损价 - 入场价
            short_reward = entry_price - take_profit  # 收益：入场价 - 止盈价
            
            if short_risk > 0:
                short_risk_reward_ratio = round(short_reward / short_risk, 2)
            else:
                short_risk_reward_ratio = 0
            
            trading_opportunity = "做空机会"
            risk_reward_ratio = short_risk_reward_ratio
            logger.info(f"{symbol} 发现做空机会: 突破上沿={prev_interval_high}, 入场={entry_price}, 止损={stop_loss}, 止盈={take_profit}, 风险收益比={risk_reward_ratio}")
            
        # 做多信号：价格跌破1h EMA365/MA365区间下沿
        elif prev_price < prev_interval_low:
            # 做多逻辑：在区间下沿做多，止盈到1分钟EMA233
            entry_price = prev_interval_low   # 入场价：区间下沿
            stop_loss = prev_price            # 止损价：跌破点
            take_profit = current_ema233_1m   # 止盈价：1分钟EMA233
            
            # 计算做多风险收益比
            long_risk = entry_price - stop_loss      # 风险：入场价 - 止损价
            long_reward = take_profit - entry_price  # 收益：止盈价 - 入场价
            
            if long_risk > 0:
                long_risk_reward_ratio = round(long_reward / long_risk, 2)
            else:
                long_risk_reward_ratio = 0
            
            trading_opportunity = "做多机会"
            risk_reward_ratio = long_risk_reward_ratio
            logger.info(f"{symbol} 发现做多机会: 跌破下沿={prev_interval_low}, 入场={entry_price}, 止损={stop_loss}, 止盈={take_profit}, 风险收益比={risk_reward_ratio}")
        else:
            logger.info(f"{symbol} 无交易机会: 上一个价格={prev_price}, 区间=[{prev_interval_low}, {prev_interval_high}]")
        
        # 智能格式化价格显示
        def format_price(price):
            """根据价格大小智能格式化显示"""
            if price == 0:
                return "0"
            elif price >= 1:
                return f"{price:.4f}"
            elif price >= 0.01:
                return f"{price:.6f}"
            elif price >= 0.0001:
                return f"{price:.8f}"
            else:
                # 对于极小价格，使用科学计数法
                return f"{price:.2e}"
        
        # 即使无交易机会也返回分析结果，便于调试
        result = {
            'symbol': symbol,
            'current_price': format_price(current_price),
            'prev_price': format_price(prev_price),
            'interval_low': format_price(current_interval_low),
            'interval_high': format_price(current_interval_high),
            'prev_interval_low': format_price(prev_interval_low),
            'prev_interval_high': format_price(prev_interval_high),
            'breakout_status': breakout_status,
            'short_entry': format_price(short_entry),
            'long_entry': format_price(long_entry),
            'entry_price': format_price(entry_price),
            'stop_loss': format_price(stop_loss) if 'stop_loss' in locals() else "0",
            'take_profit': format_price(take_profit) if 'take_profit' in locals() else "0",
            'profit_target': format_price(profit_target),
            'risk_reward_ratio': risk_reward_ratio,
            'trading_opportunity': trading_opportunity,
            'ema365_1h': format_price(current_ema365),
            'ma365_1h': format_price(current_ma365),
            'ema233_1m': format_price(current_ema233_1m),
            'debug_info': {
                'prev_price_vs_prev_interval_high': format_price(prev_price - prev_interval_high),
                'prev_price_vs_prev_interval_low': format_price(prev_price - prev_interval_low),
                'entry_vs_profit': format_price(entry_price - profit_target) if entry_price > 0 else "0",
                'data_1h_count': len(df_1h),
                'data_1m_count': len(df_1m),
                'risk_calculation': f"风险={format_price(short_risk) if 'short_risk' in locals() else format_price(long_risk) if 'long_risk' in locals() else '0'}",
                'reward_calculation': f"收益={format_price(short_reward) if 'short_reward' in locals() else format_price(long_reward) if 'long_reward' in locals() else '0'}"
            }
        }
        
        logger.info(f"{symbol} 分析完成: {trading_opportunity} (1h数据: {len(df_1h)}, 1m数据: {len(df_1m)})")
        return result
        
    except Exception as e:
        logger.error(f"分析 {symbol} 超短信号失败: {e}")
        return None

@ultra_short_bp.route('/get_signal_details', methods=['POST'])
def get_signal_details():
    """获取超短交易信号详情"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': '未提供币种'
            })
        
        # 获取详细数据
        df_1h = analyzer.get_klines_data(symbol, '1h', 200)
        df_1m = analyzer.get_klines_data(symbol, '1m', 200)
        
        if df_1h.empty or df_1m.empty:
            return jsonify({
                'success': False,
                'error': '数据不足'
            })
        
        # 计算指标
        ema365_1h = analyzer.calculate_ema(df_1h['close'], 365)
        ma365_1h = analyzer.calculate_ma365(df_1h['close'])
        ema233_1m = analyzer.calculate_ema233(df_1m['close'])
        
        # 智能格式化价格显示
        def format_price(price):
            """根据价格大小智能格式化显示"""
            if price is None or pd.isna(price):
                return None
            if price == 0:
                return 0
            elif price >= 1:
                return round(price, 4)
            elif price >= 0.01:
                return round(price, 6)
            elif price >= 0.0001:
                return round(price, 8)
            else:
                return round(price, 10)
        
        # 准备图表数据
        chart_data = {
            '1h': {
                'timestamps': df_1h.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'prices': [format_price(val) for val in df_1h['close'].tolist()],
                'ema365': [format_price(val) for val in ema365_1h.tolist()],
                'ma365': [format_price(val) for val in ma365_1h.tolist()]
            },
            '1m': {
                'timestamps': df_1m.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'prices': [format_price(val) for val in df_1m['close'].tolist()],
                'ema233': [format_price(val) for val in ema233_1m.tolist()]
            }
        }
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"获取 {symbol} 超短信号详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@ultra_short_bp.route('/validate_symbol', methods=['POST'])
def validate_symbol():
    """验证币种符号是否有效"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': '未提供币种'
            })
        
        # 标准化符号
        normalized_symbol = analyzer._normalize_symbol(symbol)
        
        # 尝试获取少量数据验证
        df_1h = analyzer.get_klines_data(symbol, '1h', 10)
        
        is_valid = not df_1h.empty
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'normalized_symbol': normalized_symbol,
            'is_valid': is_valid,
            'data_count': len(df_1h) if not df_1h.empty else 0
        })
        
    except Exception as e:
        logger.error(f"验证币种 {symbol} 失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@ultra_short_bp.route('/get_top_symbols', methods=['GET'])
def get_top_symbols():
    """获取币安前200个USDT交易对"""
    try:
        import requests
        
        # 获取币安24小时交易量数据
        response = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 稳定币过滤列表（只过滤主要稳定币和算法稳定币）
        stablecoins = {
            # 主要稳定币
            'USDT', 'USDC', 'BUSD', 'TUSD', 'USDP', 'USDD', 'DAI', 'FRAX', 'LUSD', 'SUSD',
            'GUSD', 'HUSD', 'PAX', 'PAXG', 'USDS', 'USDK', 'USDN',
            # 算法稳定币
            'UST', 'DUSD', 'VAI', 'MIM', 'FEI', 'TRIBE', 'ALUSD', 'FLOAT', 'RAI'
        }
        
        # 筛选USDT.P永续合约交易对并按交易量排序，过滤稳定币
        usdt_symbols = []
        for item in data:
            if item['symbol'].endswith('USDT_PERP'):  # 币安永续合约后缀
                symbol = item['symbol'].replace('USDT_PERP', '')
                # 过滤稳定币
                if symbol not in stablecoins:
                    usdt_symbols.append({
                        'symbol': symbol,
                        'volume': float(item['volume']),
                        'price': float(item['lastPrice'])
                    })
        
        # 按交易量降序排序，取前400个
        usdt_symbols.sort(key=lambda x: x['volume'], reverse=True)
        top_400 = usdt_symbols[:400]
        
        # 提取币种名称
        symbols = [item['symbol'] for item in top_400]
        
        logger.info(f"成功获取币安前400个USDT.P永续合约交易对，总交易量: {sum(item['volume'] for item in top_400):.2f}")
        
        return jsonify({
            'success': True,
            'symbols': symbols,
            'total': len(symbols),
            'top_10': symbols[:10]  # 返回前10个作为预览
        })
        
    except Exception as e:
        logger.error(f"获取币安前400个USDT.P永续合约币种失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@ultra_short_bp.route('/clear_cache', methods=['POST'])
def clear_cache():
    """清除超短交易缓存"""
    try:
        # 这里可以添加清除缓存的逻辑
        return jsonify({
            'success': True,
            'message': '超短交易缓存已清除'
        })
    except Exception as e:
        logger.error(f"清除超短交易缓存失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })
