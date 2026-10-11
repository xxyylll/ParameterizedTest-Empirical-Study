#!/usr/bin/env python3
"""RQ1「影响因素」：项目规模、JUnit 版本、测试套件规模、年龄与 PT 采纳 / PAI 的关系，以及多元 logistic 回归。

这些数字此前只存在于 METHOD_complete.md / MANIFEST.md 里 —— 是在早先会话中临时算出、直接写进文档的，
没有留下脚本。本文件把它们固定下来，并统一从 rq1_bins.load() 取语料（与 Table 3 等同源）。
在旧 174 口径（--merged merged_data_218.csv）上逐位复现过文档的每个数。

各项定义：
  规模 × 采纳     size_grp × uses_pt 的 3×2 卡方，Cramér's V = sqrt(χ² / (n·(min(r,c)−1)))
  规模 × PAI      全部项目（含 PAI=0）按 size_grp 的 Kruskal-Wallis
  JUnit 版本      按测试方法的 JUnit 框架分组：JUnit4-only / JUnit5-only / Mixed（两者都有）；
                  两个都没有的项目（如纯 TestNG）不进这一项。报告：
                    - 三组采纳率；
                    - 三组 PAI 中位数（全部项目 / 仅采纳者）与三组 KW；
                    - JUnit5-only vs JUnit4-only 的 Mann-Whitney U 与 Cliff's δ，分别对 PAI（全部项目，
                      即文档原口径）、采纳 0/1、PAI（仅采纳者）三种对象。
                  **全部项目口径下的 PAI 差异几乎全由采纳率造成**（JUnit4-only 大量 PAI=0）；
                  只看采纳者时差异消失，所以三种都报告。
  套件规模 × PAI  log1p(total_tests) 与 PAI 的 Spearman
  年龄            全部项目按 age_grp 的 PAI Kruskal-Wallis
  多元 logistic   uses_pt ~ Medium + Large + HasJUnit5（Small 为参照；HasJUnit5 = junit5_total > 0）

用法：
  python adoption_factors.py                                # 当前底表（paths.MERGED_DATA），写 adoption_factors.csv
  python adoption_factors.py --merged merged_data_218.csv   # 指定底表，只打印，用于核对旧数字
其它脚本（build_rq1_results.py）通过 compute() 取结构化结果。
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

JUNIT_ORDER = ('JUnit4-only', 'JUnit5-only', 'Mixed')
LOGIT_VARS = ('Medium scale (625-1805)', 'Large scale (>=1806)', 'Has JUnit5')


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


def mwu(x, y):
    u, p = stats.mannwhitneyu(x, y, alternative='two-sided')
    return {'U': float(u), 'p': float(p), 'delta': cliffs_delta_from_u(u, len(x), len(y)),
            'n1': len(x), 'n2': len(y)}


def compute(df=None):
    """返回全部影响因素的结构化结果。df 缺省时取 rq1_bins.load()。"""
    if df is None:
        df = rq1_bins.load()
    df = df.copy()
    for c in ('junit4_total', 'junit5_total', 'total_tests', 'uses_pt'):
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    R = {'n': len(df), 'adopters': int(df.uses_pt.sum())}

    # 1. 规模 × 采纳
    ct = pd.crosstab(df['size_grp'], df['uses_pt']).reindex(rq1_bins.SIZE_LABELS)
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    R['size_adoption'] = {
        'groups': [{'group': g, 'adopters': int(ct.loc[g, 1]), 'n': int(ct.loc[g].sum()),
                    'rate': ct.loc[g, 1] / ct.loc[g].sum() * 100} for g in rq1_bins.SIZE_LABELS],
        'chi2': chi2, 'df': int(dof), 'p': p,
        'V': float(np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))),
    }

    # 2. 规模 × PAI（全部项目）
    groups = [df.loc[df.size_grp == g, 'pai'].dropna() for g in rq1_bins.SIZE_LABELS]
    h, p = stats.kruskal(*groups)
    R['size_pai'] = {'medians': [float(g.median()) for g in groups], 'H': h, 'p': p}

    # 3. JUnit 版本
    df['jg'] = df.apply(junit_group, axis=1)
    jg = df.dropna(subset=['jg'])
    ad = jg[jg.uses_pt == 1]
    pick = lambda d, g, col='pai': d.loc[d.jg == g, col]
    h_all, p_all = stats.kruskal(*[pick(jg, g) for g in JUNIT_ORDER])
    h_ad, p_ad = stats.kruskal(*[pick(ad, g) for g in JUNIT_ORDER])
    R['junit'] = {
        'excluded_no_junit': len(df) - len(jg),
        'groups': [{'group': g, 'n': int((jg.jg == g).sum()), 'adopters': int((ad.jg == g).sum()),
                    'rate': pick(jg, g, 'uses_pt').mean() * 100,
                    'pai_median_all': float(pick(jg, g).median()),
                    'pai_median_adopters': float(pick(ad, g).median())} for g in JUNIT_ORDER],
        'kw_all': {'H': h_all, 'p': p_all},
        'kw_adopters': {'H': h_ad, 'p': p_ad},
        'mwu_pai_all': mwu(pick(jg, 'JUnit5-only'), pick(jg, 'JUnit4-only')),
        'mwu_adoption': mwu(pick(jg, 'JUnit5-only', 'uses_pt'), pick(jg, 'JUnit4-only', 'uses_pt')),
        'mwu_pai_adopters': mwu(pick(ad, 'JUnit5-only'), pick(ad, 'JUnit4-only')),
    }

    # 4. 套件规模 × PAI
    rho, p = stats.spearmanr(np.log1p(df.total_tests), df.pai)
    R['suite_pai'] = {'rho': rho, 'p': p}

    # 5. 年龄 × PAI
    groups = [g for g in (df.loc[df.age_grp == a, 'pai'].dropna() for a in rq1_bins.AGE_LABELS) if len(g)]
    h, p = stats.kruskal(*groups)
    R['age_pai'] = {'H': h, 'p': p}

    # 6. 多元 logistic
    import statsmodels.api as sm
    X = pd.DataFrame({
        LOGIT_VARS[0]: (df.size_grp == rq1_bins.SIZE_LABELS[1]).astype(int),
        LOGIT_VARS[1]: (df.size_grp == rq1_bins.SIZE_LABELS[2]).astype(int),
        LOGIT_VARS[2]: (df.junit5_total > 0).astype(int),
    })
    m = sm.Logit(df.uses_pt.astype(int), sm.add_constant(X)).fit(disp=0)
    ci = np.exp(m.conf_int())
    R['logit'] = {
        'N': int(m.nobs), 'pseudo_r2': m.prsquared, 'aic': m.aic, 'llr_p': m.llr_pvalue,
        'vars': [{'var': v, 'OR': float(np.exp(m.params[v])), 'ci_low': float(ci.loc[v, 0]),
                  'ci_high': float(ci.loc[v, 1]), 'p': float(m.pvalues[v])} for v in LOGIT_VARS],
    }
    return R


def report(R):
    print(f"N = {R['n']}   采纳 = {R['adopters']}\n")
    s = R['size_adoption']
    print('规模 × 采纳  采纳率 ' + ' / '.join(f"{g['rate']:.1f}%" for g in s['groups']) +
          f"   χ²={s['chi2']:.2f}, df={s['df']}, p={s['p']:.5f}, V={s['V']:.3f}")
    s = R['size_pai']
    print(f"规模 × PAI   中位 PAI {[round(x, 3) for x in s['medians']]}   H={s['H']:.2f}, p={s['p']:.4f}")
    j = R['junit']
    print('JUnit 版本   采纳率 ' + '  '.join(f"{g['group']} {g['rate']:.1f}%(n={g['n']})" for g in j['groups']) +
          f"   （无 JUnit 的 {j['excluded_no_junit']} 个不计）")
    print('             PAI 中位（全部项目）' + '  '.join(f"{g['group']} {g['pai_median_all']:.3f}%" for g in j['groups']) +
          f"   三组 KW H={j['kw_all']['H']:.2f}, p={j['kw_all']['p']:.2e}")
    print('             PAI 中位（仅采纳者）' + '  '.join(f"{g['group']} {g['pai_median_adopters']:.3f}%" for g in j['groups']) +
          f"   三组 KW H={j['kw_adopters']['H']:.2f}, p={j['kw_adopters']['p']:.3f}")
    for key, label in (('mwu_pai_all', 'PAI，全部项目（文档原口径）'), ('mwu_adoption', '采纳 0/1'),
                       ('mwu_pai_adopters', 'PAI，仅采纳者')):
        t = j[key]
        print(f"             JUnit5-only vs JUnit4-only，{label}：U={t['U']:.0f}, p={t['p']:.2e}, δ={t['delta']:.3f}"
              f"（n={t['n1']} / {t['n2']}）")
    print(f"套件规模×PAI ρ={R['suite_pai']['rho']:.3f}, p={R['suite_pai']['p']:.2e}")
    print(f"年龄 × PAI   H={R['age_pai']['H']:.2f}, p={R['age_pai']['p']:.3f}")
    L = R['logit']
    print(f"\n多元 logistic  N={L['N']}  Pseudo-R²={L['pseudo_r2']:.3f}  AIC={L['aic']:.1f}")
    for v in L['vars']:
        print(f"   {v['var']:26} OR={v['OR']:6.3f}  [{v['ci_low']:.3f}, {v['ci_high']:.3f}]  p={v['p']:.4f}")


def to_rows(R):
    s, j, L = R['size_adoption'], R['junit'], R['logit']
    rows = [
        ('size x adoption', 'chi-square', s['chi2'], s['p'],
         f"adoption% {[round(g['rate'], 1) for g in s['groups']]}; df={s['df']}; CramerV={s['V']:.3f}"),
        ('size x PAI', 'Kruskal-Wallis', R['size_pai']['H'], R['size_pai']['p'],
         f"median PAI {[round(x, 3) for x in R['size_pai']['medians']]}"),
        ('JUnit version x PAI (3 groups, all)', 'Kruskal-Wallis', j['kw_all']['H'], j['kw_all']['p'],
         'median PAI {' + ', '.join(f"{g['group']}: {g['pai_median_all']:.3f}" for g in j['groups']) + '}'),
        ('JUnit version x PAI (3 groups, adopters)', 'Kruskal-Wallis', j['kw_adopters']['H'], j['kw_adopters']['p'],
         'median PAI {' + ', '.join(f"{g['group']}: {g['pai_median_adopters']:.3f}" for g in j['groups']) + '}'),
    ]
    for key, label in (('mwu_pai_all', 'JUnit5-only vs JUnit4-only: PAI (all)'),
                       ('mwu_adoption', 'JUnit5-only vs JUnit4-only: adoption 0/1'),
                       ('mwu_pai_adopters', 'JUnit5-only vs JUnit4-only: PAI (adopters)')):
        t = j[key]
        rows.append((label, 'Mann-Whitney U', t['U'], t['p'], f"n={t['n1']}/{t['n2']}; cliffs_delta={t['delta']:.3f}"))
    rows += [
        ('test suite size x PAI', 'Spearman (log1p)', R['suite_pai']['rho'], R['suite_pai']['p'], ''),
        ('age x PAI', 'Kruskal-Wallis', R['age_pai']['H'], R['age_pai']['p'], ''),
    ]
    rows += [('logit: ' + v['var'], 'OR', v['OR'], v['p'], f"95%CI [{v['ci_low']:.3f}, {v['ci_high']:.3f}]")
             for v in L['vars']]
    rows.append(('logit model', f"N={L['N']}", L['pseudo_r2'], L['llr_p'],
                 f"pseudo_R2={L['pseudo_r2']:.3f}; AIC={L['aic']:.1f}"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--merged', default=None, help='改用指定底表（相对本目录或绝对路径）；只打印不写文件')
    a = ap.parse_args()
    if a.merged:
        rq1_bins.MERGED = a.merged if os.path.isabs(a.merged) else os.path.join(HERE, a.merged)
    print(f'底表: {os.path.basename(rq1_bins.MERGED)}')
    R = compute()
    report(R)
    if not a.merged:
        path = os.path.join(HERE, 'adoption_factors.csv')
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['factor', 'test', 'statistic', 'p', 'detail'])
            for factor, test, stat, p, detail in to_rows(R):
                w.writerow([factor, test, round(float(stat), 4), f'{float(p):.4g}', detail])
        print(f'\nwrote {os.path.relpath(path, os.path.dirname(HERE))}')


if __name__ == '__main__':
    main()
