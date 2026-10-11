#!/usr/bin/env python3
"""RQ3.1 森林图：12 行（4 指标 × 3 层次），x 轴是 Cliff's delta，每个项目一个点。

为什么不用热力图做正文主图：热力图把量值编码成颜色，而颜色是量化比较里最弱的编码；
这里用位置编码 delta，并让 46 个项目的点直接散布出来，于是方向、程度、项目间一致性
三件事在同一张图上可读。热力图保留作附录（见 plot_rq3_heatmap_portrait.py），
它不可替代的是「具体是哪个项目」。

点的面积按该项目的测试数开方缩放 —— 项目测试数从 231 到 23,021 差 100 倍，
等大小的点会让小项目和大项目看起来同等可靠。

配色沿用热力图两端的极色（红=PT 更高，蓝=非 PT 更高，灰=不显著），
两张图共用一套颜色语言。

输出 rq3_forest.{png,pdf}
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
import csv
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rq3_metrics import METRICS, METRIC_LABELS, mann_whitney_u  # noqa: E402

# --- CLI：数据源 / JUnit 过滤 / CCTR 口径 / 输出前缀 -------------------------
import argparse as _ap
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SSD, METRICS_DIR, APACHE_PROJECTS, DUP_RESULT, FINAL  # noqa: E402

_p = _ap.ArgumentParser()
# 默认输入是 RQ3.1 的 46 个项目表（rq3_bh_correction.py 用的同一份）；原先默认 44 个项目的旧表
_p.add_argument('--csv', default=_os.path.join(METRICS_DIR, 'test_metrics_all_46projects_v2.csv'))
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



IN_CSV = _ARGS.csv
# 默认写到 rq3/results/rq3_1/，文件名带上口径：--junit5 → _junit5，--cctr eq → _cctreq
OUT = _ARGS.out or _os.path.join(RESULTS_DIR, 'rq3_forest'
                                 + ('_junit5' if _ARGS.junit5 else '') + ('_cctreq' if _ARGS.cctr == 'eq' else ''))

PT_COLOR, NONPT_COLOR, NS_COLOR = '#a3221b', '#1c4d8c', '#b9b8b3'
SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#dcdbd7'
BAND = '#f0efec'                      # 中性带（|d| < 0.147，negligible）
THRESH = (0.147, 0.33, 0.474)         # Cliff's delta 的 small / medium / large 界

def _groups():
    return [('Test method itself', METRICS[0:4], METRIC_LABELS[0:4]),
            ('Test-scope helpers', METRICS[4:8], METRIC_LABELS[4:8]),
            ('Total (test + helpers)', METRICS[8:12], METRIC_LABELS[8:12])]
SHORT = {'LOC': 'LOC', 'CC': 'CC', 'CCTR': 'CCTR', 'DUP%': 'DUP%'}


def main():
    rows = _load_rows()
    by_project = defaultdict(list)
    for r in rows:
        by_project[r['project']].append(r)

    cells = {}
    for m in METRICS:
        out = []
        for p, prs in by_project.items():
            g1 = [float(r[m]) for r in prs if r['category'] == 'pt' and r[m] != '']
            g2 = [float(r[m]) for r in prs if r['category'] == 'nonpt' and r[m] != '']
            if not g1 or not g2:
                continue
            d, pv = mann_whitney_u(g1, g2)
            out.append((p, d, pv, len(g1) + len(g2)))
        cells[m] = out

    n_rows = sum(len(g[1]) for g in _groups())
    fig, ax = plt.subplots(figsize=(9.0, 6.6))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    # y：从上往下排，组间留空
    ypos, ylabels, group_spans = {}, [], []
    y = 0.0
    for gname, ms, labs in _groups():
        start = y
        for m, lab in zip(ms, labs):
            ypos[m] = y
            ylabels.append((y, lab.split(' (')[0]))
            y += 1.0
        group_spans.append((gname, start, y - 1.0))
        y += 0.9

    top, bottom = -0.7, y - 0.6
    ax.axvspan(-THRESH[0], THRESH[0], color=BAND, zorder=0)       # negligible 带
    for t in THRESH:
        for sgn in (-1, 1):
            ax.axvline(sgn * t, color=GRID, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
    ax.axvline(0, color='#8a8984', linewidth=1.2, zorder=2)

    nmax = max(n for m in METRICS for _, _, _, n in cells[m])
    for m in METRICS:
        yy = ypos[m]
        ds = []
        for p, d, pv, n in sorted(cells[m], key=lambda t: -t[3]):   # 大项目先画，小点压在上面
            ds.append(d)
            c = NS_COLOR if pv >= 0.05 else (PT_COLOR if d > 0 else NONPT_COLOR)
            ax.scatter([d], [yy], s=18 + 150 * (n / nmax) ** 0.5, color=c, alpha=0.55,
                       edgecolor=SURFACE, linewidth=0.6, zorder=3)
        med = statistics.median(ds)
        ax.plot([med, med], [yy - 0.30, yy + 0.30], color=INK, linewidth=2.2, zorder=5,
                solid_capstyle='butt')
        sig_pt = sum(1 for _, d, pv, _ in cells[m] if pv < 0.05 and d > 0)
        sig_np = sum(1 for _, d, pv, _ in cells[m] if pv < 0.05 and d < 0)
        tag = f'{sig_pt}/{len(cells[m])} PT' if sig_pt >= sig_np else f'{sig_np}/{len(cells[m])} non-PT'
        yf = (yy - top) / (bottom - top)                     # 注释放到坐标区外，避免压住大圆点
        ax.text(1.035, 1 - yf, f'{med:+.2f}', transform=ax.transAxes, ha='right',
                va='center', fontsize=9, color=INK, fontweight='bold')
        ax.text(1.065, 1 - yf, tag, transform=ax.transAxes, ha='left', va='center',
                fontsize=8.5, color=INK2)

    for gname, y0, y1 in group_spans:
        yf = ((y0 + y1) / 2 - top) / (bottom - top)
        ax.text(-0.175, 1 - yf, gname, transform=ax.transAxes, ha='center', va='center',
                fontsize=9, color=INK, fontweight='bold', rotation=90)
        if y1 + 0.95 < bottom:
            ax.axhline(y1 + 0.45, color=GRID, linewidth=0.8, zorder=1)

    ax.set_yticks([t[0] for t in ylabels])
    ax.set_yticklabels([t[1] for t in ylabels], fontsize=9.5)
    ax.set_ylim(bottom, top)
    ax.set_xlim(-0.85, 1.0)
    ax.set_xticks([-0.474, -0.33, -0.147, 0, 0.147, 0.33, 0.474, 0.8])
    ax.set_xticklabels(['−0.47', '−0.33', '−0.15', '0', '0.15', '0.33', '0.47', '0.80'], fontsize=9)
    ax.set_xlabel("Cliff's delta   (negative = non-PT higher   ·   positive = PT higher)",
                  color=INK2, fontsize=10, labelpad=8)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)

    ax.set_title('The gap comes from helpers — and duplication flips sign between levels',
                 color=INK, fontsize=12, fontweight='bold', loc='left', pad=30)
    ax.text(0, 1.052, '46 Apache projects · one dot per project (area ∝ test count) · '
                      'black bar = median · grey = not significant',
            transform=ax.transAxes, fontsize=8.8, color=INK2)

    handles = [Line2D([], [], marker='o', linestyle='none', markersize=8, color=PT_COLOR,
                      alpha=0.65, label='PT higher (p < 0.05)'),
               Line2D([], [], marker='o', linestyle='none', markersize=8, color=NONPT_COLOR,
                      alpha=0.65, label='non-PT higher (p < 0.05)'),
               Line2D([], [], marker='o', linestyle='none', markersize=8, color=NS_COLOR,
                      alpha=0.65, label='not significant')]
    ax.legend(handles=handles, frameon=False, fontsize=8.8, ncol=3, loc='lower left',
              bbox_to_anchor=(0.0, -0.175), labelcolor=INK2, handletextpad=0.3, columnspacing=1.3)

    fig.subplots_adjust(left=0.175, right=0.815, top=0.845, bottom=0.145)
    for ext in ('png', 'pdf'):
        fig.savefig(f'{OUT}.{ext}', metadata={'CreationDate': None} if ext == 'pdf' else None, dpi=200, facecolor=SURFACE)
    print(f'wrote {OUT}.png / .pdf')


if __name__ == '__main__':
    main()
