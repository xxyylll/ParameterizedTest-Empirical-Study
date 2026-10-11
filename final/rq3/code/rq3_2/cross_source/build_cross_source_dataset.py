#!/usr/bin/env python3
"""
RQ3.3 dataset builder: label every parameterized test with the parameter
source it uses, and join to the unified complexity metrics.

Motivation. RQ3.2 asked whether design choices *within* MethodSource change
the complexity profile, and found that they do -- but only on the helper side.
That question cannot be asked of the other sources: ValueSource, CsvSource and
CsvFileSource pin construction and dependency by language construct (e.g.
CsvSource is L0 for 100% of its 366 tests), so they have no design space to
vary. The question that *does* generalise is the one level up: **does the
choice of source type itself determine the complexity profile?** Inline
sources have no helper layer at all by construction, provider-backed sources
have an arbitrary one.

Sources and the mechanism family each belongs to:

    ValueSource, CsvSource          inline      argument data written into the annotation
    EnumSource                      type        data comes from an enum type
    MethodSource, ArgumentsSource,
    FieldSource                     provider    data comes from user-written code
    CsvFileSource                   file        data comes from a classpath resource

Notes on the join:
  - 14 of 8,279 tests appear under more than one source annotation (e.g.
    @MethodSource + @EnumSource). Their metrics cannot be attributed to a
    single source, so they are excluded and listed in the join report.
  - pt/nonpt overload and duplicate-row handling follow RQ3.2's rules.
  - n_params / n_sets are carried from each source table; they are available
    for every source and are used downstream to control for data volume.

Outputs: cross_source_metrics.csv, cross_source_join_report.csv
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'cross_source')
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
RQ2_DIR = _paths.RQ2_2_RESULTS
METRICS_CSV = _os.path.join(METRICS_DIR, "test_metrics_all_46projects_v2.csv")
OUT_CSV = os.path.join(RESULTS_DIR, "cross_source_metrics.csv")
REPORT_CSV = os.path.join(RESULTS_DIR, "cross_source_join_report.csv")

# table -> (default source label, or None to read it from the row's 'source' column)
SOURCE_TABLES = [
    ("MethodSource", os.path.join(RQ2_DIR, "rq22_methodsource_all.csv")),
    ("ValueSource", os.path.join(RQ2_DIR, "rq22_valuesource_all.csv")),
    ("EnumSource", os.path.join(RQ2_DIR, "rq22_enumsource_all.csv")),
    ("CsvSource", os.path.join(RQ2_DIR, "rq22_csvsource_all.csv")),
    ("CsvFileSource", os.path.join(RQ2_DIR, "rq22_csvfilesource_all.csv")),
    (None, os.path.join(RQ2_DIR, "rq22_argumentssource_fieldsource_all.csv")),
]

FAMILY = {
    'ValueSource': 'inline', 'CsvSource': 'inline',
    'EnumSource': 'type',
    'MethodSource': 'provider', 'ArgumentsSource': 'provider', 'FieldSource': 'provider',
    'CsvFileSource': 'file',
}

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


def main():
    # ---- collect every (key -> source label) ----
    owners = defaultdict(set)
    context = {}
    for default_label, path in SOURCE_TABLES:
        for r in csv.DictReader(open(path, newline='', encoding='utf-8')):
            if not r.get('test_class'):
                continue
            label = default_label or r.get('source', '').strip()
            if not label:
                continue
            k = (r['project'], r['test_class'], r['test_name'])
            owners[k].add(label)
            context[(k, label)] = r
    print(f'{len(owners)} distinct parameterized tests across {len(SOURCE_TABLES)} source tables',
          file=sys.stderr)

    report_rows = []
    single = {}
    for k, labels in owners.items():
        if len(labels) > 1:
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'multi_source', 'action': 'dropped',
                                'detail': '+'.join(sorted(labels))})
            continue
        single[k] = next(iter(labels))
    print(f'  {len(report_rows)} dropped as multi-source; {len(single)} single-source', file=sys.stderr)

    # ---- join to metrics ----
    hits = defaultdict(list)
    with open(METRICS_CSV, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            k = (r['project'], r['test_class'], r['test_name'])
            if k in single:
                hits[k].append(r)

    out_rows = []
    for k, label in single.items():
        cands = hits.get(k, [])
        if not cands:
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'no_metrics_row', 'action': 'dropped', 'detail': label})
            continue
        pt_rows = [r for r in cands if r['category'] == 'pt']
        pool = pt_rows if pt_rows else cands
        if pt_rows and len(pt_rows) < len(cands):
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'pt_nonpt_overload', 'action': 'kept_pt_row', 'detail': label})
        if not pt_rows:
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'no_pt_row', 'action': 'kept_nonpt_row', 'detail': label})
        if len(pool) > 1:
            sigs = {tuple(r[c] for c in SIGNATURE_COLS) for r in pool}
            report_rows.append({'project': k[0], 'test_class': k[1], 'test_name': k[2],
                                'issue': 'ambiguous_duplicate' if len(sigs) > 1 else 'identical_duplicate',
                                'action': 'kept_first_row' if len(sigs) > 1 else 'deduplicated',
                                'detail': f'{len(pool)} rows'})
        m = pool[0]
        src = context[(k, label)]
        row = {'project': k[0], 'test_class': k[1], 'test_name': k[2],
               'source_type': label, 'family': FAMILY.get(label, 'other'),
               'n_params': src.get('n_params', ''), 'n_sets': src.get('n_sets', '')}
        for c in METRIC_COLS:
            row[c] = m.get(c, '')
        out_rows.append(row)

    fields = ['project', 'test_class', 'test_name', 'source_type', 'family',
              'n_params', 'n_sets'] + METRIC_COLS
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
    with open(REPORT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['project', 'test_class', 'test_name', 'issue', 'action', 'detail'])
        w.writeheader()
        w.writerows(report_rows)

    print(f'\nWrote {len(out_rows)} rows -> {os.path.basename(OUT_CSV)}', file=sys.stderr)
    print(f'Wrote {len(report_rows)} report rows -> {os.path.basename(REPORT_CSV)}', file=sys.stderr)
    print('\nby source :', dict(Counter(r['source_type'] for r in out_rows).most_common()), file=sys.stderr)
    print('by family :', dict(Counter(r['family'] for r in out_rows).most_common()), file=sys.stderr)
    print('issues    :', dict(Counter(r['issue'] for r in report_rows)), file=sys.stderr)


if __name__ == '__main__':
    main()
