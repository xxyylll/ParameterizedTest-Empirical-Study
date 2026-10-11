#!/usr/bin/env python3
"""
RQ3.2 figures, in the same visual language as the RQ3.1 heatmaps
(heatmap_unified_44projects.py): 9-bin diverging red/blue scale keyed to the
negligible/small/medium/large Cliff's delta bands, *** = significant.

  rq32_construction_heatmap.png  Cliff's delta, Dynamic vs Literal, shown both
                                 for the full sample and within the L0 stratum
                                 (dependency held fixed)
  rq32_dependency_heatmap.png    Cliff's delta for all 10 dependency-level
                                 pairs (*** = Holm-adjusted p < 0.05)
  rq32_construction_boxplots.png distributions per metric, Literal vs Dynamic
  rq32_dependency_boxplots.png   distributions per metric, L0 .. L4
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'methodsource')
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import argparse
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
PREFIX = 'rq32'   # set from argv in main()
DEP_LEVELS = ['L0', 'L1', 'L2', 'L3', 'L4']

# Row order: scope block x metric, matching the RQ3.1 heatmap layout.
ROWS = [(scope, metric) for scope in ('main-body', 'helper', 'total')
        for metric in ('LOC', 'CC', 'CCTR', 'DUP%')]
ROW_LABELS = [f'{m} ({s})' for s, m in ROWS]

BOUNDS = [-1.0001, -0.474, -0.33, -0.147, -1e-9, 1e-9, 0.147, 0.33, 0.474, 1.0001]
# A cell is starred only when it is BOTH statistically significant AND at least
# a 'small' effect. With n>5k virtually every comparison reaches p<0.05, so
# significance alone stops discriminating; the magnitude gate keeps the marker
# meaningful and the rule identical across the sample and full-population runs.
SIG_P = 0.05
SIG_DELTA = 0.147


def starred(delta, p):
    return p < SIG_P and abs(delta) >= SIG_DELTA
COLORS = ['#1c4d8c', '#3f7cb8', '#8fb3d9', '#d6e4f2', '#ffffff',
          '#fbe0d2', '#eba184', '#cf5a3d', '#a3221b']
CMAP = ListedColormap(COLORS)
NORM = BoundaryNorm(BOUNDS, CMAP.N)

COUNT_METRICS = {'LOC', 'CC', 'CCTR'}


def read(name):
    return list(csv.DictReader(open(os.path.join(RESULTS_DIR, f'{PREFIX}_{name}'), newline='', encoding='utf-8')))


def style_heatmap(ax, grid, col_labels, stars, title, legend_high, legend_low):
    ax.imshow(grid, cmap=CMAP, norm=NORM, aspect='auto')
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=20, ha='right', fontsize=10)
    ax.set_yticks(range(len(ROW_LABELS)))
    ax.set_yticklabels(ROW_LABELS, fontsize=10)
    for i in range(len(ROWS)):
        for j in range(len(col_labels)):
            if stars[i][j]:
                ax.text(j, i, '***', ha='center', va='center',
                        fontsize=11, fontweight='bold', color='black')
    ax.set_xticks([x - 0.5 for x in range(1, len(col_labels))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(ROWS))], minor=True)
    ax.grid(which='minor', color='white', linewidth=2)
    ax.tick_params(which='minor', length=0)
    # thicker separators between the three scope blocks
    for y in (3.5, 7.5):
        ax.axhline(y, color='#444444', linewidth=1.6)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, fontsize=12.5, fontweight='bold', pad=12)
    labels = [f'Large {legend_high} (>0.474)', f'Medium {legend_high}', f'Small {legend_high}',
              f'Negligible {legend_high}', 'Equal',
              f'Negligible {legend_low}', f'Small {legend_low}', f'Medium {legend_low}',
              f'Large {legend_low} (<-0.474)']
    handles = [Patch(facecolor=c, edgecolor='#888888', linewidth=0.5, label=l)
               for c, l in zip(reversed(COLORS), labels)]
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.02, 1.0),
              fontsize=9, frameon=True, framealpha=0.95, borderaxespad=0)


def construction_heatmap():
    rows = {(r['scope'], r['metric']): r for r in read('construction_stats.csv')}
    pop = {r['group']: r['n'] for r in csv.DictReader(
        open(os.path.join(RESULTS_DIR, f'{PREFIX}_population.csv'), newline='', encoding='utf-8'))}
    cols = [('cliffs_delta', 'p_raw',
             f'All MethodSource tests\n(n={pop["construction_Dynamic"]} Dynamic / '
             f'{pop["construction_Literal"]} Literal)'),
            ('L0_only_cliffs_delta', 'L0_only_p_raw',
             f'L0 only\n(n={pop["L0_Dynamic"]} Dynamic / {pop["L0_Literal"]} Literal)')]
    grid, stars = [], []
    for key in ROWS:
        r = rows[key]
        grid.append([float(r[dc]) for dc, _, _ in cols])
        stars.append([starred(float(r[dc]), float(r[pc])) for dc, pc, _ in cols])
    fig, ax = plt.subplots(figsize=(7.6, 6.4))
    style_heatmap(ax, grid, [c[2] for c in cols], stars,
                  "RQ3.2 Construction: Dynamic vs Literal MethodSource\n"
                  "(Red = Dynamic higher, Blue = Literal higher, *** = p<0.05 and at least small)",
                  'Dynamic', 'Literal')
    out = os.path.join(RESULTS_DIR, f'{PREFIX}_construction_heatmap.png')
    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote', os.path.basename(out))


def dependency_heatmap():
    data = defaultdict_rows(read('dependency_pairwise.csv'))
    comparisons = [f'{b} vs {a}' for i, a in enumerate(DEP_LEVELS) for b in DEP_LEVELS[i + 1:]]
    grid, stars = [], []
    for key in ROWS:
        grid.append([float(data[(key[0], key[1], c)]['cliffs_delta']) for c in comparisons])
        stars.append([starred(float(data[(key[0], key[1], c)]['cliffs_delta']),
                              float(data[(key[0], key[1], c)]['p_holm'])) for c in comparisons])
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    style_heatmap(ax, grid, comparisons, stars,
                  "RQ3.2 Dependency level: pairwise comparisons (L0 = no dependency)\n"
                  "(Red = higher level more complex, *** = Holm p<0.05 and at least small)",
                  'higher level', 'lower level')
    out = os.path.join(RESULTS_DIR, f'{PREFIX}_dependency_heatmap.png')
    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote', os.path.basename(out))


def defaultdict_rows(rows):
    return {(r['scope'], r['metric'], r['comparison']): r for r in rows}


COLUMN_OF = {
    ('main-body', 'LOC'): 'self_loc', ('helper', 'LOC'): 'helper_loc_sum', ('total', 'LOC'): 'total_loc',
    ('main-body', 'CC'): 'self_cc', ('helper', 'CC'): 'helper_cc_sum', ('total', 'CC'): 'total_cc',
    ('main-body', 'CCTR'): 'self_cctr', ('helper', 'CCTR'): 'helper_cctr_sum', ('total', 'CCTR'): 'total_cctr',
    ('main-body', 'DUP%'): 'self_dupPerc', ('helper', 'DUP%'): 'helper_dupPerc', ('total', 'DUP%'): 'total_dupPerc',
}


def boxplots(group_col, group_values, group_colors, title, outname, data_filter=None):
    rows = read('methodsource_metrics.csv')
    if rows and 'dependency_status' in rows[0]:
        rows = [r for r in rows if r['dependency_status'].startswith('OK')]
    if data_filter:
        rows = [r for r in rows if data_filter(r)]
    fig, axes = plt.subplots(3, 4, figsize=(15, 9.5))
    for idx, (scope, metric) in enumerate(ROWS):
        ax = axes[idx // 4][idx % 4]
        col = COLUMN_OF[(scope, metric)]
        series, labels = [], []
        for gv in group_values:
            vals = [float(r[col]) for r in rows if r[group_col] == gv and r[col] != '']
            series.append(vals)
            labels.append(f'{gv}\nn={len(vals)}')
        bp = ax.boxplot(series, tick_labels=labels, patch_artist=True, showfliers=False,
                        medianprops=dict(color='black', linewidth=1.6),
                        widths=0.6)
        for patch, c in zip(bp['boxes'], group_colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.85)
            patch.set_edgecolor('#444444')
        if metric in COUNT_METRICS:
            ax.set_yscale('symlog')
        ax.set_title(f'{metric} ({scope})', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', labelsize=8.5)
        ax.tick_params(axis='y', labelsize=8.5)
        ax.grid(axis='y', alpha=0.3, linewidth=0.6)
        ax.set_axisbelow(True)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
    fig.suptitle(title, fontsize=13.5, fontweight='bold', y=0.995)
    fig.text(0.5, 0.005, 'LOC / CC / CCTR on symlog scale (right-skewed counts); '
                          'DUP% is a 0-1 line ratio. Outliers hidden for readability.',
             ha='center', fontsize=9, style='italic', color='#444444')
    plt.tight_layout(rect=[0, 0.02, 1, 0.985])
    out = os.path.join(RESULTS_DIR, f'{PREFIX}_{outname}')
    plt.savefig(out, dpi=150, facecolor='white')
    plt.close(fig)
    print('wrote', f'{PREFIX}_{outname}')


def main():
    global PREFIX
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix', default='rq32')
    PREFIX = ap.parse_args().prefix
    construction_heatmap()
    dependency_heatmap()
    boxplots('construction', ['Literal', 'Dynamic'], ['#8fb3d9', '#eba184'],
             'RQ3.2 Construction: complexity profile of Literal vs Dynamic MethodSource',
             'construction_boxplots.png',
             data_filter=lambda r: r['construction'] in ('Literal', 'Dynamic'))
    boxplots('dependency', DEP_LEVELS,
             ['#d6e4f2', '#fbe0d2', '#eba184', '#cf5a3d', '#a3221b'],
             'RQ3.2 Dependency level: complexity profile across L0 - L4',
             'dependency_boxplots.png',
             data_filter=lambda r: r['dependency'] in DEP_LEVELS)


if __name__ == '__main__':
    main()
