#!/usr/bin/env python3
"""RQ2.1：parameter source 的总体分布（基于 ssk 快照 + RQ1 的 174 项目口径）。

与旧的 `source_types_summary.csv` / `parameter_source_statistics.csv` 的区别：
  1. 数据源是 `parser_result_ssk/`（全部项目同一时间 clone），不是时间不一致的 `parser_result/`
  2. 项目框架与 RQ1 一致（218 − 42 retired − 2 data integrity = 174）
  3. **JUnit4 的 @Parameters 单独统计** —— 旧表只算了 JUnit5，漏掉了近一半的 PT

输出 rq2/rq2_1_source_distribution_ssk.csv
"""
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'rq1'))
from method_source_analysis import extract_source_annotations, is_parameterized_test  # noqa: E402
from paths import PARSER_SSK as SSK, PROJECT_NAME_MAP, require   # noqa: E402
from rq1_bins import load as load_corpus                          # noqa: E402
EXCL = {'Commons-HttpClient', 'Lucene-Core'}        # 与 HttpComponents-Client 重复 / 子模块
_norm = lambda s: (s or '').strip().lower()


def rq1_projects():
    """RQ1 的 174 个项目，映射到 ssk 的目录名。

    语料筛选直接复用 rq1_bins.load()，不再自己重写一遍 retired / data-integrity 的过滤，
    保证与 RQ1 完全同源。项目名映射存在 `project_name_map.json`。
    """
    manual = json.load(open(PROJECT_NAME_MAP))
    old2ssk = {v: k for k, v in manual.items()}
    return {old2ssk.get(p, str(p).lower()) for p in load_corpus()['project']}


def main():
    keep = rq1_projects()
    j4 = j5 = multi = 0
    j4_proj, j5_proj = set(), set()
    src_cnt = collections.Counter()
    src_proj = collections.defaultdict(set)

    for fn in sorted(os.listdir(SSK)):
        if not fn.endswith('_output.json'):
            continue
        proj = fn.replace('_output.json', '')
        if proj not in keep:
            continue
        for m in json.load(open(os.path.join(SSK, fn))):
            ann, jv = m.get('annotations', []), m.get('junit', 'unknown')
            if not is_parameterized_test(ann, jv):
                continue
            if jv == 'junit4':
                j4 += 1; j4_proj.add(proj); continue
            j5 += 1; j5_proj.add(proj)
            sa = extract_source_annotations(ann, jv)
            if len(sa) > 1:
                multi += 1
            for s in (sa or ['Unknown']):
                k = s.replace('JUnit5_', '')
                src_cnt[k] += 1
                src_proj[k].add(proj)

    require(SSK, 'RQ2.1 的 source 分布')
    out = os.path.join(HERE, 'rq2_1_source_distribution_ssk.csv')
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['category', 'n', 'pct_of_group', 'n_projects', 'pct_of_projects_in_group'])
        tot = j4 + j5
        w.writerow(['JUnit4 @Parameters', j4, f'{100*j4/tot:.2f}', len(j4_proj), ''])
        w.writerow(['JUnit5 (all sources)', j5, f'{100*j5/tot:.2f}', len(j5_proj), ''])
        w.writerow([])
        w.writerow(['-- within JUnit5 --', '', '', '', ''])
        for k, v in src_cnt.most_common():
            w.writerow([k, v, f'{100*v/j5:.2f}', len(src_proj[k]), f'{100*len(src_proj[k])/len(j5_proj):.1f}'])
        w.writerow(['multi-source tests', multi, f'{100*multi/j5:.2f}', '', ''])

    print(f'{len(keep)} 个项目口径；PT 合计 {j4+j5}  (JUnit4 {j4} / JUnit5 {j5})')
    print(f'JUnit5 内部 top: {dict(src_cnt.most_common(5))}')
    print('wrote', os.path.basename(out))


if __name__ == '__main__':
    main()
