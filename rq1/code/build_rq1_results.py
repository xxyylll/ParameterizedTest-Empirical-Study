#!/usr/bin/env python3
"""生成 RQ1_RESULTS.md —— RQ1 全部结果的汇总文档。

文档里的每个数字都由本脚本从各分析的输出计算或读取，不手抄：
  - 语料、描述统计、分组采纳率：rq1_bins.load()（与所有 RQ1 分析同源）
  - 影响因素与多元 logistic：adoption_factors.compute()
  - 分组采纳率的卡方：adoption_by_groups_figure.adoption_stats()（与图同一个函数）
  - Table 1：dataset_stats.csv；Table 3：table3_pai_pdar.csv
  - category 回归：category_logit_results.csv；PDAR：pdar_summary_ssk.csv
所以先跑完各分析（run_rq1.sh 会按顺序做），再跑本脚本。不要手改 results/RQ1_RESULTS.md。
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
import csv
import io
import os
import sys
from datetime import date

import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import rq1_bins                                    # noqa: E402
import adoption_factors as AF                       # noqa: E402
from adoption_by_groups_figure import adoption_stats  # noqa: E402

OUT = os.path.join(RESULTS_DIR, 'RQ1_RESULTS.md')

# Fig. 2 两张直方图的分箱，均为左闭右开
PAI_BINS = [0, 1, 5, 10, 20, float('inf')]
PAI_LABELS = ['<1%', '1–5%', '5–10%', '10–20%', '≥20%']
PDAR_BINS = [0, 5, 10, 15, 20, 25, 30, 40, 50, 100.0001]
PDAR_LABELS = ['[0,5)', '[5,10)', '[10,15)', '[15,20)', '[20,25)', '[25,30)', '[30,40)', '[40,50)', '[50,100]']


def fp(p):
    """p 值格式：< 0.001 用科学计数法，否则 3 位小数。"""
    p = float(p)
    if p < 0.001:
        m, e = f'{p:.1e}'.split('e')
        return f'{m}×10^{int(e)}'
    return f'{p:.3f}'


def sig(p):
    p = float(p)
    return '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'


def delta_mag(d):
    a = abs(d)
    return 'negligible' if a < 0.147 else 'small' if a < 0.33 else 'medium' if a < 0.474 else 'large'


def read_table3():
    blocks = open(os.path.join(RESULTS_DIR, 'table3_pai_pdar.csv')).read().strip().split('\n\n')
    return pd.read_csv(io.StringIO(blocks[0])), pd.read_csv(io.StringIO(blocks[1]))


def read_category():
    lines = open(os.path.join(RESULTS_DIR, 'category_logit_results.csv')).read().strip().split('\n')
    head = lines[0].lstrip('# ').split(',')
    meta = dict(zip(head[0::2], head[1::2]))
    return meta, pd.read_csv(io.StringIO('\n'.join(lines[1:])))


def main():
    df = rq1_bins.load()
    ad = df[df.uses_pt == 1]
    n, na = len(df), len(ad)
    R = AF.compute(df)
    t1 = pd.read_csv(os.path.join(RESULTS_DIR, 'dataset_stats.csv'))
    t3, kw = read_table3()
    cmeta, cat = read_category()
    pdar = pd.read_csv(os.path.join(RESULTS_DIR, 'pdar_summary_ssk.csv'))
    deep = int((df.pai >= 5).sum())
    j = R['junit']
    jgrp = {g['group']: g for g in j['groups']}
    L = R['logit']
    lv = {v['var']: v for v in L['vars']}

    out = []
    w = out.append
    w('# RQ1 结果汇总\n')
    w(f'> **本文件由 `build_rq1_results.py` 自动生成（{date.today().isoformat()}），不要手改。** '
      f'数字全部来自各分析脚本的输出；重跑见第 9 节。\n>\n'
      f'> 语料 **{n}** 个项目，其中 **{na}** 个采纳 PT。底表 `{os.path.basename(rq1_bins.MERGED)}`（ssk 快照）。\n')

    # ---------------- 0. 结论
    size = R['size_adoption']['groups']
    w('## 0. 主要结论\n')
    w(f'1. **采纳普遍、使用很浅。** {na}/{n} = {na / n * 100:.1f}% 的项目至少有一个 PT，'
      f'但采纳者里 PT 只占测试方法的 {ad.pai.median():.2f}%（中位数）；PT 占比 ≥ 5% 的项目只有 '
      f'{deep}/{n} = {deep / n * 100:.1f}%。')
    w(f'2. **规模越大越可能采纳。** 采纳率 {size[0]["rate"]:.1f}% / {size[1]["rate"]:.1f}% / {size[2]["rate"]:.1f}%'
      f'（Small / Medium / Large），χ² p = {fp(R["size_adoption"]["p"])}；'
      f'控制 JUnit 版本后 Large 的 OR = {lv["Large scale (>=1806)"]["OR"]:.2f}。')
    # 3–5 条是定性判断，措辞由 p 值决定，避免数字更新后结论文字过时
    jp = R['junit_pt']
    jpg = {g['group']: g for g in jp['groups']}
    adp = jp['mwu']
    more_likely = lv['Has JUnit5']['p'] < 0.05 and j['mwu_adoption']['p'] < 0.05
    head3 = ('**用了 JUnit 5 的项目更可能采纳' if more_likely else '**JUnit 版本与采纳无显著关联') + \
            ('，但采纳后用得并不显著更多。**' if adp['p'] >= 0.05 else '，且采纳后 PAI 也有显著差异。**')
    w(f'3. {head3} 采纳率 JUnit5-only {jgrp["JUnit5-only"]["rate"]:.1f}% vs JUnit4-only {jgrp["JUnit4-only"]["rate"]:.1f}%'
      f'（按测试框架），logistic 中 Has JUnit5 的 OR = {lv["Has JUnit5"]["OR"]:.2f}（p = {fp(lv["Has JUnit5"]["p"])}）；'
      f'采纳者里按 PT 的框架分组，PAI 中位 JUnit5-PT-only {jpg["JUnit5-PT-only"]["pai_median"]:.2f}%（n = {jpg["JUnit5-PT-only"]["n"]}）'
      f' vs JUnit4-PT-only {jpg["JUnit4-PT-only"]["pai_median"]:.2f}%（n = {jpg["JUnit4-PT-only"]["n"]}），'
      f'p = {fp(adp["p"])}，δ = {adp["delta"]:.3f}（{delta_mag(adp["delta"])}）。')

    age_dom_p = {
        '年龄 × 采纳率': adoption_stats(df, 'age_grp', rq1_bins.AGE_LABELS)[2],
        '领域 × 采纳率': adoption_stats(df, 'domain_grp', rq1_bins.DOMAIN_ORDER)[2],
        '年龄 × 采纳率（去掉 >=2018）': R['age_adoption']['excl']['p'],
        '领域 × 采纳率（去掉 Web & Content）': R['domain_adoption']['excl']['p'],
        '年龄 × PAI（全部项目）': R['age_pai']['p'],
        **{f'{r.factor} × {r.metric}（Table 3）': r.p for r in kw[kw.factor.isin(['Age', 'Domain'])].itertuples()},
        **{f'category {r.variable}': r.p for r in cat.itertuples()},
    }
    sig_hits = [k for k, v in age_dom_p.items() if float(v) < 0.05]
    if not sig_hits:
        w(f'4. **年龄与领域都无关。** 采纳率、PAI、PDAR 按年龄或领域分组，以及 category logistic 回归，'
          f'共 {len(age_dom_p)} 项检验全部不显著（最小 p = {fp(min(map(float, age_dom_p.values())))}）。')
    else:
        w(f'4. **年龄 / 领域：** 以下检验显著 —— {"、".join(sig_hits)}；其余不显著。')

    pdar_kw = kw[kw.metric == 'PDAR']
    m0 = ad.merge(pdar[['project', 'pdar']], on='project')
    rho_pai, p_pai = stats.spearmanr(m0.pdar, m0.pai)
    no_factor = (pdar_kw.p.astype(float) >= 0.05).all()
    w(f'5. **PDAR 中位数 {pdar.pdar.median():.2f}%**（n = {len(pdar)}）：采纳了 PT 的项目里，碰过测试代码的开发者中'
      f'约每 {100 / pdar.pdar.median():.1f} 人有 1 人改过 PT。'
      + ('PDAR 与规模、年龄、领域均无显著关联' if no_factor else 'PDAR 与部分项目特征有显著关联（见第 5 节）')
      + f'，与 PAI 的 Spearman ρ = {rho_pai:.2f}（p = {fp(p_pai)}）。\n')

    # ---------------- 1. Table 1
    w('## 1. 语料（Table 1）\n')
    w(f'{n} 个项目，语料构成见仓库根 README 第 3 节。\n')
    w('| Metric | Mean | Median | Min | Max |\n|---|---:|---:|---:|---:|')
    for r in t1.itertuples():
        w(f'| {r.metric} | {r.mean} | {r.median} | {r.min} | {r.max} |')
    w('')
    fj = pd.to_numeric(df.files_java, errors='coerce')
    fs = pd.to_numeric(df.get('files_java_suffix'), errors='coerce')
    if fs.notna().all():
        diff = fj - fs
        g = lambda x: pd.cut(x, bins=rq1_bins.SIZE_BINS, labels=rq1_bins.SIZE_LABELS, right=rq1_bins.SIZE_RIGHT).astype(str)
        moved = int((g(fj) != g(fs)).sum())
        w('「# of Java files」与 Size 分组是同一列 `files_java`：ssk 快照 HEAD 上 `git ls-tree -r --name-only HEAD | grep -F .java`'
          ' 的行数。它是子串匹配，会多计路径中间含 `.java` 的少数文件（如 `*.java.template`、'
          f'`web.javascript.debugger/` 目录下的文件）。按严格的 `.java` 后缀计（`files_java_suffix` 列），{n} 个项目里 '
          f'{int((diff > 0).sum())} 个有差异、合计 {int(diff.sum()):,} 个（{diff.sum() / fj.sum() * 100:.2f}%），'
          f'均值 {fs.mean():,.0f}、最大值 {fs.max():,.0f}，换 Size 组的项目 {moved} 个。\n')
    # ---------------- 2. 描述统计
    w('## 2. 采纳的描述统计\n')
    q = lambda s, x: s.quantile(x)
    w('| 指标 | 值 |\n|---|---|')
    w(f'| CAR（至少 1 个 PT 的项目占比） | **{na}/{n} = {na / n * 100:.1f}%** |')
    w(f'| Deep Adoption（PAI ≥ 5%） | {deep}/{n} = {deep / n * 100:.1f}% |')
    w(f'| PAI，全部 {n} 个：中位 / 均值 | **{df.pai.median():.3f}%** / {df.pai.mean():.3f}%'
      f'（Q1–Q3 = {q(df.pai, .25):.3f}–{q(df.pai, .75):.3f}%，max {df.pai.max():.2f}%） |')
    w(f'| PAI，采纳者 {na} 个：中位 / 均值 | **{ad.pai.median():.3f}%** / {ad.pai.mean():.3f}%'
      f'（Q1–Q3 = {q(ad.pai, .25):.3f}–{q(ad.pai, .75):.3f}%） |')
    w(f'| PDAR，采纳者 {len(pdar)} 个：中位 / 均值 | **{pdar.pdar.median():.2f}%** / {pdar.pdar.mean():.2f}%'
      f'（Q1–Q3 = {q(pdar.pdar, .25):.2f}–{q(pdar.pdar, .75):.2f}%） |')
    w(f'| PT 总数 | {int(df.pt_total.sum()):,}（JUnit 4 {int(df.junit4_pt.sum()):,} = {df.junit4_pt.sum() / df.pt_total.sum() * 100:.1f}%，'
      f'{R["junit_pt"]["projects_with_junit4_pt"]} 个项目；JUnit 5 {int(df.junit5_pt.sum()):,} = {df.junit5_pt.sum() / df.pt_total.sum() * 100:.1f}%，'
      f'{R["junit_pt"]["projects_with_junit5_pt"]} 个项目） |\n')
    w('PAI = 项目内 PT 数 / 测试方法总数。PDAR = 改过 PT 的开发者 / 改过测试代码的开发者，只在采纳者上计算。\n')

    # ---------------- 2.1 分布（Fig. 2）
    def hist(x, bins, labels):
        return pd.cut(x, bins=bins, labels=labels, right=False).value_counts().reindex(labels).astype(int)
    w('### 2.1 PAI 与 PDAR 的分布（Fig. 2）\n')
    w('分箱均为**左闭右开**（如「1–5%」是 [1%, 5%)，「≥20%」含 20%）。\n')
    h_ad, h_all = hist(ad.pai, PAI_BINS, PAI_LABELS), hist(df.pai, PAI_BINS, PAI_LABELS)
    w('| PAI | ' + ' | '.join(PAI_LABELS) + ' | 合计 |\n|---|' + '---:|' * (len(PAI_LABELS) + 1))
    w(f'| **采纳者** | ' + ' | '.join(str(v) for v in h_ad) + f' | {h_ad.sum()} |')
    w(f'| 全部项目（含未采纳，PAI = 0） | ' + ' | '.join(str(v) for v in h_all) + f' | {h_all.sum()} |')
    edge = ad[ad.pai.isin(PAI_BINS)]
    w(f'\n恰好落在 PAI 分箱边界上的采纳者：{len(edge)} 个' + ('，闭合方向不影响计数。' if not len(edge) else
      '（' + '、'.join(f'{r.project} {r.pai:.2f}%' for r in edge.itertuples()) + '）。'))

    h_pd = hist(pdar.pdar, PDAR_BINS, PDAR_LABELS)
    w('| PDAR | ' + ' | '.join(PDAR_LABELS) + ' | 合计 |\n|---|' + '---:|' * (len(PDAR_LABELS) + 1))
    w(f'| 采纳者 | ' + ' | '.join(str(v) for v in h_pd) + f' | {h_pd.sum()} |')
    edge = pdar[pdar.pdar.isin(PDAR_BINS)]
    w(f'\n恰好落在 PDAR 分箱边界上的：' + ('无。' if not len(edge) else
      '、'.join(f'{r.project} {r.pdar:.2f}%（{r.pt_participants}/{r.test_developers}）' for r in edge.itertuples())
      + ' —— 按左闭右开归入右侧区间；改成右闭会改变相邻区间的计数。') + '\n')

    # ---------------- 3. 分组采纳率
    w('## 3. 采纳率按项目特征分组（`pt_adoption_by_groups.png`）\n')
    w('| 因素 | 组 | 采纳 / 项目数 | 采纳率 | χ² | p | Cramér\'s V |\n|---|---|---:|---:|---:|---:|---:|')
    for name, col, order in (('Size', 'size_grp', rq1_bins.SIZE_LABELS),
                             ('Age', 'age_grp', rq1_bins.AGE_LABELS),
                             ('Domain', 'domain_grp', rq1_bins.DOMAIN_ORDER)):
        s, chi2, p = adoption_stats(df, col, order)
        for i, (g, r) in enumerate(s.iterrows()):
            v = (chi2 / (s.total.sum() * (min(len(s), 2) - 1))) ** 0.5
            tail = f'{chi2:.2f} | {fp(p)} {sig(p)} | {v:.3f}' if i == 0 else ' |  | '
            w(f'| {name if i == 0 else ""} | {g} | {int(r.pt_users)}/{int(r.total)} | {r.pct:.1f}% | {tail} |')
    w('\nCramér\'s V = √(χ² / (N · (min(行, 列) − 1)))；这里列数为 2，即 √(χ² / N)。\n')
    w('与 Table 3 的 KW 一样，Age 与 Domain 的卡方也报「排除小组」口径（Age 去掉 >=2018，Domain 去掉 Web & Content）：\n')
    w('| 因素 | 口径 | N | χ² | df | p | Cramér\'s V |\n|---|---|---:|---:|---:|---:|---:|')
    for key, name in (('age_adoption', 'Age'), ('domain_adoption', 'Domain')):
        for sc in ('all', 'excl'):
            c = R[key][sc]
            label = '全部组' if sc == 'all' else f"去掉 {', '.join(c['excluded'])}"
            w(f"| {name if sc == 'all' else ''} | {label} | {c['n']} | {c['chi2']:.2f} | {c['df']} | "
              f"{fp(c['p'])} {sig(c['p'])} | {c['V']:.3f} |")
    w('')


    # ---------------- 4. 影响因素
    w('## 4. 影响因素\n')
    w('### 4.1 规模\n')
    sp = R['size_pai']
    w(f'- 采纳：χ² = {R["size_adoption"]["chi2"]:.2f}，df = {R["size_adoption"]["df"]}，'
      f'p = {fp(R["size_adoption"]["p"])} {sig(R["size_adoption"]["p"])}，V = {R["size_adoption"]["V"]:.3f}')
    w(f'- PAI（全部项目）：中位 {sp["medians"][0]:.3f}% / {sp["medians"][1]:.3f}% / {sp["medians"][2]:.3f}%，'
      f'Kruskal-Wallis H = {sp["H"]:.2f}，p = {fp(sp["p"])} {sig(sp["p"])}')
    w('- 规模切点 625 / 1806 是固定常量，左闭右开（`<625` / `625–1805` / `≥1806`）。'
      f'它们在本语料上分出 {", ".join(str(g["n"]) for g in size)} 个项目，**不是本语料的三分位**。\n')

    w('### 4.2 JUnit 版本\n')
    t = jp['mwu']
    w('**PAI（论文口径）：在采纳者里按 PT 用的框架分组。**\n')
    w('| 组 | 项目数 | PAI 中位 (IQR) |\n|---|---:|---|')
    for g in jp['groups']:
        label = {'JUnit4-PT-only': '只用 JUnit 4 写 PT', 'JUnit5-PT-only': '只用 JUnit 5 写 PT',
                 'Both': '两种都用'}[g['group']]
        w(f'| {label}（{g["group"]}） | {g["n"]} | {g["pai_median"]:.2f}% ({g["pai_q1"]:.2f}–{g["pai_q3"]:.2f}) |')
    w(f'\nJUnit5-PT-only vs JUnit4-PT-only：Mann-Whitney U = {t["U"]:.0f}，p = {fp(t["p"])} {sig(t["p"])}，'
      f'Cliff\'s δ = {t["delta"]:.3f}（{delta_mag(t["delta"])}）。'
      f'用到 JUnit 4 PT 的项目共 {jp["projects_with_junit4_pt"]} 个，用到 JUnit 5 PT 的 {jp["projects_with_junit5_pt"]} 个。\n')
    w(f'**采纳（补充）：在全部项目里按测试方法用的框架分组。** 这是 4.4 节 logistic 回归中 Has JUnit5 变量的口径；'
      f'两个框架都没有的 {j["excluded_no_junit"]} 个项目（如纯 TestNG）不计。**它与上面的 PAI 分组不是同一种分组。**\n')
    w('| 组 | 项目数 | 采纳率 |\n|---|---:|---:|')
    for g in j['groups']:
        w(f'| {g["group"]} | {g["n"]} | {g["rate"]:.1f}%（{g["adopters"]}/{g["n"]}） |')
    t = j['mwu_adoption']
    w(f'\nJUnit5-only vs JUnit4-only 的采纳（0/1）：U = {t["U"]:.0f}，p = {fp(t["p"])} {sig(t["p"])}，'
      f'δ = {t["delta"]:.3f}（{delta_mag(t["delta"])}）。\n')
    if j['mwu_adoption']['p'] < 0.05 and jp['mwu']['p'] >= 0.05:
        w('> **解读要点。** 用 JUnit 5 的项目显著更可能采纳 PT；但在已采纳的项目里，只用 JUnit 5 写 PT 的项目 PAI 中位数虽更高，'
          '差异不显著。论文里应写「JUnit 5 项目更可能采纳 PT」，而不是「JUnit 5 项目用得更多」。\n')
    else:
        w(f'> **解读要点。** 采纳：p = {fp(j["mwu_adoption"]["p"])}；采纳者内的 PAI：p = {fp(jp["mwu"]["p"])}。\n')

    w('### 4.3 测试套件规模与年龄\n')
    w(f'- 测试套件规模 × PAI：Spearman ρ = {R["suite_pai"]["rho"]:.3f}（log1p 变换），'
      f'p = {fp(R["suite_pai"]["p"])} {sig(R["suite_pai"]["p"])}')
    w(f'- 年龄（四档）× PAI：Kruskal-Wallis H = {R["age_pai"]["H"]:.2f}，p = {fp(R["age_pai"]["p"])} {sig(R["age_pai"]["p"])}\n')

    w('### 4.4 多元 logistic 回归（是否采纳 PT）\n')
    w(f'uses_pt ~ 规模（Small 为参照）+ Has JUnit5。N = {L["N"]}，Pseudo-R² = {L["pseudo_r2"]:.3f}，'
      f'AIC = {L["aic"]:.1f}，LLR p = {fp(L["llr_p"])}。\n')
    w('| 变量 | OR | 95% CI | p |\n|---|---:|---|---:|')
    for v in L['vars']:
        w(f'| {v["var"]} | **{v["OR"]:.3f}** | [{v["ci_low"]:.3f}, {v["ci_high"]:.3f}] | {fp(v["p"])} {sig(v["p"])} |')
    w('')

    w('### 4.5 领域：category logistic 回归（`category_logit.py`）\n')
    w(f'只排除完全没有 category 的 {cmeta["excluded_no_category"]} 个项目，N = {cmeta["N"]}。按 EPV 原则只给项目数 ≥ 20 的类别设变量，'
      f'其余项目留作参照组（{cmeta["reference_group"]} 个）。Pseudo-R² = {float(cmeta["pseudo_r2"]):.4f}，'
      f'LLR p = {fp(cmeta["llr_p"])}。\n')
    w('| category | 项目数 | OR | 95% CI | p |\n|---|---:|---:|---|---:|')
    for r in cat.itertuples():
        w(f'| {r.variable} | {r.n_projects} | {r.OR:.3f} | [{r.ci_low:.3f}, {r.ci_high:.3f}] | {fp(r.p)} {sig(r.p)} |')
    w('\n按 domain（四大类）分组的采纳率见第 3 节；两种口径都没有显著差异。\n')

    # ---------------- 5. Table 3
    w(f'## 5. 采纳强度按项目特征分组（Table 3，采纳者 n = {na}）\n')
    w('| Factor | Group | n | PAI median (IQR) | PDAR median (IQR) |\n|---|---|---:|---|---|')
    prev = None
    for r in t3.itertuples():
        mark = ' †' if isinstance(r.note, str) and r.note else ''
        w(f'| {r.factor if r.factor != prev else ""} | {r.group}{mark} | {r.n_pai} | '
          f'{r.pai_median:.2f} ({r.pai_iqr}) | {r.pdar_median:.2f} ({r.pdar_iqr}) |')
        prev = r.factor
    w('\n† n ≤ 6，在「仅 n > 6 的组」口径下不进 KW 检验。\n')
    w('| Factor | Metric | KW（全部组） | KW（仅 n > 6 的组） |\n|---|---|---|---|')
    for (fac, met), g in kw.groupby(['factor', 'metric'], sort=False):
        a = g[g.scope == 'all groups'].iloc[0]
        b = g[g.scope != 'all groups'].iloc[0]
        w(f'| {fac} | {met} | H = {a.KW_H:.2f}, p = {fp(a.p)}（{int(a.k_groups)} 组） | '
          f'H = {b.KW_H:.2f}, p = {fp(b.p)}（{int(b.k_groups)} 组） |')
    w('\n> **KW 口径需要在正文统一**：脚注若写「n ≤ 6 的组不进 KW」，表里就应报右列。两列结论相同（全部不显著）。\n')

    # ---------------- 6. PDAR
    w('## 6. PDAR\n')
    w(f'改动行 ∩ 参数化测试区间判定，{len(pdar)} 个采纳者。\n')
    w('| 口径 | 中位 | 均值 | Q1 | Q3 | 最小 | 最大 |\n|---|---:|---:|---:|---:|---:|---:|')
    for col, label in (('pdar', '**主口径（PT 方法及其同文件数据源）**'), ('pdar_pt_only', '只算 PT 方法')):
        s = pdar[col]
        w(f'| {label} | {s.median():.2f} | {s.mean():.2f} | {q(s, .25):.2f} | {q(s, .75):.2f} | {s.min():.2f} | {s.max():.2f} |')
    m = ad.merge(pdar[['project', 'pdar', 'test_developers']], on='project')
    w(f'\n与其他项目特征的 Spearman 相关（n = {len(m)}）：\n')
    w('| PDAR 与 | ρ | p |\n|---|---:|---:|')
    for label, x in (('PAI', m.pai), ('Java 文件数', pd.to_numeric(m.files_java)),
                     ('测试方法总数', pd.to_numeric(m.total_tests)), ('测试开发者数', m.test_developers)):
        r, p = stats.spearmanr(m.pdar, x)
        w(f'| {label} | {r:.3f} | {fp(p)} {sig(p)} |')
    w('')

    # ---------------- 7. 图
    w('## 7. 图\n')
    w('| 文件 | 内容 | 生成脚本 |\n|---|---|---|')
    w('| `pt_adoption_by_groups.png/pdf` | 采纳率按 Size / Age / Domain（第 3 节） | `adoption_by_groups_figure.py` |')
    w('| `rq1_pai_three_panel.png/pdf` | PAI 按 Size / Age / Domain 的小提琴 + 箱线图（第 5 节） | `three_panel_figures.py` |')
    w('| `rq1_pdar_three_panel.png/pdf` | PDAR 同上 | `three_panel_figures.py` |\n')
    w('三联图上标注的 KW 只纳入 n ≥ 10 的组；按当前各组大小，与 Table 3「仅 n > 6」口径纳入的组完全相同。\n')

    # ---------------- 8. 注意事项
    w('## 8. 口径与注意事项\n')
    w('- **快照**：计数与 `files_java` 取自 ssk 快照（与 RQ2 / RQ3 同一次 clone）。PDAR 的逐提交表取自 2026-06 的全量 clone。')
    w('- **PDAR 只在采纳者上计算**：未采纳项目的 PDAR 恒为 0，计入只会把中位数拉向 0。')
    w('- **parser 人工核验样本**（`parser_validation/`）：200 条（PT 100 + 非 PT 100），人工标签尚未填写；抽样说明见 `draw_parser_validation.py` 文件头。')
    w('- **Domain** 用四大类互斥映射，15 个项目靠手工补录（`rq1_bins.DOMAIN_MANUAL`）；不补的话采纳者里只有 '
      f'{int((~ad.project.str.strip().str.lower().isin(rq1_bins.DOMAIN_MANUAL) & ad.domain_grp.notna()).sum())} 个能自动归类。\n')

    # ---------------- 9. 复现
    w('## 9. 复现\n')
    w('```bash\ncd rq1/code\n./run_rq1.sh          # 依次跑全部 RQ1 分析与作图，最后重新生成本文件\n```\n')
    w('需要外部数据的步骤（重建底表需要 `PT_PARSER_SSK` 与 `PT_SSD`；Table 1 需要 `PT_PARSER_SSK`；重算 PDAR 汇总需要 '
      '`PT_PDAR_RESULT`）在数据缺失时会跳过，并沿用仓库里已提交的产物，其余步骤只依赖仓库内的文件。')

    open(OUT, 'w').write('\n'.join(out) + '\n')
    print(f'wrote {os.path.relpath(OUT, os.path.dirname(HERE))}')


if __name__ == '__main__':
    main()
