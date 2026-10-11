#!/usr/bin/env python3
"""
RQ3.2 dataset builder: join the RQ2.2 MethodSource codebook (construction +
dependency) with the unified complexity metrics (LOC / CC / CCTR / DUP, each
split into main-body / helper / total).

Inputs
  - RQ2.2 structure table (379 manually-validated MethodSource tests):
      rq2/results/rq2_2/pt_methodsource_structure_validated379.csv
  - Unified metrics (tree-sitter LOC/CC/CCTR joined with CCFinderSW dupPerc):
      $PT_METRICS/test_metrics_all_46projects_v2.csv（缺省用 rq3/results/rq3_1/ 下随包的 .gz）

Join key is (project, test_class, test_name).

Key resolution rules (all deviations are written to the join report):
  1. A key may match both a 'pt' and a 'nonpt' metrics row when a test class
     declares an overloaded method name (e.g. `@Test void f()` next to
     `@ParameterizedTest void f(X x)`). MethodSource tests are parameterized
     by definition, so the 'pt' row wins.
  2. Remaining multi-row keys with byte-identical metrics are deduplicated
     silently; ones that genuinely disagree keep the first row and are
     flagged as 'ambiguous_duplicate' in the report.
  3. Keys with no metrics row at all are dropped and flagged as
     'no_metrics_row' (the metrics run and the RQ2 run were taken from
     different project snapshots for a handful of tests).

Outputs (same folder)
  - rq32_methodsource_metrics.csv : one row per joined MethodSource test
  - rq32_join_report.csv          : dropped / flagged keys with reasons
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
import argparse
import csv
import os
import sys
from collections import defaultdict
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
from paths import METRICS_DIR, FINAL  # noqa: E402


csv.field_size_limit(10 ** 9)

HERE = os.path.dirname(os.path.abspath(__file__))
RQ2_DIR = _paths.RQ2_2_RESULTS
# The 379-test manually validated sample (default) vs the 5508-test
# auto-derived full population.
STRUCTURE_CSV = os.path.join(RQ2_DIR, "pt_methodsource_structure_validated379.csv")
FULL_CSV = os.path.join(RQ2_DIR, "rq22_methodsource_all.csv")
METRICS_CSV = _os.path.join(METRICS_DIR, "test_metrics_all_46projects_v2.csv")

# Metrics carried through to the analysis stage.
METRIC_COLS = [
    'category', 'helper_count',
    'self_loc', 'helper_loc_sum', 'total_loc',
    'self_cc', 'helper_cc_sum', 'total_cc',
    'self_cctr', 'helper_cctr_sum', 'total_cctr',
    'self_dupLines', 'self_totalLines', 'self_dupPerc',
    'helper_dupLines_sum', 'helper_totalLines_sum', 'helper_dupPerc',
    'total_dupLines', 'total_totalLines', 'total_dupPerc',
    'ambiguous_helper_count', 'unresolved_helper_count',
]

# RQ2 codebook columns carried through as grouping / context variables.
# The validated-sample table and the full-population table use overlapping but
# not identical schemas, so only the columns actually present are carried.
STRUCT_COLS_WANTED = [
    'construction', 'dependency', 'dependency_status', 'transformation_status',
    'hits_production', 'provider_declaring_class', 'n_test_scope_helpers',
    'n_params', 'n_sets', 'status',
]

# Columns used to decide whether two rows for the same key really disagree.
SIGNATURE_COLS = [c for c in METRIC_COLS if c not in ('category',)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--full', action='store_true',
                    help='use the 5508-test auto-derived full population instead of '
                         'the 379-test manually validated sample')
    ap.add_argument('--structure-csv', default=None, help='override the RQ2 codebook table')
    ap.add_argument('--prefix', default=None, help='output filename prefix')
    args = ap.parse_args()

    structure_csv = args.structure_csv or (FULL_CSV if args.full else STRUCTURE_CSV)
    prefix = args.prefix or ('rq32_full' if args.full else 'rq32')
    out_csv = os.path.join(RESULTS_DIR, f'{prefix}_methodsource_metrics.csv')
    report_csv = os.path.join(RESULTS_DIR, f'{prefix}_join_report.csv')
    print(f'codebook : {structure_csv}', file=sys.stderr)

    struct_rows = list(csv.DictReader(open(structure_csv, newline='', encoding='utf-8')))
    struct_cols = [c for c in STRUCT_COLS_WANTED if c in struct_rows[0]]
    struct_by_key = {}
    for r in struct_rows:
        struct_by_key[(r['project'], r['test_class'], r['test_name'])] = r
    print(f'RQ2.2 structure rows: {len(struct_rows)} ({len(struct_by_key)} unique keys)', file=sys.stderr)

    hits = defaultdict(list)
    scanned = 0
    with open(METRICS_CSV, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            scanned += 1
            k = (r['project'], r['test_class'], r['test_name'])
            if k in struct_by_key:
                hits[k].append(r)
    print(f'metrics rows scanned: {scanned}; keys matched: {len(hits)}', file=sys.stderr)

    out_rows = []
    report_rows = []

    for key, srow in struct_by_key.items():
        project, test_class, test_name = key
        candidates = hits.get(key, [])

        if not candidates:
            report_rows.append({
                'project': project, 'test_class': test_class, 'test_name': test_name,
                'issue': 'no_metrics_row', 'action': 'dropped',
                'detail': 'no (project, test_class, test_name) row in the metrics CSV',
            })
            continue

        pt_rows = [r for r in candidates if r['category'] == 'pt']
        if pt_rows and len(pt_rows) < len(candidates):
            report_rows.append({
                'project': project, 'test_class': test_class, 'test_name': test_name,
                'issue': 'pt_nonpt_overload', 'action': 'kept_pt_row',
                'detail': f'{len(candidates)} rows ({sum(1 for r in candidates if r["category"]=="nonpt")} nonpt) '
                          f'-> kept the parameterized one',
            })
        chosen_pool = pt_rows if pt_rows else candidates
        if not pt_rows:
            report_rows.append({
                'project': project, 'test_class': test_class, 'test_name': test_name,
                'issue': 'no_pt_row', 'action': 'kept_nonpt_row',
                'detail': 'metrics pipeline did not label this MethodSource test as parameterized',
            })

        if len(chosen_pool) > 1:
            sigs = {tuple(r[c] for c in SIGNATURE_COLS) for r in chosen_pool}
            if len(sigs) > 1:
                diff_cols = [c for c in SIGNATURE_COLS
                             if len({r[c] for r in chosen_pool}) > 1]
                report_rows.append({
                    'project': project, 'test_class': test_class, 'test_name': test_name,
                    'issue': 'ambiguous_duplicate', 'action': 'kept_first_row',
                    'detail': f'{len(chosen_pool)} pt rows disagreeing on: {";".join(diff_cols)}',
                })
            else:
                report_rows.append({
                    'project': project, 'test_class': test_class, 'test_name': test_name,
                    'issue': 'identical_duplicate', 'action': 'deduplicated',
                    'detail': f'{len(chosen_pool)} byte-identical pt rows',
                })

        mrow = chosen_pool[0]

        out = {'project': project, 'test_class': test_class, 'test_name': test_name}
        for c in struct_cols:
            out[c] = srow.get(c, '')
        for c in METRIC_COLS:
            out[c] = mrow.get(c, '')
        out_rows.append(out)

    fieldnames = ['project', 'test_class', 'test_name'] + struct_cols + METRIC_COLS
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    with open(report_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['project', 'test_class', 'test_name', 'issue', 'action', 'detail'])
        w.writeheader()
        w.writerows(report_rows)

    print(f'\nWrote {len(out_rows)} joined rows to {out_csv}', file=sys.stderr)
    print(f'Wrote {len(report_rows)} report rows to {report_csv}', file=sys.stderr)

    from collections import Counter
    print('\njoin issues:', dict(Counter(r['issue'] for r in report_rows)), file=sys.stderr)
    print('construction:', dict(Counter(r['construction'] for r in out_rows)), file=sys.stderr)
    print('dependency  :', dict(Counter(r['dependency'] for r in out_rows)), file=sys.stderr)


if __name__ == '__main__':
    main()
