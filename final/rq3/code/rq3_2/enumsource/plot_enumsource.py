#!/usr/bin/env python3
"""
EnumSource figures, in the RQ3.x visual language.

  enumsource_structure_heatmap.png   Data-carrying vs Label-based, overall and
                                     within each enum_location stratum
  enumsource_dimensions_heatmap.png  all three design dimensions side by side.
                                     A cell is starred only when it is
                                     significant, at least a small effect, AND
                                     sign-stable under leave-one-project-out --
                                     EnumSource usage is concentrated enough
                                     (jena = 64% of test-located enums) that
                                     the third condition matters.
  enumsource_boxplots.png            distributions by enum_structure
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'enumsource')
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [(s, m) for s in ('main-body', 'helper', 'total') for m in ('LOC', 'CC', 'CCTR', 'DUP%')]
ROW_LABELS = [f'{m} ({s})' for s, m in ROWS]

BOUNDS = [-1.0001, -0.474, -0.33, -0.147, -1e-9, 1e-9, 0.147, 0.33, 0.474, 1.0001]
COLORS = ['#1c4d8c', '#3f7cb8', '#8fb3d9', '#d6e4f2', '#ffffff',
          '#fbe0d2', '#eba184', '#cf5a3d', '#a3221b']
CMAP = ListedColormap(COLORS)
NORM = BoundaryNorm(BOUNDS, CMAP.N)
SIG_P, SIG_DELTA = 0.05, 0.147

COLUMN_OF = {
    ('main-body', 'LOC'): 'self_loc', ('helper', 'LOC'): 'helper_loc_sum', ('total', 'LOC'): 'total_loc',
    ('main-body', 'CC'): 'self_cc', ('helper', 'CC'): 'helper_cc_sum', ('total', 'CC'): 'total_cc',
    ('main-body', 'CCTR'): 'self_cctr', ('helper', 'CCTR'): 'helper_cctr_sum', ('total', 'CCTR'): 'total_cctr',
    ('main-body', 'DUP%'): 'self_dupPerc', ('helper', 'DUP%'): 'helper_dupPerc', ('total', 'DUP%'): 'total_dupPerc',
}


def read(name):
    return list(csv.DictReader(open(os.path.join(RESULTS_DIR, name), newline='', encoding='utf-8')))


def draw(grid, stars, col_labels, title, high, low, outname, width, note=None):
    fig, ax = plt.subplots(figsize=(width, 6.6))
    ax.imshow(grid, cmap=CMAP, norm=NORM, aspect='auto')
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=18, ha='right', fontsize=9.5)
    ax.set_yticks(range(len(ROW_LABELS)))
    ax.set_yticklabels(ROW_LABELS, fontsize=10)
    for i in range(len(ROWS)):
        for j in range(len(col_labels)):
            if stars[i][j]:
                ax.text(j, i, '***', ha='center', va='center', fontsize=11,
                        fontweight='bold', color='black')
    ax.set_xticks([x - 0.5 for x in range(1, len(col_labels))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(ROWS))], minor=True)
    ax.grid(which='minor', color='white', linewidth=2)
    ax.tick_params(which='minor', length=0)
    for y in (3.5, 7.5):
        ax.axhline(y, color='#444444', linewidth=1.6)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=12)
    labels = [f'Large {high} (>0.474)', f'Medium {high}', f'Small {high}', f'Negligible {high}',
              'Equal', f'Negligible {low}', f'Small {low}', f'Medium {low}', f'Large {low} (<-0.474)']
    handles = [Patch(facecolor=c, edgecolor='#888888', linewidth=0.5, label=l)
               for c, l in zip(reversed(COLORS), labels)]
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.02, 1.0), fontsize=9,
              frameon=True, framealpha=0.95, borderaxespad=0)
    if note:
        fig.text(0.02, -0.02, note, fontsize=9, style='italic', color='#444444')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, outname), dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote', outname)


def structure_heatmap():
    two = read('enumsource_twogroup_stats.csv')
    idx = {(r['contrast'], r['stratum'], r['scope'], r['metric']): r for r in two}
    strata = [('all', 'All EnumSource tests'),
              ('location_group=production', 'Enum in production code'),
              ('location_group=test', 'Enum declared in test code')]
    cols, grid, stars = [], [], []
    for st, lbl in strata:
        r0 = idx[('structure', st, 'main-body', 'LOC')]
        cols.append(f"{lbl}\n(n={r0['n_a']} DC / {r0['n_b']} LB)")
    for key in ROWS:
        g, s = [], []
        for st, _ in strata:
            r = idx[('structure', st, key[0], key[1])]
            d, p = float(r['cliffs_delta']), float(r['p_raw'])
            g.append(d)
            s.append(p < SIG_P and abs(d) >= SIG_DELTA)
        grid.append(g)
        stars.append(s)
    draw(grid, stars, cols,
         "EnumSource: Data-carrying (DC) vs Label-based (LB) enums\n"
         "(Red = Data-carrying higher, Blue = Label-based higher,\n*** = p<0.05 and at least small)",
         'Data-carrying', 'Label-based', 'enumsource_structure_heatmap.png', 8.6)


def dimensions_heatmap():
    two = {(r['contrast'], r['stratum'], r['scope'], r['metric']): r
           for r in read('enumsource_twogroup_stats.csv')}
    loo = {(r['contrast'], r['scope'], r['metric']): r for r in read('enumsource_robustness_loo.csv')}
    dims = [('structure', 'Data-carrying vs Label-based', 'Data-carrying\nvs Label-based'),
            ('location', 'test vs production', 'Enum in test code\nvs in production'),
            ('names_mode', 'SUBSET vs ALL', 'names= subset\nvs all constants')]
    grid, stars = [], []
    for key in ROWS:
        g, s = [], []
        for contrast, loo_key, _ in dims:
            r = two[(contrast, 'all', key[0], key[1])]
            d, p = float(r['cliffs_delta']), float(r['p_raw'])
            lr = loo.get((loo_key, key[0], key[1]))
            stable = lr is not None and lr['sign_stable'] == 'yes'
            g.append(d)
            s.append(p < SIG_P and abs(d) >= SIG_DELTA and stable)
        grid.append(g)
        stars.append(s)
    draw(grid, stars, [d[2] for d in dims],
         "EnumSource design dimensions\n(Red = first-named group higher; *** = significant,\n"
         "at least small, AND sign-stable under leave-one-project-out)",
         'first group', 'second group', 'enumsource_dimensions_heatmap.png', 7.8,
         note='Unstarred coloured cells are effects that do not survive dropping a single project.')


def boxplots():
    rows = [r for r in read('enumsource_metrics.csv')
            if (r.get('n_sets') or '').strip()
            and (r.get('enum_structure') or '').strip() != 'n/a'
            and (r.get('dependency') or '').strip() != 'External']
    groups = ['Data-carrying', 'Label-based']
    fig, axes = plt.subplots(3, 4, figsize=(15, 9.5))
    for idx, (scope, metric) in enumerate(ROWS):
        ax = axes[idx // 4][idx % 4]
        col = COLUMN_OF[(scope, metric)]
        series, labels = [], []
        for g in groups:
            vals = [float(r[col]) for r in rows if r['enum_structure'] == g and r[col] != '']
            series.append(vals)
            labels.append(f'{g}\nn={len(vals)}')
        bp = ax.boxplot(series, tick_labels=labels, patch_artist=True, showfliers=False,
                        medianprops=dict(color='black', linewidth=1.6), widths=0.6)
        for patch, c in zip(bp['boxes'], ['#eba184', '#8fb3d9']):
            patch.set_facecolor(c)
            patch.set_alpha(0.88)
            patch.set_edgecolor('#444444')
        if metric in ('LOC', 'CC', 'CCTR'):
            ax.set_yscale('symlog')
        ax.set_title(f'{metric} ({scope})', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', labelsize=8.5)
        ax.tick_params(axis='y', labelsize=8.5)
        ax.grid(axis='y', alpha=0.3, linewidth=0.6)
        ax.set_axisbelow(True)
        for sp in ('top', 'right'):
            ax.spines[sp].set_visible(False)
    fig.suptitle('EnumSource: complexity profile by enum structure', fontsize=13.5,
                 fontweight='bold', y=0.995)
    fig.text(0.5, 0.005, 'Data-carrying enums hold the test data in the enum constants; '
                          'label-based enums are bare names. LOC/CC/CCTR symlog; DUP% is a 0-1 ratio.',
             ha='center', fontsize=9, style='italic', color='#444444')
    plt.tight_layout(rect=[0, 0.02, 1, 0.985])
    plt.savefig(os.path.join(RESULTS_DIR, 'enumsource_boxplots.png'), dpi=150, facecolor='white')
    plt.close(fig)
    print('wrote enumsource_boxplots.png')


if __name__ == '__main__':
    structure_heatmap()
    dimensions_heatmap()
    boxplots()
