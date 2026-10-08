#!/usr/bin/env python3
"""RQ2.2 construction 分布：全部 parameter source 并排，每行一条 100% 堆叠条。

与 plot_dependency_distribution.py 同一形式，便于两张图对照。

设计要点：

1. **Construction 本质是二分的**（Literal / Dynamic），Literal 一侧按粒度再分。
   所以 Literal 家族用单色蓝的序数阶（由浅到深），
   Dynamic 用对比色橙 —— 「蓝 = 编译期就定了，橙 = 要执行才知道」一眼可读。
   注意 MethodSource / ArgumentsSource / FieldSource 的分类器不细分 Literal 子类，
   所以它们只有笼统的 `Literal`；ValueSource / CsvSource 则细分到 Primitive / Metadata。
   （CsvSource 早先还有一类 Literal-Converted —— CSV 文本经 String 工厂或 @ConvertWith 转成项目类型 ——
   现已并入 Literal-Primitive：注解里写的仍是字面量，转换由 JUnit 注入时完成。
   细分信息保留在 param_kinds 列的 converted: 前缀。）

2. **CsvFileSource 的 `File`** 用对比色相区分（不留空隙 —— 空隙会让条形看起来是断的）：
   参数在外部资源文件里，既非字面量也非代码生成。

3. **EnumSource 根本没有 construction 维度** —— 枚举常量是声明的，不是构造的，
   literal↔dynamic 这条轴对它不适用。整条画成中性灰并直接写 N/A。
   早先试过在同一根条上放它的 `enum_structure`，但那是在一张图里混了两个不同的变量，
   读者会以为 data-carrying / label-based 和 Literal / Dynamic 是同一个量纲 —— 已去掉。

4. 其余每条仍是该 source 的 **100%**（分母为它自己的 OK 行数）。

输出 full/construction_distribution.{png,pdf} 和 .csv
"""
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = [('MethodSource',                  'rq22_methodsource_all.csv',                      'construction'),
       ('ValueSource',                   'rq22_valuesource_all.csv',           'construction'),
       ('EnumSource',                    'rq22_enumsource_all.csv',             None),
       ('CsvSource',                     'rq22_csvsource_all.csv',               'construction'),
       ('CsvFileSource',                 'rq22_csvfilesource_all.csv',       'construction'),
       ('ArgumentsSource / FieldSource', 'rq22_argumentssource_fieldsource_all.csv', 'construction')]

MAIN = ['Literal-Primitive', 'Literal-Metadata', 'Literal', 'Dynamic']
EXTRAS = ['File']
MCOLORS = {'Literal-Primitive': '#86b6ef', 'Literal-Metadata': '#2a78d6',
           'Literal': '#1c5cab', 'Dynamic': '#eb6834'}
ECOLORS = {'File': '#1baf7a'}
NA_COLOR = '#c9c7c1'          # 中性灰：该轴对它不适用，不是一个取值
MNAME = {'Literal-Primitive': 'Literal — primitive', 'Literal-Metadata': 'Literal — metadata',
         'Literal': 'Literal (not sub-divided)', 'Dynamic': 'Dynamic (needs execution)'}
ENAME = {'File': 'External data file'}
WHITE_LABEL = {'Literal-Metadata', 'Literal', 'Dynamic'}

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#dcdbd7'


def enum_analysable(rows):
    """EnumSource 进入分母的口径。

    三个条件（与分析表里一致）：n_sets 能算出来、enum_structure 不是 n/a、
    且枚举不是 External（JDK / 第三方）—— External 的枚举声明不在项目里，
    它的表示方式与利用方式都无从刻画，不该进分母。
    得 814（Production 432 + L3 247 + L1 120 + L4 13 + L2 2）。
    """
    return [r for r in rows
            if (r.get('n_sets') or '').strip()
            and (r.get('enum_structure') or '').strip() != 'n/a'
            and (r.get('dependency') or '').strip() != 'External']


def load(path, col):
    """col 为 None 表示该 source 没有 construction 维度，整条按 N/A 处理。"""
    rows = list(csv.DictReader(open(os.path.join(HERE, path))))
    ok = [r for r in rows if (r.get('status') or 'OK') == 'OK']
    if col is None:                                   # EnumSource
        return None, len(enum_analysable(rows)), len(rows)
    counts = {}
    for r in ok:
        v = (r.get(col) or '').strip()
        if v and v != 'n/a':
            counts[v] = counts.get(v, 0) + 1
    return counts, sum(counts.values()), len(rows)


def main():
    data = [(name,) + load(p, col) for name, p, col in SRC]
    data.reverse()

    fig, ax = plt.subplots(figsize=(11, 5.0))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)

    yticks, ylabels = [], []
    for i, (name, counts, n, n_all) in enumerate(data):
        yticks.append(i)
        ylabels.append(f'{name}\n(n={n:,})')
        if counts is None:                       # 该轴不适用：整条中性灰
            ax.barh(i, 1.0, height=0.62, color=NA_COLOR,
                    edgecolor=SURFACE, linewidth=1.2, zorder=3)
            ax.text(0.5, i, 'N/A — construction not applicable', ha='center', va='center',
                    fontsize=8.5, color=INK2, fontweight='bold', zorder=4)
            continue
        x = 0.0
        for k in MAIN:
            c = counts.get(k, 0)
            if not c:
                continue
            w = c / n
            ax.barh(i, w, left=x, height=0.62, color=MCOLORS[k],
                    edgecolor=SURFACE, linewidth=1.2, zorder=3)
            if w >= 0.055:
                ax.text(x + w / 2, i, f'{w*100:.0f}%', ha='center', va='center', fontsize=8.5,
                        color='white' if k in WHITE_LABEL else INK, fontweight='bold', zorder=4)
            x += w
        present = [e for e in EXTRAS if counts.get(e)]
        for e in present:
            w = counts[e] / n
            ax.barh(i, w, left=x, height=0.62, color=ECOLORS[e],
                edgecolor=SURFACE, linewidth=1.2, zorder=3)
            if w >= 0.055:
                ax.text(x + w / 2, i, f'{w*100:.0f}%', ha='center', va='center', fontsize=8.5,
                    color='white' if e in WHITE_LABEL else INK, fontweight='bold', zorder=4)
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

    ax.set_title('Only MethodSource builds its parameters by running code',
                 color=INK, fontsize=12.5, fontweight='bold', loc='left', pad=34)
    ax.text(0, 1.115, 'Blue = the parameter values are fixed at compile time;  '
                      'orange = producing them requires executing logic.',
            transform=ax.transAxes, fontsize=9, color=INK2)
    ax.text(0, 1.055, 'EnumSource has no construction dimension at all — its constants are declared, not built.',
            transform=ax.transAxes, fontsize=9, color=INK2)

    h1 = [Patch(facecolor=MCOLORS[k], label=MNAME[k]) for k in MAIN]
    h2 = [Patch(facecolor=ECOLORS[e], label=ENAME[e]) for e in EXTRAS]
    h2.append(Patch(facecolor=NA_COLOR, label='Axis does not apply'))
    leg1 = ax.legend(handles=h1, frameon=False, fontsize=8.6, ncol=4, loc='upper left',
                     bbox_to_anchor=(0.0, -0.20), labelcolor=INK2,
                     handlelength=1.0, handleheight=1.0, columnspacing=1.4,
                     title='How the parameter values come about', title_fontsize=8.6)
    leg1.get_title().set_color(INK); leg1.get_title().set_ha('left')
    ax.add_artist(leg1)
    leg2 = ax.legend(handles=h2, frameon=False, fontsize=8.6, ncol=3, loc='upper left',
                     bbox_to_anchor=(0.0, -0.44), labelcolor=INK2,
                     handlelength=1.0, handleheight=1.0, columnspacing=1.4,
                     title='Outside that axis', title_fontsize=8.6)
    leg2.get_title().set_color(INK); leg2.get_title().set_ha('left')
    ax.add_artist(leg2)

    fig.subplots_adjust(left=0.215, right=0.985, top=0.775, bottom=0.355)
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(HERE, f'construction_distribution.{ext}'), dpi=200, facecolor=SURFACE)
    print('wrote construction_distribution.png / .pdf')

    with open(os.path.join(HERE, 'construction_distribution.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['source', 'n', 'n_all'] + MAIN + EXTRAS)
        for name, counts, n, n_all in reversed(data):
            w.writerow([name, n, n_all] + ['n/a' if counts is None else counts.get(k, 0)
                                           for k in MAIN + EXTRAS])
    print('wrote construction_distribution.csv')


if __name__ == '__main__':
    main()
