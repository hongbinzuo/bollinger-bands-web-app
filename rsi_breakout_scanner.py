#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSI日线突破币种扫描系统
扫描前500个币种，寻找满足RSI突破条件的币种
"""

import logging
import requests
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from typing import List, Dict, Tuple, Optional
# import talib  # 使用pandas内置函数替代

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
rsi_breakout_bp = Blueprint('rsi_breakout', __name__, url_prefix='/rsi-breakout')

class RSIBreakoutScanner:
    """RSI日线突破币种扫描器"""
    
    def __init__(self):
        self.supported_symbols = []
        self.rsi_period = 14  # RSI周期
        self.ma_period = 20   # 均线周期
        
    def get_bybit_klines(self, symbol, interval, limit):
        """从Bybit获取K线数据"""
        try:
            interval_map = {
                '1d': 'D'
            }
            bybit_interval = interval_map.get(interval, 'D')
            
            url = f"https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'spot',
                'symbol': symbol,
                'interval': bybit_interval,
                'limit': min(limit, 1000)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') == 0:
                klines = data['result']['list']
                return self.convert_bybit_data(klines)
            else:
                logger.error(f"Bybit API错误: {data.get('retMsg', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Bybit获取 {symbol} K线数据失败: {e}")
            return None
    
    def get_gate_klines(self, symbol, interval, limit):
        """从Gate.io获取K线数据"""
        try:
            interval_map = {
                '1d': '1d'
            }
            gate_interval = interval_map.get(interval, '1d')
            
            # 格式化币种符号：BTCUSDT -> BTC_USDT
            formatted_symbol = symbol
            if symbol.endswith('USDT') and not '_' in symbol:
                formatted_symbol = symbol[:-4] + '_USDT'
            elif symbol.endswith('USDT') and '_' in symbol:
                # 已经是正确格式，直接使用
                formatted_symbol = symbol
            
            url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': formatted_symbol,
                'interval': gate_interval,
                'limit': min(limit, 1000)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            if klines:
                return self.convert_gate_data(klines)
            return None
                
        except Exception as e:
            logger.error(f"Gate.io获取 {symbol} K线数据失败: {e}")
            return None
    
    def convert_bybit_data(self, klines):
        """转换Bybit数据格式"""
        if not klines or not isinstance(klines, list):
            logger.error("Bybit数据格式错误: klines为空或非列表")
            return None
            
        converted_data = []
        for kline in klines:
            if not kline or len(kline) < 6:
                continue
            try:
                converted_data.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            except (ValueError, IndexError) as e:
                logger.error(f"Bybit数据转换错误: {e}")
                continue
        
        return converted_data if converted_data else None
    
    def convert_gate_data(self, klines):
        """转换Gate.io数据格式"""
        if not klines or not isinstance(klines, list):
            logger.error("Gate.io数据格式错误: klines为空或非列表")
            return None
            
        converted_data = []
        for kline in klines:
            if not kline or len(kline) < 6:
                continue
            try:
                converted_data.append({
                    'timestamp': int(kline[0]) * 1000,  # Gate.io返回秒级时间戳，转为毫秒
                    'open': float(kline[5]),
                    'high': float(kline[3]),
                    'low': float(kline[4]),
                    'close': float(kline[2]),
                    'volume': float(kline[1])
                })
            except (ValueError, IndexError) as e:
                logger.error(f"Gate.io数据转换错误: {e}")
                continue
        
        return converted_data if converted_data else None
    
    def calculate_rsi(self, prices, period=14):
        """计算RSI指标 - 使用指数移动平均"""
        try:
            prices = pd.Series(prices)
            delta = prices.diff()
            
            # 使用指数移动平均（EMA）而不是简单移动平均
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.values
        except Exception as e:
            logger.error(f"RSI计算失败: {e}")
            return None
    
    def calculate_ma(self, prices, period=20):
        """计算移动平均线"""
        try:
            prices = pd.Series(prices)
            ma_values = prices.rolling(window=period).mean()
            return ma_values.values
        except Exception as e:
            logger.error(f"MA计算失败: {e}")
            return None
    
    def check_rsi_oversold_duration(self, rsi_values, threshold=30, min_days=1):
        """检查RSI超卖持续时间"""
        if rsi_values is None or len(rsi_values) < min_days:
            return False, 0
        
        # 找到最近一次RSI低于阈值的开始位置
        oversold_start = None
        for i in range(len(rsi_values) - 1, -1, -1):
            if not np.isnan(rsi_values[i]) and rsi_values[i] < threshold:
                if oversold_start is None:
                    oversold_start = i
            elif oversold_start is not None:
                break
        
        if oversold_start is None:
            return False, 0
        
        # 计算超卖持续天数
        oversold_days = len(rsi_values) - 1 - oversold_start
        return oversold_days >= min_days, oversold_days
    
    def check_rsi_hl(self, rsi_values, lookback=10):
        """检查RSI是否产生HL（Higher Low）"""
        if rsi_values is None or len(rsi_values) < lookback:
            return False
        
        # 获取最近的数据
        recent_rsi = rsi_values[-lookback:]
        recent_rsi = recent_rsi[~np.isnan(recent_rsi)]
        
        if len(recent_rsi) < 6:
            return False
        
        # 找到最近的两个低点
        lows = []
        for i in range(1, len(recent_rsi) - 1):
            if (recent_rsi[i] < recent_rsi[i-1] and 
                recent_rsi[i] < recent_rsi[i+1]):
                lows.append((i, recent_rsi[i]))
        
        # 如果有至少两个低点，检查是否形成HL
        if len(lows) >= 2:
            # 取最近的两个低点
            last_two_lows = lows[-2:]
            return last_two_lows[1][1] > last_two_lows[0][1]  # 第二个低点高于第一个
        
        return False
    
    def check_rsi_ma_crossover(self, rsi_values, ma_values):
        """检查RSI上穿均线且均线拐头向上"""
        if (rsi_values is None or ma_values is None or 
            len(rsi_values) < 5 or len(ma_values) < 5):
            return False
        
        # 检查最近5天内是否有RSI上穿均线
        rsi_cross_up = False
        for i in range(max(1, len(rsi_values) - 5), len(rsi_values)):
            if (not np.isnan(rsi_values[i]) and not np.isnan(rsi_values[i-1]) and
                not np.isnan(ma_values[i]) and not np.isnan(ma_values[i-1])):
                if (rsi_values[i-1] <= ma_values[i-1] and 
                    rsi_values[i] > ma_values[i]):
                    rsi_cross_up = True
                    break
        
        if not rsi_cross_up:
            return False
        
        # 检查均线趋势（更宽松的条件）
        recent_ma = ma_values[-5:]
        recent_ma = recent_ma[~np.isnan(recent_ma)]
        
        if len(recent_ma) < 3:
            return False
        
        # 均线整体呈上升趋势（不要求连续上升）
        return recent_ma[-1] > recent_ma[0]
    
    def analyze_symbol_rsi_breakout(self, symbol):
        """分析单个币种的RSI突破条件"""
        try:
            logger.info(f"分析 {symbol} 的RSI突破条件...")
            
            # 获取日线数据 - 优先使用Gate.io
            limit = 50  # 获取50天数据
            price_data = self.get_gate_klines(symbol, '1d', limit)
            
            if not price_data:
                # 备用：尝试Bybit
                price_data = self.get_bybit_klines(symbol, '1d', limit)
            
            if not price_data or len(price_data) < 30:
                logger.warning(f"{symbol} 数据不足，跳过")
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(price_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp')
            
            # 计算RSI和MA
            close_prices = df['close'].values
            rsi_values = self.calculate_rsi(close_prices, self.rsi_period)
            ma_values = self.calculate_ma(close_prices, self.ma_period)
            
            if rsi_values is None or ma_values is None:
                logger.warning(f"{symbol} RSI/MA计算失败，跳过")
                return None
            
            # 获取当前RSI值
            current_rsi = rsi_values[-1]
            if np.isnan(current_rsi):
                logger.warning(f"{symbol} 当前RSI值无效，跳过")
                return None
            
            # 计算RSI均值（最近7天）
            recent_rsi = rsi_values[-7:] if len(rsi_values) >= 7 else rsi_values
            recent_rsi_clean = recent_rsi[~np.isnan(recent_rsi)]
            rsi_mean = np.mean(recent_rsi_clean) if len(recent_rsi_clean) > 0 else current_rsi
            
            # 检查条件1：RSI超卖>=1天
            oversold_condition, oversold_days = self.check_rsi_oversold_duration(
                rsi_values, threshold=30, min_days=1
            )
            
            # 检查条件2：RSI产生了HL
            hl_condition = self.check_rsi_hl(rsi_values, lookback=10)
            
            # 检查条件3：RSI上穿均线 & 均线拐头向上
            crossover_condition = self.check_rsi_ma_crossover(rsi_values, ma_values)
            
            # 检查条件4：RSI值低于50
            rsi_below_50 = current_rsi < 50
            
            # 检查一周内是否超卖
            weekly_oversold = False
            if len(rsi_values) >= 7:
                weekly_rsi = rsi_values[-7:]
                weekly_oversold = np.any(weekly_rsi < 30)
            
            # 打印详细信息
            logger.info(f"{symbol} 详细信息:")
            logger.info(f"  当前RSI: {current_rsi:.2f}")
            logger.info(f"  RSI均值(7天): {rsi_mean:.2f}")
            logger.info(f"  一周内超卖: {'是' if weekly_oversold else '否'}")
            logger.info(f"  超卖持续天数: {oversold_days}")
            logger.info(f"  有HL模式: {'是' if hl_condition else '否'}")
            logger.info(f"  RSI上穿均线: {'是' if crossover_condition else '否'}")
            logger.info(f"  RSI<50: {'是' if rsi_below_50 else '否'}")
            
            # 综合判断
            all_conditions_met = (oversold_condition and hl_condition and 
                                crossover_condition and rsi_below_50)
            
            if all_conditions_met:
                logger.info(f"✓ {symbol} 满足RSI突破条件！")
                return {
                    'symbol': symbol,
                    'current_rsi': round(current_rsi, 2),
                    'rsi_mean_7d': round(rsi_mean, 2),
                    'weekly_oversold': weekly_oversold,
                    'oversold_days': oversold_days,
                    'has_hl': hl_condition,
                    'has_crossover': crossover_condition,
                    'rsi_below_50': rsi_below_50,
                    'current_price': close_prices[-1],
                    'analysis_date': datetime.now().isoformat()
                }
            else:
                logger.info(f"- {symbol} 不满足RSI突破条件")
                return None
                
        except Exception as e:
            logger.error(f"分析 {symbol} RSI突破条件失败: {e}")
            return None
    
    def get_gate_symbols(self, limit=500):
        """从Gate.io获取前N个币种"""
        try:
            logger.info(f"从Gate.io获取前{limit}个币种...")
            
            url = "https://api.gateio.ws/api/v4/spot/currency_pairs"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Gate.io API错误: {response.status_code} - {response.text}")
                return self.get_fallback_symbols(limit)
            
            data = response.json()
            if not data:
                logger.error("Gate.io币种列表为空")
                return self.get_fallback_symbols(limit)
            
            # 过滤USDT交易对
            usdt_pairs = []
            for pair in data:
                if (pair.get('quote') == 'USDT' and 
                    pair.get('trade_status') == 'tradable'):
                    base = pair.get('base', '')
                    if base and base != 'USDT':
                        usdt_pairs.append(f"{base}USDT")
            
            if not usdt_pairs:
                logger.error("未找到USDT交易对")
                return self.get_fallback_symbols(limit)
            
            # 限制数量
            symbols = usdt_pairs[:min(limit, len(usdt_pairs))]
            logger.info(f"获取到{len(symbols)}个USDT交易对")
            return symbols
            
        except Exception as e:
            logger.error(f"获取Gate.io币种列表失败: {e}")
            return self.get_fallback_symbols(limit)
    
    def get_fallback_symbols(self, limit=500):
        """获取备用币种列表"""
        fallback_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'XRPUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT',
            'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'ATOMUSDT',
            'ALGOUSDT', 'VETUSDT', 'FILUSDT', 'TRXUSDT', 'ETCUSDT',
            'XLMUSDT', 'ICPUSDT', 'THETAUSDT', 'EOSUSDT', 'AAVEUSDT',
            'SUSHIUSDT', 'SNXUSDT', 'YFIUSDT', 'COMPUSDT', 'MKRUSDT',
            'CRVUSDT', '1INCHUSDT', 'BALUSDT', 'RENUSDT', 'KNCUSDT',
            'ZRXUSDT', 'BATUSDT', 'ZECUSDT', 'DASHUSDT', 'NEOUSDT',
            'QTUMUSDT', 'OMGUSDT', 'LSKUSDT', 'NANOUSDT', 'ONTUSDT',
            'IOTAUSDT', 'ICXUSDT', 'WAVESUSDT', 'REPUSDT', 'MANAUSDT',
            'SANDUSDT', 'AXSUSDT', 'GALAUSDT', 'ENJUSDT', 'CHZUSDT',
            'FLOWUSDT', 'NEARUSDT', 'FTMUSDT', 'ROSEUSDT', 'HBARUSDT',
            'ONEUSDT', 'ZILUSDT', 'IOSTUSDT', 'BTTUSDT', 'WINUSDT',
            'BCHUSDT', 'BSVUSDT', 'EOSUSDT', 'XMRUSDT', 'DASHUSDT',
            'ZECUSDT', 'DCRUSDT', 'DGBUSDT', 'SCUSDT', 'DGBUSDT',
            'RVNUSDT', 'BEAMUSDT', 'GRINUSDT', 'MWCUSDT', 'AEUSDT',
            'AIONUSDT', 'BLZUSDT', 'BNTUSDT', 'BQXUSDT', 'BRDUSDT',
            'BTSUSDT', 'CDTUSDT', 'CMTUSDT', 'CNDUSDT', 'CTRUSDT',
            'DGDUSDT', 'DLTUSDT', 'DNTUSDT', 'EDGUSDT', 'ENGUSDT',
            'ENJUSDT', 'EOSUSDT', 'ETCUSDT', 'ETHUSDT', 'EVXUSDT',
            'FCTUSDT', 'FUNUSDT', 'GASUSDT', 'GNTUSDT', 'GRSUSDT',
            'GTOUSDT', 'GVTUSDT', 'GXSUSDT', 'HSRUSDT', 'ICNUSDT',
            'ICXUSDT', 'INSUSDT', 'IOSTUSDT', 'IOTAUSDT', 'KMDUSDT',
            'KNCUSDT', 'LENDUSDT', 'LINKUSDT', 'LRCUSDT', 'LSKUSDT',
            'LTCUSDT', 'LUNUSDT', 'MANAUSDT', 'MCOUSDT', 'MDAUSDT',
            'MITHUSDT', 'MKRUSDT', 'MLNUSDT', 'MODUSDT', 'MTHUSDT',
            'MTLUSDT', 'NANOUSDT', 'NEBLUSDT', 'NEOUSDT', 'NULSUSDT',
            'OAXUSDT', 'OMGUSDT', 'ONTUSDT', 'OSTUSDT', 'OXTUSDT',
            'PAXUSDT', 'PIVXUSDT', 'POAUSDT', 'POEUSDT', 'POLYUSDT',
            'POWRUSDT', 'PPTUSDT', 'QKCUSDT', 'QLCUSDT', 'QSPUSDT',
            'QTUMUSDT', 'RCNUSDT', 'RDNUSDT', 'REPUSDT', 'REQUSDT',
            'RLCUSDT', 'RPXUSDT', 'SALTUSDT', 'SANUSDT', 'SBDUSDT',
            'SCUSDT', 'SKYUSDT', 'SNGLSUSDT', 'SNMUSDT', 'SNTUSDT',
            'STORJUSDT', 'STRATUSDT', 'SUBUSDT', 'SYSUSDT', 'TNBUSDT',
            'TNTUSDT', 'TRIGUSDT', 'TRXUSDT', 'USDCUSDT', 'USDTUSDT',
            'UTKUSDT', 'VENUSDT', 'VIBUSDT', 'VIBEUSDT', 'WABIUSDT',
            'WANUSDT', 'WAVESUSDT', 'WINGSUSDT', 'WTCUSDT', 'XLMUSDT',
            'XMRUSDT', 'XRPUSDT', 'XVGUSDT', 'XZCUSDT', 'YOYOWUSDT',
            'ZECUSDT', 'ZILUSDT', 'ZRXUSDT'
        ]
        
        logger.info(f"使用备用币种列表，共{len(fallback_symbols)}个币种")
        return fallback_symbols[:min(limit, len(fallback_symbols))]

    def scan_top_symbols(self, limit=500):
        """扫描前500个币种"""
        try:
            logger.info(f"开始扫描前{limit}个币种的RSI突破条件...")
            
            # 从Gate.io获取币种列表
            symbols_to_scan = self.get_gate_symbols(limit)
            
            results = []
            all_symbols_info = []  # 存储所有币种的详细信息
            total_symbols = len(symbols_to_scan)
            logger.info(f"开始扫描{total_symbols}个币种...")
            
            for i, symbol in enumerate(symbols_to_scan):
                try:
                    if i % 10 == 0:  # 每10个币种报告一次进度
                        logger.info(f"扫描进度: {i+1}/{total_symbols} ({((i+1)/total_symbols)*100:.1f}%)")
                    
                    result = self.analyze_symbol_rsi_breakout(symbol)
                    if result:
                        results.append(result)
                        logger.info(f"✓ 找到符合条件的币种: {symbol} (RSI: {result['current_rsi']})")
                    
                    # 收集所有币种的基本信息（即使不满足条件）
                    try:
                        # 获取基本RSI信息
                        limit = 50
                        price_data = self.get_gate_klines(symbol, '1d', limit)
                        if not price_data:
                            price_data = self.get_bybit_klines(symbol, '1d', limit)
                        
                        if price_data and len(price_data) >= 30:
                            df = pd.DataFrame(price_data)
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            df = df.sort_values('timestamp')
                            
                            close_prices = df['close'].values
                            rsi_values = self.calculate_rsi(close_prices, self.rsi_period)
                            
                            if rsi_values is not None:
                                current_rsi = rsi_values[-1]
                                if not np.isnan(current_rsi):
                                    # 计算RSI均值（最近7天）
                                    recent_rsi = rsi_values[-7:] if len(rsi_values) >= 7 else rsi_values
                                    recent_rsi_clean = recent_rsi[~np.isnan(recent_rsi)]
                                    rsi_mean = np.mean(recent_rsi_clean) if len(recent_rsi_clean) > 0 else current_rsi
                                    
                                    # 检查一周内是否超卖
                                    weekly_oversold = False
                                    if len(rsi_values) >= 7:
                                        weekly_rsi = rsi_values[-7:]
                                        weekly_oversold = np.any(weekly_rsi < 30)
                                    
                                    all_symbols_info.append({
                                        'symbol': symbol,
                                        'current_rsi': round(current_rsi, 2),
                                        'rsi_mean_7d': round(rsi_mean, 2),
                                        'weekly_oversold': weekly_oversold,
                                        'current_price': close_prices[-1]
                                    })
                    except Exception as e:
                        logger.debug(f"获取 {symbol} 基本信息失败: {e}")
                    
                    # 添加延迟避免API限制
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"扫描 {symbol} 时出错: {e}")
                    continue
            
            # 打印所有币种的汇总信息
            logger.info(f"\n=== 扫描完成 ===")
            logger.info(f"找到 {len(results)} 个满足条件的币种")
            logger.info(f"成功分析 {len(all_symbols_info)} 个币种")
            
            # 按RSI值排序显示
            all_symbols_info.sort(key=lambda x: x['current_rsi'])
            logger.info(f"\n=== 所有币种RSI信息（按RSI值排序）===")
            for info in all_symbols_info[:20]:  # 显示前20个
                logger.info(f"{info['symbol']}: RSI={info['current_rsi']}, 均值={info['rsi_mean_7d']}, 一周超卖={'是' if info['weekly_oversold'] else '否'}")
            
            if len(all_symbols_info) > 20:
                logger.info(f"... 还有 {len(all_symbols_info) - 20} 个币种")
            
            return results
            
        except Exception as e:
            logger.error(f"扫描币种失败: {e}")
            return []

# 创建扫描器实例
scanner = RSIBreakoutScanner()

@rsi_breakout_bp.route('/api/scan', methods=['POST'])
def scan_rsi_breakout():
    """RSI突破币种扫描API"""
    try:
        data = request.get_json() or {}
        limit = data.get('limit', 500)
        
        logger.info(f"收到RSI突破扫描请求，限制数量: {limit}")
        
        results = scanner.scan_top_symbols(limit)
        
        return jsonify({
            'success': True,
            'results': results,
            'total_found': len(results),
            'scan_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        logger.error(f"RSI突破扫描失败: {e}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
