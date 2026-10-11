#!/usr/bin/env python3
"""pt_adoption_by_groups.{png,pdf}：按规模 / 创立年代 / 领域分组的 PT 采纳率（全部 RQ1 项目）。

原脚本是 rq1_new/scale_age_adoption/regen_adoption_by_groups.py，读仓库根目录的 merged_data.csv，
并自己复制了一套 Size / Age / Domain 常量（含 15 条 Domain 手工补录）。现在语料筛选与全部分组
直接取自 rq1_bins.load() —— 唯一定义处，与 Table 3、三联图、adoption_factors 同源。
画图部分与原脚本相同；只把 Size 标签改成与左闭右开口径一致（625–1805 / ≥1806）。
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ1_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import os
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rq1_bins   # noqa: E402

SIZE_LABELS = ['Small\n(<625)', 'Medium\n(625–1805)', 'Large\n(≥1806)']
AGE_LABELS = ['≤2005', '2006–2011', '2012–2017', '≥2018']
DOMAIN_LABELS = ['Data &\nAnalytics', 'Network &\nComm.', 'Dev. &\nTools', 'Web &\nContent']
BAR_COLOR = '#4472C4'


def adoption_stats(df, col, order):
    d = df.dropna(subset=[col])
    d = d[d[col].astype(str).isin(order)]
    s = d.groupby(d[col].astype(str))['uses_pt'].agg(['sum', 'count']).reindex(order)
    s.columns = ['pt_users', 'total']
    s['pct'] = s['pt_users'] / s['total'] * 100
    chi2, p, _, _ = chi2_contingency(pd.crosstab(d[col].astype(str), d['uses_pt']))
    return s, chi2, p


def draw_panel(ax, stats_df, labels, xlabel, title, chi2, p):
    x = np.arange(len(stats_df))
    ax.bar(x, stats_df['pct'], color=BAR_COLOR, edgecolor='black', linewidth=1.2)
    for i, (_, row) in enumerate(stats_df.iterrows()):
        h = row['pct']
        ax.text(i, h + 2, f"{h:.1f}%\n({int(row['pt_users'])}/{int(row['total'])})",
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    if p < 0.001:
        sig = ' ***'
    elif p < 0.01:
        sig = ' **'
    elif p < 0.05:
        sig = ' *'
    else:
        sig = ''
    ax.text(0.05, 0.95, f'χ² = {chi2:.2f}\np = {p:.4f}{sig}',
            transform=ax.transAxes, fontsize=11, va='top',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='black', alpha=0.9))
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_xlabel(xlabel, fontsize=13, fontweight='bold')
    ax.set_ylabel('PT Adoption Rate (%)', fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3, linestyle='--')


def main():
    df = rq1_bins.load()
    df['uses_pt'] = pd.to_numeric(df['uses_pt'], errors='coerce').fillna(0).astype(int)
    print(f'n = {len(df)}  |  PT adopters = {df.uses_pt.sum()}')

    panels = [
        (adoption_stats(df, 'size_grp', rq1_bins.SIZE_LABELS), SIZE_LABELS,
         'Project Scale (Java Files)', 'PT Adoption by Project Scale'),
        (adoption_stats(df, 'age_grp', rq1_bins.AGE_LABELS), AGE_LABELS,
         'Project Founding Era', 'PT Adoption by Founding Era'),
        (adoption_stats(df, 'domain_grp', rq1_bins.DOMAIN_ORDER), DOMAIN_LABELS,
         'Project Domain', 'PT Adoption by Domain'),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(22, 6))
    for ax, ((s, chi2, p), labels, xlabel, title) in zip(axes, panels):
        draw_panel(ax, s, labels, xlabel, title, chi2, p)
        print(f'  {title:32} ' + ' / '.join(f'{r.pct:.1f}%({int(r.pt_users)}/{int(r.total)})'
                                             for r in s.itertuples()) + f'   χ²={chi2:.2f} p={p:.4f}')
    fig.suptitle(f'PT Adoption Rates by Project Characteristics  (n={len(df)})',
                 fontsize=16, fontweight='bold', y=1.00)
    plt.tight_layout()
    for ext in ('png', 'pdf'):
        out = os.path.join(RESULTS_DIR, f'pt_adoption_by_groups.{ext}')
        # PDF 去掉生成时间，使重跑产物逐字节可复现
        meta = {'CreationDate': None} if ext == 'pdf' else None
        plt.savefig(out, dpi=300, bbox_inches='tight', metadata=meta)
        print(f'Saved: {os.path.basename(out)}')
    plt.close()


if __name__ == '__main__':
    main()
