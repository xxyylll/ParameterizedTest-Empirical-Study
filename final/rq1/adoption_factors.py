#!/usr/bin/env python3
"""RQ1「影响因素」：项目规模、JUnit 版本、测试套件规模、年龄与 PT 采纳 / PAI 的关系，以及多元 logistic 回归。

这些数字此前只存在于 METHOD_complete.md / MANIFEST.md 里 —— 是在早先会话中临时算出、直接写进文档的，
没有留下脚本。本文件把它们固定下来，并统一从 rq1_bins.load() 取语料（与 Table 3 等同源）。
在旧 174 口径（--merged merged_data_218.csv）上逐位复现过文档的每个数。

各项定义：
  规模 × 采纳     size_grp × uses_pt 的 3×2 卡方，Cramér's V = sqrt(χ² / (n·(min(r,c)−1)))
  规模 × PAI      全部项目（含 PAI=0）按 size_grp 的 Kruskal-Wallis
  JUnit 版本 × PAI（论文口径）
                  在采纳者里按 **PT 用的框架**分组：JUnit4-PT-only（junit4_pt > 0 且 junit5_pt = 0）、
                  JUnit5-PT-only（反之）、两者都有。JUnit5-PT-only vs JUnit4-PT-only 的 PAI 做 Mann-Whitney U
                  与 Cliff's δ。在旧 174 口径上复现了论文的 n = 29 / 65、p = 0.074。
  JUnit 版本 × 采纳（补充，对应 logistic 的 Has JUnit5）
                  在全部项目里按 **测试方法用的框架**分组：JUnit4-only / JUnit5-only / Mixed；两个框架都没有的项目
                  （如纯 TestNG）不计。报告三组采纳率，以及 JUnit5-only vs JUnit4-only 的采纳（0/1）Mann-Whitney U。
                  注意它和上面的论文口径是**两种不同的分组**，不要混用。
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

    # 3a. JUnit 版本 × PAI（论文口径：采纳者内按 PT 的框架分组）
    for c in ('junit4_pt', 'junit5_pt'):
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    ad = df[df.uses_pt == 1]
    pt_groups = {
        'JUnit4-PT-only': ad[(ad.junit4_pt > 0) & (ad.junit5_pt == 0)],
        'JUnit5-PT-only': ad[(ad.junit5_pt > 0) & (ad.junit4_pt == 0)],
        'Both': ad[(ad.junit4_pt > 0) & (ad.junit5_pt > 0)],
    }
    R['junit_pt'] = {
        'groups': [{'group': g, 'n': len(d), 'pai_median': float(d.pai.median()),
                    'pai_q1': float(d.pai.quantile(.25)), 'pai_q3': float(d.pai.quantile(.75))}
                   for g, d in pt_groups.items()],
        'mwu': mwu(pt_groups['JUnit5-PT-only'].pai, pt_groups['JUnit4-PT-only'].pai),
        'projects_with_junit4_pt': int((df.junit4_pt > 0).sum()),
        'projects_with_junit5_pt': int((df.junit5_pt > 0).sum()),
    }

    # 3b. JUnit 版本 × 采纳（补充：全部项目按测试方法的框架分组，对应 logistic 的 Has JUnit5）
    df['jg'] = df.apply(junit_group, axis=1)
    jg = df.dropna(subset=['jg'])
    R['junit'] = {
        'excluded_no_junit': len(df) - len(jg),
        'groups': [{'group': g, 'n': int((jg.jg == g).sum()), 'adopters': int(jg.loc[jg.jg == g, 'uses_pt'].sum()),
                    'rate': jg.loc[jg.jg == g, 'uses_pt'].mean() * 100} for g in JUNIT_ORDER],
        'mwu_adoption': mwu(jg.loc[jg.jg == 'JUnit5-only', 'uses_pt'], jg.loc[jg.jg == 'JUnit4-only', 'uses_pt']),
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
    jp = R['junit_pt']
    print('JUnit × PAI  （论文口径，采纳者内按 PT 的框架）' + '  '.join(
        f"{g['group']} n={g['n']} 中位 {g['pai_median']:.2f}%" for g in jp['groups']))
    t = jp['mwu']
    print(f"             JUnit5-PT-only vs JUnit4-PT-only：U={t['U']:.0f}, p={t['p']:.3f}, δ={t['delta']:.3f}"
          f"   （用到 JUnit 4 PT 的项目 {jp['projects_with_junit4_pt']} 个，JUnit 5 PT 的 {jp['projects_with_junit5_pt']} 个）")
    j = R['junit']
    print('JUnit × 采纳 （补充，全部项目按测试框架）' + '  '.join(
        f"{g['group']} {g['rate']:.1f}%(n={g['n']})" for g in j['groups']) +
        f"   （无 JUnit 的 {j['excluded_no_junit']} 个不计）")
    t = j['mwu_adoption']
    print(f"             JUnit5-only vs JUnit4-only 采纳 0/1：U={t['U']:.0f}, p={t['p']:.2e}, δ={t['delta']:.3f}")
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
    ]
    jp = R['junit_pt']
    t = jp['mwu']
    rows.append(('JUnit PT framework x PAI (adopters; paper)', 'Mann-Whitney U (JUnit5-PT-only vs JUnit4-PT-only)',
                 t['U'], t['p'],
                 'n {' + ', '.join(f"{g['group']}: {g['n']} (median {g['pai_median']:.2f})" for g in jp['groups']) + '}'
                 f"; cliffs_delta={t['delta']:.3f}; projects with JUnit4 PT={jp['projects_with_junit4_pt']},"
                 f" JUnit5 PT={jp['projects_with_junit5_pt']}"))
    t = j['mwu_adoption']
    rows.append(('JUnit test framework x adoption (supplementary)', 'Mann-Whitney U (JUnit5-only vs JUnit4-only)',
                 t['U'], t['p'], 'rates {' + ', '.join(f"{g['group']}: {g['rate']:.1f}% (n={g['n']})" for g in j['groups'])
                 + f"}}; cliffs_delta={t['delta']:.3f}"))
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
