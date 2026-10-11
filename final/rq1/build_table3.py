#!/usr/bin/env python3
"""Table 3：active 且采纳 PT 的 107 个项目，PAI 与 PDAR 按项目特征分组的中位数与 IQR。

分档口径（与论文正文一致，均为**右闭**）：
  Size   `files_java` 三等分，切点 625 / 1806，**左闭右开**：
         [0, 625) / [625, 1806) / [1806, inf) → <625 / 625–1805 / >=1806
         恰好等于切点的项目归入右侧那组。全语料只有 1 个项目正好是 1806 个文件，
         左闭右开时它属于 Large，于是分组为 26/29/51（右闭则是 26/30/50）。
  Age    首次提交年份 ≤2005 / 2006–2011 / 2012–2017 / ≥2018。
         年份边界是明确的整数，用右闭才能让 ≤2005 真的包含 2005 —— 与 Size 的闭合方向不同，
         这是有意的，因为两者的标签语义本就不同。
  Domain ASF category 映射到四个大类，按优先级互斥

KW 检验排除 n ≤ 6 的组（论文脚注所述），该组仍列出以保持完整。

输出 rq1_new/table3_pai_pdar.csv
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import kruskal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
# 分档口径、语料筛选、domain 映射全部来自 rq1_bins —— 本文件早先复制过一份常量，
# 写法虽不同但结果一致（[0,2005,...] right=True 等价于 [0,2006,...] right=False）。
# 同一定义两处维护正是本项目反复出错的根源，这里改为单一来源。
from rq1_bins import (load as load_corpus, SIZE_LABELS, AGE_LABELS,  # noqa: E402
                      DOMAIN_ORDER)

MIN_GROUP = 6                       # n <= 6 的组不进 KW 检验


def load():
    """107 个采纳 PT 的项目，已带 size_grp / age_grp / domain_grp / pai / pdar。"""
    return load_corpus(adopters_only=True, with_pdar=True)


def stats(s):
    s = pd.to_numeric(s, errors='coerce').dropna()
    if s.empty:
        return '', '', ''
    return f'{s.median():.2f}', f'{s.quantile(.25):.2f}', f'{s.quantile(.75):.2f}'


def main():
    a = load()
    rows, tests = [], []
    for factor, col, order in (('Size', 'size_grp', SIZE_LABELS),
                               ('Age', 'age_grp', AGE_LABELS),
                               ('Domain', 'domain_grp', DOMAIN_ORDER)):
        groups = {g: a[a[col] == g] for g in order}
        for g in order:
            sub = groups[g]
            pm, pq1, pq3 = stats(sub['pai'])
            dm, dq1, dq3 = stats(sub['pdar'])
            n_pdar = pd.to_numeric(sub['pdar'], errors='coerce').notna().sum()
            rows.append([factor, g, len(sub), pm, f'{pq1}-{pq3}', n_pdar, dm, f'{dq1}-{dq3}',
                         'excluded from KW (n<=6)' if len(sub) <= MIN_GROUP else ''])
        # 小组是否进 KW 检验，两种口径都算出来：论文脚注说排除，但表里报的 H/p
        # 实际是含全部组的结果（Age: H=2.33 p=0.508 对应 df=3）。二者必须统一，
        # 这里都给出，由正文选定一种。
        for scope, sel in (('all groups', groups),
                           (f'n>{MIN_GROUP} only', {g: s for g, s in groups.items() if len(s) > MIN_GROUP})):
            for lbl, series in (('PAI', 'pai'), ('PDAR', 'pdar')):
                vals = [pd.to_numeric(s[series], errors='coerce').dropna() for s in sel.values()]
                vals = [v for v in vals if len(v) > 0]
                if len(vals) >= 2:
                    H, p = kruskal(*vals)
                    tests.append([factor, lbl, scope, f'{H:.2f}', f'{p:.3f}', len(vals)])

    out = os.path.join(HERE, 'table3_pai_pdar.csv')
    with open(out, 'w', newline='') as f:
        import csv
        w = csv.writer(f)
        w.writerow(['factor', 'group', 'n_pai', 'pai_median', 'pai_iqr',
                    'n_pdar', 'pdar_median', 'pdar_iqr', 'note'])
        w.writerows(rows)
        w.writerow([])
        w.writerow(['factor', 'metric', 'scope', 'KW_H', 'p', 'k_groups'])
        w.writerows(tests)

    hdr = f"{'Factor':8}{'Group':20}{'n':>4}{'PAI med':>9}{'PAI IQR':>16}{'PDAR med':>10}{'PDAR IQR':>16}"
    print(f'N = {len(a)}\n'); print(hdr); print('-' * len(hdr))
    for r in rows:
        print(f'{r[0]:8}{r[1]:20}{r[2]:>4}{r[3]:>9}{r[4]:>16}{r[6]:>10}{r[7]:>16}')
    print()
    print(f"{'Factor':8}{'Metric':6}{'Scope':16}{'H':>7}{'p':>8}{'k':>3}")
    for t in tests:
        print(f'{t[0]:8}{t[1]:6}{t[2]:16}{t[3]:>7}{t[4]:>8}{t[5]:>3}')
    print('\nwrote', os.path.basename(out))


if __name__ == '__main__':
    main()
