#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斐波概率预测模型 评测矩阵 + 小型权重网格搜索（下一步1）

功能：
- 对多标的×多周期×多 horizon 的组合跑评测矩阵（使用 test_fibonacci_prob_evaluation.evaluate）。
- 在一组小网格的 base_weights 上搜索，统计总体 AUC/Brier，找出最优权重组合。

使用示例：
  python test_fibonacci_prob_gridsearch.py \
      --symbols BTC,ETH,SOL --timeframes 4h,1d --days 120 --horizon_bars 24,36 \
      --stride 6

说明：
- 该脚本不会修改线上逻辑，只用于离线评估与权重建议。
"""

from __future__ import annotations

import argparse
import itertools
import statistics
from typing import Dict, List, Tuple

from fibonacci_probability_model import FibonacciProbabilityModel
from test_fibonacci_prob_evaluation import evaluate  # 复用评测实现


def parse_list(s: str) -> List[str]:
    return [x.strip() for x in s.split(',') if x.strip()]


def run_matrix(symbols: List[str], timeframes: List[str], days: int, stride: int, horizons: List[int],
               base_weights: Dict[str, float]) -> Dict:
    m = FibonacciProbabilityModel()
    m.base_weights = dict(base_weights)
    reports = []
    for sym in symbols:
        for tf in timeframes:
            for hz in horizons:
        rep = evaluate(sym, tf, days, stride, hz, base_weights=base_weights)
                reports.append(rep)
    # 汇总指标
    auc_list = [r['auc'] for r in reports if r.get('points', 0) > 0]
    brier_list = [r['brier'] for r in reports if r.get('points', 0) > 0]
    acc_list = [r['acc@0.5'] for r in reports if r.get('points', 0) > 0]
    summary = {
        'auc_mean': statistics.mean(auc_list) if auc_list else None,
        'brier_mean': statistics.mean(brier_list) if brier_list else None,
        'acc_mean': statistics.mean(acc_list) if acc_list else None,
        'count': len(auc_list),
    }
    return {'summary': summary, 'reports': reports}


def gridsearch(symbols: List[str], timeframes: List[str], days: int, stride: int, horizons: List[int]) -> None:
    # 基于当前默认权重构造小网格（每个因子在默认值±0.05 内变动），并归一化
    default = FibonacciProbabilityModel().base_weights
    keys = list(default.keys())
    # 每个因子取 { -0.05, 0.0, +0.05 } 的偏移（搜索空间 3^6 = 729）
    offsets = [-0.05, 0.0, 0.05]
    best = None
    best_w = None
    tried = 0
    for grid in itertools.product(offsets, repeat=len(keys)):
        tried += 1
        w = {k: max(0.01, default[k] + delta) for k, delta in zip(keys, grid)}
        s = sum(w.values())
        w = {k: v / s for k, v in w.items()}
        result = run_matrix(symbols, timeframes, days, stride, horizons, w)
        auc = result['summary']['auc_mean'] or 0.0
        brier = result['summary']['brier_mean'] or 1.0
        # 目标：最大化 AUC，最小化 Brier —— 采用简单分数 auc - (brier)
        score = auc - brier
        if best is None or score > best:
            best = score
            best_w = (w, result['summary'])
            print(f"[improve] score={score:.4f} auc={auc:.4f} brier={brier:.4f} weights={w}")
    print("搜索完成：")
    print(f"- 尝试组合：{tried}")
    if best_w:
        w, summ = best_w
        print("最优权重：")
        for k, v in w.items():
            print(f"  {k}: {v:.3f}")
        print("指标：")
        for k, v in summ.items():
            print(f"  {k}: {v}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', default='BTC,ETH,SOL')
    ap.add_argument('--timeframes', default='4h,1d')
    ap.add_argument('--days', type=int, default=120)
    ap.add_argument('--stride', type=int, default=6)
    ap.add_argument('--horizon_bars', default='24,36')
    ap.add_argument('--mode', default='grid', choices=['grid', 'matrix'])
    args = ap.parse_args()

    symbols = parse_list(args.symbols)
    timeframes = parse_list(args.timeframes)
    horizons = [int(x) for x in parse_list(args.horizon_bars)]

    if args.mode == 'matrix':
        result = run_matrix(symbols, timeframes, args.days, args.stride, horizons, FibonacciProbabilityModel().base_weights)
        print('汇总：', result['summary'])
    else:
        gridsearch(symbols, timeframes, args.days, args.stride, horizons)


if __name__ == '__main__':
    main()
