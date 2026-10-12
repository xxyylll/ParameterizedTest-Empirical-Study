#!/usr/bin/env python3
"""RQ1 的描述统计、PAI / PDAR 分布（Fig. 2）与 PDAR 相关性。

输出（rq1/results/）：
  adoption_descriptives.csv   CAR、Deep adoption、PAI 与 PDAR 的分位数、PT 总数与 JUnit 4 / 5 构成、
                              files_java 两种计数方式的差异
  pai_pdar_distribution.csv   Fig. 2 两张直方图的分箱计数（左闭右开，如 1–5% 是 [1%, 5%)）
  pdar_correlations.csv       PDAR 与 PAI、项目规模、测试规模、测试开发者数的 Spearman 相关（采纳者）

语料统一从 rq1_bins.load() 取；PDAR 读 pdar_summary_ssk.csv。
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
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

import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rq1_bins                 # noqa: E402
import adoption_factors as AF   # noqa: E402

PAI_BINS = [0, 1, 5, 10, 20, float('inf')]
PAI_LABELS = ['<1%', '1-5%', '5-10%', '10-20%', '>=20%']
PDAR_BINS = [0, 5, 10, 15, 20, 25, 30, 40, 50, 100.0001]
PDAR_LABELS = ['[0,5)', '[5,10)', '[10,15)', '[15,20)', '[20,25)', '[25,30)', '[30,40)', '[40,50)', '[50,100]']


def quantiles(s, prefix):
    s = pd.to_numeric(s)
    return [(f'{prefix} median', s.median()), (f'{prefix} mean', s.mean()),
            (f'{prefix} Q1', s.quantile(.25)), (f'{prefix} Q3', s.quantile(.75)),
            (f'{prefix} min', s.min()), (f'{prefix} max', s.max())]


def main():
    df = rq1_bins.load()
    ad = df[df.uses_pt == 1]
    pdar = pd.read_csv(os.path.join(RESULTS_DIR, 'pdar_summary_ssk.csv'))
    jp = AF.compute(df)['junit_pt']
    n, na = len(df), len(ad)
    pt, j4, j5 = df.pt_total.sum(), df.junit4_pt.sum(), df.junit5_pt.sum()

    rows = [('projects', n), ('adopters (>= 1 PT)', na), ('CAR %', na / n * 100),
            ('deep adopters (PAI >= 5%)', int((df.pai >= 5).sum())), ('deep adoption %', (df.pai >= 5).mean() * 100)]
    rows += quantiles(df.pai, 'PAI % (all projects)')
    rows += quantiles(ad.pai, 'PAI % (adopters)')
    rows += quantiles(pdar.pdar, 'PDAR % (adopters)')
    rows += quantiles(pdar.pdar_pt_only, 'PDAR % (adopters, PT methods only)')
    rows += [('PTs', pt),
             ('JUnit 4 PTs', j4), ('JUnit 4 PT share %', j4 / pt * 100),
             ('projects with JUnit 4 PTs', jp['projects_with_junit4_pt']),
             ('JUnit 5 PTs', j5), ('JUnit 5 PT share %', j5 / pt * 100),
             ('projects with JUnit 5 PTs', jp['projects_with_junit5_pt'])]
    # files_java 是 `git ls-tree | grep -F .java` 的子串计数（Size 分组用它）；files_java_suffix 是严格后缀计数
    fj, fs = pd.to_numeric(df.files_java), pd.to_numeric(df.files_java_suffix)
    grp = lambda x: pd.cut(x, bins=rq1_bins.SIZE_BINS, labels=rq1_bins.SIZE_LABELS, right=rq1_bins.SIZE_RIGHT).astype(str)
    rows += [('files_java: projects where substring and suffix counts differ', int((fj != fs).sum())),
             ('files_java: total difference (files)', int((fj - fs).sum())),
             ('files_java: total difference %', (fj - fs).sum() / fj.sum() * 100),
             ('files_java: projects changing Size group under suffix count', int((grp(fj) != grp(fs)).sum()))]
    fmt = lambda v: str(int(v)) if float(v).is_integer() else f'{float(v):.4f}'
    pd.DataFrame([(k, fmt(v)) for k, v in rows], columns=['metric', 'value']) \
        .to_csv(os.path.join(RESULTS_DIR, 'adoption_descriptives.csv'), index=False)

    def hist(x, bins, labels):
        return pd.cut(x, bins=bins, labels=labels, right=False).value_counts().reindex(labels).astype(int)
    dist = []
    for name, x, bins, labels in (('PAI', ad.pai, PAI_BINS, PAI_LABELS),
                                  ('PAI (all projects, non-adopters at 0)', df.pai, PAI_BINS, PAI_LABELS),
                                  ('PDAR', pdar.pdar, PDAR_BINS, PDAR_LABELS)):
        dist += [(name, b, c) for b, c in hist(x, bins, labels).items()]
    pd.DataFrame(dist, columns=['distribution', 'bin', 'projects']) \
        .to_csv(os.path.join(RESULTS_DIR, 'pai_pdar_distribution.csv'), index=False)

    m = ad.merge(pdar[['project', 'pdar', 'test_developers']], on='project')
    corr = []
    for label, x in (('PAI', m.pai), ('Java files', pd.to_numeric(m.files_java)),
                     ('test methods', pd.to_numeric(m.total_tests)), ('test developers', m.test_developers)):
        r, p = stats.spearmanr(m.pdar, x)
        corr.append(('PDAR', label, len(m), round(r, 4), p))
    pd.DataFrame(corr, columns=['x', 'y', 'n', 'spearman_rho', 'p']) \
        .to_csv(os.path.join(RESULTS_DIR, 'pdar_correlations.csv'), index=False)
    print('wrote adoption_descriptives.csv, pai_pdar_distribution.csv, pdar_correlations.csv')


if __name__ == '__main__':
    main()
