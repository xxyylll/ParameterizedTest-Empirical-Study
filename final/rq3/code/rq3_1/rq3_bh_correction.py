#!/usr/bin/env python3
"""RQ3.1：对每项目 Mann-Whitney 的 p 值做 Benjamini-Hochberg 校正。

**校正家族 = 一个指标 × 一个层次**，组内是 46 个项目的 46 个 p 值。
4 个指标（LOC / CC / CCTR / DUP%）× 3 个层次（self / helpers / total）= 12 组；
`--cctr eq` 时 CCTR 换成同权版 CCTR*，仍是 12 组，两次合看是 15 组
（LOC/CC/DUP 的 9 组两版相同，只有 CCTR 的 3 组不同）。

按指标×层次分组而不是把 552 个 p 值放一起，是因为每组回答的是同一个问题
（「这个指标在这个层次上，PT 与非 PT 有没有差异」），组间问题不同，
合并校正会让本来稳健的组被别组的噪声拖累。

显著性一律以 **q < 0.05** 判定，不再用原始 p。

输出 rq3_bh_<cctr>.csv（每项目每指标一行，含 p、q、是否显著）
     和 rq3_bh_summary_<cctr>.csv（每组的显著项目数：校正前 vs 校正后）
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ3_1_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import argparse
import csv
import statistics
import os
import sys
from collections import defaultdict

# 指标清单与 Mann-Whitney 实现统一来自 rq3_metrics —— 唯一定义处。
# 此前这里原样复制了一份，因为当时它们住在 heatmap_unified_44projects.py 里，
# 而那个模块没有 `__main__` 保护，一 import 就会重跑绘图并覆盖已有的图。
# 现已抽到 rq3_metrics.py（无副作用），复制的那份随之删除。
from rq3_metrics import METRICS, METRIC_LABELS, mann_whitney_u


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from paths import METRICS_DIR, require                      # noqa: E402
ALPHA = 0.05
THRESH = (0.147, 0.33, 0.474)          # Cliff's delta: negligible / small / medium / large


def magnitude(d):
    a = abs(d)
    return ('negligible' if a < THRESH[0] else 'small' if a < THRESH[1]
            else 'medium' if a < THRESH[2] else 'large')


def bh(pvals):
    """Benjamini-Hochberg：返回与输入同序的 q 值。

    q_(i) = min_{j>=i} ( p_(j) * m / j )，再按原序放回。
    从大到小累积取最小值，保证 q 单调不减。
    """
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        i = m - rank + 1                              # 原始升序位次
        val = min(prev, pvals[idx] * m / i)
        q[idx] = val
        prev = val
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default=os.path.join(METRICS_DIR, 'test_metrics_all_46projects_v2.csv'))
    ap.add_argument('--junit5', action='store_true', default=True,
                    help='对照组仅 JUnit5（默认开启，与正文口径一致）')
    ap.add_argument('--all-nonpt', dest='junit5', action='store_false')
    ap.add_argument('--cctr', choices=['orig', 'eq'], default='eq',
                    help='eq = 同权 CCTR*（正文建议口径）')
    a = ap.parse_args()

    metrics = list(METRICS)
    labels = list(METRIC_LABELS)
    if a.cctr == 'eq':
        metrics = [m.replace('self_cctr', 'self_cctr_eq')
                    .replace('helper_cctr_sum', 'helper_cctr_eq_sum')
                    .replace('total_cctr', 'total_cctr_eq') for m in metrics]
        labels = [l.replace('CCTR', 'CCTR*') for l in labels]

    require(a.csv, 'BH 校正')
    rows = list(csv.DictReader(open(a.csv)))
    if a.junit5:
        rows = [r for r in rows if (r.get('junit_api') or '') == 'junit5']
    by_project = defaultdict(list)
    for r in rows:
        by_project[r['project']].append(r)

    detail, summary = [], []
    for m, lab in zip(metrics, labels):
        cells = []
        for p, prs in by_project.items():
            g1 = [float(r[m]) for r in prs if r['category'] == 'pt' and r.get(m) not in ('', None)]
            g2 = [float(r[m]) for r in prs if r['category'] == 'nonpt' and r.get(m) not in ('', None)]
            if not g1 or not g2:
                continue
            d, pv = mann_whitney_u(g1, g2)
            cells.append([p, d, pv, len(g1), len(g2)])
        qs = bh([c[2] for c in cells])
        sig_p = sig_q = 0
        for c, q in zip(cells, qs):
            p_sig, q_sig = c[2] < ALPHA, q < ALPHA
            sig_p += p_sig; sig_q += q_sig
            detail.append([lab, c[0], f'{c[1]:.4f}', magnitude(c[1]),
                           f'{c[2]:.3e}', f'{q:.3e}', int(p_sig), int(q_sig), c[3], c[4]])
        lost = sig_p - sig_q
        summary.append([lab, len(cells), sig_p, sig_q, lost])

    tag = a.cctr
    with open(os.path.join(RESULTS_DIR, f'rq3_bh_{tag}.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric', 'project', 'cliffs_delta', 'magnitude', 'p', 'q_BH',
                    'sig_p<0.05', 'sig_q<0.05', 'n_pt', 'n_nonpt'])
        w.writerows(detail)
    with open(os.path.join(RESULTS_DIR, f'rq3_bh_summary_{tag}.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric_x_layer', 'n_projects', 'sig_before_BH', 'sig_after_BH', 'lost'])
        w.writerows(summary)

    # 正文用的结果表：每个「指标 × 层次」的中位 Cliff's δ 与量级，以及 q<0.05 下显著为正 / 为负 / 不显著的项目数。
    # 此前这张表（rq3_bh_final_*.csv）没有生成脚本，这里从上面的逐项目结果汇总得到。
    final = []
    for lab in [s_[0] for s_ in summary]:
        rows = [r for r in detail if r[0] == lab]
        ds = [float(r[2]) for r in rows]
        med = statistics.median(ds)
        final.append([lab, f'{med:+.4f}', magnitude(med),
                      sum(1 for r in rows if r[7] and float(r[2]) > 0),
                      sum(1 for r in rows if r[7] and float(r[2]) < 0),
                      sum(1 for r in rows if not r[7]),
                      sum(r[6] for r in rows), len(rows)])
    with open(os.path.join(RESULTS_DIR, f'rq3_bh_final_{tag}.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric_x_layer', 'median_cliffs_delta', 'magnitude', 'n_sig_positive_q',
                    'n_sig_negative_q', 'n_not_sig_q', 'n_sig_before_BH', 'n_projects'])
        w.writerows(final)

    print(f'输入 {os.path.basename(a.csv)}  |  对照组 {"仅 JUnit5" if a.junit5 else "全部非 PT"}  |  CCTR 口径 {tag}')
    print(f'校正家族 = 指标 × 层次，共 {len(summary)} 组，每组 {summary[0][1]} 个项目\n')
    print(f"{'metric × layer':18}{'k':>4}{'sig p<.05':>11}{'sig q<.05':>11}{'掉了':>6}")
    print('-' * 50)
    for s in summary:
        print(f'{s[0]:18}{s[1]:>4}{s[2]:>11}{s[3]:>11}{s[4]:>6}')
    print(f'\nwrote rq3_bh_{tag}.csv / rq3_bh_summary_{tag}.csv / rq3_bh_final_{tag}.csv')


if __name__ == '__main__':
    main()
