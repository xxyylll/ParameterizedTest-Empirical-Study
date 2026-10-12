#!/usr/bin/env python3
"""计算 RQ2.2 usage-intent 编码的 inter-rater reliability。

输入：
  results/rq2_2/irr/sample_items.csv     150 条样本及作者标签（draw_irr_sample.py 产出）
  results/rq2_2/irr/rater_answers.xlsx   三位评审人的答卷，每人一个 sheet（60 条）：
                                         Gengwu = R1，Hanbin = R2，Renming = R3

设计（见 draw_irr_sample.py）：每条都有作者标签，主结果是「评审人 vs 作者」的 Cohen's κ，
按维度分别计算；三人共看的 15 条只报原始一致率。

每个维度只在作者标了的条目上比较（例如 enum 两个维度只看 EnumSource）。评审人留空或填 n/a 的不计。
评审人填 `unclear` 的两种口径都报：
  unclear_as_disagreement   计入，视为与作者不一致（保守）
  unclear_excluded          排除后再算

输出（results/rq2_2/irr/）：
  irr_kappa.csv     每位评审人 × 维度 × 口径：n、一致率、κ；另有 rater = pooled（三人合并）
  irr_shared15.csv  共享 15 条：三人全同的条数、与作者一致的人次
  irr_unclear.csv   unclear 占已填标签的比例，按评审人与按维度
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ2_2_IRR_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)

import os
from collections import Counter

import numpy as np
import pandas as pd

SAMPLE = os.path.join(RESULTS_DIR, 'sample_items.csv')
ANSWERS = os.path.join(RESULTS_DIR, 'rater_answers.xlsx')
RATERS = {'Gengwu': 'R1', 'Hanbin': 'R2', 'Renming': 'R3'}
DIMS = ['equivalence_class', 'semantic_role', 'methodsource_intent', 'type_complexity',
        'value_complexity', 'behavior_carrying', 'enum_structure', 'enum_usage_intent']
MODES = ('unclear_as_disagreement', 'unclear_excluded')


def low(v):
    return '' if pd.isna(v) else str(v).strip().lower()


def author_labels(a):
    """把作者表的列名与取值统一成评审表的写法。"""
    out = pd.DataFrame({'item_id': a.item_id, 'source': a.source, 'assigned': a.assigned})
    out['equivalence_class'] = a['Strategic Layer'].map(low).map(
        {'same equivalence class': 'same', 'different equivalence class': 'different'})
    sem = a['Semantic layer'].map(low).where(a['Semantic layer'].notna(), a['Semantic Layer'].map(low))
    out['semantic_role'] = sem.map({'general': 'general', 'file / resource lookup': 'file-resource',
                                    'external language': 'external-language'})
    out['methodsource_intent'] = a['Methodsource Intent'].map(low).map(
        {'type complexity': 'type', 'both type & value': 'both', 'value complexity': 'value'})
    out['type_complexity'] = a['type_complexity'].map(low).replace('', np.nan)
    out['value_complexity'] = a['Value Complexity'].map(low).map(
        {'code-derived': 'code-derived', 'externally sourced': 'externally-sourced'})
    ms, en = a.source == 'MethodSource', a.source == 'EnumSource'
    beh_ms = a['Behavior Carring'].map(low).isin(['strategy-object-based', 'lambda based'])
    beh_en = a['Behavior？'].map(low) == 'yes'
    out['behavior_carrying'] = np.where(ms, np.where(beh_ms, 'yes', 'no'),
                                        np.where(en, np.where(beh_en, 'yes', 'no'), None))
    out['behavior_carrying'] = out['behavior_carrying'].where(ms | en)
    out['enum_structure'] = a['Enum representation'].map(low).map(
        {'data-carring': 'data-carrying', 'label': 'label'})
    out['enum_usage_intent'] = a['How this test exploits it'].map(low).map(
        {'shared-contract use': 'shared-contract', 'semantic-specific use': 'semantic-specific'})
    return out


def rater_label(dim, v):
    v = low(v)
    if v in ('', 'nan', 'n/a'):
        return np.nan
    if dim == 'type_complexity':
        v = v.replace("project's own type", 'project')
    return v


def kappa(p, q):
    n = len(p)
    po = np.mean([x == y for x, y in zip(p, q)])
    cp, cq = Counter(p), Counter(q)
    pe = sum(cp[c] * cq[c] for c in set(p) | set(q)) / n / n
    return po, ((po - pe) / (1 - pe) if pe < 1 else float('nan'))


def pairs(A, R, dim, mode):
    m = A[['item_id', dim]].merge(R[['item_id', dim]], on='item_id', suffixes=('_a', '_r'))
    m = m[m[dim + '_a'].notna() & m[dim + '_r'].notna()]
    if mode == 'unclear_excluded':
        m = m[m[dim + '_r'] != 'unclear']
    return list(m[dim + '_a']), list(m[dim + '_r'])


def main():
    A = author_labels(pd.read_csv(SAMPLE))
    xl = pd.ExcelFile(ANSWERS)
    R = {}
    for sheet, rid in RATERS.items():
        d = xl.parse(sheet)
        assert set(d.item_id) == set(A[A.assigned.str.contains(rid)].item_id), f'{sheet} 的条目与 {rid} 的分派不符'
        for c in DIMS:
            d[c] = [rater_label(c, v) for v in d[c]]
        R[sheet] = d

    rows = []
    for mode in MODES:
        for dim in DIMS:
            P_all, Q_all = [], []
            for sheet, d in R.items():
                p, q = pairs(A, d, dim, mode)
                P_all += p
                Q_all += q
                po, k = kappa(p, q) if p else (np.nan, np.nan)
                rows.append([mode, sheet, dim, len(p), round(po, 3), round(k, 3)])
            po, k = kappa(P_all, Q_all)
            rows.append([mode, 'pooled', dim, len(P_all), round(po, 3), round(k, 3)])
    kap = pd.DataFrame(rows, columns=['mode', 'rater', 'dim', 'n', 'agreement', 'kappa'])
    kap.to_csv(os.path.join(RESULTS_DIR, 'irr_kappa.csv'), index=False)

    shared = A[A.assigned == 'R1;R2;R3'].set_index('item_id')
    srows = []
    for dim in DIMS:
        lab = shared[dim].dropna()
        votes = [[d.set_index('item_id').loc[i, dim] for d in R.values()] for i in lab.index]
        all_same = sum(len({str(v) for v in vs}) == 1 for vs in votes)
        with_author = sum(v == lab[i] for i, vs in zip(lab.index, votes) for v in vs)
        srows.append([dim, len(lab), all_same, with_author, 3 * len(lab)])
    pd.DataFrame(srows, columns=['dim', 'n_items', 'all_three_agree', 'rater_author_agree', 'rater_author_pairs']) \
        .to_csv(os.path.join(RESULTS_DIR, 'irr_shared15.csv'), index=False)

    long = pd.concat([d[['item_id'] + DIMS].melt(id_vars='item_id', var_name='dim', value_name='val').assign(rater=s)
                      for s, d in R.items()]).dropna(subset=['val'])
    long['unclear'] = long.val == 'unclear'
    unc = pd.concat([
        long.groupby('rater').unclear.agg(['sum', 'count']).reset_index().rename(columns={'rater': 'group'}).assign(by='rater'),
        long.groupby('dim').unclear.agg(['sum', 'count']).reset_index().rename(columns={'dim': 'group'}).assign(by='dim'),
        pd.DataFrame([{'group': 'all', 'sum': long.unclear.sum(), 'count': len(long), 'by': 'all'}]),
    ])
    unc = unc.rename(columns={'sum': 'n_unclear', 'count': 'n_labels'})
    unc['share'] = (unc.n_unclear / unc.n_labels).round(3)
    unc[['by', 'group', 'n_unclear', 'n_labels', 'share']].to_csv(os.path.join(RESULTS_DIR, 'irr_unclear.csv'), index=False)

    pooled = kap[kap.rater == 'pooled'].pivot(index='dim', columns='mode', values='kappa').reindex(DIMS)
    print('三人合并 κ：')
    print(pooled.to_string())
    print(f'unclear 占已填标签：{long.unclear.sum()}/{len(long)} = {long.unclear.mean():.1%}')


if __name__ == '__main__':
    main()
