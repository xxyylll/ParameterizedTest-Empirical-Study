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
import argparse
import csv
import os
import sys
from collections import defaultdict

# 指标清单与 Mann-Whitney 实现从 heatmap_unified_44projects.py 原样复制过来。
# 不直接 import 的原因：那个模块没有 `if __name__ == "__main__"` 保护，
# 一导入就会重跑绘图并覆盖已有的图（plot_rq3_forest.py 也有这个副作用）。
# 本脚本只做统计、不该产生任何图文件，所以宁可复制这个纯函数。
import math

METRICS = ['self_loc', 'self_cc', 'self_cctr', 'self_dupPerc',
           'helper_loc_sum', 'helper_cc_sum', 'helper_cctr_sum', 'helper_dupPerc',
           'total_loc', 'total_cc', 'total_cctr', 'total_dupPerc']
METRIC_LABELS = ['LOC (test)', 'CC (test)', 'CCTR (test)', 'DUP% (test)',
                 'LOC (helpers)', 'CC (helpers)', 'CCTR (helpers)', 'DUP% (helpers)',
                 'LOC (total)', 'CC (total)', 'CCTR (total)', 'DUP% (total)']


def mann_whitney_u(group1, group2):
    n1, n2 = len(group1), len(group2)
    N = n1 + n2
    combined = [(x, 1) for x in group1] + [(x, 2) for x in group2]
    combined.sort(key=lambda t: t[0])
    ranks = [0.0] * N
    i = 0
    tie_term_sum = 0
    while i < N:
        j = i
        while j + 1 < N and combined[j + 1][0] == combined[i][0]:
            j += 1
        tie_size = j - i + 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        if tie_size > 1:
            tie_term_sum += tie_size ** 3 - tie_size
        i = j + 1
    R1 = sum(r for r, (val, grp) in zip(ranks, combined) if grp == 1)
    U1 = R1 - n1 * (n1 + 1) / 2.0
    mean_U = n1 * n2 / 2.0
    sigma_U = math.sqrt((n1 * n2 / 12.0) * ((N + 1) - tie_term_sum / (N * (N - 1))))
    if sigma_U == 0:
        z = 0.0
    else:
        z = (U1 - 0.5 - mean_U) / sigma_U if U1 > mean_U else ((U1 + 0.5 - mean_U) / sigma_U if U1 < mean_U else 0.0)
    p = max(0.0, min(1.0, 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))))
    cliffs_delta = (2 * U1) / (n1 * n2) - 1
    return cliffs_delta, p


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
    with open(os.path.join(HERE, f'rq3_bh_{tag}.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric', 'project', 'cliffs_delta', 'magnitude', 'p', 'q_BH',
                    'sig_p<0.05', 'sig_q<0.05', 'n_pt', 'n_nonpt'])
        w.writerows(detail)
    with open(os.path.join(HERE, f'rq3_bh_summary_{tag}.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric_x_layer', 'n_projects', 'sig_before_BH', 'sig_after_BH', 'lost'])
        w.writerows(summary)

    print(f'输入 {os.path.basename(a.csv)}  |  对照组 {"仅 JUnit5" if a.junit5 else "全部非 PT"}  |  CCTR 口径 {tag}')
    print(f'校正家族 = 指标 × 层次，共 {len(summary)} 组，每组 {summary[0][1]} 个项目\n')
    print(f"{'metric × layer':18}{'k':>4}{'sig p<.05':>11}{'sig q<.05':>11}{'掉了':>6}")
    print('-' * 50)
    for s in summary:
        print(f'{s[0]:18}{s[1]:>4}{s[2]:>11}{s[3]:>11}{s[4]:>6}')
    print(f'\nwrote rq3_bh_{tag}.csv / rq3_bh_summary_{tag}.csv')


if __name__ == '__main__':
    main()
