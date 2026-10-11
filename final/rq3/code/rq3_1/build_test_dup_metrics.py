#!/usr/bin/env python3
"""
DUP metric pipeline: per test, compute duplication percentage (dupPerc) for
the test's own body, its test-scope helpers, and the total -- from
CCFinderSW classwise clone-detection output (dup_result_ssk/<project>_dup/
result.txt, one per project; only src/test/java was scanned by CCFinderSW).

Per user's spec:
  - unit: line-ratio (dupPerc = duplicated lines / total lines), NOT tokens.
  - attribution: continuous overlap, not a binary in/out call. For a given
    method (test or helper), dupLines = count of that method's own physical
    lines (its full node span, matching CCFinderSW's own line-based clone
    reporting -- NOT the comment/blank-stripped "loc" from the CC/LOC/CCTR
    pipeline) that are covered by at least one CCFinderSW clone occurrence
    anywhere in the file. dupPerc = dupLines / totalLines.
  - cross-file duplication: every occurrence counts independently at its own
    location -- if test A's and test B's code were both reported as a clone
    pair, both A and B get their own dupLines contribution; this is not
    double counting, each side really does have that fraction duplicated.
  - aggregation:
      dupLines(total)  = dupLines(self)  + sum(dupLines(helper_i))
      totalLines(total)= totalLines(self)+ sum(totalLines(helper_i))
      dupPerc(total)    = dupLines(total) / totalLines(total)
    and likewise for the helper-only subtotal.

Reuses build_test_metrics_unified.py's call-sequence parsing, source-class
classification, and file/method-pool machinery (now line-span-aware) so
helper resolution is identical to the loc/cc/cctr pipeline -- the same
project source tree, the same test-source-only filter, the same
name+arity-based overload disambiguation.
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SSD, METRICS_DIR, APACHE_PROJECTS, DUP_RESULT, FINAL  # noqa: E402
import csv
import os
import sys
from collections import defaultdict

from build_test_metrics_unified import (

    PROJECTS, SKIP_PREFIXES, TS_PARSER, make_projects,
    build_source_class_sets, classify_declaring_class,
    get_prefix_and_rest, parse_rest, load_test_jsons, drop_data_method_refs,
    build_file_method_pool, resolve_test_class_file, resolve_helper_entry,
    resolve_test_class_file_with_chain, filter_by_class_path,
)

DUP_ROOT = DUP_RESULT
OUT_CSV = _os.path.join(METRICS_DIR, "test_dup_metrics_44projects.csv")
REPORT_CSV = _os.path.join(METRICS_DIR, "test_dup_metrics_44projects_report.csv")

TEMP_MARKER = 'temp_test_files/'


# ---------------------------------------------------------------------------
# CCFinderSW classwise result.txt parser
# ---------------------------------------------------------------------------

def parse_ccfinder_result(result_path, base_dir):
    """Return {real_file_path: set(duplicated 1-indexed line numbers)}."""
    file_paths = {}
    clone_lines_by_index = defaultdict(set)
    section = None

    with open(result_path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if line == '#begin{file description}':
                section = 'file'
                continue
            if line == '#end{file description}':
                section = None
                continue
            if line == '#begin{clone}':
                section = 'clone'
                continue
            if line == '#end{clone}':
                section = None
                continue
            if not line or line.startswith('#'):
                continue

            if section == 'file':
                parts = line.split('\t')
                if len(parts) < 4:
                    continue
                idx, temp_path = parts[0], parts[3]
                # 在 Windows 上跑 CCFinderSW 时 result.txt 里是反斜杠路径，
                # 统一成正斜杠再找 marker，否则一条都匹配不上，整个项目静默变成 0 结果。
                temp_path = temp_path.replace('\\', '/')
                pos = temp_path.find(TEMP_MARKER)
                if pos == -1:
                    continue
                suffix = temp_path[pos + len(TEMP_MARKER):]
                file_paths[idx] = os.path.join(base_dir, *suffix.split('/'))
            elif section == 'clone':
                parts = line.split('\t')
                if len(parts) < 4:
                    continue
                idx = parts[0]
                start_line = int(parts[1].split(',')[0])
                end_line = int(parts[2].split(',')[0])
                for ln in range(start_line, end_line + 1):
                    clone_lines_by_index[idx].add(ln)

    dup_lines_by_file = {}
    missing = 0
    for idx, lines in clone_lines_by_index.items():
        rp = file_paths.get(idx)
        if rp is None:
            continue
        if not os.path.exists(rp):
            missing += 1
            continue
        dup_lines_by_file.setdefault(rp, set()).update(lines)
    return dup_lines_by_file, missing, len(file_paths)


# ---------------------------------------------------------------------------
# Method-node lookup for the TEST itself (prefers non-static, to dodge the
# JUnit5 default @MethodSource same-name-static-provider collision)
# ---------------------------------------------------------------------------

def find_self_entry(pool, test_name, expected_chain):
    candidates = filter_by_class_path(pool.get(test_name, []), expected_chain)
    if not candidates:
        return None, 'not_found'
    non_static = [c for c in candidates if not c['is_static']]
    if len(non_static) == 1:
        return non_static[0], 'ok'
    if len(candidates) == 1:
        return candidates[0], 'ok'
    # still ambiguous (e.g. 2+ non-static overloads with the same name)
    return None, 'ambiguous'


def dup_span(file_path, start_line, end_line, dup_lines_by_file):
    total = end_line - start_line + 1
    if total <= 0:
        return 0, 0
    dup_set = dup_lines_by_file.get(file_path)
    if not dup_set:
        return 0, total
    dup = sum(1 for ln in range(start_line, end_line + 1) if ln in dup_set)
    return dup, total


ZERO = {'dup': 0, 'total': 0}


def add_span(dst, dup, total):
    dst['dup'] += dup
    dst['total'] += total


def perc(d):
    return d['dup'] / d['total'] if d['total'] else 0.0


# ---------------------------------------------------------------------------
# Per-project processing
# ---------------------------------------------------------------------------

def process_project(proj):
    name = proj['name']
    print(f'\n=== {name} ===', file=sys.stderr)
    result_path = os.path.join(DUP_ROOT, f'{name}_dup', 'result.txt')
    if not os.path.isfile(result_path):
        # CCFinderSW hasn't been run for this project (hadoop OOMs on this machine and is
        # being run elsewhere). Skip it rather than aborting the whole pipeline -- the
        # project simply contributes no dup rows, so its dup columns stay empty after the
        # merge, while every other project's metrics still get produced.
        print(f'  SKIPPED: no CCFinderSW result at {result_path}', file=sys.stderr)
        return [], [{'project': name, 'test': '', 'helper': '',
                     'issue': f'no CCFinderSW result.txt ({result_path}) -- project skipped'}]
    dup_lines_by_file, missing, total_files = parse_ccfinder_result(result_path, proj['base_dir'])
    print(f'  {total_files} files in CCFinderSW report, {len(dup_lines_by_file)} with >=1 duplicated line, '
          f'{missing} unresolved to a real path', file=sys.stderr)

    parsed_tests = load_test_jsons(proj['aaa_dir'])
    production_classes, test_classes, test_class_files = build_source_class_sets(proj['base_dir'])

    stats = defaultdict(int)
    rows = []
    report_rows = []

    for d in parsed_tests:
        test_class = d.get('testClassName', '')
        test_name = d.get('testCaseName', '')
        is_pt = d.get('isParameterized', False)
        test_qname = f'{test_class}.{test_name}'

        self_file, self_chain = resolve_test_class_file_with_chain(test_class, test_class_files)
        self_entry, self_status = (None, 'not_found')
        if self_file is not None:
            pool = build_file_method_pool(self_file)
            self_entry, self_status = find_self_entry(pool, test_name, self_chain)

        if self_entry is not None:
            self_dup, self_total = dup_span(self_file, self_entry['start_line'], self_entry['end_line'], dup_lines_by_file)
            stats['self_ok'] += 1
        else:
            self_dup, self_total = 0, 0
            report_rows.append({'project': name, 'test': test_qname, 'helper': test_qname, 'issue': f'test-self-{self_status}'})
            stats[f'self_{self_status}'] += 1

        helper_totals = dict(ZERO)
        helpers_seen = set()
        ambiguous_helpers = set()
        unresolved_helpers = set()
        seen_non_test = set()

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

            source_kind = classify_declaring_class(declaring_class, production_classes, test_classes)
            if source_kind != 'test':
                if lookup_name not in seen_non_test:
                    seen_non_test.add(lookup_name)
                    stats[f'filtered_{source_kind}'] += 1
                continue

            if lookup_name in helpers_seen or lookup_name in ambiguous_helpers or lookup_name in unresolved_helpers:
                continue

            status, entry = resolve_helper_entry(lookup_name, declaring_class, arity, test_class_files, stats,
                                                  is_new=(prefix == 'NEW'))
            if status == 'ok':
                helpers_seen.add(lookup_name)
                if entry['start_line'] is not None:
                    h_file = resolve_test_class_file(declaring_class, test_class_files)
                    h_dup, h_total = dup_span(h_file, entry['start_line'], entry['end_line'], dup_lines_by_file)
                else:
                    h_dup, h_total = 0, 0  # implicit default constructor: no source, no lines
                add_span(helper_totals, h_dup, h_total)
            elif status == 'ambiguous':
                ambiguous_helpers.add(lookup_name)
                report_rows.append({'project': name, 'test': test_qname, 'helper': lookup_name, 'issue': 'ambiguous'})
            else:
                unresolved_helpers.add(lookup_name)
                report_rows.append({'project': name, 'test': test_qname, 'helper': lookup_name, 'issue': 'not_found'})

        total_dup = self_dup + helper_totals['dup']
        total_total = self_total + helper_totals['total']

        rows.append({
            'project': name,
            'test_class': test_class,
            'test_name': test_name,
            'category': 'pt' if is_pt else 'nonpt',
            'helper_count': len(helpers_seen),
            'self_dupLines': self_dup,
            'self_totalLines': self_total,
            'self_dupPerc': round(self_dup / self_total, 6) if self_total else 0.0,
            'helper_dupLines_sum': helper_totals['dup'],
            'helper_totalLines_sum': helper_totals['total'],
            'helper_dupPerc': round(perc(helper_totals), 6),
            'total_dupLines': total_dup,
            'total_totalLines': total_total,
            'total_dupPerc': round(total_dup / total_total, 6) if total_total else 0.0,
            'ambiguous_helper_count': len(ambiguous_helpers),
            'unresolved_helper_count': len(unresolved_helpers),
            'helper_names': ';'.join(sorted(helpers_seen)),
            'ambiguous_helper_names': ';'.join(sorted(ambiguous_helpers)),
            'unresolved_helper_names': ';'.join(sorted(unresolved_helpers)),
        })

    print(f'  {len(parsed_tests)} tests, pt={sum(1 for r in rows if r["category"]=="pt")} '
          f'nonpt={sum(1 for r in rows if r["category"]=="nonpt")}', file=sys.stderr)
    print(f'  stats: {dict(stats)}', file=sys.stderr)
    return rows, report_rows


def main():
    # Usage: build_test_dup_metrics.py [project_name ...] [--out path] [--report path]
    args = sys.argv[1:]
    out_csv, report_csv = OUT_CSV, REPORT_CSV
    names = []
    i = 0
    while i < len(args):
        if args[i] == '--out':
            out_csv = args[i + 1]
            i += 2
        elif args[i] == '--report':
            report_csv = args[i + 1]
            i += 2
        else:
            names.append(args[i])
            i += 1
    projects = make_projects(names) if names else PROJECTS

    all_rows = []
    all_report_rows = []
    for proj in projects:
        rows, report_rows = process_project(proj)
        all_rows.extend(rows)
        all_report_rows.extend(report_rows)

    fieldnames = ['project', 'test_class', 'test_name', 'category', 'helper_count',
                  'self_dupLines', 'self_totalLines', 'self_dupPerc',
                  'helper_dupLines_sum', 'helper_totalLines_sum', 'helper_dupPerc',
                  'total_dupLines', 'total_totalLines', 'total_dupPerc',
                  'ambiguous_helper_count', 'unresolved_helper_count',
                  'helper_names', 'ambiguous_helper_names', 'unresolved_helper_names']

    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    with open(report_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['project', 'test', 'helper', 'issue'])
        w.writeheader()
        w.writerows(all_report_rows)

    print(f'\nWrote {len(all_rows)} test rows to {out_csv}', file=sys.stderr)
    print(f'Wrote {len(all_report_rows)} issue rows to {report_csv}', file=sys.stderr)


if __name__ == '__main__':
    main()
