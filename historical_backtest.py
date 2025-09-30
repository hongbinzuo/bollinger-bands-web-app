#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史回测脚本
测试最近3个月的20个币种数据，验证信号逻辑的准确性
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time
from typing import List, Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoricalBacktest:
    def __init__(self):
        self.strategy = MultiTimeframeStrategy()
        
        # 测试币种列表
        self.test_symbols = [
            'ENAUSDT', 'SOLUSDT', 'ETCUSDT', 'ETHUSDT', 'BTCUSDT',
            'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOTUSDT', 'DOGEUSDT',
            'AVAXUSDT', 'SHIBUSDT', 'MATICUSDT', 'LTCUSDT', 'UNIUSDT',
            'LINKUSDT', 'ATOMUSDT', 'XLMUSDT', 'BCHUSDT', 'FILUSDT'
        ]
        
        # 回测结果
        self.backtest_results = {}
        
    def get_historical_data(self, symbol: str, timeframe: str, days: int = 90) -> pd.DataFrame:
        """获取历史数据"""
        try:
            # 计算需要的数据量 (90天)
            if timeframe == '4h':
                limit = days * 6  # 每天6根4小时K线
            elif timeframe == '8h':
                limit = days * 3  # 每天3根8小时K线
            elif timeframe == '12h':
                limit = days * 2  # 每天2根12小时K线
            elif timeframe == '1d':
                limit = days      # 每天1根日K线
            elif timeframe == '3d':
                limit = days // 3  # 每3天1根K线
            elif timeframe == '1w':
                limit = days // 7  # 每周1根K线
            else:
                limit = 1000
            
            logger.info(f"获取 {symbol} {timeframe} 历史数据，预计 {limit} 根K线")
            df = self.strategy.get_klines_data(symbol, timeframe, limit)
            
            if df.empty:
                logger.warning(f"未获取到 {symbol} {timeframe} 数据")
                return pd.DataFrame()
            
            # 过滤最近3个月的数据
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df.index >= cutoff_date]
            
            logger.info(f"获取到 {symbol} {timeframe} 数据: {len(df)} 根K线")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} {timeframe} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def analyze_symbol_signals(self, symbol: str) -> Dict[str, Any]:
        """分析单个币种的所有时间框架信号"""
        logger.info(f"开始分析 {symbol} 的历史信号...")
        
        symbol_results = {
            'symbol': symbol,
            'timeframes': {},
            'total_signals': 0,
            'successful_timeframes': 0,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        for timeframe in self.strategy.timeframes:
            try:
                logger.info(f"分析 {symbol} {timeframe} 时间框架...")
                
                # 获取历史数据
                df = self.get_historical_data(symbol, timeframe, 90)
                if df.empty:
                    symbol_results['timeframes'][timeframe] = {
                        'status': 'error',
                        'message': '无历史数据',
                        'signals': []
                    }
                    continue
                
                # 计算技术指标
                df = self.strategy.calculate_emas(df)
                df = self.strategy.calculate_bollinger_bands(df)
                df.dropna(inplace=True)
                
                if df.empty:
                    symbol_results['timeframes'][timeframe] = {
                        'status': 'error',
                        'message': '计算指标后数据为空',
                        'signals': []
                    }
                    continue
                
                # 判断趋势
                is_bullish = self.strategy.is_bullish_trend(df)
                is_bearish = self.strategy.is_bearish_trend(df)
                trend = 'bullish' if is_bullish else 'bearish' if is_bearish else 'neutral'
                
                # 寻找信号
                pullback_signals = self.strategy.find_ema_pullback_levels(df, trend)
                crossover_signals = self.strategy.find_ema_crossover_signals(df)
                breakout_signals = self.strategy.find_price_breakout_signals(df)
                support_resistance_signals = self.strategy.find_support_resistance_signals(df)
                
                # 合并所有信号
                all_signals = []
                all_signals.extend(pullback_signals)
                all_signals.extend(crossover_signals)
                all_signals.extend(breakout_signals)
                all_signals.extend(support_resistance_signals)
                
                # 计算止盈
                take_profit_timeframe = self.strategy.take_profit_timeframes.get(timeframe, '15m')
                take_profit_price = None
                
                try:
                    tp_df = self.strategy.get_klines_data(symbol, take_profit_timeframe, 200)
                    if not tp_df.empty:
                        tp_df = self.strategy.calculate_bollinger_bands(tp_df)
                        tp_df.dropna(inplace=True)
                        if not tp_df.empty:
                            take_profit_price = tp_df['bb_middle'].iloc[-1]
                except Exception as e:
                    logger.warning(f"计算 {symbol} {timeframe} 止盈价格失败: {e}")
                
                # 为每个信号计算收益率
                for signal in all_signals:
                    entry_price = signal.get('entry_price', 0)
                    if entry_price > 0 and take_profit_price and take_profit_price > 0:
                        if signal.get('signal') == 'long':
                            profit_pct = ((take_profit_price - entry_price) / entry_price) * 100
                        else:
                            profit_pct = ((entry_price - take_profit_price) / entry_price) * 100
                        signal['profit_pct'] = round(profit_pct, 2)
                        signal['take_profit_price'] = take_profit_price
                    else:
                        signal['profit_pct'] = 0
                        signal['take_profit_price'] = 0
                
                symbol_results['timeframes'][timeframe] = {
                    'status': 'success',
                    'trend': trend,
                    'data_points': len(df),
                    'signals': all_signals,
                    'signal_count': len(all_signals),
                    'take_profit_timeframe': take_profit_timeframe,
                    'take_profit_price': take_profit_price,
                    'current_price': df['close'].iloc[-1] if not df.empty else 0
                }
                
                symbol_results['total_signals'] += len(all_signals)
                symbol_results['successful_timeframes'] += 1
                
                logger.info(f"{symbol} {timeframe}: {len(all_signals)} 个信号")
                
            except Exception as e:
                logger.error(f"分析 {symbol} {timeframe} 失败: {e}")
                symbol_results['timeframes'][timeframe] = {
                    'status': 'error',
                    'message': str(e),
                    'signals': []
                }
        
        return symbol_results
    
    def run_backtest(self) -> Dict[str, Any]:
        """运行历史回测"""
        logger.info("=" * 60)
        logger.info("开始历史回测 - 最近3个月数据")
        logger.info("=" * 60)
        
        start_time = time.time()
        total_results = {
            'backtest_info': {
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbols_tested': len(self.test_symbols),
                'timeframes': self.strategy.timeframes,
                'test_period': '90天'
            },
            'symbol_results': {},
            'summary': {}
        }
        
        # 分析每个币种
        for i, symbol in enumerate(self.test_symbols):
            logger.info(f"分析币种 {i+1}/{len(self.test_symbols)}: {symbol}")
            
            try:
                symbol_result = self.analyze_symbol_signals(symbol)
                total_results['symbol_results'][symbol] = symbol_result
                
                # 添加延迟避免API限制
                if i < len(self.test_symbols) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"分析 {symbol} 失败: {e}")
                total_results['symbol_results'][symbol] = {
                    'symbol': symbol,
                    'error': str(e),
                    'timeframes': {},
                    'total_signals': 0,
                    'successful_timeframes': 0
                }
        
        # 计算总结统计
        total_signals = 0
        successful_analyses = 0
        signal_by_timeframe = {}
        signal_by_type = {}
        
        for symbol, result in total_results['symbol_results'].items():
            if 'total_signals' in result:
                total_signals += result['total_signals']
                successful_analyses += result['successful_timeframes']
                
                # 按时间框架统计
                for tf, tf_result in result.get('timeframes', {}).items():
                    if tf_result.get('status') == 'success':
                        signal_count = tf_result.get('signal_count', 0)
                        if tf not in signal_by_timeframe:
                            signal_by_timeframe[tf] = 0
                        signal_by_timeframe[tf] += signal_count
                        
                        # 按信号类型统计
                        for signal in tf_result.get('signals', []):
                            signal_type = signal.get('signal', 'unknown')
                            if signal_type not in signal_by_type:
                                signal_by_type[signal_type] = 0
                            signal_by_type[signal_type] += 1
        
        # 计算平均收益率
        all_profits = []
        for symbol, result in total_results['symbol_results'].items():
            for tf, tf_result in result.get('timeframes', {}).items():
                if tf_result.get('status') == 'success':
                    for signal in tf_result.get('signals', []):
                        profit = signal.get('profit_pct', 0)
                        if profit != 0:
                            all_profits.append(profit)
        
        avg_profit = np.mean(all_profits) if all_profits else 0
        max_profit = np.max(all_profits) if all_profits else 0
        min_profit = np.min(all_profits) if all_profits else 0
        
        total_results['summary'] = {
            'total_symbols': len(self.test_symbols),
            'successful_symbols': len([r for r in total_results['symbol_results'].values() if r.get('total_signals', 0) > 0]),
            'total_signals': total_signals,
            'successful_analyses': successful_analyses,
            'signals_by_timeframe': signal_by_timeframe,
            'signals_by_type': signal_by_type,
            'profit_stats': {
                'avg_profit_pct': round(avg_profit, 2),
                'max_profit_pct': round(max_profit, 2),
                'min_profit_pct': round(min_profit, 2),
                'total_signals_with_profit': len(all_profits)
            },
            'duration_seconds': round(time.time() - start_time, 2)
        }
        
        return total_results
    
    def print_summary(self, results: Dict[str, Any]):
        """打印回测总结"""
        summary = results['summary']
        
        logger.info("=" * 60)
        logger.info("历史回测总结")
        logger.info("=" * 60)
        
        logger.info(f"测试币种数量: {summary['total_symbols']}")
        logger.info(f"成功分析币种: {summary['successful_symbols']}")
        logger.info(f"总信号数量: {summary['total_signals']}")
        logger.info(f"成功分析时间框架: {summary['successful_analyses']}")
        logger.info(f"回测耗时: {summary['duration_seconds']} 秒")
        
        logger.info("\n按时间框架统计:")
        for tf, count in summary['signals_by_timeframe'].items():
            logger.info(f"  {tf}: {count} 个信号")
        
        logger.info("\n按信号类型统计:")
        for signal_type, count in summary['signals_by_type'].items():
            logger.info(f"  {signal_type}: {count} 个信号")
        
        logger.info("\n收益率统计:")
        profit_stats = summary['profit_stats']
        logger.info(f"  平均收益率: {profit_stats['avg_profit_pct']}%")
        logger.info(f"  最大收益率: {profit_stats['max_profit_pct']}%")
        logger.info(f"  最小收益率: {profit_stats['min_profit_pct']}%")
        logger.info(f"  有收益率的信号: {profit_stats['total_signals_with_profit']} 个")
        
        # 显示每个币种的详细结果
        logger.info("\n各币种信号统计:")
        for symbol, result in results['symbol_results'].items():
            if result.get('total_signals', 0) > 0:
                logger.info(f"  {symbol}: {result['total_signals']} 个信号")
                for tf, tf_result in result.get('timeframes', {}).items():
                    if tf_result.get('status') == 'success' and tf_result.get('signal_count', 0) > 0:
                        logger.info(f"    {tf}: {tf_result['signal_count']} 个信号")

def main():
    """主函数"""
    try:
        backtest = HistoricalBacktest()
        results = backtest.run_backtest()
        backtest.print_summary(results)
        
        # 保存结果到文件
        import json
        with open('backtest_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"\n回测结果已保存到 backtest_results.json")
        
    except Exception as e:
        logger.error(f"回测失败: {e}", exc_info=True)

if __name__ == "__main__":
    main()
