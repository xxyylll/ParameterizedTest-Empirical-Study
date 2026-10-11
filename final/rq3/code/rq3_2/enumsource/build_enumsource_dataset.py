#!/usr/bin/env python3
"""
EnumSource dataset builder: join the RQ2.2 EnumSource codebook to the unified
complexity metrics (LOC / CC / CCTR / DUP, split main-body / helper / total).

EnumSource is kept separate from RQ3.2 because its codebook has a different
shape. It has no Literal/Dynamic construction dimension at all, and its
`dependency` column is *fully determined* by where the enum type lives
(production -> 'Production', test-scope -> L1/L2/L3/L4, external -> 'External'),
so it carries no information beyond `enum_location`. What EnumSource does offer
is three genuine design labels that MethodSource has no analogue for:

  enum_location    production / test / external -- does the test reuse a
                   production enum, or does it declare its own?
  enum_structure   Data-carrying / Label-based -- do the enum constants carry
                   fields (the data lives in the enum) or are they bare names?
  names_mode       ALL / SUBSET -- does the test run over every constant, or
                   pick an explicit subset via names=?

`enum_structure` is a property of the enum type itself, not a measurement of
the test, so unlike MethodSource's Structure dimension it is a legitimate
grouping variable rather than a restatement of the outcome.

Outputs: enumsource_metrics.csv, enumsource_join_report.csv
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'enumsource')
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import os
import sys
from collections import defaultdict, Counter
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
from paths import METRICS_DIR, FINAL  # noqa: E402


csv.field_size_limit(10 ** 9)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_CSV = _os_root.path.join(_paths.RQ2_2_RESULTS, 'rq22_enumsource_all.csv')
METRICS_CSV = _os.path.join(METRICS_DIR, "test_metrics_all_46projects_v2.csv")
OUT_CSV = os.path.join(RESULTS_DIR, "enumsource_metrics.csv")
REPORT_CSV = os.path.join(RESULTS_DIR, "enumsource_join_report.csv")

LABEL_COLS = ['enum_type', 'enum_location', 'dependency', 'enum_structure',
              'names_mode', 'n_enum_constants', 'n_params', 'n_sets', 'status']

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
SIGNATURE_COLS = [c for c in METRIC_COLS if c != 'category']

LOCATION_GROUP = {
    'production': 'production',
    'production(generated)': 'production_generated',
    'test': 'test',
    'external': 'external',
}


def main():
    src = {}
    for r in csv.DictReader(open(SRC_CSV, newline='', encoding='utf-8')):
        if not r.get('test_class'):
            continue
        src[(r['project'], r['test_class'], r['test_name'])] = r
    print(f'EnumSource codebook rows: {len(src)}', file=sys.stderr)

    hits = defaultdict(list)
    with open(METRICS_CSV, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            k = (r['project'], r['test_class'], r['test_name'])
            if k in src:
                hits[k].append(r)

    out_rows, report_rows = [], []
    for k, s in src.items():
        cands = hits.get(k, [])
        if not cands:
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'no_metrics_row', 'action': 'dropped', 'detail': ''})
            continue
        pt_rows = [r for r in cands if r['category'] == 'pt']
        pool = pt_rows if pt_rows else cands
        if pt_rows and len(pt_rows) < len(cands):
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'pt_nonpt_overload', 'action': 'kept_pt_row', 'detail': ''})
        if not pt_rows:
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'no_pt_row', 'action': 'kept_nonpt_row', 'detail': ''})
        if len(pool) > 1:
            sigs = {tuple(r[c] for c in SIGNATURE_COLS) for r in pool}
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'ambiguous_duplicate' if len(sigs) > 1 else 'identical_duplicate',
                                'action': 'kept_first_row' if len(sigs) > 1 else 'deduplicated',
                                'detail': f'{len(pool)} rows'})
        m = pool[0]
        row = {'project': k[0], 'test_class': k[1], 'test_name': k[2]}
        for c in LABEL_COLS:
            row[c] = s.get(c, '')
        row['location_group'] = LOCATION_GROUP.get(s.get('enum_location', ''), 'unknown')
        row['names_mode_group'] = 'ALL' if s.get('names_mode', '') == '' else 'SUBSET'
        for c in METRIC_COLS:
            row[c] = m.get(c, '')
        out_rows.append(row)

    fields = (['project', 'test_class', 'test_name'] + LABEL_COLS
              + ['location_group', 'names_mode_group'] + METRIC_COLS)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
    with open(REPORT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['project', 'test_class', 'test_name', 'issue', 'action', 'detail'])
        w.writeheader()
        w.writerows(report_rows)

    print(f'\nWrote {len(out_rows)} rows -> {os.path.basename(OUT_CSV)}', file=sys.stderr)
    print(f'Wrote {len(report_rows)} report rows', file=sys.stderr)
    ok = [r for r in out_rows if r['status'] == 'OK']
    print(f'\nstatus OK: {len(ok)}', file=sys.stderr)
    print('location  :', dict(Counter(r['location_group'] for r in ok)), file=sys.stderr)
    print('structure :', dict(Counter(r['enum_structure'] for r in ok)), file=sys.stderr)
    print('names_mode:', dict(Counter(r['names_mode_group'] for r in ok)), file=sys.stderr)
    print('dependency:', dict(Counter(r['dependency'] for r in ok)), file=sys.stderr)
    print('issues    :', dict(Counter(r['issue'] for r in report_rows)), file=sys.stderr)


if __name__ == '__main__':
    main()
