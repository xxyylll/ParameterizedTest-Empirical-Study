#!/usr/bin/env python3
"""
RQ3.3 figures, in the RQ3.1/RQ3.2 visual language (9-bin diverging scale keyed
to the Cliff's delta bands; *** = significant AND at least a small effect).

  cross_source_heatmap.png         every source vs the ValueSource baseline
  cross_source_family_heatmap.png  inline / type / file / provider, all pairs
  cross_source_volume_heatmap.png  provider vs inline inside n_sets quartiles
  cross_source_boxplots.png        distributions per source type
"""
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ['ValueSource', 'CsvSource', 'EnumSource', 'CsvFileSource',
           'MethodSource', 'ArgumentsSource', 'FieldSource']
BASELINE = 'ValueSource'
FAMILIES = ['inline', 'type', 'file', 'provider']

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
    return list(csv.DictReader(open(os.path.join(HERE, name), newline='', encoding='utf-8')))


def starred(d, p):
    return p < SIG_P and abs(d) >= SIG_DELTA


def draw(grid, stars, col_labels, title, high, low, outname, width):
    fig, ax = plt.subplots(figsize=(width, 6.4))
    ax.imshow(grid, cmap=CMAP, norm=NORM, aspect='auto')
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=20, ha='right', fontsize=10)
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
    ax.set_title(title, fontsize=12.5, fontweight='bold', pad=12)
    labels = [f'Large {high} (>0.474)', f'Medium {high}', f'Small {high}', f'Negligible {high}',
              'Equal', f'Negligible {low}', f'Small {low}', f'Medium {low}', f'Large {low} (<-0.474)']
    handles = [Patch(facecolor=c, edgecolor='#888888', linewidth=0.5, label=l)
               for c, l in zip(reversed(COLORS), labels)]
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.02, 1.0), fontsize=9,
              frameon=True, framealpha=0.95, borderaxespad=0)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, outname), dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote', outname)


def source_heatmap():
    data = {(r['scope'], r['metric'], r['comparison']): r for r in read('cross_source_pairwise.csv')}
    pop = {r['group']: r['n'] for r in read('cross_source_population.csv')}
    others = [s for s in SOURCES if s != BASELINE]
    cols = [f'{s}\n(n={pop[s]})' for s in others]
    grid, stars = [], []
    for key in ROWS:
        g, st = [], []
        for s in others:
            r = data[(key[0], key[1], f'{s} vs {BASELINE}')]
            d, p = float(r['cliffs_delta']), float(r['p_holm'])
            g.append(d)
            st.append(starred(d, p))
        grid.append(g)
        stars.append(st)
    draw(grid, stars, cols,
         f"RQ3.3 Parameter source vs {BASELINE} baseline (n={pop[BASELINE]})\n"
         "(Red = this source higher, *** = Holm p<0.05 and at least small)",
         'this source', BASELINE, 'cross_source_heatmap.png', 9.5)


def family_heatmap():
    data = {(r['scope'], r['metric'], r['comparison']): r for r in read('cross_source_family_pairwise.csv')}
    comps = [f'{b} vs {a}' for i, a in enumerate(FAMILIES) for b in FAMILIES[i + 1:]]
    grid, stars = [], []
    for key in ROWS:
        g, st = [], []
        for c in comps:
            r = data[(key[0], key[1], c)]
            d, p = float(r['cliffs_delta']), float(r['p_holm'])
            g.append(d)
            st.append(starred(d, p))
        grid.append(g)
        stars.append(st)
    draw(grid, stars, comps,
         "RQ3.3 Source mechanism families\n"
         "(inline = data in the annotation, provider = data from user-written code;\n"
         "Red = second-named family higher, *** = Holm p<0.05 and at least small)",
         'latter', 'former', 'cross_source_family_heatmap.png', 9.0)


def volume_heatmap():
    data = {(r['scope'], r['metric'], r['stratum']): r for r in read('cross_source_volume_strata.csv')}
    strata = ['Q1', 'Q2', 'Q3', 'Q4']
    cols = []
    for s in strata:
        any_row = next(r for (sc, m, st), r in data.items() if st == s)
        cols.append(f"{s}\nn_sets {any_row['n_sets_range']}")
    grid, stars = [], []
    for key in ROWS:
        g, st = [], []
        for s in strata:
            r = data[(key[0], key[1], s)]
            d, p = float(r['cliffs_delta']), float(r['p_raw'])
            g.append(d)
            st.append(starred(d, p))
        grid.append(g)
        stars.append(st)
    draw(grid, stars, cols,
         "RQ3.3 Provider vs inline, controlling for data volume\n"
         "(within quartiles of n_sets; Red = provider higher, *** = p<0.05 and at least small)",
         'provider', 'inline', 'cross_source_volume_heatmap.png', 8.0)


def boxplots():
    rows = read('cross_source_metrics.csv')
    fig, axes = plt.subplots(3, 4, figsize=(17, 9.5))
    palette = ['#d6e4f2', '#bcd2ea', '#fbe0d2', '#f2c0a8', '#eba184', '#cf5a3d', '#a3221b']
    for idx, (scope, metric) in enumerate(ROWS):
        ax = axes[idx // 4][idx % 4]
        col = COLUMN_OF[(scope, metric)]
        series, labels = [], []
        for s in SOURCES:
            vals = [float(r[col]) for r in rows if r['source_type'] == s and r[col] != '']
            series.append(vals)
            labels.append(f'{s.replace("Source","")}\nn={len(vals)}')
        bp = ax.boxplot(series, tick_labels=labels, patch_artist=True, showfliers=False,
                        medianprops=dict(color='black', linewidth=1.5), widths=0.62)
        for patch, c in zip(bp['boxes'], palette):
            patch.set_facecolor(c)
            patch.set_alpha(0.9)
            patch.set_edgecolor('#444444')
        if metric in ('LOC', 'CC', 'CCTR'):
            ax.set_yscale('symlog')
        ax.set_title(f'{metric} ({scope})', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', labelsize=7, rotation=45)
        ax.tick_params(axis='y', labelsize=8.5)
        ax.grid(axis='y', alpha=0.3, linewidth=0.6)
        ax.set_axisbelow(True)
        for sp in ('top', 'right'):
            ax.spines[sp].set_visible(False)
    fig.suptitle('RQ3.3 Complexity profile by parameter source type', fontsize=13.5,
                 fontweight='bold', y=0.996)
    fig.text(0.5, 0.004, 'Sources ordered by how far the argument data lives from the test method. '
                          'LOC/CC/CCTR on symlog scale; DUP% is a 0-1 ratio. Outliers hidden.',
             ha='center', fontsize=9, style='italic', color='#444444')
    plt.tight_layout(rect=[0, 0.02, 1, 0.985])
    plt.savefig(os.path.join(HERE, 'cross_source_boxplots.png'), dpi=150, facecolor='white')
    plt.close(fig)
    print('wrote cross_source_boxplots.png')


if __name__ == '__main__':
    source_heatmap()
    family_heatmap()
    volume_heatmap()
    boxplots()
