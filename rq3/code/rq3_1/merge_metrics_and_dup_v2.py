#!/usr/bin/env python3
"""
Join test_metrics_unified_46projects_v2.csv (loc/cc/cctr, tree-sitter) with
test_dup_metrics_44projects.csv (dupPerc, CCFinderSW) on
(project, test_class, test_name), into one combined CSV for downstream
statistics/heatmap use.
"""
# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv

METRICS_CSV = _os_root.path.join(_paths.METRICS_DIR, "test_metrics_unified_46projects_v2.csv")
DUP_CSV = _os_root.path.join(_paths.METRICS_DIR, "test_dup_metrics_44projects.csv")
OUT_CSV = _os_root.path.join(_paths.METRICS_DIR, "test_metrics_all_46projects_v2.csv")

DUP_FIELDS = ['self_dupLines', 'self_totalLines', 'self_dupPerc',
              'helper_dupLines_sum', 'helper_totalLines_sum', 'helper_dupPerc',
              'total_dupLines', 'total_totalLines', 'total_dupPerc']


def load(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    metrics_rows = load(METRICS_CSV)
    dup_rows = load(DUP_CSV)
    dup_by_key = {(r['project'], r['test_class'], r['test_name']): r for r in dup_rows}

    out_rows = []
    missing = 0
    for r in metrics_rows:
        key = (r['project'], r['test_class'], r['test_name'])
        d = dup_by_key.get(key)
        merged = dict(r)
        if d is None:
            missing += 1
            for f in DUP_FIELDS:
                merged[f] = ''
        else:
            for f in DUP_FIELDS:
                merged[f] = d[f]
        out_rows.append(merged)

    fieldnames = list(metrics_rows[0].keys()) + DUP_FIELDS
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f'Wrote {len(out_rows)} rows to {OUT_CSV} ({missing} missing dup match)')


if __name__ == '__main__':
    main()
