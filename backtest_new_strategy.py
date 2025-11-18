#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测新策略：使用GATE.IO前50个币种的最近1周历史数据
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_timeframe_strategy import MultiTimeframeStrategy

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StrategyBacktester:
    def __init__(self):
        self.original_strategy = MultiTimeframeStrategy('original')
        self.modified_strategy = MultiTimeframeStrategy('modified')
        
    def get_gate_top_symbols(self, limit=50):
        """获取GATE.IO前50个币种"""
        try:
            import requests
            
            # 获取GATE.IO交易对信息
            url = "https://api.gateio.ws/api/v4/spot/currency_pairs"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                pairs = response.json()
                # 筛选USDT交易对，按24h交易量排序
                usdt_pairs = [pair for pair in pairs if pair['quote'] == 'USDT']
                
                # 获取交易量数据
                ticker_url = "https://api.gateio.ws/api/v4/spot/tickers"
                ticker_response = requests.get(ticker_url, timeout=10)
                
                if ticker_response.status_code == 200:
                    tickers = ticker_response.json()
                    ticker_dict = {t['currency_pair']: t for t in tickers}
                    
                    # 按24h交易量排序
                    usdt_pairs_with_volume = []
                    for pair in usdt_pairs:
                        pair_name = pair['id']
                        if pair_name in ticker_dict:
                            volume = float(ticker_dict[pair_name].get('base_volume', 0))
                            usdt_pairs_with_volume.append((pair_name, volume))
                    
                    # 按交易量降序排序，取前50个
                    usdt_pairs_with_volume.sort(key=lambda x: x[1], reverse=True)
                    top_symbols = [pair[0] for pair in usdt_pairs_with_volume[:limit]]
                    
                    logger.info(f"获取到GATE.IO前{len(top_symbols)}个币种")
                    return top_symbols
                else:
                    logger.error(f"获取交易量数据失败: {ticker_response.status_code}")
                    return []
            else:
                logger.error(f"获取交易对数据失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"获取GATE.IO币种失败: {e}")
            return []
    
    def get_historical_data(self, symbol, timeframe='1d', days=7):
        """获取历史数据"""
        try:
            import requests
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # 转换为时间戳
            start_ts = int(start_time.timestamp())
            end_ts = int(end_time.timestamp())
            
            # 获取K线数据
            url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': symbol,
                'interval': timeframe,
                'from': start_ts,
                'to': end_ts
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    # 转换为DataFrame
                    df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    
                    # 转换数据类型
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    df = df.dropna()
                    logger.info(f"获取{symbol} {timeframe}数据: {len(df)}条")
                    return df
                else:
                    logger.warning(f"{symbol} {timeframe}无数据")
                    return pd.DataFrame()
            else:
                logger.error(f"获取{symbol}数据失败: {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取{symbol}历史数据失败: {e}")
            return pd.DataFrame()
    
    def backtest_strategy(self, strategy, symbols, timeframe='1d'):
        """回测单个策略"""
        logger.info(f"开始回测策略: {strategy.strategy_type}")
        logger.info(f"时间框架: {strategy.timeframes}")
        logger.info(f"止盈配置: {strategy.take_profit_timeframes}")
        
        results = []
        total_signals = 0
        
        for i, symbol in enumerate(symbols):
            logger.info(f"分析币种 {i+1}/{len(symbols)}: {symbol}")
            
            try:
                # 获取历史数据
                df = self.get_historical_data(symbol, timeframe, days=7)
                if df.empty or len(df) < 50:
                    logger.warning(f"{symbol}数据不足，跳过")
                    continue
                
                # 分析每个时间框架
                for tf in strategy.timeframes:
                    try:
                        # 获取对应时间框架的数据
                        tf_df = self.get_historical_data(symbol, tf, days=7)
                        if tf_df.empty or len(tf_df) < 20:
                            continue
                        
                        # 计算技术指标
                        tf_df = strategy.calculate_emas(tf_df, tf)
                        tf_df = strategy.calculate_bollinger_bands(tf_df)
                        tf_df = tf_df.dropna()
                        
                        if tf_df.empty:
                            continue
                        
                        # 判断趋势
                        if strategy.is_bullish_trend(tf_df):
                            trend = 'bullish'
                        elif strategy.is_bearish_trend(tf_df):
                            trend = 'bearish'
                        else:
                            continue
                        
                        # 寻找信号
                        signals = strategy.find_ema_pullback_levels(tf_df, trend, tf, symbol)
                        
                        if signals:
                            for signal in signals:
                                # 计算止盈
                                take_profit_tf = strategy.take_profit_timeframes.get(tf, '15m')
                                tp_df = self.get_historical_data(symbol, take_profit_tf, days=7)
                                
                                if not tp_df.empty:
                                    tp_df = strategy.calculate_bollinger_bands(tp_df)
                                    tp_df = tp_df.dropna()
                                    
                                    if not tp_df.empty:
                                        bb_middle = tp_df['bb_middle'].iloc[-1]
                                        entry_price = signal['entry_price']
                                        
                                        # 计算收益率
                                        if signal['signal'] == 'long':
                                            profit_pct = (bb_middle - entry_price) / entry_price * 100
                                        else:
                                            profit_pct = (entry_price - bb_middle) / entry_price * 100
                                        
                                        results.append({
                                            'symbol': symbol,
                                            'timeframe': tf,
                                            'strategy': strategy.strategy_type,
                                            'signal_type': signal['signal'],
                                            'ema_period': signal['ema_period'],
                                            'entry_price': entry_price,
                                            'take_profit_price': bb_middle,
                                            'profit_pct': profit_pct,
                                            'signal_time': signal['signal_time'],
                                            'condition': signal['condition']
                                        })
                                        
                                        total_signals += 1
                        
                        # 添加延迟避免API限制
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"分析{symbol} {tf}失败: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"分析{symbol}失败: {e}")
                continue
        
        logger.info(f"策略{strategy.strategy_type}回测完成，共生成{total_signals}个信号")
        return results
    
    def run_backtest(self):
        """运行完整回测"""
        logger.info("=" * 60)
        logger.info("开始回测新策略")
        logger.info("=" * 60)
        
        # 获取前50个币种
        logger.info("获取GATE.IO前50个币种...")
        symbols = self.get_gate_top_symbols(50)
        
        if not symbols:
            logger.error("无法获取币种列表")
            return
        
        logger.info(f"获取到{len(symbols)}个币种: {symbols[:10]}...")
        
        # 回测原策略
        logger.info("\n" + "=" * 40)
        logger.info("回测原策略")
        logger.info("=" * 40)
        original_results = self.backtest_strategy(self.original_strategy, symbols[:20])  # 先用20个币种测试
        
        # 回测修改策略
        logger.info("\n" + "=" * 40)
        logger.info("回测修改策略")
        logger.info("=" * 40)
        modified_results = self.backtest_strategy(self.modified_strategy, symbols[:20])  # 先用20个币种测试
        
        # 分析结果
        self.analyze_results(original_results, modified_results)
    
    def analyze_results(self, original_results, modified_results):
        """分析回测结果"""
        logger.info("\n" + "=" * 60)
        logger.info("回测结果分析")
        logger.info("=" * 60)
        
        # 原策略结果
        logger.info("原策略结果:")
        logger.info(f"  总信号数: {len(original_results)}")
        if original_results:
            original_profits = [r['profit_pct'] for r in original_results]
            logger.info(f"  平均收益率: {np.mean(original_profits):.2f}%")
            logger.info(f"  最大收益率: {np.max(original_profits):.2f}%")
            logger.info(f"  最小收益率: {np.min(original_profits):.2f}%")
            logger.info(f"  正收益信号: {sum(1 for p in original_profits if p > 0)}/{len(original_profits)}")
        
        # 修改策略结果
        logger.info("\n修改策略结果:")
        logger.info(f"  总信号数: {len(modified_results)}")
        if modified_results:
            modified_profits = [r['profit_pct'] for r in modified_results]
            logger.info(f"  平均收益率: {np.mean(modified_profits):.2f}%")
            logger.info(f"  最大收益率: {np.max(modified_profits):.2f}%")
            logger.info(f"  最小收益率: {np.min(modified_profits):.2f}%")
            logger.info(f"  正收益信号: {sum(1 for p in modified_profits if p > 0)}/{len(modified_profits)}")
        
        # 策略对比
        logger.info("\n策略对比:")
        if original_results and modified_results:
            original_avg = np.mean([r['profit_pct'] for r in original_results])
            modified_avg = np.mean([r['profit_pct'] for r in modified_results])
            
            logger.info(f"  原策略平均收益率: {original_avg:.2f}%")
            logger.info(f"  修改策略平均收益率: {modified_avg:.2f}%")
            logger.info(f"  收益率差异: {modified_avg - original_avg:.2f}%")
        
        # 保存详细结果
        self.save_results(original_results, modified_results)
    
    def save_results(self, original_results, modified_results):
        """保存回测结果"""
        try:
            # 保存原策略结果
            if original_results:
                original_df = pd.DataFrame(original_results)
                original_df.to_csv('backtest_original_strategy.csv', index=False, encoding='utf-8-sig')
                logger.info("原策略结果已保存到: backtest_original_strategy.csv")
            
            # 保存修改策略结果
            if modified_results:
                modified_df = pd.DataFrame(modified_results)
                modified_df.to_csv('backtest_modified_strategy.csv', index=False, encoding='utf-8-sig')
                logger.info("修改策略结果已保存到: backtest_modified_strategy.csv")
            
            logger.info("回测结果保存完成！")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")

def main():
    """主函数"""
    backtester = StrategyBacktester()
    backtester.run_backtest()

if __name__ == "__main__":
    main()
