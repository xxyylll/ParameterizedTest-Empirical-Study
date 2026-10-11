#!/usr/bin/env python3
"""
Amortisation figures. Two focused charts rather than one wide heatmap, because
the point of each is a single comparison that should be readable at a glance.

  amortization_effect_reversal.png  raw vs reuse-adjusted Cliff's delta for
                                    L1-L4 vs L0, one panel per measure. A
                                    dumbbell with a zero line: the arrow
                                    crossing zero IS the finding, and showing
                                    all three measures makes visible that it
                                    crosses for CCTR and CC but not reliably
                                    for LOC. Leave-one-project-out ranges sit
                                    behind each point; a hollow adjusted point
                                    marks a sign one project can flip.
  amortization_reuse_profile.png    the mechanism behind it: how reused the
                                    moved complexity is, and how much of it is
                                    single-use, by dependency level.
  amortization_reuse_distribution.png  the full shape of the reuse distribution
                                    rather than its median -- it is heavy-tailed
                                    enough that a point estimate misleads.

Palette: two categorical slots (#cf5a3d, #3f7cb8) validated with the dataviz
validator -- adjacent CVD dE 18.1 (protan), normal-vision dE 25.8, both well
clear of the floors.
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'amortization')
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

RAW = '#cf5a3d'          # categorical slot 1 - raw / reader model
ADJ = '#3f7cb8'          # categorical slot 2 - reuse-adjusted / maintainer model
BAR = '#46708f'          # single-series magnitude hue
INK = '#1a1a19'
INK2 = '#52514e'
GRID = '#d8d6d1'
BAND = '#f0eeea'

LEVELS = ['L1', 'L2', 'L3', 'L4']


def read(name):
    return list(csv.DictReader(open(os.path.join(RESULTS_DIR, name), newline='', encoding='utf-8')))


def effect_reversal():
    comp = {(r['contrast'], r['measure']): r
            for r in read('amortization_model_comparison.csv')}
    loo = {(r['contrast'], r['metric']): r for r in read('amortization_robustness_loo.csv')}
    measures = [('LOC', 'loc'), ('CC', 'cc'), ('CCTR', 'cctr')]

    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.1), sharey=True)
    ys = list(range(len(LEVELS)))[::-1]

    for ax, (mlabel, mkey) in zip(axes, measures):
        ax.axvspan(-0.147, 0.147, color=BAND, zorder=0)
        for x in (-0.33, 0.33):
            ax.axvline(x, color=GRID, linewidth=1, linestyle=':', zorder=1)
        ax.axvline(0, color=INK, linewidth=1.6, zorder=2)

        for y, lv in zip(ys, LEVELS):
            name = f'{lv} vs L0'
            r = comp[(name, mlabel)]
            d_raw = float(r['delta_reader'])
            d_adj = float(r['delta_maintainer'])

            for metric, colour in ((f'reader_total_{mkey}', RAW),
                                   (f'maintainer_total_{mkey}', ADJ)):
                lr = loo.get((name, metric))
                if lr:
                    ax.plot([float(lr['delta_min_loo']), float(lr['delta_max_loo'])], [y, y],
                            color=colour, linewidth=5, alpha=0.22,
                            solid_capstyle='round', zorder=3)

            ax.annotate('', xy=(d_adj, y), xytext=(d_raw, y),
                        arrowprops=dict(arrowstyle='-|>', color=INK2, linewidth=1.2,
                                        shrinkA=6, shrinkB=6, alpha=0.7), zorder=4)
            ax.scatter([d_raw], [y], s=105, color=RAW, zorder=5,
                       edgecolor='white', linewidth=1.5)

            # a hollow point marks an adjusted delta whose sign one project can flip
            unstable = loo.get((name, f'maintainer_total_{mkey}'), {}).get('sign_stable') == 'no'
            ax.scatter([d_adj], [y], s=105,
                       color='white' if unstable else ADJ, zorder=5,
                       edgecolor=ADJ, linewidth=2.0 if unstable else 1.5)

            ax.text(d_raw, y + 0.30, f'{d_raw:+.2f}', ha='center', va='bottom',
                    fontsize=8.5, color=RAW, fontweight='bold')
            ax.text(d_adj, y - 0.32, f'{d_adj:+.2f}' + ('†' if unstable else ''),
                    ha='center', va='top', fontsize=8.5, color=ADJ, fontweight='bold')

        ax.set_xlim(-0.42, 0.62)
        ax.set_ylim(-0.75, len(LEVELS) - 0.35)
        ax.set_title(mlabel, fontsize=11.5, fontweight='bold', color=INK, pad=8)
        ax.set_xticks([-0.4, -0.2, 0, 0.2, 0.4, 0.6])
        ax.tick_params(axis='x', labelsize=8.5, colors=INK2)
        ax.tick_params(axis='y', length=0)
        for sp in ('top', 'right', 'left'):
            ax.spines[sp].set_visible(False)
        ax.spines['bottom'].set_color(GRID)

    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([f'{lv} vs L0' for lv in LEVELS], fontsize=11)

    axes[0].scatter([], [], s=105, color=RAW, edgecolor='white', linewidth=1.5,
                    label='raw  (self + all helpers)')
    axes[0].scatter([], [], s=105, color=ADJ, edgecolor='white', linewidth=1.5,
                    label='reuse-adjusted  (self + helpers ÷ reuse)')
    axes[0].scatter([], [], s=105, color='white', edgecolor=ADJ, linewidth=2.0,
                    label='† sign flips if one project is dropped')
    fig.legend(fontsize=9.5, loc='upper center', bbox_to_anchor=(0.5, 0.995),
               ncol=3, frameon=False, handletextpad=0.4, columnspacing=1.6)

    fig.suptitle('Charging each test only its share of shared helpers removes the dependency penalty —\n'
                 'cleanly for CCTR and CC, only partly for LOC',
                 fontsize=12.5, fontweight='bold', color=INK, x=0.008, ha='left', y=1.17)
    fig.text(0.008, -0.10,
             "Cliff's δ; positive = that dependency level more complex than L0. Shaded band = negligible (|δ| < 0.147); "
             'dotted lines = small/medium boundary (0.33).\nFaint bars are the leave-one-project-out range. MethodSource, '
             'tests with at least one helper (n = 3,383 L0 / 353 L1 / 480 L2 / 502 L3 / 670 L4).',
             fontsize=8.5, color=INK2, style='italic')
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, 'amortization_effect_reversal.png')
    plt.savefig(out, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote amortization_effect_reversal.png')


def reuse_profile():
    rows = [r for r in read('amortization_metrics.csv') if r['dependency']]
    levels = ['L0', 'L1', 'L2', 'L3', 'L4']

    def series(col):
        out = {}
        for lv in levels:
            vs = []
            for r in rows:
                if r['dependency'] == lv and r[col] != '':
                    try:
                        vs.append(float(r[col]))
                    except ValueError:
                        pass
            out[lv] = sorted(vs)
        return out

    amort = series('amortization_cctr')
    priv = series('private_cctr_share')

    def q(v, p):
        if not v:
            return 0.0
        i = (len(v) - 1) * p
        lo, hi = int(i), min(int(i) + 1, len(v) - 1)
        return v[lo] + (v[hi] - v[lo]) * (i - lo)

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.3))
    ys = list(range(len(levels)))[::-1]

    # --- panel A: weighted reuse (median + IQR), log scale ---
    ax = axes[0]
    med = [q(amort[lv], 0.5) for lv in levels]
    lo = [q(amort[lv], 0.25) for lv in levels]
    hi = [q(amort[lv], 0.75) for lv in levels]
    for y, l, h in zip(ys, lo, hi):
        ax.plot([l, h], [y, y], color=BAR, linewidth=9, alpha=0.26, zorder=2,
                solid_capstyle='round')
    ax.barh(ys, med, height=0.52, color=BAR, edgecolor='white', linewidth=1.2, zorder=3)
    ax.axvline(med[0], color=RAW, linewidth=1.4, linestyle='--', zorder=5)
    ax.text(med[0], -0.62, ' L0 baseline', color=RAW, fontsize=8.5,
            va='center', ha='left', style='italic')
    for y, m, h in zip(ys, med, hi):
        ax.text(max(m, h) * 1.18, y, f'{m:,.0f}×', va='center', ha='left',
                fontsize=9.5, color=INK, fontweight='bold')
    ax.set_xscale('log')
    ax.set_xlim(4, 2200)
    ax.set_title('How reused is the complexity each test leans on?',
                 fontsize=11.5, fontweight='bold', color=INK, loc='left', pad=14)
    ax.set_xlabel('complexity-weighted helper reuse — median (bar), IQR (light band)  ·  log scale',
                  fontsize=9, color=INK2)

    # --- panel B: private share (mean) ---
    ax = axes[1]
    means = [sum(priv[lv]) / len(priv[lv]) if priv[lv] else 0 for lv in levels]
    ax.barh(ys, means, height=0.52, color=BAR, edgecolor='white', linewidth=1.2, zorder=3)
    ax.axvline(means[0], color=RAW, linewidth=1.4, linestyle='--', zorder=5)
    ax.text(means[0], -0.62, ' L0 baseline', color=RAW, fontsize=8.5,
            va='center', ha='left', style='italic')
    for y, m in zip(ys, means):
        ax.text(m + 0.004, y, f'{m:.3f}', va='center', ha='left',
                fontsize=9.5, color=INK, fontweight='bold')
    ax.set_xlim(0, 0.20)
    ax.set_title('…and how much of it is nobody else’s?',
                 fontsize=11.5, fontweight='bold', color=INK, loc='left', pad=14)
    ax.set_xlabel('mean share of helper CCTR sitting in single-use helpers',
                  fontsize=9, color=INK2)

    for ax in axes:
        ax.set_ylim(-1.0, len(levels) - 0.35)
        ax.set_yticks(ys)
        ax.set_yticklabels(levels, fontsize=11)
        ax.tick_params(axis='x', labelsize=9, colors=INK2)
        ax.tick_params(axis='y', length=0)
        ax.grid(axis='x', color=GRID, linewidth=0.7, alpha=0.6, zorder=0)
        ax.set_axisbelow(True)
        for sp in ('top', 'right', 'left'):
            ax.spines[sp].set_visible(False)
        ax.spines['bottom'].set_color(GRID)

    fig.suptitle('Why the reversal happens: dependency concentrates complexity in heavily shared helpers',
                 fontsize=13, fontweight='bold', color=INK, x=0.012, ha='left', y=1.03)
    fig.text(0.012, -0.06,
             'MethodSource by dependency level, CCTR. The median single-use share is 0 at every level — most tests have none — '
             'so panel B shows the mean,\nwhich is driven by the minority of tests that do. L1 is the outlier in both panels: '
             'the least reused helpers and the most private complexity.',
             fontsize=8.5, color=INK2, style='italic')
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, 'amortization_reuse_profile.png')
    plt.savefig(out, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote amortization_reuse_profile.png')




def reuse_distribution():
    """ECDFs, because weighted reuse is heavy-tailed: median 24 for PT against a
    mean of 163 and an SD of 388. An ECDF shows every quantile at once, with no
    binning choice, which a bar of the median cannot.

    The dependency levels are drawn as small multiples rather than five
    overlaid lines: a five-step sequential ramp fails the normal-vision
    separation floor (adjacent ΔE 9.7 < 15), and the dataviz validator's remedy
    for that is to facet rather than to lean on secondary encoding.
    """
    rows = read('amortization_metrics.csv')

    def series(sel):
        out = []
        for r in sel:
            v = r['amortization_cctr']
            if v != '':
                try:
                    out.append(float(v))
                except ValueError:
                    pass
        return sorted(out)

    def ecdf(ax, v, colour, label, lw=2.0, z=4):
        if not v:
            return
        n = len(v)
        ys = [(i + 1) / n for i in range(n)]
        ax.step(v, ys, where='post', color=colour, linewidth=lw, label=label, zorder=z)

    fig = plt.figure(figsize=(13.2, 7.1))
    gs = fig.add_gridspec(2, 5, height_ratios=[1.45, 1.0], hspace=0.95, wspace=0.28)

    # --- top: pt vs nonpt, the comparison the medians hide ---
    ax = fig.add_subplot(gs[0, :])
    # JUnit 5 on both sides: every PT in the corpus is JUnit 5, so an unrestricted
    # non-PT pool would mix parameterization with a change of test framework
    pt = series([r for r in rows if r['category'] == 'pt' and r['junit_api'] == 'junit5'])
    npt = series([r for r in rows if r['category'] == 'nonpt' and r['junit_api'] == 'junit5'])
    ecdf(ax, npt, ADJ, f'non-parameterized, JUnit 5  (n={len(npt):,})')
    ecdf(ax, pt, RAW, f'parameterized, JUnit 5  (n={len(pt):,})')
    # stagger the two median callouts: on a log axis 24 and 35 sit almost on top
    # of each other, so one goes above the 0.5 line and one below
    for v, colour, ytext, xmul, ha in ((pt, RAW, 0.60, 0.42, 'right'),
                                       (npt, ADJ, 0.33, 1.9, 'left')):
        med = v[len(v) // 2]
        ax.plot([med, med], [0, 0.5], color=colour, linewidth=1, linestyle=':', zorder=3)
        ax.scatter([med], [0.5], s=46, color=colour, zorder=6, edgecolor='white', linewidth=1.2)
        ax.annotate(f'median {med:,.0f}×', xy=(med, 0.5), xytext=(med * xmul, ytext),
                    fontsize=9, color=colour, fontweight='bold', ha=ha)
    ax.axhline(0.5, color=GRID, linewidth=0.9, zorder=1)
    ax.set_xscale('log')
    ax.set_xlim(0.85, 3200)
    ax.set_ylim(0, 1.02)
    ax.set_ylabel('cumulative share of tests', fontsize=9.5, color=INK2)
    ax.set_xlabel('complexity-weighted helper reuse  (log scale)', fontsize=9.5, color=INK2)
    ax.set_title('Parameterized tests lean on less-reused helpers — and the gap is in the tail, not the middle',
                 fontsize=11.5, fontweight='bold', color=INK, loc='left', pad=8)
    ax.legend(fontsize=9.5, loc='lower right', frameon=False)
    ax.grid(axis='both', color=GRID, linewidth=0.6, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    for sp in ('left', 'bottom'):
        ax.spines[sp].set_color(GRID)

    # --- bottom: dependency levels as small multiples against a common reference ---
    ref = series([r for r in rows if r['dependency'] in ('L0', 'L1', 'L2', 'L3', 'L4')])
    for i, lv in enumerate(['L0', 'L1', 'L2', 'L3', 'L4']):
        axs = fig.add_subplot(gs[1, i])
        v = series([r for r in rows if r['dependency'] == lv])
        ecdf(axs, ref, '#c9c7c1', None, lw=1.6, z=2)
        ecdf(axs, v, '#35709f', None, lw=2.0, z=4)
        if v:
            med = v[len(v) // 2]
            axs.scatter([med], [0.5], s=34, color='#35709f', zorder=6,
                        edgecolor='white', linewidth=1.1)
            axs.text(0.04, 0.88, f'median {med:,.0f}×', transform=axs.transAxes,
                     fontsize=8.5, color=INK, fontweight='bold')
        axs.set_xscale('log')
        axs.set_xlim(0.85, 3200)
        axs.set_ylim(0, 1.02)
        axs.set_title(f'{lv}  (n={len(v):,})', fontsize=10, fontweight='bold', color=INK)
        axs.tick_params(labelsize=7.5, colors=INK2)
        if i:
            axs.set_yticklabels([])
        axs.grid(axis='both', color=GRID, linewidth=0.5, alpha=0.45, zorder=0)
        axs.set_axisbelow(True)
        for sp in ('top', 'right'):
            axs.spines[sp].set_visible(False)
        for sp in ('left', 'bottom'):
            axs.spines[sp].set_color(GRID)

    fig.text(0.008, 0.405, 'By dependency level — grey line is all MethodSource tests, for reference',
             fontsize=11.5, fontweight='bold', color=INK)
    fig.suptitle('The real shape of helper reuse', fontsize=13.5, fontweight='bold',
                 color=INK, x=0.008, ha='left', y=1.0)
    fig.text(0.008, -0.035,
             'Empirical CDF of complexity-weighted helper reuse, tests with at least one helper. '
             'A value of 1 means the complexity the test leans on is shared with no other test.\n'
             'Both sides restricted to JUnit 5. The distribution is strongly right-skewed (PT: median 24, mean 163, SD 388, p99 2,361), '
             'so the median alone understates how much mass sits in the heavily-shared tail.',
             fontsize=8.5, color=INK2, style='italic')
    out = os.path.join(RESULTS_DIR, 'amortization_reuse_distribution.png')
    plt.savefig(out, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote amortization_reuse_distribution.png')


if __name__ == '__main__':
    effect_reversal()
    reuse_profile()
    reuse_distribution()
