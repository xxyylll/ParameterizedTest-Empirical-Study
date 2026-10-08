#!/usr/bin/env python3
"""RQ1 轻量 parser 的人工验证样本：100 个判为 PT + 100 个判为非 PT。

验证的是**注解级分类是否正确**，两个方向各有风险：
  - 判为 PT 的 100 条 → 查假阳性（不是参数化测试却被判成 PT）
  - 判为非 PT 的 100 条 → 查假阴性（是参数化测试却被漏掉）
    已知至少存在一例：nifi 的 AAA 管线比本 parser 多找到 12 个 PT。

**PT 侧按 JUnit4 / JUnit5 对半分层**。两者的识别机制完全不同
（`@ParameterizedTest` vs `@RunWith(Parameterized.class)`），按总体比例抽会掩盖
其中一种的错误率；各 50 条能让两种机制都得到检验。
按总体比例是 JUnit4 48.8% / JUnit5 51.2%，本来就接近对半，代价很小。

非 PT 侧不分层随机抽 —— 假阴性可能出现在任何地方，没有先验理由偏向某处。

语料与 RQ1 一致：174 个项目（218 − 42 retired − 2 data integrity）。
随机种子 42。

输出 parser_validation_sample.csv（含源码，便于直接判读）
"""
import csv
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SSK = os.path.join(ROOT, 'parser_result_ssk')
SEED = 42
N_PT, N_NONPT = 100, 100
MAX_SRC = 1600                      # 源码截断，防止单条过长

sys.path.insert(0, os.path.join(ROOT, 'rq2'))
sys.path.insert(0, os.path.join(ROOT, 'rq1_new'))
from method_source_analysis import is_parameterized_test  # noqa: E402
from rq1_bins import load as load_rq1                     # noqa: E402


def ssk_projects():
    """RQ1 的 174 个项目映射到 ssk 目录名。"""
    m = json.load(open(os.path.join(ROOT, 'project_name_map.json')))
    old2ssk = {v: k for k, v in m.items()}
    return {old2ssk.get(p, str(p).lower()) for p in load_rq1()['project']}


def main():
    keep = ssk_projects()
    pt_j4, pt_j5, nonpt = [], [], []
    for fn in sorted(os.listdir(SSK)):
        if not fn.endswith('_output.json'):
            continue
        proj = fn.replace('_output.json', '')
        if proj not in keep:
            continue
        for m in json.load(open(os.path.join(SSK, fn))):
            ann, jv = m.get('annotations', []), m.get('junit', 'unknown')
            rec = {'project': proj, 'file_path': m.get('filePath', ''),
                   'test_name': m.get('methodName', ''), 'junit': jv,
                   'annotations': ';'.join(ann),
                   'parser_label': '', 'source_code': (m.get('sourceCode') or '')[:MAX_SRC]}
            if is_parameterized_test(ann, jv):
                rec['parser_label'] = 'PT'
                (pt_j4 if jv == 'junit4' else pt_j5).append(rec)
            else:
                rec['parser_label'] = 'nonPT'
                nonpt.append(rec)

    rng = random.Random(SEED)
    for pool in (pt_j4, pt_j5, nonpt):
        rng.shuffle(pool)
    picked = pt_j4[:N_PT // 2] + pt_j5[:N_PT - N_PT // 2] + nonpt[:N_NONPT]
    rng.shuffle(picked)                      # 打散，避免评判时按组产生锚定
    for i, r in enumerate(picked, 1):
        r['item_id'] = f'PV-{i:03d}'

    cols = ['item_id', 'project', 'test_name', 'file_path', 'junit', 'annotations',
            'parser_label', 'manual_label', 'agree', 'notes', 'source_code']
    out = os.path.join(HERE, 'parser_validation_sample.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in picked:
            r['manual_label'] = ''; r['agree'] = ''; r['notes'] = ''
            w.writerow(r)

    print(f'语料 {len(keep)} 个项目  |  池：PT junit4 {len(pt_j4)} / junit5 {len(pt_j5)} / 非PT {len(nonpt)}')
    print(f'抽样 {len(picked)} 条 = PT {N_PT}（junit4 {N_PT//2} + junit5 {N_PT-N_PT//2}）+ 非PT {N_NONPT}')
    print(f'覆盖项目 {len({r["project"] for r in picked})} 个')
    print('wrote', os.path.relpath(out, ROOT))


if __name__ == '__main__':
    main()
