#!/usr/bin/env python3
"""RQ3.1 热力图（竖版）：46 行（项目）× 12 列（指标），适合论文附录整页。

原来的横版是 12 行 × 46 列、10016×1423 px（7:1），一页宽度塞 46 列会挤成一条线。
转置后每行一个项目，正好填满竖排的一整页。

色标、分箱、显著性标记沿用原 heatmap_unified_44projects.py，两张图可直接对照。
项目按测试数降序，行标签带 n。

输出 rq3_heatmap_portrait.{png,pdf}
"""
import csv
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rq3_metrics import METRICS, METRIC_LABELS, mann_whitney_u  # noqa: E402

# --- CLI：数据源 / JUnit 过滤 / CCTR 口径 / 输出前缀 -------------------------
import argparse as _ap
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SSD, METRICS_DIR, APACHE_PROJECTS, DUP_RESULT, FINAL  # noqa: E402

_p = _ap.ArgumentParser()
_p.add_argument('--csv', default=_os.path.join(METRICS_DIR, 'test_metrics_all_44projects.csv'))
_p.add_argument('--out', default=None)
_p.add_argument('--junit5', action='store_true', help='只保留 junit_api == junit5 的测试')
_p.add_argument('--cctr', choices=['orig', 'eq'], default='orig',
                help="eq = 用 cctr_eq（@ParameterizedTest 与 @Test 同权）替换 CCTR")
_ARGS = _p.parse_args()

if _ARGS.cctr == 'eq':
    # CCTR 的 T 分量原本给 @ParameterizedTest 记 2 分、@Test 记 1 分，每个 PT 白得 1 分。
    # 同权口径把三个 CCTR 指标换成 *_eq 版本，其余指标不变。
    METRICS = [m.replace('self_cctr', 'self_cctr_eq')
                .replace('helper_cctr_sum', 'helper_cctr_eq_sum')
                .replace('total_cctr', 'total_cctr_eq') for m in METRICS]
    METRIC_LABELS = [l.replace('CCTR', 'CCTR*') for l in METRIC_LABELS]


def _load_rows():
    rs = list(csv.DictReader(open(_ARGS.csv, newline='', encoding='utf-8')))
    if _ARGS.junit5:
        rs = [r for r in rs if r.get('junit_api') == 'junit5']
    return rs



IN_CSV = _os.path.join(METRICS_DIR, 'test_metrics_all_44projects.csv')
OUT = _ARGS.out or _os.path.join(METRICS_DIR, 'rq3_heatmap_portrait')

BOUNDS = [-1.0001, -0.474, -0.33, -0.147, -1e-9, 1e-9, 0.147, 0.33, 0.474, 1.0001]
COLORS = ['#1c4d8c', '#3f7cb8', '#8fb3d9', '#d6e4f2', '#ffffff',
          '#fbe0d2', '#eba184', '#cf5a3d', '#a3221b']
SURFACE, INK, INK2 = '#fcfcfb', '#0b0b0b', '#52514e'


def main():
    rows = _load_rows()
    by_project = defaultdict(list)
    for r in rows:
        by_project[r['project']].append(r)
    projects = sorted(by_project, key=lambda p: -len(by_project[p]))

    delta, pval = {}, {}
    for p in projects:
        prs = by_project[p]
        for m in METRICS:
            g1 = [float(r[m]) for r in prs if r['category'] == 'pt' and r[m] != '']
            g2 = [float(r[m]) for r in prs if r['category'] == 'nonpt' and r[m] != '']
            if not g1 or not g2:
                delta[(p, m)] = pval[(p, m)] = None
                continue
            delta[(p, m)], pval[(p, m)] = mann_whitney_u(g1, g2)

    grid = [[float('nan') if delta[(p, m)] is None else delta[(p, m)] for m in METRICS]
            for p in projects]

    n_p, n_m = len(projects), len(METRICS)
    fig, ax = plt.subplots(figsize=(7.8, 2.2 + 0.205 * n_p))   # 顶部留给旋转的列标签和标题
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.imshow(grid, cmap=ListedColormap(COLORS), norm=BoundaryNorm(BOUNDS, len(COLORS)),
              aspect='auto')

    ax.set_xticks(range(n_m))
    ax.set_xticklabels(METRIC_LABELS, rotation=40, ha='left', fontsize=8.5)
    ax.xaxis.set_ticks_position('top')
    ax.set_yticks(range(n_p))
    ax.set_yticklabels([f'{p}  ({len(by_project[p]):,})' for p in projects], fontsize=7.5)

    for i, p in enumerate(projects):
        for j, m in enumerate(METRICS):
            pv = pval[(p, m)]
            if pv is not None and pv < 0.05:
                ax.text(j, i, '*', ha='center', va='center', fontsize=8,
                        fontweight='bold', color='black')

    # 三个层次之间的分隔（每 4 列一组）
    for xline in (3.5, 7.5):
        ax.axvline(xline, color='black', linewidth=1.1)
    ax.set_xticks([v - 0.5 for v in range(1, n_m)], minor=True)
    ax.set_yticks([v - 0.5 for v in range(1, n_p)], minor=True)
    ax.grid(which='minor', color=SURFACE, linewidth=1.0)
    ax.tick_params(which='minor', length=0)
    ax.tick_params(colors=INK2, length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    labels = ['Large PT (>0.474)', 'Medium PT', 'Small PT', 'Negligible PT', 'Equal',
              'Negligible non-PT', 'Small non-PT', 'Medium non-PT', 'Large non-PT (<−0.474)']
    handles = [Patch(facecolor=c, edgecolor='#888888', linewidth=0.5, label=l)
               for c, l in zip(reversed(COLORS), labels)]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(0.235, 0.006),
               fontsize=7.5, frameon=False, ncol=3, labelcolor=INK2,
               handlelength=1.1, handleheight=1.1, columnspacing=1.2)

    fig.text(0.012, 0.988, "PT vs non-PT per project (Cliff's delta)", ha='left', va='top',
             color=INK, fontsize=12, fontweight='bold')
    fig.text(0.012, 0.972, 'red = PT higher · blue = non-PT higher · * = p < 0.05 · '
                           "row label shows the project's test count",
             ha='left', va='top', fontsize=8, color=INK2)

    fig.subplots_adjust(left=0.235, right=0.925, top=0.875, bottom=0.075)
    for ext in ('png', 'pdf'):
        fig.savefig(f'{OUT}.{ext}', dpi=200, facecolor=SURFACE)
    print(f'wrote {OUT}.png / .pdf  ({n_p} projects × {n_m} metrics)')


if __name__ == '__main__':
    main()
