#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整回测程序：从今天8点开始测试200个币种的信号
计算胜率、盈亏，初始10000U，止损10%
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

class ComprehensiveBacktester:
    def __init__(self):
        self.strategy = MultiTimeframeStrategy('modified')
        self.initial_capital = 10000  # 初始资金10000U
        self.stop_loss_pct = 0.10  # 10%止损
        self.current_capital = self.initial_capital
        self.trades = []
        
    def get_gate_top_symbols(self, limit=200):
        """获取GATE.IO前200个币种"""
        try:
            import requests
            
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                usdt_pairs = [t for t in data if t['currency_pair'].endswith('_USDT')]
                usdt_pairs.sort(key=lambda x: float(x.get('base_volume', 0)), reverse=True)
                
                symbols = [pair['currency_pair'] for pair in usdt_pairs[:limit]]
                logger.info(f"获取到GATE.IO前{len(symbols)}个币种")
                return symbols
            else:
                logger.error(f"获取币种失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"获取币种失败: {e}")
            return []
    
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
                    df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open', 'quote_volume', 'trades'])
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
                    df = pd.DataFrame(data, columns=['timestamp', 'volume', 'close', 'high', 'low', 'open', 'quote_volume', 'trades'])
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
        logger.info(f"初始资金: {self.initial_capital}U")
        logger.info(f"止损设置: {self.stop_loss_pct*100}%")
        
        total_signals = 0
        
        for i, symbol in enumerate(symbols):
            logger.info(f"\n分析币种 {i+1}/{len(symbols)}: {symbol}")
            
            # 获取该币种的信号
            signals = self.get_signals_at_time(symbol, start_time)
            
            if signals:
                logger.info(f"找到{len(signals)}个信号")
                
                for j, signal in enumerate(signals):
                    logger.info(f"  信号{j+1}: {signal['signal']} EMA{signal['ema_period']} 入场价:{signal['entry_price']:.4f}")
                    
                    # 检查信号结果
                    result, profit_pct, reason = self.check_signal_result(signal, symbol, start_time)
                    
                    # 计算盈亏
                    if result == 'win':
                        profit_usd = self.current_capital * profit_pct
                        self.current_capital += profit_usd
                        logger.info(f"    ✅ 胜: {reason} 收益率:{profit_pct:.2%} 盈亏:{profit_usd:.2f}U 余额:{self.current_capital:.2f}U")
                    elif result == 'loss':
                        profit_usd = self.current_capital * profit_pct
                        self.current_capital += profit_usd
                        logger.info(f"    ❌ 败: {reason} 收益率:{profit_pct:.2%} 盈亏:{profit_usd:.2f}U 余额:{self.current_capital:.2f}U")
                    else:
                        profit_usd = 0
                        logger.info(f"    ⏳ {reason}")
                    
                    self.trades.append({
                        'symbol': symbol,
                        'signal_type': signal['signal'],
                        'ema_period': signal['ema_period'],
                        'entry_price': signal['entry_price'],
                        'take_profit_price': signal['take_profit_price'],
                        'result': result,
                        'profit_pct': profit_pct,
                        'profit_usd': profit_usd,
                        'reason': reason,
                        'balance': self.current_capital
                    })
                    
                    total_signals += 1
                    
                    # 添加延迟
                    time.sleep(0.1)
            else:
                logger.info("无信号")
        
        return total_signals
    
    def analyze_results(self):
        """分析回测结果"""
        logger.info("\n" + "=" * 60)
        logger.info("回测结果分析")
        logger.info("=" * 60)
        
        if not self.trades:
            logger.info("无回测结果")
            return
        
        # 统计结果
        total_trades = len(self.trades)
        win_trades = [t for t in self.trades if t['result'] == 'win']
        loss_trades = [t for t in self.trades if t['result'] == 'loss']
        pending_trades = [t for t in self.trades if t['result'] == 'pending']
        
        win_rate = len(win_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # 计算盈亏
        total_profit_usd = sum(t['profit_usd'] for t in self.trades)
        win_profit_usd = sum(t['profit_usd'] for t in win_trades)
        loss_profit_usd = sum(t['profit_usd'] for t in loss_trades)
        
        # 计算最终余额
        final_balance = self.current_capital
        total_return = (final_balance - self.initial_capital) / self.initial_capital * 100
        
        logger.info(f"初始资金: {self.initial_capital:.2f}U")
        logger.info(f"最终余额: {final_balance:.2f}U")
        logger.info(f"总盈亏: {total_profit_usd:.2f}U")
        logger.info(f"总收益率: {total_return:.2f}%")
        
        logger.info(f"\n交易统计:")
        logger.info(f"总交易数: {total_trades}")
        logger.info(f"胜交易数: {len(win_trades)}")
        logger.info(f"败交易数: {len(loss_trades)}")
        logger.info(f"未触发数: {len(pending_trades)}")
        logger.info(f"胜率: {win_rate:.2f}%")
        
        if win_trades:
            avg_win_pct = np.mean([t['profit_pct'] for t in win_trades])
            logger.info(f"平均胜率收益率: {avg_win_pct:.2%}")
        
        if loss_trades:
            avg_loss_pct = np.mean([t['profit_pct'] for t in loss_trades])
            logger.info(f"平均败率收益率: {avg_loss_pct:.2%}")
        
        # 按信号类型统计
        long_trades = [t for t in self.trades if t['signal_type'] == 'long']
        short_trades = [t for t in self.trades if t['signal_type'] == 'short']
        
        logger.info(f"\n按信号类型统计:")
        logger.info(f"做多交易: {len(long_trades)}")
        logger.info(f"做空交易: {len(short_trades)}")
        
        # 按EMA周期统计
        ema_stats = {}
        for trade in self.trades:
            ema = trade['ema_period']
            if ema not in ema_stats:
                ema_stats[ema] = []
            ema_stats[ema].append(trade)
        
        logger.info(f"\n按EMA周期统计:")
        for ema, ema_trades in ema_stats.items():
            ema_wins = [t for t in ema_trades if t['result'] == 'win']
            ema_win_rate = len(ema_wins) / len(ema_trades) * 100 if ema_trades else 0
            logger.info(f"  EMA{ema}: {len(ema_trades)}个交易, 胜率: {ema_win_rate:.2f}%")
        
        # 保存详细结果
        results_df = pd.DataFrame(self.trades)
        results_df.to_csv('comprehensive_backtest_results.csv', index=False, encoding='utf-8-sig')
        logger.info(f"\n详细结果已保存到: comprehensive_backtest_results.csv")
        
        # 显示详细结果
        logger.info("\n详细交易结果:")
        for trade in self.trades:
            status = "✅" if trade['result'] == 'win' else "❌" if trade['result'] == 'loss' else "⏳"
            logger.info(f"  {status} {trade['symbol']} {trade['signal_type']} EMA{trade['ema_period']} {trade['reason']} 盈亏:{trade['profit_usd']:.2f}U 余额:{trade['balance']:.2f}U")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("完整策略回测")
    logger.info("=" * 60)
    
    # 设置回测开始时间（今天早上8点）
    today = datetime.now().date()
    start_time = datetime.combine(today, datetime.min.time().replace(hour=8))
    
    logger.info(f"回测开始时间: {start_time}")
    
    # 获取前200个币种
    backtester = ComprehensiveBacktester()
    symbols = backtester.get_gate_top_symbols(200)
    
    if not symbols:
        logger.error("无法获取币种列表")
        return
    
    logger.info(f"获取到{len(symbols)}个币种")
    
    # 执行回测
    total_signals = backtester.backtest_strategy(symbols, start_time)
    
    # 分析结果
    backtester.analyze_results()
    
    logger.info(f"\n回测完成！共处理{total_signals}个信号")

if __name__ == "__main__":
    main()

