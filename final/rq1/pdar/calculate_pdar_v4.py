#!/usr/bin/env python3
"""把方法级 Layer 1 的逐提交结果与已发表逐提交表合并，算出项目级 PDAR 的各个口径。

每个被判定提交的 modifiedPT 在 v4 下为

    L1  =  l1m_x  ∨  (parse_err ∧ 第一阶段 L1)     x ∈ {pt, prov}；解析出错时回退旧判定
    L2  =  l2（第二阶段重算：两侧、正确的路径）
    modifiedPT = L1 ∨ L2                         L3（pickaxe）不再进入分子

对照口径 `pdar_with_l3` 再并上第一阶段的 is_core，用来度量去掉 L3 的影响（`l3_only_devs`）。
未判定的提交（merge / 根提交 / 本地缺失）取第一阶段的 L1/L2 原值。
分母 `touched_test`、email 去重规则与 v3 完全相同（email 去空白、转小写；无 email 的提交丢弃）。

输出 `pdar_v4_summary.csv`（逐项目）并打印 107 个采纳者上的中位数对比。
"""

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


def apply_pickaxe_from(project, new, pub_by_hash, pk_dir, summ):
    """用另一轮（跑过 pickaxe 的）结果补上 pickaxe_new 与 pickaxe 状态。

    那一轮写出了所有 pickaxe_new=1 的被判定提交；没写出的被判定提交 pickaxe_new=0。
    本轮新增写出的「只改非 .java」提交那一轮没判定过，pickaxe 取已发表 is_core。
    """
    with open(os.path.join(pk_dir, f'{project}_method_commits.csv'), newline='', encoding='utf-8') as f:
        old = {r['commit_hash']: r for r in csv.DictReader(f)}
    with open(os.path.join(pk_dir, f'{project}_method_summary.json'), encoding='utf-8') as f:
        summ['pickaxe'] = json.load(f).get('pickaxe')
    for h, r in new.items():
        if h in old:
            r['pickaxe_new'] = old[h]['pickaxe_new']
        elif r.get('attr') == 'non_java_file':
            r['pickaxe_new'] = pub_by_hash[h]['is_core']
        else:
            r['pickaxe_new'] = '0'
    for h, r in old.items():
        if h not in new and r['pickaxe_new'] == '1':
            new[h] = dict(r, l1m_pt='0', l1m_prov='0', l2='', parse_err='0', attr='')


def project_pdar(project, result_dir, pk_dir=None):
    with open(os.path.join(PUBLISHED_DIR, f'{project}_commits.csv'), newline='', encoding='utf-8') as f:
        pub = list(csv.DictReader(f))
    with open(os.path.join(result_dir, f'{project}_method_commits.csv'), newline='', encoding='utf-8') as f:
        new = {r['commit_hash']: r for r in csv.DictReader(f)}
    with open(os.path.join(result_dir, f'{project}_method_summary.json'), encoding='utf-8') as f:
        summ = json.load(f)
    if pk_dir:
        apply_pickaxe_from(project, new, {r['commit_hash']: r for r in pub}, pk_dir, summ)

    sets = {k: set() for k in ('test', 'pub', 'm_pt', 'm_prov', 'm_prov_l3',
                               'core_pub', 'core_pickaxe_new', 'core_diff')}
    for row in pub:
        email = row.get('author_email', '').strip().lower()
        if not email:
            continue
        layer = row['detection_layer']
        if row['touched_test'] == '1':
            sets['test'].add(email)
        pub_m = row['modifiedPT'] == '1'
        pub_core = row['is_core'] == '1'
        if pub_m:
            sets['pub'].add(email)
        if pub_core:
            sets['core_pub'].add(email)

        r = new.get(row['commit_hash'])
        if r is None:
            # 未写出：要么被判定过且一切为 0（第一阶段 modifiedPT、is_core 也为 0），
            # 要么未被判定（merge / 根提交 / 本地缺失）—— 取第一阶段的 L1/L2 原值，L3 只进对照口径
            if layer in ('junit5_hunk', 'junit4_file'):
                for k in ('m_pt', 'm_prov', 'm_prov_l3'):
                    sets[k].add(email)
            if pub_core:
                sets['m_prov_l3'].add(email)
                sets['core_pickaxe_new'].add(email)
                sets['core_diff'].add(email)
            continue

        fallback = b(r['parse_err']) and layer == 'junit5_hunk'
        l2 = b(r['l2'])
        if b(r['l1m_pt']) or fallback or l2:
            sets['m_pt'].add(email)
        if b(r['l1m_prov']) or fallback or l2:
            sets['m_prov'].add(email)
            sets['m_prov_l3'].add(email)
        if pub_core:
            sets['m_prov_l3'].add(email)
        if b(r['pickaxe_new']):
            sets['core_pickaxe_new'].add(email)
        if b(r['core_diff']):
            sets['core_diff'].add(email)

    td = len(sets['test'])
    attr = summ.get('attribution', {})
    pk = summ.get('pickaxe') or []
    out = dict(
        project=project,
        test_developers=td,
        pt_participants=len(sets['m_prov']),
        core_developers=len(sets['core_diff']),
        pdar_pub=pct(len(sets['pub']), td),
        pdar_m_pt=pct(len(sets['m_pt']), td),
        pdar_m_prov=pct(len(sets['m_prov']), td),
        pdar_with_l3=pct(len(sets['m_prov_l3']), td),
        l3_only_devs=len(sets['m_prov_l3'] - sets['m_prov']),
        core_pub=pct(len(sets['core_pub']), td),
        core_pickaxe_new=pct(len(sets['core_pickaxe_new']), td),
        core_diff=pct(len(sets['core_diff']), td),
        commits_old_l1=summ['old_l1_hits'],
        commits_l1m_pt=summ['commits_l1m_pt'],
        commits_l1m_prov=summ['commits_l1m_prov'],
        commits_parse_err=summ['commits_parse_err'],
        found_ratio=summ['found_ratio'],
        pickaxe_completed=all(p.get('completed') for p in pk) if pk else None,
        published_hit_not_in_stream=summ['published_hit_not_in_stream'],
        **{f'attr_{a}': attr.get(a, 0) for a in ATTRS},
    )
    # pickaxe 失败或没跑的项目，依赖它的两个口径记为缺失，而不是把失败当成「0 个提交」
    if not out['pickaxe_completed']:
        out['core_pickaxe_new'] = None
    flags = []
    if (summ['found_ratio'] or 0) < FOUND_RATIO_MIN:
        flags.append('low_found_ratio')
    if attr.get('unexplained') or attr.get('not_reproduced'):
        flags.append('unexplained_attribution')
    if summ['published_hit_not_in_stream']:
        flags.append('hit_not_in_stream')
    if summ.get('fullscan_mismatch'):
        flags.append('fullscan_mismatch')
    if not out['pickaxe_completed']:
        flags.append('pickaxe_incomplete')
    out['flags'] = ';'.join(flags)
    return out


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--result-dir', default=OUT_DIR)
    ap.add_argument('--out', default=None)
    ap.add_argument('--pickaxe-from', default=os.path.join(HERE, 'result_v4_pickaxe'),
                    help='从这一轮（跑过 pickaxe 的）结果目录取 pickaxe_new；传空串表示用本轮自己的')
    a = ap.parse_args()
    import rq1_bins
    projects = sorted(rq1_bins.load(adopters_only=True)['project'])

    # v3 的论文数字（2026-06 那一轮），用来核对第一阶段表是否就是论文那份
    pub_summary = {}
    with open(os.path.join(HERE, 'pdar_v3_published.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            pub_summary[r['project']] = float(r['pdar'])

    rows, missing = [], []
    for p in projects:
        if not os.path.exists(os.path.join(a.result_dir, f'{p}_method_summary.json')):
            missing.append(p)
            continue
        r = project_pdar(p, a.result_dir, a.pickaxe_from or None)
        if p not in pub_summary:
            # 论文 v3 那一轮之后才加入语料的项目（目前只有 Parquet），没有可核对的已发表值；
            # 它的第一阶段表截在 2026-06-23，与其余项目的批量 clone 时间对齐
            r['flags'] = (r['flags'] + ';' if r['flags'] else '') + 'added_after_v3'
        elif abs(r['pdar_pub'] - pub_summary[p]) > 0.01:
            r['flags'] = (r['flags'] + ';' if r['flags'] else '') + 'pub_mismatch'
        rows.append(r)

    # 论文口径的项目级表：rq1/pdar_summary_ssk.csv（rq1_bins / build_table3 读它）
    #   pdar      = v4 主口径（方法级 L1，含同文件 provider）
    #   core_pdar = 由 diff 直接判定（± 行含 @ParameterizedTest / @RunWith(Parameterized，只看 .java）
    #   其余列供敏感性分析与作图
    paper = os.path.join(os.path.dirname(HERE), 'pdar_summary_ssk.csv')
    if rows and not missing:
        cols = ['project', 'pt_participants', 'core_developers', 'test_developers', 'pdar', 'core_pdar',
                'pdar_pt_only', 'pdar_with_l3', 'pdar_v3', 'core_pdar_v3', 'core_pdar_pickaxe']
        with open(paper, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow([r['project'], r['pt_participants'], r['core_developers'], r['test_developers'],
                            r['pdar_m_prov'], r['core_diff'], r['pdar_m_pt'], r['pdar_with_l3'], r['pdar_pub'],
                            r['core_pub'], r['core_pickaxe_new']])
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
        for k in ('pdar_pub', 'pdar_m_pt', 'pdar_m_prov', 'pdar_with_l3',
                  'core_pub', 'core_pickaxe_new', 'core_diff'):
            vals = [r[k] for r in sub if r[k] is not None]
            print(f'  {k:20} 中位 {statistics.median(vals):6.2f}  均值 {statistics.mean(vals):6.2f}')
        d = [r['pdar_m_prov'] - r['pdar_pub'] for r in sub]
        print(f'  Δ(m_prov − pub)      中位 {statistics.median(d):+.2f}  范围 {min(d):+.2f} ~ {max(d):+.2f}  '
              f'Δ=0 的项目 {sum(1 for x in d if abs(x) < 1e-9)}')
    tot = {a_: sum(r[f'attr_{a_}'] for r in rows) for a_ in ATTRS}
    print(f'\n旧 L1 命中而新判定未命中的归因（合计）：{tot}')
    l3 = sum(r['l3_only_devs'] for r in rows)
    print(f'只靠 L3（第一阶段 pickaxe）才进入分子的开发者：{l3} 人，'
          f'涉及 {sum(1 for r in rows if r["l3_only_devs"])} 个项目：'
          f'{[(r["project"], r["l3_only_devs"]) for r in rows if r["l3_only_devs"]]}')
    print(f'输出：{out}')


if __name__ == '__main__':
    main()
