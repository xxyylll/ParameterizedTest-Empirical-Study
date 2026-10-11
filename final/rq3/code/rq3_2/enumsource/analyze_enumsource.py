#!/usr/bin/env python3
"""
EnumSource analysis: do EnumSource design choices correspond to different
complexity profiles?

  A. enum_structure   Data-carrying vs Label-based  (+ stratified by location)
  B. enum_location    production vs test            (+ stratified by structure)
                      and Kruskal-Wallis across all four location groups
  C. dependency       L1 / L3 within test-scope enums (L2 n=2, L4 n=13)
  D. names_mode       ALL vs SUBSET (does the test run over every constant?)
  E. robustness       leave-one-project-out delta ranges

Structure and location are confounded (Label-based skews production 67%,
Data-carrying skews test 52%), so A and B are each also run inside strata of
the other -- the same treatment RQ3.2 gave Construction x Dependency.

Reported for main-body / helper / total x LOC / CC / CCTR / DUP%.

Outputs: enumsource_twogroup_stats.csv, enumsource_location_kruskal.csv,
         enumsource_dependency_pairwise.csv, enumsource_descriptives.csv,
         enumsource_robustness_loo.csv, enumsource_population.csv
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

# pt_stats 位于 rq3_2/ 根目录，四个子分析共用
import sys as _s2, os as _o2
_s2.path.insert(0, _o2.path.dirname(_o2.path.dirname(_o2.path.abspath(__file__))))
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pt_stats import (mann_whitney_u, cliffs_magnitude, kruskal_wallis,
                      holm_adjust, bh_adjust, describe)

HERE = os.path.dirname(os.path.abspath(__file__))
IN_CSV = os.path.join(RESULTS_DIR, "enumsource_metrics.csv")

METRICS = []
for mid, label, cols, is_float in [
    ('loc', 'LOC', ('self_loc', 'helper_loc_sum', 'total_loc'), False),
    ('cc', 'CC', ('self_cc', 'helper_cc_sum', 'total_cc'), False),
    ('cctr', 'CCTR', ('self_cctr', 'helper_cctr_sum', 'total_cctr'), False),
    ('dupPerc', 'DUP%', ('self_dupPerc', 'helper_dupPerc', 'total_dupPerc'), True),
    ('dupLines', 'DUP lines', ('self_dupLines', 'helper_dupLines_sum', 'total_dupLines'), True),
]:
    for scope, scope_label, col in zip(('self', 'helper', 'total'),
                                        ('main-body', 'helper', 'total'), cols):
        METRICS.append({'metric_label': label, 'scope_label': scope_label,
                        'column': col, 'is_float': is_float})

HEADLINE = {'self_loc', 'helper_loc_sum', 'total_loc', 'self_cc', 'helper_cc_sum', 'total_cc',
            'self_cctr', 'helper_cctr_sum', 'total_cctr',
            'self_dupPerc', 'helper_dupPerc', 'total_dupPerc'}
LOCATIONS = ['production', 'production_generated', 'test']


def enum_analysable(r):
    """The RQ2.2 analysable population, reproduced exactly.

    RQ2.2 (`plot_construction_distribution.py::enum_analysable`) admits an
    EnumSource test when all three hold: n_sets could be resolved, the enum's
    structure is not 'n/a', and the enum is not External (a JDK or third-party
    enum is not declared in the project, so neither how it is represented nor
    how it is used can be characterised). That yields **814** tests.

    This analysis uses the same definition rather than its own `status == OK`
    filter, so the denominator here matches the one reported in RQ2.2 and no
    before/after discrepancy has to be explained away. The 814 are a strict
    subset of the 834 status-OK rows; the 20 dropped are 15 External, 4 with an
    unresolved n_sets and 1 with structure 'n/a'.
    """
    return ((r.get('n_sets') or '').strip()
            and (r.get('enum_structure') or '').strip() != 'n/a'
            and (r.get('dependency') or '').strip() != 'External')


def values(rows, meta):
    out = []
    for r in rows:
        raw = r[meta['column']]
        if raw != '':
            out.append(float(raw) if meta['is_float'] else int(raw))
    return out


def fmt(x, nd=4):
    return '' if x is None or x != x else f'{x:.{nd}f}'


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {len(rows):4d} rows -> {os.path.basename(path)}', file=sys.stderr)


def two_group(meta, a_rows, b_rows):
    """delta > 0 means group A larger."""
    va, vb = values(a_rows, meta), values(b_rows, meta)
    if not va or not vb:
        return None
    delta, p = mann_whitney_u(va, vb)
    da, db = describe(va), describe(vb)
    return {'n_a': da['n'], 'n_b': db['n'],
            'median_a': fmt(da['median']), 'median_b': fmt(db['median']),
            'cliffs_delta': fmt(delta), 'magnitude': cliffs_magnitude(delta),
            'p_raw': fmt(p, 6), '_p': p}


def contrast(rows, name, a_label, b_label, col, strata=None):
    """One contrast (A vs B) on `col`, optionally repeated inside each stratum."""
    out = []
    ps = []
    for meta in METRICS:
        a = [r for r in rows if r[col] == a_label]
        b = [r for r in rows if r[col] == b_label]
        base = two_group(meta, a, b)
        if base is None:
            continue
        row = {'contrast': name, 'group_a': a_label, 'group_b': b_label,
               'stratum': 'all', 'scope': meta['scope_label'], 'metric': meta['metric_label']}
        row.update(base)
        ps.append(row.pop('_p'))
        out.append(row)
        for scol, sval in (strata or []):
            sa = [r for r in a if r[scol] == sval]
            sb = [r for r in b if r[scol] == sval]
            st = two_group(meta, sa, sb)
            if st is None:
                continue
            srow = {'contrast': name, 'group_a': a_label, 'group_b': b_label,
                    'stratum': f'{scol}={sval}', 'scope': meta['scope_label'],
                    'metric': meta['metric_label']}
            srow.update(st)
            srow.pop('_p')
            out.append(srow)
    # BH across the metric family, applied to the unstratified rows only
    base_rows = [r for r in out if r['stratum'] == 'all']
    for r, q in zip(base_rows, bh_adjust(ps)):
        r['p_bh_across_metrics'] = fmt(q, 6)
    for r in out:
        r.setdefault('p_bh_across_metrics', '')
    return out


def main():
    all_rows = list(csv.DictReader(open(IN_CSV, newline='', encoding='utf-8')))
    rows = [r for r in all_rows if enum_analysable(r)]
    print(f'loaded {len(all_rows)} joined EnumSource tests; '
          f'{len(rows)} in the RQ2.2 analysable population '
          f'({len({r["project"] for r in rows})} projects)', file=sys.stderr)

    with open(os.path.join(RESULTS_DIR, 'enumsource_population.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['dimension', 'group', 'n', 'projects'])
        for col in ('enum_structure', 'location_group', 'names_mode_group', 'dependency'):
            for g in sorted({r[col] for r in rows}):
                sel = [r for r in rows if r[col] == g]
                w.writerow([col, g, len(sel), len({r['project'] for r in sel})])

    # ---- project concentration -------------------------------------------
    # EnumSource usage is heavily concentrated (jena alone is ~29% of all
    # tests and 64% of test-located enums), so a contrast between groups can
    # degenerate into a contrast between projects. This table is what the
    # leave-one-project-out check in section E should be read against.
    conc = []
    for col in ('enum_structure', 'location_group', 'names_mode_group', 'dependency'):
        for g in sorted({r[col] for r in rows}):
            sel = [r for r in rows if r[col] == g]
            by_proj = Counter(r['project'] for r in sel)
            top, topn = by_proj.most_common(1)[0]
            conc.append({'dimension': col, 'group': g, 'n': len(sel),
                         'projects': len(by_proj), 'top_project': top,
                         'top_project_n': topn,
                         'top_project_share': f'{topn / len(sel):.4f}'})
    write_csv(os.path.join(RESULTS_DIR, 'enumsource_project_concentration.csv'),
              ['dimension', 'group', 'n', 'projects', 'top_project', 'top_project_n',
               'top_project_share'], conc)

    # ---- descriptives ----
    desc = []
    for meta in METRICS:
        for col in ('enum_structure', 'location_group', 'names_mode_group'):
            for g in sorted({r[col] for r in rows}):
                d = describe(values([r for r in rows if r[col] == g], meta))
                desc.append({'dimension': col, 'group': g, 'scope': meta['scope_label'],
                             'metric': meta['metric_label'], 'n': d['n'],
                             'median': fmt(d['median']), 'q1': fmt(d['q1']),
                             'q3': fmt(d['q3']), 'mean': fmt(d['mean'])})
    write_csv(os.path.join(RESULTS_DIR, 'enumsource_descriptives.csv'),
              ['dimension', 'group', 'scope', 'metric', 'n', 'median', 'q1', 'q3', 'mean'], desc)

    # ---- A / B / D two-group contrasts, each stratified by the other ----
    two = []
    two += contrast(rows, 'structure', 'Data-carrying', 'Label-based', 'enum_structure',
                    strata=[('location_group', 'production'), ('location_group', 'test')])
    two += contrast(rows, 'location', 'test', 'production', 'location_group',
                    strata=[('enum_structure', 'Data-carrying'), ('enum_structure', 'Label-based')])
    two += contrast(rows, 'names_mode', 'SUBSET', 'ALL', 'names_mode_group',
                    strata=[('enum_structure', 'Data-carrying'), ('enum_structure', 'Label-based')])
    write_csv(os.path.join(RESULTS_DIR, 'enumsource_twogroup_stats.csv'),
              ['contrast', 'group_a', 'group_b', 'stratum', 'scope', 'metric',
               'n_a', 'n_b', 'median_a', 'median_b', 'cliffs_delta', 'magnitude',
               'p_raw', 'p_bh_across_metrics'], two)

    # ---- B. Kruskal-Wallis across the four location groups ----
    kw = []
    kw_p = []
    for meta in METRICS:
        groups = [values([r for r in rows if r['location_group'] == l], meta) for l in LOCATIONS]
        H, df, p = kruskal_wallis(groups)
        kw.append({'scope': meta['scope_label'], 'metric': meta['metric_label'],
                   'H': fmt(H), 'df': df, 'p_raw': fmt(p, 6),
                   'n_total': sum(len(g) for g in groups)})
        kw_p.append(p)
    for r, q in zip(kw, bh_adjust(kw_p)):
        r['p_bh'] = fmt(q, 6)
        r['significant_005'] = 'yes' if float(r['p_raw']) < 0.05 else 'no'
    write_csv(os.path.join(RESULTS_DIR, 'enumsource_location_kruskal.csv'),
              ['scope', 'metric', 'n_total', 'H', 'df', 'p_raw', 'p_bh', 'significant_005'], kw)

    # ---- C. dependency inside test-scope enums ----
    test_rows = [r for r in rows if r['location_group'] == 'test']
    levels = [l for l in ('L1', 'L2', 'L3', 'L4')
              if len([r for r in test_rows if r['dependency'] == l]) >= 10]
    print(f'  test-scope dependency levels with n>=10: {levels}', file=sys.stderr)
    dep = []
    for meta in METRICS:
        groups = {l: [r for r in test_rows if r['dependency'] == l] for l in levels}
        H, df, p = kruskal_wallis([values(groups[l], meta) for l in levels])
        block = []
        pairs = [(a, b) for i, a in enumerate(levels) for b in levels[i + 1:]]
        for a, b in pairs:
            res = two_group(meta, groups[b], groups[a])   # delta>0 => higher level larger
            if res is None:
                continue
            block.append({'scope': meta['scope_label'], 'metric': meta['metric_label'],
                          'comparison': f'{b} vs {a}', 'n_high': res['n_a'], 'n_low': res['n_b'],
                          'median_high': res['median_a'], 'median_low': res['median_b'],
                          'cliffs_delta': res['cliffs_delta'], 'magnitude': res['magnitude'],
                          'p_raw': res['p_raw'], '_p': res['_p'],
                          'kw_H': fmt(H), 'kw_p': fmt(p, 6)})
        ps = [r['_p'] for r in block]
        for r, h, q in zip(block, holm_adjust(ps), bh_adjust(ps)):
            r['p_holm'] = fmt(h, 6)
            r['p_bh'] = fmt(q, 6)
            del r['_p']
        dep.extend(block)
    write_csv(os.path.join(RESULTS_DIR, 'enumsource_dependency_pairwise.csv'),
              ['scope', 'metric', 'comparison', 'n_high', 'n_low', 'median_high', 'median_low',
               'cliffs_delta', 'magnitude', 'p_raw', 'p_holm', 'p_bh', 'kw_H', 'kw_p'], dep)

    # ---- E. leave-one-project-out ----
    loo = []
    for name, col, a_label, b_label in [('structure', 'enum_structure', 'Data-carrying', 'Label-based'),
                                        ('location', 'location_group', 'test', 'production'),
                                        ('names_mode', 'names_mode_group', 'SUBSET', 'ALL')]:
        a_all = [r for r in rows if r[col] == a_label]
        b_all = [r for r in rows if r[col] == b_label]
        projects = sorted({r['project'] for r in a_all + b_all})
        for meta in METRICS:
            if meta['column'] not in HEADLINE:
                continue
            full, _ = mann_whitney_u(values(a_all, meta), values(b_all, meta))
            ds = []
            for p_ in projects:
                d, _ = mann_whitney_u(values([r for r in a_all if r['project'] != p_], meta),
                                      values([r for r in b_all if r['project'] != p_], meta))
                if d == d:
                    ds.append((p_, d))
            if not ds:
                continue
            lo_, hi_ = min(ds, key=lambda t: t[1]), max(ds, key=lambda t: t[1])
            loo.append({'contrast': f'{a_label} vs {b_label}', 'scope': meta['scope_label'],
                        'metric': meta['metric_label'], 'delta_full': fmt(full),
                        'delta_min_loo': fmt(lo_[1]), 'delta_max_loo': fmt(hi_[1]),
                        'min_when_dropping': lo_[0], 'max_when_dropping': hi_[0],
                        'sign_stable': 'yes' if lo_[1] * hi_[1] > 0 else 'no'})
    write_csv(os.path.join(RESULTS_DIR, 'enumsource_robustness_loo.csv'),
              ['contrast', 'scope', 'metric', 'delta_full', 'delta_min_loo', 'delta_max_loo',
               'min_when_dropping', 'max_when_dropping', 'sign_stable'], loo)

    for name in ('structure', 'location', 'names_mode'):
        print(f'\n=== {name} (delta > 0 = first group larger) ===', file=sys.stderr)
        for r in two:
            if r['contrast'] == name and r['stratum'] == 'all' and r['metric'] != 'DUP lines':
                strat = [s for s in two if s['contrast'] == name and s['stratum'] != 'all'
                         and s['scope'] == r['scope'] and s['metric'] == r['metric']]
                extra = '  |  ' + '  '.join(f"{s['stratum'].split('=')[1][:9]}: {s['cliffs_delta']}"
                                             for s in strat)
                print(f"  {r['scope']:>9s} {r['metric']:>5s}: d={r['cliffs_delta']:>7s} "
                      f"({r['magnitude']:>10s}) p={r['p_raw']:>8s}{extra}", file=sys.stderr)


if __name__ == '__main__':
    main()
