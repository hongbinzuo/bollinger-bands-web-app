#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC Tuesday Recovery Strategy Analyzer
分析BTC周二反弹策略，判断亚盘、欧盘、美盘哪个时段最可能产生1-1.5%反弹
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Tuple, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BTCTuesdayRecoveryAnalyzer:
    def __init__(self):
        self.bybit_base_url = "https://api.bybit.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 交易时段定义 (UTC时间)
        self.sessions = {
            'asia': {'start': 0, 'end': 8},      # 亚盘: 00:00-08:00 UTC
            'europe': {'start': 8, 'end': 16},   # 欧盘: 08:00-16:00 UTC  
            'us': {'start': 16, 'end': 24}       # 美盘: 16:00-24:00 UTC
        }
        
        # 反弹目标范围
        self.recovery_targets = {
            'min_recovery': 1.0,    # 最小反弹1%
            'max_recovery': 1.5     # 最大反弹1.5%
        }

    def get_btc_price_data(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 168) -> Optional[pd.DataFrame]:
        """
        从Bybit获取BTC价格数据
        """
        try:
            url = f"{self.bybit_base_url}/v5/market/kline"
            params = {
                'category': 'spot',
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['retCode'] != 0:
                logger.error(f"Bybit API错误: {data['retMsg']}")
                return None
                
            klines = data['result']['list']
            if not klines:
                logger.error("未获取到K线数据")
                return None
                
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            # 数据类型转换
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 时间戳转换
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['datetime_utc'] = df['datetime'].dt.tz_localize('UTC')
            
            # 按时间排序
            df = df.sort_values('datetime_utc').reset_index(drop=True)
            
            logger.info(f"成功获取 {len(df)} 条BTC价格数据")
            return df
            
        except Exception as e:
            logger.error(f"获取BTC价格数据失败: {e}")
            return None

    def get_current_btc_price(self) -> Optional[float]:
        """获取当前BTC价格"""
        try:
            url = f"{self.bybit_base_url}/v5/market/tickers"
            params = {'category': 'spot', 'symbol': 'BTCUSDT'}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['retCode'] == 0 and data['result']['list']:
                price = float(data['result']['list'][0]['lastPrice'])
                logger.info(f"当前BTC价格: ${price:,.2f}")
                return price
            return None
            
        except Exception as e:
            logger.error(f"获取当前BTC价格失败: {e}")
            return None

    def identify_tuesday_sessions(self, df: pd.DataFrame) -> List[Dict]:
        """
        识别周二交易时段数据
        """
        tuesday_sessions = []
        
        # 获取所有周二的数据
        tuesday_data = df[df['datetime_utc'].dt.weekday == 1].copy()  # 周二 = 1
        
        if tuesday_data.empty:
            logger.warning("未找到周二数据")
            return tuesday_sessions
            
        # 按日期分组
        for date, day_data in tuesday_data.groupby(tuesday_data['datetime_utc'].dt.date):
            day_sessions = {
                'date': date,
                'sessions': {}
            }
            
            # 分析每个时段
            for session_name, session_times in self.sessions.items():
                start_hour = session_times['start']
                end_hour = session_times['end']
                
                # 筛选该时段的数据
                session_data = day_data[
                    (day_data['datetime_utc'].dt.hour >= start_hour) & 
                    (day_data['datetime_utc'].dt.hour < end_hour)
                ].copy()
                
                if not session_data.empty:
                    session_analysis = self.analyze_session(session_data, session_name)
                    day_sessions['sessions'][session_name] = session_analysis
                    
            tuesday_sessions.append(day_sessions)
            
        logger.info(f"识别到 {len(tuesday_sessions)} 个周二交易日")
        return tuesday_sessions

    def analyze_session(self, session_data: pd.DataFrame, session_name: str) -> Dict:
        """
        分析单个交易时段
        """
        if session_data.empty:
            return {'error': '无数据'}
            
        # 基础统计
        open_price = session_data.iloc[0]['open']
        close_price = session_data.iloc[-1]['close']
        high_price = session_data['high'].max()
        low_price = session_data['low'].min()
        
        # 计算涨跌幅
        price_change = close_price - open_price
        price_change_pct = (price_change / open_price) * 100
        
        # 计算最大回撤和反弹
        max_drawdown = ((low_price - open_price) / open_price) * 100
        max_recovery = ((high_price - open_price) / open_price) * 100
        
        # 判断是否在目标反弹范围内
        target_recovery = self.recovery_targets['min_recovery'] <= max_recovery <= self.recovery_targets['max_recovery']
        
        # 计算波动率
        returns = session_data['close'].pct_change().dropna()
        volatility = returns.std() * 100 if len(returns) > 1 else 0
        
        return {
            'session': session_name,
            'open_price': open_price,
            'close_price': close_price,
            'high_price': high_price,
            'low_price': low_price,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'max_drawdown_pct': max_drawdown,
            'max_recovery_pct': max_recovery,
            'target_recovery_achieved': target_recovery,
            'volatility_pct': volatility,
            'data_points': len(session_data)
        }

    def analyze_tuesday_patterns(self, tuesday_sessions: List[Dict]) -> Dict:
        """
        分析周二模式
        """
        if not tuesday_sessions:
            return {'error': '无周二数据'}
            
        session_stats = {}
        
        # 统计每个时段的成功率
        for session_name in self.sessions.keys():
            session_analyses = []
            
            for day_data in tuesday_sessions:
                if session_name in day_data['sessions']:
                    session_analyses.append(day_data['sessions'][session_name])
            
            if session_analyses:
                # 计算统计指标
                target_achieved = sum(1 for s in session_analyses if s.get('target_recovery_achieved', False))
                total_sessions = len(session_analyses)
                success_rate = (target_achieved / total_sessions) * 100 if total_sessions > 0 else 0
                
                avg_recovery = np.mean([s.get('max_recovery_pct', 0) for s in session_analyses])
                avg_volatility = np.mean([s.get('volatility_pct', 0) for s in session_analyses])
                
                session_stats[session_name] = {
                    'total_sessions': total_sessions,
                    'target_achieved': target_achieved,
                    'success_rate': success_rate,
                    'avg_recovery_pct': avg_recovery,
                    'avg_volatility_pct': avg_volatility,
                    'analyses': session_analyses
                }
        
        return session_stats

    def predict_best_session_today(self, session_stats: Dict) -> Dict:
        """
        基于历史数据预测今天的最佳交易时段
        """
        if not session_stats:
            return {'error': '无历史数据'}
            
        # 获取当前时间
        now_utc = datetime.utcnow()
        current_hour = now_utc.hour
        
        # 判断当前处于哪个时段
        current_session = None
        for session_name, times in self.sessions.items():
            if times['start'] <= current_hour < times['end']:
                current_session = session_name
                break
                
        # 按成功率排序
        sorted_sessions = sorted(
            session_stats.items(),
            key=lambda x: x[1]['success_rate'],
            reverse=True
        )
        
        best_session = sorted_sessions[0] if sorted_sessions else None
        
        prediction = {
            'current_time_utc': now_utc.isoformat(),
            'current_session': current_session,
            'best_session': best_session[0] if best_session else None,
            'best_session_stats': best_session[1] if best_session else None,
            'all_session_stats': session_stats,
            'recommendation': self.generate_recommendation(best_session, current_session)
        }
        
        return prediction

    def generate_recommendation(self, best_session: Tuple, current_session: str) -> str:
        """
        生成交易建议
        """
        if not best_session:
            return "数据不足，无法给出建议"
            
        session_name, stats = best_session
        success_rate = stats['success_rate']
        avg_recovery = stats['avg_recovery_pct']
        
        if current_session == session_name:
            return f"当前正处于最佳时段({session_name})，历史成功率{success_rate:.1f}%，平均反弹{avg_recovery:.2f}%"
        elif current_session:
            return f"当前时段({current_session})，建议等待最佳时段({session_name})，历史成功率{success_rate:.1f}%"
        else:
            return f"建议关注{session_name}时段，历史成功率{success_rate:.1f}%，平均反弹{avg_recovery:.2f}%"

    def run_analysis(self) -> Dict:
        """
        运行完整分析
        """
        logger.info("开始BTC周二反弹策略分析...")
        
        # 获取价格数据
        df = self.get_btc_price_data()
        if df is None:
            return {'error': '无法获取价格数据'}
            
        # 获取当前价格
        current_price = self.get_current_btc_price()
        
        # 识别周二时段
        tuesday_sessions = self.identify_tuesday_sessions(df)
        if not tuesday_sessions:
            return {'error': '未找到周二数据'}
            
        # 分析模式
        session_stats = self.analyze_tuesday_patterns(tuesday_sessions)
        
        # 预测最佳时段
        prediction = self.predict_best_session_today(session_stats)
        
        # 生成报告
        report = {
            'analysis_time': datetime.now().isoformat(),
            'current_btc_price': current_price,
            'data_period': {
                'start': df['datetime_utc'].min().isoformat(),
                'end': df['datetime_utc'].max().isoformat(),
                'total_hours': len(df)
            },
            'tuesday_sessions_count': len(tuesday_sessions),
            'session_statistics': session_stats,
            'prediction': prediction,
            'strategy_summary': self.generate_strategy_summary(session_stats)
        }
        
        return report

    def generate_strategy_summary(self, session_stats: Dict) -> str:
        """
        生成策略总结
        """
        if not session_stats:
            return "数据不足"
            
        total_sessions = sum(stats['total_sessions'] for stats in session_stats.values())
        total_achieved = sum(stats['target_achieved'] for stats in session_stats.values())
        overall_success_rate = (total_achieved / total_sessions) * 100 if total_sessions > 0 else 0
        
        best_session = max(session_stats.items(), key=lambda x: x[1]['success_rate'])
        
        return f"""
周二反弹策略分析总结:
- 总分析时段: {total_sessions}
- 目标达成: {total_achieved} ({overall_success_rate:.1f}%)
- 最佳时段: {best_session[0]} (成功率: {best_session[1]['success_rate']:.1f}%)
- 建议: 重点关注{best_session[0]}时段，历史数据显示该时段最可能产生1-1.5%反弹
        """

def main():
    """主函数"""
    analyzer = BTCTuesdayRecoveryAnalyzer()
    
    try:
        # 运行分析
        report = analyzer.run_analysis()
        
        if 'error' in report:
            print(f"分析失败: {report['error']}")
            return
            
        # 打印结果
        print("=" * 60)
        print("BTC周二反弹策略分析报告")
        print("=" * 60)
        
        print(f"分析时间: {report['analysis_time']}")
        print(f"当前BTC价格: ${report['current_btc_price']:,.2f}")
        print(f"数据周期: {report['data_period']['start']} 至 {report['data_period']['end']}")
        print(f"周二交易日数: {report['tuesday_sessions_count']}")
        
        print("\n各时段统计:")
        for session_name, stats in report['session_statistics'].items():
            print(f"\n{session_name.upper()}时段:")
            print(f"  总时段数: {stats['total_sessions']}")
            print(f"  目标达成: {stats['target_achieved']}")
            print(f"  成功率: {stats['success_rate']:.1f}%")
            print(f"  平均反弹: {stats['avg_recovery_pct']:.2f}%")
            print(f"  平均波动率: {stats['avg_volatility_pct']:.2f}%")
        
        print(f"\n预测结果:")
        print(f"当前时段: {report['prediction']['current_session']}")
        print(f"最佳时段: {report['prediction']['best_session']}")
        print(f"建议: {report['prediction']['recommendation']}")
        
        print(f"\n{report['strategy_summary']}")
        
        # 保存详细报告
        with open('btc_tuesday_analysis_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n详细报告已保存到: btc_tuesday_analysis_report.json")
        
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
        print(f"分析失败: {e}")

if __name__ == "__main__":
    main()
