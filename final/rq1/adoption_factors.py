#!/usr/bin/env python3
"""RQ1「影响因素」：项目规模、JUnit 版本、测试套件规模、年龄与 PT 采纳的关系，以及多元 logistic 回归。

这些数字此前只存在于 METHOD_complete.md / MANIFEST.md 里 —— 是在早先会话中临时算出、直接写进文档的，
没有留下脚本。本文件把它们固定下来，并统一从 rq1_bins.load() 取语料（与 Table 3 等同源）。

各项定义（以在旧 174 口径上逐个复现文档数字为准，见 --merged）：
  规模 × 采纳     size_grp × uses_pt 的 3×2 卡方，Cramér's V = sqrt(χ² / (n·(min(r,c)−1)))
  规模 × PAI      全部项目（含 PAI=0）按 size_grp 的 Kruskal-Wallis
  JUnit 版本      按测试方法的 JUnit 框架分组：JUnit4-only / JUnit5-only / Mixed（两者都有）；
                  两个都没有的项目（如纯 TestNG）不进这一项。
                  JUnit5-only vs JUnit4-only 的采纳（0/1）做 Mann-Whitney U 与 Cliff's δ
  套件规模 × PAI  log1p(total_tests) 与 PAI 的 Spearman
  年龄            全部项目按 age_grp 的 PAI Kruskal-Wallis
  多元 logistic   uses_pt ~ Medium + Large + HasJUnit5（Small 为参照；HasJUnit5 = junit5_total > 0）

用法：
  python adoption_factors.py                         # 当前底表（paths.MERGED_DATA）
  python adoption_factors.py --merged merged_data_218.csv   # 指定底表，用于核对旧数字
输出 adoption_factors.csv（仅当使用当前底表时写出）
"""
import argparse
import csv
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import rq1_bins   # noqa: E402


def cliffs_delta_from_u(u, n1, n2):
    return 2 * u / (n1 * n2) - 1


def junit_group(r):
    j4, j5 = r['junit4_total'] > 0, r['junit5_total'] > 0
    if j4 and j5:
        return 'Mixed'
    if j5:
        return 'JUnit5-only'
    if j4:
        return 'JUnit4-only'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--merged', default=None, help='改用指定底表（相对本目录或绝对路径）')
    a = ap.parse_args()
    if a.merged:
        rq1_bins.MERGED = a.merged if os.path.isabs(a.merged) else os.path.join(HERE, a.merged)

    df = rq1_bins.load()
    for c in ('junit4_total', 'junit5_total', 'total_tests', 'uses_pt'):
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    n = len(df)
    out = []

    def rec(factor, test, stat, p, detail=''):
        out.append({'factor': factor, 'test': test, 'statistic': stat, 'p': p, 'detail': detail})

    print(f'底表: {os.path.basename(rq1_bins.MERGED)}   N = {n}   采纳 = {int(df.uses_pt.sum())}\n')

    # 1. 规模 × 采纳
    ct = pd.crosstab(df['size_grp'], df['uses_pt']).reindex(rq1_bins.SIZE_LABELS)
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    v = np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))
    rates = (ct[1] / ct.sum(axis=1) * 100).round(1)
    print('规模 × 采纳  采纳率 ' + ' / '.join(f'{r}%' for r in rates.values) +
          f'   χ²={chi2:.2f}, df={dof}, p={p:.5f}, V={v:.3f}')
    rec('size x adoption', 'chi-square', round(chi2, 2), p,
        f'adoption% {list(rates.values)}; df={dof}; CramerV={v:.3f}')

    # 2. 规模 × PAI（全部项目）
    groups = [df.loc[df.size_grp == g, 'pai'].dropna() for g in rq1_bins.SIZE_LABELS]
    h, p = stats.kruskal(*groups)
    meds = [round(g.median(), 3) for g in groups]
    print(f'规模 × PAI   中位 PAI {meds}   H={h:.2f}, p={p:.4f}')
    rec('size x PAI', 'Kruskal-Wallis', round(h, 2), p, f'median PAI {meds}')

    # 3. JUnit 版本
    df['jg'] = df.apply(junit_group, axis=1)
    jg = df.dropna(subset=['jg'])
    info = {g: (len(s), s.uses_pt.mean() * 100) for g, s in jg.groupby('jg')}
    print('JUnit 版本   采纳率 ' + '  '.join(f'{g} {info[g][1]:.1f}%(n={info[g][0]})'
                                           for g in ('JUnit4-only', 'JUnit5-only', 'Mixed')) +
          f'   （无 JUnit 的 {n - len(jg)} 个不计）')
    rates = '; '.join(f'{g}: {info[g][1]:.1f}% (n={info[g][0]})' for g in info)
    # 文档里报告的 U=2280 / δ=0.377 是对 **PAI** 做的检验（在旧 174 口径上逐位复现），
    # 而同一行列出的是采纳率 —— 两个量混在了一行。这里两者都算、分开标注。
    for col, label in (('pai', 'PAI（文档原口径）'), ('uses_pt', '采纳 0/1')):
        x5 = jg.loc[jg.jg == 'JUnit5-only', col]
        x4 = jg.loc[jg.jg == 'JUnit4-only', col]
        u, p = stats.mannwhitneyu(x5, x4, alternative='two-sided')
        d = cliffs_delta_from_u(u, len(x5), len(x4))
        print(f'             JUnit5-only vs JUnit4-only，{label}：U={u:.0f}, p={p:.2e}, δ={d:.3f}')
        rec(f'JUnit version x {col}', 'Mann-Whitney U (JUnit5-only vs JUnit4-only)', round(u, 1), p,
            f'cliffs_delta={d:.3f}; adoption rates {{{rates}}}')

    # 4. 套件规模 × PAI
    rho, p = stats.spearmanr(np.log1p(df.total_tests), df.pai)
    print(f'套件规模×PAI ρ={rho:.3f}, p={p:.2e}')
    rec('test suite size x PAI', 'Spearman (log1p)', round(rho, 3), p)

    # 5. 年龄 × PAI
    groups = [df.loc[df.age_grp == g, 'pai'].dropna() for g in rq1_bins.AGE_LABELS]
    groups = [g for g in groups if len(g)]
    h, p = stats.kruskal(*groups)
    print(f'年龄 × PAI   H={h:.2f}, p={p:.3f}')
    rec('age x PAI', 'Kruskal-Wallis', round(h, 2), p)

    # 6. 多元 logistic
    import statsmodels.api as sm
    X = pd.DataFrame({
        'Medium scale (625-1805)': (df.size_grp == rq1_bins.SIZE_LABELS[1]).astype(int),
        'Large scale (>=1806)': (df.size_grp == rq1_bins.SIZE_LABELS[2]).astype(int),
        'Has JUnit5': (df.junit5_total > 0).astype(int),
    })
    m = sm.Logit(df.uses_pt.astype(int), sm.add_constant(X)).fit(disp=0)
    ci = np.exp(m.conf_int())
    print(f'\n多元 logistic  N={int(m.nobs)}  Pseudo-R²={m.prsquared:.3f}  AIC={m.aic:.1f}')
    for var in X.columns:
        print(f'   {var:26} OR={np.exp(m.params[var]):6.3f}  '
              f'[{ci.loc[var, 0]:.3f}, {ci.loc[var, 1]:.3f}]  p={m.pvalues[var]:.4f}')
        rec('logit: ' + var, 'OR', round(float(np.exp(m.params[var])), 3), m.pvalues[var],
            f'95%CI [{ci.loc[var, 0]:.3f}, {ci.loc[var, 1]:.3f}]')
    rec('logit model', f'N={int(m.nobs)}', round(m.prsquared, 3), m.llr_pvalue,
        f'pseudo_R2={m.prsquared:.3f}; AIC={m.aic:.1f}')

    if not a.merged:
        path = os.path.join(HERE, 'adoption_factors.csv')
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['factor', 'test', 'statistic', 'p', 'detail'])
            w.writeheader()
            w.writerows(out)
        print(f'\nwrote {os.path.relpath(path, os.path.dirname(HERE))}')


if __name__ == '__main__':
    main()
