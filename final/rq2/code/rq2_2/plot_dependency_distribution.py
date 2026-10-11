#!/usr/bin/env python3
"""RQ2.2 dependency 分布：全部 parameter source 并排，每行一条 100% 堆叠条。

设计要点：

1. **L0–L4 是有序的**（离测试类由近及远），所以用单一蓝色的序数色阶 light→dark，
   而不是分类配色 —— 读者能从颜色深浅直接读出「依赖走得多远」。
   色阶通过 dataviz 校验脚本的 --ordinal 全部检查（单色相、亮度单调、相邻 ΔL ≥ 0.06、
   最浅步对画布 2.06:1）。

2. **三个不属于 L 体系的类别单独处理**：EnumSource 的 Production（枚举常量直接来自
   production code）/ External（JDK 或第三方枚举），CsvFileSource 的 File（数据在外部资源文件里）。
   它们与 L0–L4 不是同一个量纲，所以用对比色相（橙/紫/青）区分 —— 色系本身就说明了
   「这些不在那条远近轴上」，图例也分了两组。早先试过在 L4 后留空隙，但那读起来像条形断了，已去掉。

3. 每条仍是该 source 的 **100%**（分母是它自己的 OK 行数），所以额外类别不会让百分比失真。

输出 full/dependency_distribution.{png,pdf}
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ2_2_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = [('MethodSource',                  'rq22_methodsource_all.csv'),
       ('ValueSource',                   'rq22_valuesource_all.csv'),
       ('EnumSource',                    'rq22_enumsource_all.csv'),
       ('CsvSource',                     'rq22_csvsource_all.csv'),
       ('CsvFileSource',                 'rq22_csvfilesource_all.csv'),
       ('ArgumentsSource / FieldSource', 'rq22_argumentssource_fieldsource_all.csv')]

LEVELS = ['L0', 'L1', 'L2', 'L3', 'L4']
EXTRAS = ['Production', 'External', 'File']
# 序数蓝阶（--ordinal 全部 PASS）
LCOLORS = {'L0': '#86b6ef', 'L1': '#5598e7', 'L2': '#2a78d6', 'L3': '#1c5cab', 'L4': '#0d366b'}
# 非 L 体系的类别：对比色相（categorical 校验全部 PASS，最差相邻常视 ΔE 35.8）
ECOLORS = {'Production': '#eb6834', 'External': '#4a3aa7', 'File': '#1baf7a'}
LNAME = {'L0': 'L0 Source Local', 'L1': 'L1 Enclosing-Class', 'L2': 'L2 Inheritance',
         'L3': 'L3 Package', 'L4': 'L4 Cross-Package'}
ENAME = {'Production': 'Production code', 'External': 'JDK / third-party', 'File': 'External data file'}

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#dcdbd7'


def load(path):
    rows = list(csv.DictReader(open(os.path.join(RESULTS_DIR, path))))
    ok = [r for r in rows if (r.get('status') or 'OK') == 'OK']
    counts = {}
    for r in ok:
        d = r.get('dependency', '')
        if d:
            counts[d] = counts.get(d, 0) + 1
    return counts, len(ok), len(rows)


def main():
    data = [(name,) + load(p) for name, p in SRC]
    data.reverse()                                  # 从上往下按 SRC 顺序排

    fig, ax = plt.subplots(figsize=(11, 5.0))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)

    yticks, ylabels = [], []
    for i, (name, counts, n_ok, n_all) in enumerate(data):
        yticks.append(i)
        ylabels.append(f'{name}\n(n={n_ok:,})')
        x = 0.0
        # L0–L4
        for lv in LEVELS:
            c = counts.get(lv, 0)
            if not c:
                continue
            w = c / n_ok
            ax.barh(i, w, left=x, height=0.62, color=LCOLORS[lv],
                    edgecolor=SURFACE, linewidth=1.2, zorder=3)
            if w >= 0.055:                           # 窄段不标，避免叠字
                ax.text(x + w / 2, i, f'{w*100:.0f}%', ha='center', va='center',
                        fontsize=8.5, color='white' if lv in ('L2', 'L3', 'L4') else INK,
                        fontweight='bold', zorder=4)
            x += w
        # 额外类别：留一道空隙再画
        extra_present = [e for e in EXTRAS if counts.get(e)]
        for e in extra_present:
            w = counts[e] / n_ok
            ax.barh(i, w, left=x, height=0.62, color=ECOLORS[e],
                edgecolor=SURFACE, linewidth=1.2, zorder=3)
            if w >= 0.055:
                ax.text(x + w / 2, i, f'{w*100:.0f}%', ha='center', va='center',
                    fontsize=8.5, color='white' if e == 'External' else INK,
                    fontweight='bold', zorder=4)
            x += w

    ax.set_yticks(yticks); ax.set_yticklabels(ylabels, fontsize=9.5)
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, .25, .5, .75, 1.0])
    ax.set_xticklabels(['0', '25%', '50%', '75%', '100%'], fontsize=9)
    ax.set_xlabel('Share of parameterized tests within each source', color=INK2, fontsize=10, labelpad=8)
    ax.xaxis.grid(True, color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)

    ax.set_title('Most parameter sources stay local; MethodSource is the one that reaches out',
                 color=INK, fontsize=12.5, fontweight='bold', loc='left', pad=34)
    ax.text(0, 1.115, 'Dependency level of the code that builds the parameters: '
                      'L0 (inside the test class) → L4 (another package).',
            transform=ax.transAxes, fontsize=9, color=INK2)
    ax.text(0, 1.055, 'Categories that do not sit on that scale are shown in contrasting hues (see second legend row).',
            transform=ax.transAxes, fontsize=9, color=INK2)

    # 两个独立图例：有序的 L 级别一行，不在该尺度上的类别另一行
    h1 = [Patch(facecolor=LCOLORS[l], label=LNAME[l]) for l in LEVELS]
    h2 = [Patch(facecolor=ECOLORS[e], label=ENAME[e]) for e in EXTRAS]
    leg1 = ax.legend(handles=h1, frameon=False, fontsize=8.6, ncol=5, loc='upper left',
                     bbox_to_anchor=(0.0, -0.20), labelcolor=INK2,
                     handlelength=1.0, handleheight=1.0, columnspacing=1.4,
                     title='Distance from the test class', title_fontsize=8.6)
    leg1.get_title().set_color(INK); leg1.get_title().set_ha('left')
    ax.add_artist(leg1)
    leg2 = ax.legend(handles=h2, frameon=False, fontsize=8.6, ncol=3, loc='upper left',
                     bbox_to_anchor=(0.0, -0.44), labelcolor=INK2,
                     handlelength=1.0, handleheight=1.0, columnspacing=1.4,
                     title='Outside that scale', title_fontsize=8.6)
    leg2.get_title().set_color(INK); leg2.get_title().set_ha('left')
    ax.add_artist(leg2)

    fig.subplots_adjust(left=0.215, right=0.985, top=0.775, bottom=0.355)
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(RESULTS_DIR, f'dependency_distribution.{ext}'), dpi=200, facecolor=SURFACE,
                    metadata={'CreationDate': None} if ext == 'pdf' else None)
    print('wrote dependency_distribution.png / .pdf')

    with open(os.path.join(RESULTS_DIR, 'dependency_distribution.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['source', 'n_ok', 'n_all'] + LEVELS + EXTRAS)
        for name, counts, n_ok, n_all in reversed(data):
            w.writerow([name, n_ok, n_all] + [counts.get(k, 0) for k in LEVELS + EXTRAS])
    print('wrote dependency_distribution.csv')


if __name__ == '__main__':
    main()
