#!/usr/bin/env python3
"""
Per-helper detail table: one row per (test, resolved test-scope helper) pair,
carrying that helper's own LOC / CC / CCTR.

The main pipeline (build_test_metrics_unified.py) only emits the *sum* over a
test's helpers, which is enough to say "this design moves complexity into the
helper layer" but not enough to say whether that complexity is **amortised**.
A helper called by 200 tests is shared infrastructure; a helper called by one
test is complexity that was displaced rather than shared. Answering that needs
the complexity attributed to individual helpers, which is what this produces.

It reuses build_test_metrics_unified's call-sequence parsing, source-class
classification and name+arity helper resolution unchanged -- same imports as
build_test_dup_metrics.py -- so every helper here is exactly the helper the
main pipeline counted, and `helper_cctr` values sum back to `helper_cctr_sum`.

Output: test_helper_detail_46projects.csv
  project, test_class, test_name, category, helper_name,
  helper_loc, helper_cc, helper_cctr, helper_cctr_eq,
  helper_n, helper_a, helper_m, helper_t, helper_t_eq

helper_cctr_eq is the de-biased CCTR variant, scoring @ParameterizedTest with
the same weight as @Test instead of double. It matters for any comparison that
crosses the PT boundary, where the +2 every parameterized test receives is a
property of the metric rather than of the test.

Usage: build_helper_detail.py [project ...] [--out path]
"""
# 向上找到 final/（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv
import sys
from collections import defaultdict

from build_test_metrics_unified import (
    PROJECTS, SKIP_PREFIXES, make_projects,
    build_source_class_sets, classify_declaring_class,
    get_prefix_and_rest, parse_rest, load_test_jsons, drop_data_method_refs,
    resolve_helper_snippet, score_of, ZERO_SCORE,
)

OUT_CSV = _os_root.path.join(_paths.METRICS_DIR, "test_helper_detail_46projects.csv")

FIELDS = ['project', 'test_class', 'test_name', 'category', 'helper_name',
          'helper_loc', 'helper_cc', 'helper_cctr', 'helper_cctr_eq',
          'helper_n', 'helper_a', 'helper_m', 'helper_t', 'helper_t_eq']


def process_project(proj):
    """Mirror of build_test_metrics_unified.process_tests, but emitting one row
    per (test, helper) instead of the per-test aggregate."""
    print(f"\n=== {proj['name']} ===", file=sys.stderr)
    parsed_tests = load_test_jsons(proj['aaa_dir'])
    production_classes, test_classes, test_class_files = build_source_class_sets(proj['base_dir'])
    print(f'  {len(parsed_tests)} tests, {len(test_classes)} test classes', file=sys.stderr)

    stats = defaultdict(int)
    rows = []

    for d in parsed_tests:
        test_class = d.get('testClassName', '')
        test_name = d.get('testCaseName', '')
        category = 'pt' if d.get('isParameterized', False) else 'nonpt'

        helpers_seen = set()
        skip = set()

        for raw in drop_data_method_refs(d.get('parsedStatementsSequence', [])):
            s = raw.strip()
            if not s:
                continue
            prefix, rest = get_prefix_and_rest(s)
            if prefix in SKIP_PREFIXES or prefix == 'NEW ANONYMOUS_CLASS':
                continue

            qualified, params, arity = parse_rest(rest)
            if qualified is None:
                continue

            if prefix == 'NEW':
                declaring_class = qualified
                last = qualified.rsplit('.', 1)[-1]
                lookup_name = f'{qualified}.{last}'
            else:
                declaring_class = qualified.rsplit('.', 1)[0] if '.' in qualified else qualified
                lookup_name = qualified

            if classify_declaring_class(declaring_class, production_classes, test_classes) != 'test':
                continue
            if lookup_name in helpers_seen or lookup_name in skip:
                continue

            status, snippet = resolve_helper_snippet(lookup_name, declaring_class, arity,
                                                     test_class_files, stats,
                                                     is_new=(prefix == 'NEW'))
            if status != 'ok':
                skip.add(lookup_name)
                continue

            helpers_seen.add(lookup_name)
            sc = score_of(snippet, method_name=lookup_name.rsplit('.', 1)[-1]) if snippet else dict(ZERO_SCORE)
            rows.append({
                'project': proj['name'], 'test_class': test_class, 'test_name': test_name,
                'category': category, 'helper_name': lookup_name,
                'helper_loc': sc['loc'], 'helper_cc': sc['cc'], 'helper_cctr': sc['cctr'],
                'helper_cctr_eq': sc['cctr_eq'],
                'helper_n': sc['n'], 'helper_a': sc['a'], 'helper_m': sc['m'],
                'helper_t': sc['t'], 'helper_t_eq': sc['t_eq'],
            })

    n_tests = len({(r['test_class'], r['test_name']) for r in rows})
    print(f'  {len(rows)} (test, helper) pairs over {n_tests} tests with >=1 helper', file=sys.stderr)
    return rows


def main():
    args = sys.argv[1:]
    out_csv = OUT_CSV
    names = []
    i = 0
    while i < len(args):
        if args[i] == '--out':
            out_csv = args[i + 1]
            i += 2
        else:
            names.append(args[i])
            i += 1
    projects = make_projects(names) if names else PROJECTS

    all_rows = []
    for proj in projects:
        all_rows.extend(process_project(proj))

    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    print(f'\nWrote {len(all_rows)} (test, helper) rows to {out_csv}', file=sys.stderr)


if __name__ == '__main__':
    main()
