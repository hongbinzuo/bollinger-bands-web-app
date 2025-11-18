#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测程序：验证新策略3分钟止盈的胜率
从今天早上8点开始，计算信号，获取后续价格，统计胜率和盈亏
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
        self.strategy = MultiTimeframeStrategy('modified')
        self.initial_capital = 100  # 每个信号100刀
        self.stop_loss_pct = 0.10  # 10%止损
        
    def get_historical_data(self, symbol, timeframe='1d', days=7):
        """获取历史数据"""
        try:
            import requests
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            start_ts = int(start_time.timestamp())
            end_ts = int(end_time.timestamp())
            
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
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
                    df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    df = df.dropna()
                    return df
                else:
                    return pd.DataFrame()
            else:
                return pd.DataFrame()
                
        except Exception as e:
            return pd.DataFrame()
    
    def get_signals_at_time(self, symbol, target_time):
        """获取指定时间的信号"""
        try:
            # 获取该时间之前的数据来计算信号
            df = self.get_historical_data(symbol, '1d', days=30)
            if df.empty or len(df) < 50:
                return []
            
            # 计算技术指标
            df = self.strategy.calculate_emas(df, '1d')
            df = self.strategy.calculate_bollinger_bands(df)
            df = df.dropna()
            
            if df.empty:
                return []
            
            # 判断趋势
            if self.strategy.is_bullish_trend(df):
                trend = 'bullish'
            elif self.strategy.is_bearish_trend(df):
                trend = 'bearish'
            else:
                return []
            
            # 寻找信号
            signals = self.strategy.find_ema_pullback_levels(df, trend, '1d', symbol)
            
            # 过滤有效信号（检查3分钟布林中轨）
            valid_signals = []
            for signal in signals:
                # 获取3分钟数据检查止盈
                tp_df = self.get_historical_data(symbol, '3m', days=7)
                if not tp_df.empty:
                    tp_df = self.strategy.calculate_bollinger_bands(tp_df)
                    tp_df = tp_df.dropna()
                    
                    if not tp_df.empty:
                        bb_middle = tp_df['bb_middle'].iloc[-1]
                        entry_price = signal['entry_price']
                        
                        # 检查止损条件
                        if signal['signal'] == 'short':
                            # 做空信号：3分钟布林中轨应该低于入场价格
                            if bb_middle < entry_price:
                                signal['take_profit_price'] = bb_middle
                                valid_signals.append(signal)
                        else:
                            # 做多信号：3分钟布林中轨应该高于入场价格
                            if bb_middle > entry_price:
                                signal['take_profit_price'] = bb_middle
                                valid_signals.append(signal)
            
            return valid_signals
            
        except Exception as e:
            logger.error(f"获取{symbol}信号失败: {e}")
            return []
    
    def check_signal_result(self, signal, symbol, entry_time):
        """检查信号结果"""
        try:
            # 获取入场时间之后的价格数据
            end_time = datetime.now()
            start_ts = int(entry_time.timestamp())
            end_ts = int(end_time.timestamp())
            
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': symbol,
                'interval': '3m',  # 3分钟K线
                'from': start_ts,
                'to': end_ts
            }
            
            import requests
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    df = df.dropna()
                    
                    if not df.empty:
                        # 计算3分钟布林中轨
                        df = self.strategy.calculate_bollinger_bands(df)
                        df = df.dropna()
                        
                        if not df.empty:
                            entry_price = signal['entry_price']
                            take_profit_price = signal['take_profit_price']
                            signal_type = signal['signal']
                            
                            # 计算止损价格
                            if signal_type == 'long':
                                stop_loss_price = entry_price * (1 - self.stop_loss_pct)
                            else:
                                stop_loss_price = entry_price * (1 + self.stop_loss_pct)
                            
                            # 检查每个3分钟K线
                            for _, row in df.iterrows():
                                current_price = row['close']
                                bb_middle = row.get('bb_middle', current_price)
                                
                                # 检查止盈
                                if signal_type == 'long':
                                    if current_price >= take_profit_price or bb_middle >= take_profit_price:
                                        profit_pct = (take_profit_price - entry_price) / entry_price
                                        return 'win', profit_pct, '止盈'
                                else:
                                    if current_price <= take_profit_price or bb_middle <= take_profit_price:
                                        profit_pct = (entry_price - take_profit_price) / entry_price
                                        return 'win', profit_pct, '止盈'
                                
                                # 检查止损
                                if signal_type == 'long':
                                    if current_price <= stop_loss_price:
                                        return 'loss', -self.stop_loss_pct, '止损'
                                else:
                                    if current_price >= stop_loss_price:
                                        return 'loss', -self.stop_loss_pct, '止损'
                            
                            # 如果到当前时间还没触发，检查最新价格
                            latest_price = df['close'].iloc[-1]
                            if signal_type == 'long':
                                if latest_price >= take_profit_price:
                                    profit_pct = (take_profit_price - entry_price) / entry_price
                                    return 'win', profit_pct, '止盈'
                                elif latest_price <= stop_loss_price:
                                    return 'loss', -self.stop_loss_pct, '止损'
                            else:
                                if latest_price <= take_profit_price:
                                    profit_pct = (entry_price - take_profit_price) / entry_price
                                    return 'win', profit_pct, '止盈'
                                elif latest_price >= stop_loss_price:
                                    return 'loss', -self.stop_loss_pct, '止损'
                            
                            # 未触发任何条件
                            return 'pending', 0, '未触发'
            
            return 'error', 0, '数据获取失败'
            
        except Exception as e:
            logger.error(f"检查信号结果失败: {e}")
            return 'error', 0, str(e)
    
    def backtest_strategy(self, symbols, start_time):
        """回测策略"""
        logger.info(f"开始回测策略，从{start_time}开始")
        logger.info(f"测试币种: {symbols}")
        
        results = []
        total_signals = 0
        
        for symbol in symbols:
            logger.info(f"\n分析币种: {symbol}")
            
            # 获取该币种的信号
            signals = self.get_signals_at_time(symbol, start_time)
            
            if signals:
                logger.info(f"找到{len(signals)}个信号")
                
                for i, signal in enumerate(signals):
                    logger.info(f"  信号{i+1}: {signal['signal']} EMA{signal['ema_period']} 入场价:{signal['entry_price']:.4f}")
                    
                    # 检查信号结果
                    result, profit_pct, reason = self.check_signal_result(signal, symbol, start_time)
                    
                    # 计算盈亏
                    if result == 'win':
                        profit_usd = self.initial_capital * profit_pct
                        logger.info(f"    ✅ 胜: {reason} 收益率:{profit_pct:.2%} 盈亏:{profit_usd:.2f}刀")
                    elif result == 'loss':
                        profit_usd = self.initial_capital * profit_pct
                        logger.info(f"    ❌ 败: {reason} 收益率:{profit_pct:.2%} 盈亏:{profit_usd:.2f}刀")
                    else:
                        profit_usd = 0
                        logger.info(f"    ⏳ {reason}")
                    
                    results.append({
                        'symbol': symbol,
                        'signal_type': signal['signal'],
                        'ema_period': signal['ema_period'],
                        'entry_price': signal['entry_price'],
                        'take_profit_price': signal['take_profit_price'],
                        'result': result,
                        'profit_pct': profit_pct,
                        'profit_usd': profit_usd,
                        'reason': reason
                    })
                    
                    total_signals += 1
                    
                    # 添加延迟
                    time.sleep(0.1)
            else:
                logger.info("无信号")
        
        return results
    
    def analyze_results(self, results):
        """分析回测结果"""
        logger.info("\n" + "=" * 60)
        logger.info("回测结果分析")
        logger.info("=" * 60)
        
        if not results:
            logger.info("无回测结果")
            return
        
        # 统计结果
        total_signals = len(results)
        win_signals = [r for r in results if r['result'] == 'win']
        loss_signals = [r for r in results if r['result'] == 'loss']
        pending_signals = [r for r in results if r['result'] == 'pending']
        
        win_rate = len(win_signals) / total_signals * 100 if total_signals > 0 else 0
        
        # 计算盈亏
        total_profit_usd = sum(r['profit_usd'] for r in results)
        win_profit_usd = sum(r['profit_usd'] for r in win_signals)
        loss_profit_usd = sum(r['profit_usd'] for r in loss_signals)
        
        logger.info(f"总信号数: {total_signals}")
        logger.info(f"胜信号数: {len(win_signals)}")
        logger.info(f"败信号数: {len(loss_signals)}")
        logger.info(f"未触发数: {len(pending_signals)}")
        logger.info(f"胜率: {win_rate:.2f}%")
        
        logger.info(f"\n盈亏统计:")
        logger.info(f"总盈亏: {total_profit_usd:.2f}刀")
        logger.info(f"胜信号盈亏: {win_profit_usd:.2f}刀")
        logger.info(f"败信号盈亏: {loss_profit_usd:.2f}刀")
        
        if win_signals:
            avg_win_pct = np.mean([r['profit_pct'] for r in win_signals])
            logger.info(f"平均胜率收益率: {avg_win_pct:.2%}")
        
        if loss_signals:
            avg_loss_pct = np.mean([r['profit_pct'] for r in loss_signals])
            logger.info(f"平均败率收益率: {avg_loss_pct:.2%}")
        
        # 保存详细结果
        results_df = pd.DataFrame(results)
        results_df.to_csv('strategy_backtest_results.csv', index=False, encoding='utf-8-sig')
        logger.info(f"\n详细结果已保存到: strategy_backtest_results.csv")
        
        # 显示详细结果
        logger.info("\n详细信号结果:")
        for result in results:
            status = "✅" if result['result'] == 'win' else "❌" if result['result'] == 'loss' else "⏳"
            logger.info(f"  {status} {result['symbol']} {result['signal_type']} EMA{result['ema_period']} {result['reason']} 盈亏:{result['profit_usd']:.2f}刀")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("策略胜率回测")
    logger.info("=" * 60)
    
    # 设置回测开始时间（今天早上8点）
    today = datetime.now().date()
    start_time = datetime.combine(today, datetime.min.time().replace(hour=8))
    
    logger.info(f"回测开始时间: {start_time}")
    
    # 测试币种
    test_symbols = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']
    
    # 创建回测器
    backtester = StrategyBacktester()
    
    # 执行回测
    results = backtester.backtest_strategy(test_symbols, start_time)
    
    # 分析结果
    backtester.analyze_results(results)
    
    logger.info("\n回测完成！")

if __name__ == "__main__":
    main()
