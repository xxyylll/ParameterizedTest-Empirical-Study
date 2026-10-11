#!/usr/bin/env python3
"""论文 Table 1：175 个项目的语料统计。

四个指标的来源：
  # of Total files    `files_java`（merged_data.csv）
  # of Test files     由 `parser_result_ssk/{proj}_output.json` 的 filePath 去重得到 ——
                      merged_data.csv 里没有这一列
  # of Test methods   `total_tests`
  Project Age (Years) `age` 列；与「2026 − 首次提交年」完全一致，口径是当前的

输出 dataset_stats.csv
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ1_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from rq1_bins import load                            # noqa: E402
from paths import PARSER_SSK, PROJECT_NAME_MAP, require  # noqa: E402

ROWS = [('# of Java files', 'files_java'), ('# of Test files', 'test_files'),
        ('# of Test methods', 'total_tests'), ('Project Age (Years)', 'age')]


def main():
    require(PARSER_SSK, 'Table 1 的 Test files 一列')
    a = load()
    m = json.load(open(PROJECT_NAME_MAP))
    old2ssk = {v: k for k, v in m.items()}

    tf = {}
    for p in a['project']:
        ssk = old2ssk.get(p, str(p).lower())
        fp = os.path.join(PARSER_SSK, f'{ssk}_output.json')
        if os.path.exists(fp):
            tf[p] = len({x.get('filePath', '') for x in json.load(open(fp)) if x.get('filePath')})
    a['test_files'] = a['project'].map(tf)
    missing = a[a['test_files'].isna()]['project'].tolist()

    out = []
    for lab, c in ROWS:
        s = pd.to_numeric(a[c], errors='coerce').dropna()
        out.append([lab, f'{s.mean():,.0f}', f'{s.median():,.0f}',
                    f'{s.min():,.0f}', f'{s.max():,.0f}', len(s)])

    with open(os.path.join(RESULTS_DIR, 'dataset_stats.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric', 'mean', 'median', 'min', 'max', 'n'])
        w.writerows(out)

    print(f'N = {len(a)}' + (f'   （test_files 缺 {missing}）' if missing else ''))
    print(f"\n{'Metric':24}{'Mean':>10}{'Median':>10}{'Min':>8}{'Max':>10}")
    print('-' * 62)
    for r in out:
        print(f'{r[0]:24}{r[1]:>10}{r[2]:>10}{r[3]:>8}{r[4]:>10}')
    print('\nwrote dataset_stats.csv')


if __name__ == '__main__':
    main()
