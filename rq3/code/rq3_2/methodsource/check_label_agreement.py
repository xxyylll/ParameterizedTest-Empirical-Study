#!/usr/bin/env python3
"""
Validity gate for the full-population RQ3.2 run: the 379-test sample carries
manually validated construction/dependency labels, the 5508-test full table
carries auto-derived ones. This measures how far the two agree on the tests
they share, so the full-population results can be read with a known error rate.

Writes rq32_label_agreement.csv (confusion counts) and prints the summary.
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'methodsource')
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rq32_stats import cohens_kappa
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
from paths import METRICS_DIR, FINAL  # noqa: E402


HERE = os.path.dirname(os.path.abspath(__file__))
RQ2_DIR = _paths.RQ2_2_RESULTS
MANUAL = os.path.join(RQ2_DIR, "pt_methodsource_structure_validated379.csv")
AUTO = os.path.join(RQ2_DIR, "rq22_methodsource_all.csv")
OUT = os.path.join(RESULTS_DIR, "rq32_label_agreement.csv")


def key(r):
    return (r['project'], r['test_class'], r['test_name'])


def main():
    manual = {key(r): r for r in csv.DictReader(open(MANUAL, newline='', encoding='utf-8'))}
    auto = {key(r): r for r in csv.DictReader(open(AUTO, newline='', encoding='utf-8'))}
    shared = [k for k in manual if k in auto]
    print(f'manual={len(manual)}  auto={len(auto)}  shared={len(shared)}', file=sys.stderr)

    out_rows = []
    for field in ('construction', 'dependency'):
        pairs = [(manual[k][field], auto[k][field]) for k in shared
                 if manual[k][field] != '' and auto[k][field] != '']
        kappa, po, pe, n = cohens_kappa(pairs)
        print(f'\n=== {field} ===', file=sys.stderr)
        print(f'  n={n}  agreement={po:.4f}  expected={pe:.4f}  Cohen kappa={kappa:.4f}', file=sys.stderr)
        conf = Counter(pairs)
        disagree = {k: v for k, v in conf.items() if k[0] != k[1]}
        if disagree:
            print('  disagreements (manual -> auto):', file=sys.stderr)
            for (m, a), c in sorted(disagree.items(), key=lambda t: -t[1]):
                print(f'    {m:>10s} -> {a:<10s} {c}', file=sys.stderr)
        for (m, a), c in sorted(conf.items()):
            out_rows.append({'field': field, 'manual': m, 'auto': a, 'n': c,
                             'agree': 'yes' if m == a else 'no'})
        out_rows.append({'field': field, 'manual': '__SUMMARY__', 'auto': '',
                         'n': n, 'agree': f'po={po:.4f};kappa={kappa:.4f}'})

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['field', 'manual', 'auto', 'n', 'agree'])
        w.writeheader()
        w.writerows(out_rows)
    print(f'\nwrote {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()
