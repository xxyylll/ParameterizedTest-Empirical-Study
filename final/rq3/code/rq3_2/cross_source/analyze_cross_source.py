#!/usr/bin/env python3
"""
RQ3.3 analysis: does the choice of parameter source determine the complexity
profile of a parameterized test?

  A. Source type (7 groups)  -> Kruskal-Wallis, then all pairwise Mann-Whitney U
                                + Cliff's delta, Holm (FWER) and BH (FDR)
                                corrected within each metric
  B. Mechanism family        -> inline / type / provider / file, same treatment
  C. Data-volume control     -> provider-vs-inline delta recomputed within
                                quartile strata of n_sets (the number of
                                parameter sets), because source choice is partly
                                driven by how much data a test needs
  D. Robustness              -> leave-one-project-out delta ranges

As in RQ3.2 every comparison is reported for main-body / helper / total x
LOC / CC / CCTR / DUP%, so the analysis separates "this source costs more"

# pt_stats 位于 rq3_2/ 根目录，四个子分析共用
import sys as _s2, os as _o2
_s2.path.insert(0, _o2.path.dirname(_o2.path.dirname(_o2.path.abspath(__file__))))
from "this source moves the cost out of the test body".

Outputs: cross_source_descriptives.csv, cross_source_kruskal.csv,
         cross_source_pairwise.csv, cross_source_family_pairwise.csv,
         cross_source_volume_strata.csv, cross_source_robustness_loo.csv,
         cross_source_population.csv
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
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pt_stats import (mann_whitney_u, cliffs_magnitude, kruskal_wallis,
                      holm_adjust, bh_adjust, describe, quantile)

HERE = os.path.dirname(os.path.abspath(__file__))
IN_CSV = os.path.join(RESULTS_DIR, "cross_source_metrics.csv")

# ordered by how far the argument data lives from the test method
SOURCES = ['ValueSource', 'CsvSource', 'EnumSource', 'CsvFileSource',
           'MethodSource', 'ArgumentsSource', 'FieldSource']
FAMILIES = ['inline', 'type', 'file', 'provider']
BASELINE = 'ValueSource'

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
        METRICS.append({'metric': mid, 'metric_label': label, 'scope': scope,
                        'scope_label': scope_label, 'column': col, 'is_float': is_float})

HEADLINE = {'self_loc', 'helper_loc_sum', 'total_loc', 'self_cc', 'helper_cc_sum',
            'total_cc', 'self_cctr', 'helper_cctr_sum', 'total_cctr',
            'self_dupPerc', 'helper_dupPerc', 'total_dupPerc'}


def values(rows, meta):
    out = []
    for r in rows:
        raw = r[meta['column']]
        if raw == '':
            continue
        out.append(float(raw) if meta['is_float'] else int(raw))
    return out


def fmt(x, nd=4):
    if x is None or x != x:
        return ''
    return f'{x:.{nd}f}'


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {len(rows):4d} rows -> {os.path.basename(path)}', file=sys.stderr)


def pairwise_block(meta, groups, order, label_key):
    """All pairs within `order`; delta > 0 means the SECOND-listed group is larger."""
    block = []
    pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:]]
    for a, b in pairs:
        va, vb = values(groups[a], meta), values(groups[b], meta)
        if not va or not vb:
            continue
        delta, p = mann_whitney_u(vb, va)
        da, db = describe(va), describe(vb)
        block.append({'scope': meta['scope_label'], 'metric': meta['metric_label'],
                      label_key: f'{b} vs {a}', 'n_b': db['n'], 'n_a': da['n'],
                      'median_b': fmt(db['median']), 'median_a': fmt(da['median']),
                      'cliffs_delta': fmt(delta), 'magnitude': cliffs_magnitude(delta),
                      'p_raw': fmt(p, 6), '_p': p})
    ps = [r['_p'] for r in block]
    for r, h, q in zip(block, holm_adjust(ps), bh_adjust(ps)):
        r['p_holm'] = fmt(h, 6)
        r['p_bh'] = fmt(q, 6)
        del r['_p']
    return block


def main():
    rows = list(csv.DictReader(open(IN_CSV, newline='', encoding='utf-8')))
    by_source = {s: [r for r in rows if r['source_type'] == s] for s in SOURCES}
    by_family = {f: [r for r in rows if r['family'] == f] for f in FAMILIES}
    print(f'loaded {len(rows)} tests', file=sys.stderr)
    for s in SOURCES:
        print(f'   {s:16s} n={len(by_source[s]):5d}  projects={len({r["project"] for r in by_source[s]})}',
              file=sys.stderr)

    with open(os.path.join(RESULTS_DIR, 'cross_source_population.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['group', 'kind', 'n', 'projects'])
        for s in SOURCES:
            w.writerow([s, 'source', len(by_source[s]), len({r['project'] for r in by_source[s]})])
        for fam in FAMILIES:
            w.writerow([fam, 'family', len(by_family[fam]), len({r['project'] for r in by_family[fam]})])

    # ---------------- A. descriptives + Kruskal-Wallis + pairwise ----------
    desc, kw_out, pair_out, fam_out = [], [], [], []
    kw_p = []
    for meta in METRICS:
        for s in SOURCES:
            d = describe(values(by_source[s], meta))
            desc.append({'scope': meta['scope_label'], 'metric': meta['metric_label'], 'group': s,
                         'kind': 'source', 'n': d['n'], 'median': fmt(d['median']),
                         'q1': fmt(d['q1']), 'q3': fmt(d['q3']), 'mean': fmt(d['mean'])})
        for fam in FAMILIES:
            d = describe(values(by_family[fam], meta))
            desc.append({'scope': meta['scope_label'], 'metric': meta['metric_label'], 'group': fam,
                         'kind': 'family', 'n': d['n'], 'median': fmt(d['median']),
                         'q1': fmt(d['q1']), 'q3': fmt(d['q3']), 'mean': fmt(d['mean'])})

        H, df, p = kruskal_wallis([values(by_source[s], meta) for s in SOURCES])
        Hf, dff, pf = kruskal_wallis([values(by_family[f], meta) for f in FAMILIES])
        kw_out.append({'scope': meta['scope_label'], 'metric': meta['metric_label'],
                       'H_source': fmt(H), 'df_source': df, 'p_source': fmt(p, 6),
                       'H_family': fmt(Hf), 'df_family': dff, 'p_family': fmt(pf, 6)})
        kw_p.append(p)

        pair_out.extend(pairwise_block(meta, by_source, SOURCES, 'comparison'))
        fam_out.extend(pairwise_block(meta, by_family, FAMILIES, 'comparison'))
    for r, q in zip(kw_out, bh_adjust(kw_p)):
        r['p_source_bh'] = fmt(q, 6)

    write_csv(os.path.join(RESULTS_DIR, 'cross_source_descriptives.csv'),
              ['scope', 'metric', 'group', 'kind', 'n', 'median', 'q1', 'q3', 'mean'], desc)
    write_csv(os.path.join(RESULTS_DIR, 'cross_source_kruskal.csv'),
              ['scope', 'metric', 'H_source', 'df_source', 'p_source', 'p_source_bh',
               'H_family', 'df_family', 'p_family'], kw_out)
    pf = ['scope', 'metric', 'comparison', 'n_b', 'n_a', 'median_b', 'median_a',
          'cliffs_delta', 'magnitude', 'p_raw', 'p_holm', 'p_bh']
    write_csv(os.path.join(RESULTS_DIR, 'cross_source_pairwise.csv'), pf, pair_out)
    write_csv(os.path.join(RESULTS_DIR, 'cross_source_family_pairwise.csv'), pf, fam_out)

    # ---------------- C. data-volume control ------------------------------
    # Source choice is partly driven by how much data a test needs, so the
    # provider-vs-inline contrast is recomputed inside quartile strata of
    # n_sets (number of parameter sets).
    def n_sets_of(r):
        try:
            return int(r['n_sets'])
        except (ValueError, KeyError):
            return None

    withn = [r for r in rows if n_sets_of(r) is not None and r['family'] in ('inline', 'provider')]
    vals = sorted(n_sets_of(r) for r in withn)
    cuts = [quantile(vals, q) for q in (0.25, 0.5, 0.75)]

    def stratum_of(r):
        v = n_sets_of(r)
        for i, c in enumerate(cuts):
            if v <= c:
                return i
        return 3

    strata_out = []
    for meta in METRICS:
        for si in range(4):
            srows = [r for r in withn if stratum_of(r) == si]
            inl = [r for r in srows if r['family'] == 'inline']
            prov = [r for r in srows if r['family'] == 'provider']
            if not inl or not prov:
                continue
            delta, p = mann_whitney_u(values(prov, meta), values(inl, meta))
            lo = 0 if si == 0 else cuts[si - 1]
            hi = cuts[si] if si < 3 else max(vals)
            strata_out.append({
                'scope': meta['scope_label'], 'metric': meta['metric_label'],
                'stratum': f'Q{si+1}', 'n_sets_range': f'{lo:g}-{hi:g}',
                'n_provider': len(prov), 'n_inline': len(inl),
                'cliffs_delta': fmt(delta), 'magnitude': cliffs_magnitude(delta),
                'p_raw': fmt(p, 6)})
    write_csv(os.path.join(RESULTS_DIR, 'cross_source_volume_strata.csv'),
              ['scope', 'metric', 'stratum', 'n_sets_range', 'n_provider', 'n_inline',
               'cliffs_delta', 'magnitude', 'p_raw'], strata_out)

    # ---------------- D. leave-one-project-out ----------------------------
    loo = []
    inline_rows, prov_rows = by_family['inline'], by_family['provider']
    projects = sorted({r['project'] for r in inline_rows + prov_rows})
    for meta in METRICS:
        if meta['column'] not in HEADLINE:
            continue
        full, _ = mann_whitney_u(values(prov_rows, meta), values(inline_rows, meta))
        ds = []
        for p_ in projects:
            d, _ = mann_whitney_u(values([r for r in prov_rows if r['project'] != p_], meta),
                                  values([r for r in inline_rows if r['project'] != p_], meta))
            if d == d:
                ds.append((p_, d))
        lo_, hi_ = min(ds, key=lambda t: t[1]), max(ds, key=lambda t: t[1])
        loo.append({'comparison': 'provider vs inline', 'scope': meta['scope_label'],
                    'metric': meta['metric_label'], 'delta_full': fmt(full),
                    'delta_min_loo': fmt(lo_[1]), 'delta_max_loo': fmt(hi_[1]),
                    'min_when_dropping': lo_[0], 'max_when_dropping': hi_[0],
                    'sign_stable': 'yes' if lo_[1] * hi_[1] > 0 else 'no'})
    write_csv(os.path.join(RESULTS_DIR, 'cross_source_robustness_loo.csv'),
              ['comparison', 'scope', 'metric', 'delta_full', 'delta_min_loo', 'delta_max_loo',
               'min_when_dropping', 'max_when_dropping', 'sign_stable'], loo)

    print('\n=== family contrasts (delta > 0 = provider higher) ===', file=sys.stderr)
    for r in fam_out:
        if r['comparison'] == 'provider vs inline' and r['metric'] != 'DUP lines':
            print(f"  {r['scope']:>9s} {r['metric']:>5s}: d={r['cliffs_delta']:>7s} "
                  f"({r['magnitude']:>10s})  median {r['median_a']} -> {r['median_b']}", file=sys.stderr)


if __name__ == '__main__':
    main()
