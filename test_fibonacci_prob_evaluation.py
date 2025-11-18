#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斐波概率预测模型 离线评测脚本（选项 3）

功能：
- 基于历史K线回放，对“最近窗口”内的预测进行事后验证，统计 AUC、Brier、命中率等。
- 目标事件：在指定预测视野（horizon_bars）内，价格是否触及所选斐波扩展位（最近的上方目标位）。

使用：
  python test_fibonacci_prob_evaluation.py --symbol BTC --timeframe 4h --days 120 \
      --stride 6 --horizon_bars 24

注意：
- 若网络不可用或交易所无该交易对，将自动使用模型的可重复模拟数据。
- 该脚本仅打印评测报告，不修改任何服务端逻辑。
"""

from __future__ import annotations

import argparse
import math
import statistics
from typing import List, Dict, Tuple

from fibonacci_probability_model import FibonacciProbabilityModel


def auc_roc(probs: List[float], labels: List[int]) -> float:
    """简单ROC AUC实现（阈值扫一遍并梯形积分）。"""
    if not probs:
        return 0.5
    # 排序（概率从高到低）
    pairs = sorted(zip(probs, labels), key=lambda x: -x[0])
    P = sum(1 for _, y in pairs if y == 1)
    N = sum(1 for _, y in pairs if y == 0)
    if P == 0 or N == 0:
        return 0.5
    # 逐步阈值扫描
    tp = 0
    fp = 0
    prev_p = None
    roc: List[Tuple[float, float]] = [(0.0, 0.0)]
    for p, y in pairs:
        if prev_p is None or p != prev_p:
            roc.append((fp / N, tp / P))
            prev_p = p
        if y == 1:
            tp += 1
        else:
            fp += 1
    roc.append((fp / N, tp / P))
    # 梯形积分
    auc = 0.0
    for i in range(1, len(roc)):
        x0, y0 = roc[i - 1]
        x1, y1 = roc[i]
        auc += (x1 - x0) * (y0 + y1) / 2.0
    return max(0.0, min(1.0, auc))


def choose_target_level(fib_levels: Dict[float, float], cur_price: float) -> Tuple[float, float]:
    """选择当前价上方最近的斐波扩展位（level, price）。若无，返回最高一个。"""
    if not fib_levels:
        return 1.618, cur_price * 1.618
    candidates = [(lvl, px) for lvl, px in fib_levels.items() if px >= cur_price]
    if not candidates:
        return max(fib_levels.items(), key=lambda kv: kv[1])
    return min(candidates, key=lambda kv: kv[1])


def evaluate(symbol: str, timeframe: str, days: int, stride: int, horizon_bars: int,
             base_weights: Dict[str, float] | None = None) -> Dict:
    m = FibonacciProbabilityModel()
    if base_weights:
        m.base_weights = dict(base_weights)

    # 拉历史数据；失败则用 mock
    limit = min(1000, int(days * m._get_bars_per_day(timeframe)))
    price_data = m.get_bybit_klines(symbol, timeframe, limit)
    used_mock = False
    if not price_data:
        used_mock = True
        price_data = m.generate_mock_data(symbol, timeframe, limit, seed=42)

    n = len(price_data)
    if n < 200:
        # 数据太短，视作不足
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'used_mock': used_mock,
            'points': 0,
            'auc': 0.5,
            'brier': None,
            'acc@0.5': None,
        }

    probs: List[float] = []
    labels: List[int] = []

    # 从较早处开始，保留足够预测视野
    start = 100
    end = n - horizon_bars - 1
    for i in range(start, end, max(1, stride)):
        # 窗口数据截至当前 i
        window = price_data[: i + 1]
        cur_price = window[-1]['close']
        hist = m.identify_historical_high_low(window, timeframe=timeframe)
        fibs = m.calculate_fibonacci_extension_levels(hist['historical_low'], hist['historical_high'])

        # 组装分析结果（与主逻辑一致）
        velocities = m.analyze_price_velocity(window)
        volumes = m.calculate_volume_energy(window)
        fakes = m.identify_fake_breakouts(window, hist['historical_high'], timeframe=timeframe)
        indicators = m._compute_indicators(window)
        zones = []
        for lvl_px in fibs.values():
            zones.extend(m.analyze_key_zone_consolidation(window, lvl_px))
        analysis_results = {
            'velocities': velocities,
            'volume_energies': volumes,
            'fake_breakouts': fakes,
            'zone_consolidations': zones,
            'historical_data': hist,
            'indicators': indicators,
        }

        # 选择目标位并打分
        lvl, lvl_px = choose_target_level(fibs, cur_price)
        prob = m.calculate_breakout_probability(window, lvl_px, analysis_results, timeframe=timeframe)[
            'probability'
        ]
        # 未来 horizon 是否触及目标价
        future_high = max(row['high'] for row in price_data[i + 1 : i + 1 + horizon_bars])
        label = 1 if future_high >= lvl_px else 0
        probs.append(float(prob))
        labels.append(int(label))

    # 评测指标
    brier = statistics.mean((p - y) ** 2 for p, y in zip(probs, labels))
    auc = auc_roc(probs, labels)
    # 简单阈值
    thr = 0.5
    preds = [1 if p >= thr else 0 for p in probs]
    acc = sum(int(p == y) for p, y in zip(preds, labels)) / len(labels)

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'used_mock': used_mock,
        'points': len(labels),
        'auc': auc,
        'brier': brier,
        'acc@0.5': acc,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default='BTC')
    ap.add_argument('--timeframe', default='4h', choices=['5m', '15m', '1h', '4h', '1d'])
    ap.add_argument('--days', type=int, default=120)
    ap.add_argument('--stride', type=int, default=6, help='逐点评测的步长，越大越快')
    ap.add_argument('--horizon_bars', type=int, default=24, help='未来多少根K线作为命中窗口')
    args = ap.parse_args()

    report = evaluate(args.symbol, args.timeframe, args.days, args.stride, args.horizon_bars)
    print('评测报告:')
    for k, v in report.items():
        print(f'- {k}: {v}')


if __name__ == '__main__':
    main()
