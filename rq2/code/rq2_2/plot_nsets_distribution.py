#!/usr/bin/env python3
"""所有 parameter source 合并的 n_sets（参数组数）分布。

只纳入组数已精确确定的 PT（n_sets_status 为 EXACT，或该 source 本就没有状态列）。

两个面板共用同一组分箱，右端隔开一格放 RUNTIME_DEPENDENT（组数必须运行才知道）：
  A 堆叠计数 —— 整体形态 + 各 source 的贡献。
  B 组内占比折线 —— 各 source 的分布形态。必须有 B：source 之间样本量差 100 倍
    （MethodSource 4450 vs CsvFileSource 48），只看 A 的话小 source 完全不可见，
    而 CsvFileSource 恰恰是形态最特别的一个（中位数 488）。

为什么只画 RUNTIME_DEPENDENT、不画另外三类失败：runtime-dependent 是**测试本身的性质**
（参数来自文件 / 环境 / 运行期状态），值得被看到；STATIC_UNSUPPORTED / UNRESOLVED_SOURCE /
上游失败共 167 条是**分析器的局限**，画进去会让读者误以为也是测试的特征，故只在副标题里交代数量。

配色取 dataviz 参考调色板的分类槽位 1–6，固定顺序（相邻对的 CVD / 常视分离度是按此顺序验过的，
明暗两套均 PASS）。浅色槽位对比度不足 3:1，故每根柱标出总数并附 nsets_summary.csv 作为 table view。

输出 full/nsets_distribution.{png,pdf} 和 full/nsets_summary.csv
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ2_2_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv, os, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = [('MethodSource',                  'rq22_methodsource_all.csv',                      'n_sets_status'),
       ('ValueSource',                   'rq22_valuesource_all.csv',           None),
       ('EnumSource',                    'rq22_enumsource_all.csv',             'n_sets_status'),
       ('CsvSource',                     'rq22_csvsource_all.csv',               None),
       ('CsvFileSource',                 'rq22_csvfilesource_all.csv',       'n_sets_status'),
       ('ArgumentsSource / FieldSource', 'rq22_argumentssource_fieldsource_all.csv', 'n_sets_status')]
BINS = [(1,1,'1'), (2,2,'2'), (3,4,'3–4'), (5,8,'5–8'), (9,16,'9–16'), (17,32,'17–32'),
        (33,64,'33–64'), (65,128,'65–128'), (129,256,'129–256'), (257,512,'257–512'), (513,10**9,'≥513')]
COLORS  = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300']
SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#dcdbd7'


def load(path, status_col):
    """返回 (可精确计数的 n_sets 列表, runtime-dependent 条数, 因分析器局限被排除的条数)。"""
    vals, runtime, excluded = [], 0, 0
    for x in csv.DictReader(open(os.path.join(RESULTS_DIR, path))):
        st = (x.get(status_col) or '') if status_col else ''
        if st == 'RUNTIME_DEPENDENT':
            runtime += 1
            continue
        if st not in ('', 'EXACT'):
            excluded += 1
            continue
        v = x.get('n_sets', '')
        if v in ('', '-1'):
            excluded += 1
            continue
        try:
            vals.append(int(v))
        except ValueError:
            excluded += 1
    return vals, runtime, excluded


rows_of = {n: sum(1 for _ in csv.DictReader(open(os.path.join(RESULTS_DIR, p)))) for n, p, _ in SRC}
loaded = [(n,) + load(p, st) for n, p, st in SRC]
data = [(n, vs) for n, vs, _, _ in loaded]
runtime_of = {n: rt for n, _, rt, _ in loaded}
allv = [v for _, vs in data for v in vs]
n_runtime = sum(runtime_of.values())
n_excluded = sum(ex for _, _, _, ex in loaded)
x = list(range(len(BINS)))
X_NA = len(BINS) + 0.7            # runtime-dependent 单独放右端，与分箱轴隔开
DIVIDER = len(BINS) - 0.15

fig, (axA, axB) = plt.subplots(2, 1, figsize=(10.5, 7.8), sharex=True,
                               gridspec_kw={'height_ratios': [1.35, 1], 'hspace': 0.16})
fig.patch.set_facecolor(SURFACE)

# ---- A: 堆叠计数 ----
axA.set_facecolor(SURFACE)
bottom = [0] * len(BINS)
for (name, vals), c in zip(data, COLORS):
    counts = [sum(1 for v in vals if lo <= v <= hi) for lo, hi, _ in BINS]
    axA.bar(x, counts, bottom=bottom, width=0.74, label=name, color=c,
            edgecolor=SURFACE, linewidth=1.0, zorder=3)   # 画布色描边 = 段间留缝
    bottom = [b + c2 for b, c2 in zip(bottom, counts)]
na_bottom = 0
for (name, vals), c in zip(data, COLORS):
    h = runtime_of[name]
    if h:
        axA.bar([X_NA], [h], bottom=[na_bottom], width=0.74, color=c,
                edgecolor=SURFACE, linewidth=1.0, zorder=3)
        na_bottom += h
for xi, tot in list(zip(x, bottom)) + [(X_NA, na_bottom)]:
    if tot:
        axA.text(xi, tot + max(bottom) * 0.02, f'{int(tot):,}', ha='center', va='bottom',
                 fontsize=8.5, color=INK2, zorder=4)
axA.axvline(DIVIDER, color=GRID, linewidth=1.0, zorder=1)
axA.set_ylim(0, max(bottom) * 1.16)
axA.set_xlim(-0.7, X_NA + 0.7)
axA.set_ylabel('Parameterized tests', color=INK2, fontsize=10, labelpad=8)
axA.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v):,}'))
axA.text(0.004, 0.94, 'A  Overall distribution (stacked counts)', transform=axA.transAxes,
         fontsize=10, color=INK, fontweight='bold')

# ---- B: 组内占比折线 ----
axB.set_facecolor(SURFACE)
for (name, vals), c in zip(data, COLORS):
    denom = len(vals) + runtime_of[name]          # 分母含 runtime-dependent，故各序列仍合计 100%
    share = [100 * sum(1 for v in vals if lo <= v <= hi) / denom for lo, hi, _ in BINS]
    axB.plot(x, share, color=c, linewidth=2.0, marker='o', markersize=4.5,
             markeredgecolor=SURFACE, markeredgewidth=1.2, label=name, zorder=3)
    axB.plot([X_NA], [100 * runtime_of[name] / denom], color=c, marker='o', markersize=5.5,
             markeredgecolor=SURFACE, markeredgewidth=1.2, linestyle='none', zorder=3)
axB.axvline(DIVIDER, color=GRID, linewidth=1.0, zorder=1)
axB.set_ylim(0, 72)
axB.set_xlim(-0.7, X_NA + 0.7)
axB.set_ylabel('Share within source (%)', color=INK2, fontsize=10, labelpad=8)
axB.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v)}%'))
axB.text(0.004, 0.94, 'B  Shape per source (each series sums to 100%)', transform=axB.transAxes,
         fontsize=10, color=INK, fontweight='bold')
axB.set_xlabel('Number of parameter sets per parameterized test', color=INK2, fontsize=10, labelpad=8)

for ax in (axA, axB):
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, length=0, labelsize=9)
axB.set_xticks(x + [X_NA])
axB.set_xticklabels([b[2] for b in BINS] + ['runtime-\ndependent'])
for lab in axB.get_xticklabels()[-1:]:
    lab.set_fontstyle('italic')

med, p90 = statistics.median(allv), sorted(allv)[int(len(allv) * .9)]
le4 = 100 * sum(1 for v in allv if v <= 4) / len(allv)
fig.suptitle('Parameter-set counts are small and heavily right-skewed',
             x=0.008, y=0.985, ha='left', color=INK, fontsize=13.5, fontweight='bold')
fig.text(0.008, 0.948,
         f'{len(allv):,} tests with a statically determined set count  ·  median {med:.0f}  ·  p90 {p90}  ·  '
         f'max {max(allv):,}  ·  {le4:.0f}% have ≤ 4 sets',
         ha='left', fontsize=9.5, color=INK2)
fig.text(0.008, 0.913,
         f'{n_runtime:,} further tests build their parameters at run time, so no static count exists  '
         f'(a property of those tests, shown at right)  ·  {n_excluded} excluded for analyzer limitations',
         ha='left', fontsize=9.5, color=INK2)
handles, labels = axA.get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=9, ncol=6, loc='upper left',
           bbox_to_anchor=(0.008, 0.885), labelcolor=INK2, handlelength=1.0,
           handleheight=1.0, columnspacing=1.4, handletextpad=0.5)

fig.subplots_adjust(top=0.825, bottom=0.095, left=0.075, right=0.985)
for ext in ('png', 'pdf'):
    fig.savefig(os.path.join(RESULTS_DIR, f'nsets_distribution.{ext}'), dpi=200, facecolor=SURFACE,
                    metadata={'CreationDate': None} if ext == 'pdf' else None)
print('wrote nsets_distribution.png / .pdf')

with open(os.path.join(RESULTS_DIR, 'nsets_summary.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['source', 'rows', 'usable', 'median', 'mean', 'p90', 'max'])
    for name, vals in data:
        w.writerow([name, rows_of[name], len(vals), statistics.median(vals),
                    round(statistics.mean(vals), 1), sorted(vals)[int(len(vals) * .9)], max(vals)])
    w.writerow(['ALL', sum(rows_of.values()), len(allv), med, round(statistics.mean(allv), 1), p90, max(allv)])
print('wrote nsets_summary.csv')
