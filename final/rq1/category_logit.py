#!/usr/bin/env python3
"""RQ1：category 对 PT 采纳的 logistic regression。

与早先 `check_category_llr.py` 的两处关键差异：

1. **项目口径与 RQ1 一致**（218 − 42 retired − 2 data integrity，再补回 Parquet = 175），不是 176。

2. **EPV 筛选去掉的是变量，不是项目。**
   EPV 原则针对的是「某类别项目太少 → 它的 0/1 变量估计不稳」，所以应当不给它设变量；
   而旧脚本的做法是只保留属于 top-4 类别的项目，把其余 37 个整个踢出模型。后果有二：
     - 样本无故从 168 缩到 139；
     - 更要紧的是参照组变了味：留下的每个项目都至少属于四类之一，
       于是 "big-data OR" 比较的是「big-data vs 属于 library/network-server/database 之一」，
       而不是读者自然理解的「big-data vs 其余所有」。
   这里改为：**只排除完全没有 category 的项目**（6 个），其余 169 个全部入模；
   仅给项目数 ≥ MIN_PROJECTS 的类别设变量，不达标的类别不设变量但项目保留，
   它们在所有变量上取 0，自然构成参照组。

按 175 口径计数，达标的只有 library(73) / big-data(40，含 Parquet) / network-server(26)；
database 以 19 个差一个落选 —— 这是去掉 2 个 data-integrity 项目带来的直接后果（176 时是 20）。

输出 rq1/category_logit_results.csv
"""
import collections
import csv
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rq1_bins import load  # noqa: E402

MIN_PROJECTS = 20          # EPV：低于此数的类别不单独设变量


def main():
    a = load()
    a['cats'] = a['categories'].fillna('').map(
        lambda v: [x.strip() for x in v.split(',') if x.strip()])

    no_cat = a[a['cats'].map(len) == 0]
    d = a[a['cats'].map(len) > 0].copy()        # RR 第 4 节：无 category 的项目排除

    counts = collections.Counter(t for lst in d['cats'] for t in lst)
    keep = [k for k, v in counts.most_common() if v >= MIN_PROJECTS]

    X = pd.DataFrame({k: d['cats'].map(lambda l, k=k: int(k in l)) for k in keep}, index=d.index)
    y = (d['pt_total'] > 0).astype(int)
    ref = (X.sum(axis=1) == 0).sum()

    res = sm.Logit(y, sm.add_constant(X)).fit(disp=0)

    print(f'排除无 category 的项目 {len(no_cat)} 个 → N = {len(d)}')
    print(f'自变量（项目数 >= {MIN_PROJECTS}）: ' +
          ', '.join(f'{k}({counts[k]})' for k in keep))
    print(f'落选的类别: ' + ', '.join(f'{k}({v})' for k, v in counts.most_common()
                                    if MIN_PROJECTS > v >= 10))
    print(f'参照组（所有变量取 0）: {ref} 个项目\n')
    print(f'Pseudo-R2 = {res.prsquared:.4f}   LLR p = {res.llr_pvalue:.4f}   AIC = {res.aic:.1f}\n')
    print(f"{'variable':18}{'n':>5}{'OR':>8}{'95% CI':>20}{'p':>9}")
    print('-' * 60)
    rows = []
    for v in keep:
        ci = res.conf_int().loc[v]
        star = '***' if res.pvalues[v] < .001 else '**' if res.pvalues[v] < .01 else \
               '*' if res.pvalues[v] < .05 else ''
        print(f'{v:18}{counts[v]:>5}{np.exp(res.params[v]):>8.3f}'
              f'{f"[{np.exp(ci[0]):.3f}, {np.exp(ci[1]):.3f}]":>20}{res.pvalues[v]:>9.4f} {star}')
        rows.append([v, counts[v], f'{np.exp(res.params[v]):.3f}',
                     f'{np.exp(ci[0]):.3f}', f'{np.exp(ci[1]):.3f}',
                     f'{res.pvalues[v]:.4f}', star])

    out = os.path.join(HERE, 'category_logit_results.csv')
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['# N', len(d), 'excluded_no_category', len(no_cat),
                    'reference_group', ref, 'pseudo_r2', f'{res.prsquared:.4f}',
                    'llr_p', f'{res.llr_pvalue:.4f}'])
        w.writerow(['variable', 'n_projects', 'OR', 'ci_low', 'ci_high', 'p', 'sig'])
        w.writerows(rows)
    print('\nwrote', os.path.relpath(out, os.path.dirname(HERE)))


if __name__ == '__main__':
    main()
