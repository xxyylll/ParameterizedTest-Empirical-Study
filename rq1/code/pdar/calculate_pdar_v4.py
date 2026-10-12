#!/usr/bin/env python3
"""把第二阶段（方法级）的逐提交结果与第一阶段逐提交表合并，算出项目级 PDAR。

每个被判定提交的 modifiedPT 在 v4 下为

    L1  =  l1m_x  ∨  (parse_err ∧ 第一阶段 L1)     x ∈ {pt, prov}；解析出错时回退第一阶段的判定
    L2  =  l2（第二阶段重算：两侧、正确的路径）
    modifiedPT = L1 ∨ L2

未判定的提交（merge / 根提交 / 本地缺失）取第一阶段的 L1/L2 原值。
分母为改过测试代码（touched_test）的开发者；email 去空白、转小写去重，无 email 的提交丢弃。

输出 rq1/results/pdar_summary_ssk.csv（论文口径）与 result_v4/pdar_v4_summary.csv（逐项目明细）。
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths

import argparse
import csv
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from pdar_v4_method_level import OUT_DIR, PUBLISHED_DIR  # noqa: E402

ATTRS = ['non_java_file', 'rename', 'pt_mention_not_method', 'overrun_prev', 'overrun_forward',
         'parse_error', 'not_reproduced', 'unexplained']
FOUND_RATIO_MIN = 0.95


def pct(num, den):
    return round(num / den * 100, 2) if den else 0.0


def b(v):
    return v not in ('', '0', None)


def project_pdar(project, result_dir):
    with open(os.path.join(PUBLISHED_DIR, f'{project}_commits.csv'), newline='', encoding='utf-8') as f:
        pub = list(csv.DictReader(f))
    with open(os.path.join(result_dir, f'{project}_method_commits.csv'), newline='', encoding='utf-8') as f:
        new = {r['commit_hash']: r for r in csv.DictReader(f)}
    with open(os.path.join(result_dir, f'{project}_method_summary.json'), encoding='utf-8') as f:
        summ = json.load(f)

    sets = {k: set() for k in ('test', 'm_pt', 'm_prov', 'core_diff')}
    for row in pub:
        email = row.get('author_email', '').strip().lower()
        if not email:
            continue
        layer = row['detection_layer']
        if row['touched_test'] == '1':
            sets['test'].add(email)
        pub_core = row['is_core'] == '1'

        r = new.get(row['commit_hash'])
        if r is None:
            # 未写出：要么被判定过且一切为 0（第一阶段 modifiedPT、is_core 也为 0），
            # 要么未被判定（merge / 根提交 / 本地缺失）—— 取第一阶段的 L1/L2 原值
            if layer in ('junit5_hunk', 'junit4_file'):
                for k in ('m_pt', 'm_prov'):
                    sets[k].add(email)
            if pub_core:
                sets['core_diff'].add(email)
            continue

        fallback = b(r['parse_err']) and layer == 'junit5_hunk'
        l2 = b(r['l2'])
        if b(r['l1m_pt']) or fallback or l2:
            sets['m_pt'].add(email)
        if b(r['l1m_prov']) or fallback or l2:
            sets['m_prov'].add(email)
        if b(r['core_diff']):
            sets['core_diff'].add(email)

    td = len(sets['test'])
    attr = summ.get('attribution', {})
    out = dict(
        project=project,
        test_developers=td,
        pt_participants=len(sets['m_prov']),
        core_developers=len(sets['core_diff']),
        pdar_m_pt=pct(len(sets['m_pt']), td),
        pdar_m_prov=pct(len(sets['m_prov']), td),
        core_diff=pct(len(sets['core_diff']), td),
        commits_old_l1=summ['old_l1_hits'],
        commits_l1m_pt=summ['commits_l1m_pt'],
        commits_l1m_prov=summ['commits_l1m_prov'],
        commits_parse_err=summ['commits_parse_err'],
        found_ratio=summ['found_ratio'],
        published_hit_not_in_stream=summ['published_hit_not_in_stream'],
        **{f'attr_{a}': attr.get(a, 0) for a in ATTRS},
    )
    flags = []
    if (summ['found_ratio'] or 0) < FOUND_RATIO_MIN:
        flags.append('low_found_ratio')
    if attr.get('unexplained') or attr.get('not_reproduced'):
        flags.append('unexplained_attribution')
    if summ['published_hit_not_in_stream']:
        flags.append('hit_not_in_stream')
    if summ.get('fullscan_mismatch'):
        flags.append('fullscan_mismatch')
    out['flags'] = ';'.join(flags)
    return out


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--result-dir', default=OUT_DIR)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    import rq1_bins
    projects = sorted(rq1_bins.load(adopters_only=True)['project'])

    rows, missing = [], []
    for p in projects:
        if not os.path.exists(os.path.join(a.result_dir, f'{p}_method_summary.json')):
            missing.append(p)
            continue
        rows.append(project_pdar(p, a.result_dir))

    # 论文口径的项目级表：rq1/pdar_summary_ssk.csv（rq1_bins / build_table3 读它）
    #   pdar      = v4 主口径（方法级 L1，含同文件 provider）
    #   core_pdar = 由 diff 直接判定（± 行含 @ParameterizedTest / @RunWith(Parameterized，只看 .java）
    #   pdar_pt_only = 只算 @ParameterizedTest 方法本身（不含同文件数据源）
    paper = _paths.PDAR_SUMMARY
    if rows and not missing:
        cols = ['project', 'pt_participants', 'core_developers', 'test_developers', 'pdar', 'core_pdar',
                'pdar_pt_only']
        with open(paper, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow([r['project'], r['pt_participants'], r['core_developers'], r['test_developers'],
                            r['pdar_m_prov'], r['core_diff'], r['pdar_m_pt']])
        print(f'论文口径项目级表：{paper}')

    out = a.out or os.path.join(a.result_dir, 'pdar_v4_summary.csv')
    if rows:
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    print(f'{len(rows)}/{len(projects)} 个项目有结果；缺 {len(missing)} 个' + (f'：{missing}' if missing else ''))
    flagged = [(r['project'], r['flags']) for r in rows if r['flags']]
    print(f'带标记的项目 {len(flagged)} 个：{flagged}')
    clean = [r for r in rows if not r['flags']]
    for label, sub in (('全部', rows), ('无标记', clean)):
        if not sub:
            continue
        print(f'\n[{label}] n={len(sub)}')
        for k in ('pdar_m_pt', 'pdar_m_prov', 'core_diff'):
            vals = [r[k] for r in sub if r[k] is not None]
            print(f'  {k:20} 中位 {statistics.median(vals):6.2f}  均值 {statistics.mean(vals):6.2f}')
    tot = {a_: sum(r[f'attr_{a_}'] for r in rows) for a_ in ATTRS}
    print(f'\n第一阶段 L1 命中而第二阶段未命中的归因（合计）：{tot}')
    print(f'输出：{out}')


if __name__ == '__main__':
    main()
