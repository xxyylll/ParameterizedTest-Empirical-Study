#!/usr/bin/env python3
"""抽取 inter-rater reliability 样本（只覆盖 usage intent 维度）。

设计要点：

1. **只抽 good case**。`Good Cases?` 为 no 的行（参数没被用到、只有一个参数、根本不是 PT、
   被 @Disabled 等）一律排除 —— 让评分者去判这些，测到的分歧是数据质量问题而非 codebook 问题。

2. **MethodSource 只抽真正需要分类的**。`could be replaced by Value/Csv/EnumSource` 的 230 条
   不进样本：它们的 intent 列记的是「可替代性」而不是 type/value 判断。
   于是 MethodSource 的待验证维度收敛成干净的三分类（type / both / value）。
   代价：论文里「35.4% 可被更简单的 source 替代」这一论断没有 inter-rater 验证，
   应作为单编码者观察呈现。

3. **按待验证的标签分层，并对少数类过采样**。总体里 different-equivalence 只有 7.7%，
   按比例抽 60 条只会落到 4~5 条，κ 的置信区间会宽到不可用（模拟得 [0.44, 1.00]）。
   这里把它提到约 25%。代价是样本的类别比例是人为的，论文中必须写明
   「stratified by assigned label，κ 反映各类别上的可复现性，而非总体一致率」。

4. 分派：15 条三人共看（用于定性检查评分者之间是否同向分歧），
   其余 135 条每人 45 条。每条都有作者标签，所以主结果是 3 个「评分者 vs 作者」的
   Cohen's κ（各 n=60），共享块只报原始一致率 —— n=15 撑不起一个统计量。

输出 irr/sample_items.csv（含标签，供作者算 κ）与 irr/packet_{1,2,3}.csv（不含标签，发评分者）。
"""
import sys as _sys, os as _os
import csv
import os
import random
from collections import Counter, defaultdict

from check_usable import usable

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
from paths import MANUAL_DIR as SRC_DIR  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42

FILES = {
    'MethodSource': 'PT to Non-PT - MethodSource.csv',
    'ValueSource':  'PT to Non-PT - valuesource summary.csv',
    'CsvSource':    'PT to Non-PT - CSVSource.csv',
    'EnumSource':   'PT to Non-PT - Enumsource.csv',
}
SEM_COL = {'MethodSource': 'Semantic layer', 'ValueSource': 'Semantic layer', 'CsvSource': 'Semantic Layer'}
MS_KEEP = {'type complexity', 'both type & value', 'value complexity'}

n = lambda s: (s or '').strip().lower()


def type_complexity_of(raw):
    """把自由文本的 Type Complexity Subcategory 归一化成类型来源集合。

    原始记法是人工写的（"2 project's own type"、"1 jdk, 1 primitive"、
    "jdk, project's own type"），不可能让评分者复现原文；但它们全部能映射到
    {project, jdk, third-party} 的集合 —— 361 条 type/both 行零例外。
    primitive 不算一种「来源」，它只是与复杂类型并列的同行参数。
    """
    t = (raw or '').lower()
    o = []
    if "project's own" in t or 'projects own' in t:
        o.append('project')
    if 'jdk' in t:
        o.append('jdk')
    if 'third-party' in t or 'third party' in t:
        o.append('third-party')
    return '+'.join(o)
is_good = lambda r: n(r.get('Good Cases?')) not in ('no', 'no?', 'n')
is_diff = lambda r: n(r.get('Strategic Layer')) == 'different equivalence class'


def load(src):
    path = os.path.join(SRC_DIR, FILES[src])
    rows = [r for r in csv.DictReader(open(path, encoding='utf-8', errors='replace')) if is_good(r)]
    for r in rows:
        r['_source'] = src
    if src == 'MethodSource':
        rows = [r for r in rows if n(r['Methodsource Intent']) in MS_KEEP]
    return rows


def draw(rows, quota, rng):
    """从 rows 里抽 quota 条，**跳过材料做不出来的**；不足就全要。

    评分者看不到 provider 或枚举声明就无法判定，这类条目放进样本只会制造无效数据，
    所以在抽样阶段就过滤掉，而不是事后在材料包里标一句「未能定位」。
    """
    rows = list(rows)
    rng.shuffle(rows)
    out = []
    for r in rows:
        if len(out) >= quota:
            break
        ok, _ = usable(r)
        if ok:
            out.append(r)
    return out


def stratified(rows, key, quotas, rng, boost=None, boost_share=0.25):
    """按 key 分层抽样；boost 命中的行在每层内按 boost_share 保底。

    少数类必须显式保底而不能靠随机 —— behavior-carrying 只占 13%，
    不保底的话 60 条里只会落到 8 条，连原始一致率都没法报。
    """
    buckets = defaultdict(list)
    for r in rows:
        buckets[key(r)].append(r)
    out = []
    for k, q in quotas.items():
        pool = buckets.get(k, [])
        if boost is None:
            out += draw(pool, q, rng)
            continue
        hot = [r for r in pool if boost(r)]
        cold = [r for r in pool if not boost(r)]
        n_hot = min(len(hot), max(1, round(q * boost_share)))
        picked = draw(hot, n_hot, rng)
        taken = {id(x) for x in picked}
        picked += draw(cold, q - len(picked), rng)
        if len(picked) < q:                       # cold 不够就从 hot 补
            picked += draw([r for r in hot if id(r) not in taken], q - len(picked), rng)
        out += picked
    return out


def main():
    rng = random.Random(SEED)
    data = {s: load(s) for s in FILES}
    picked = []

    # ---- MethodSource 60：(intent × 等价类) 双层分层，层内再对 behavior-carrying 保底 1/4。
    #      三个维度同时压住，才能让 intent / equivalence / behavior 三个 κ 都有足够格子。
    #      注意 behavior-carrying 是**嵌套**维度而非独立维度：value-complexity 层里 58 条
    #      一条都没有，EnumSource 的 label 表示层 116 条里也一条都没有。
    #      所以 boost 只在它可能出现的层里生效（min() 会自动封顶），不能靠全局配额。
    is_beh = lambda r: n(r['Behavior Carring']) in ('strategy-object-based', 'lambda based')
    picked += stratified(data['MethodSource'],
                         lambda r: (n(r['Methodsource Intent']), is_diff(r)),
                         {('type complexity', False): 17, ('type complexity', True): 7,
                          ('both type & value', False): 13, ('both type & value', True): 5,
                          ('value complexity', False): 13, ('value complexity', True): 5},
                         rng, boost=is_beh, boost_share=0.40)

    # ---- ValueSource 35 / CsvSource 25：按语义角色三分层，File / External Language 大幅过采样
    picked += stratified(data['ValueSource'], lambda r: n(r[SEM_COL['ValueSource']]),
                         {'general': 13, 'file / resource lookup': 11, 'external language': 11},
                         rng, boost=is_diff, boost_share=0.27)
    picked += stratified(data['CsvSource'], lambda r: n(r[SEM_COL['CsvSource']]),
                         {'general': 9, 'file / resource lookup': 8, 'external language': 8},
                         rng, boost=is_diff, boost_share=0.27)

    # ---- EnumSource 30：表示 × 利用方式 四格尽量均衡；behavior-carrying 保底
    picked += stratified(data['EnumSource'],
                         lambda r: (n(r['Enum representation']), n(r['How this test exploits it'])),
                         {('data-carring', 'shared-contract use'): 8, ('label', 'shared-contract use'): 7,
                          ('label', 'semantic-specific use'): 8, ('data-carring', 'semantic-specific use'): 7},
                         rng, boost=lambda r: n(r['Behavior？']) == 'yes', boost_share=0.50)

    rng.shuffle(picked)
    for i, r in enumerate(picked, 1):
        r['_item_id'] = f'IRR-{i:03d}'

    # ---- 分派：15 条共享 + 每人 45 条
    shared, rest = picked[:15], picked[15:]
    for r in shared:
        r['_assigned'] = 'R1;R2;R3'
    for i, r in enumerate(rest):
        r['_assigned'] = f'R{i % 3 + 1}'

    os.makedirs(HERE, exist_ok=True)
    label_cols = ['Strategic Layer', 'Semantic layer', 'Semantic Layer', 'Methodsource Intent',
                  'Type Complexity Subcategory', 'Value Complexity', 'Behavior Carring',
                  'Enum representation', 'How this test exploits it', 'Behavior？']
    with open(os.path.join(HERE, 'sample_items.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['item_id', 'assigned', 'source', 'project', 'file_path', 'test_name']
                   + label_cols + ['type_complexity'])
        for r in picked:
            w.writerow([r['_item_id'], r['_assigned'], r['_source'], r['project'], r['file_path'],
                        r['test_name']] + [(r.get(c) or '').strip() for c in label_cols]
                       + [type_complexity_of(r.get('Type Complexity Subcategory'))])

    # 评分者包：绝不含任何标签列
    for rid in ('R1', 'R2', 'R3'):
        mine = [r for r in picked if rid in r['_assigned'].split(';')]
        with open(os.path.join(HERE, f'packet_{rid}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['item_id', 'source', 'project', 'test_name', 'file_path',
                        'equivalence_class', 'semantic_role', 'methodsource_intent',
                        'type_complexity', 'value_complexity', 'behavior_carrying',
                        'enum_structure', 'enum_usage_intent', 'confidence', 'notes'])
            for r in sorted(mine, key=lambda x: x['_item_id']):
                w.writerow([r['_item_id'], r['_source'], r['project'], r['test_name'], r['file_path']] + [''] * 10)
        print(f'  packet_{rid}.csv  {len(mine)} 条')

    # ---- 达成的分布
    print(f'\n抽样 {len(picked)} 条（共享 15 + 每人 45）')
    by_src = Counter(r['_source'] for r in picked)
    print('按 source:', dict(by_src))
    d = sum(1 for r in picked if is_diff(r))
    print(f'different equivalence class: {d}/{len(picked)} = {100*d/len(picked):.1f}%  （总体 7.7%）')
    print('MethodSource intent:', dict(Counter(n(r['Methodsource Intent']) for r in picked if r['_source'] == 'MethodSource')))
    sem = Counter(n(r.get(SEM_COL.get(r['_source'], ''), '')) for r in picked if r['_source'] in ('ValueSource', 'CsvSource'))
    print('Value+Csv 语义角色:', dict(sem))
    enum = [r for r in picked if r['_source'] == 'EnumSource']
    print('Enum 表示:', dict(Counter(n(r['Enum representation']) for r in enum)))
    print('Enum 利用方式:', dict(Counter(n(r['How this test exploits it']) for r in enum)))
    print('Enum behavior=yes:', sum(1 for r in enum if n(r['Behavior？']) == 'yes'))
    print('MethodSource behavior-carrying:', sum(1 for r in picked if r['_source'] == 'MethodSource'
                                                 and n(r['Behavior Carring']) in ('strategy-object-based', 'lambda based')))


if __name__ == '__main__':
    main()
