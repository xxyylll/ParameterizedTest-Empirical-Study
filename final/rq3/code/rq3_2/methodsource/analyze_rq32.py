#!/usr/bin/env python3
"""
RQ3.2 analysis: do different MethodSource design patterns correspond to
different complexity profiles?

  A. Construction  : Literal vs Dynamic      -> Mann-Whitney U + Cliff's delta
  A2. Construction within the L0 stratum     -> same test, dependency held fixed
      (Literal is 82% L0 while Dynamic spreads across L0-L4, so the two
       grouping variables are confounded; A2 isolates the construction effect)
  B. Dependency    : L0 / L1 / L2 / L3 / L4  -> Kruskal-Wallis, then pairwise
                                                Mann-Whitney U + Cliff's delta
                                                with Holm (FWER) and BH (FDR)
                                                correction within each metric
  C. Robustness    : leave-one-project-out Cliff's delta range for the headline
                     comparisons (374 tests come from 31 projects, so tests are
                     not fully independent)

Every comparison is reported for main-body / helper / total x LOC / CC / CCTR /
DUP, so the analysis shows not just whether total complexity differs but where
it sits -- in the test main body or in the helper logic behind the provider.

Outputs (same folder):
  rq32_construction_stats.csv        A + A2, one row per metric
  rq32_dependency_descriptives.csv   per dependency level, per metric
  rq32_dependency_kruskal.csv        Kruskal-Wallis per metric
  rq32_dependency_pairwise.csv       10 pairs x metric, delta + raw/Holm/BH p
  rq32_robustness_loo.csv            leave-one-project-out delta ranges
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rq32_stats import (mann_whitney_u, cliffs_magnitude, kruskal_wallis,
                        holm_adjust, bh_adjust, describe)

HERE = os.path.dirname(os.path.abspath(__file__))

DEP_LEVELS = ['L0', 'L1', 'L2', 'L3', 'L4']

# (metric_id, label, {scope: column}, is_float)
METRICS = []
for mid, label, cols, is_float in [
    ('loc', 'LOC', {'self': 'self_loc', 'helper': 'helper_loc_sum', 'total': 'total_loc'}, False),
    ('cc', 'CC', {'self': 'self_cc', 'helper': 'helper_cc_sum', 'total': 'total_cc'}, False),
    ('cctr', 'CCTR', {'self': 'self_cctr', 'helper': 'helper_cctr_sum', 'total': 'total_cctr'}, False),
    ('dupPerc', 'DUP%', {'self': 'self_dupPerc', 'helper': 'helper_dupPerc', 'total': 'total_dupPerc'}, True),
    ('dupLines', 'DUP lines', {'self': 'self_dupLines', 'helper': 'helper_dupLines_sum', 'total': 'total_dupLines'}, True),
]:
    for scope, scope_label in [('self', 'main-body'), ('helper', 'helper'), ('total', 'total')]:
        METRICS.append({
            'key': f'{scope}_{mid}',
            'metric': mid,
            'metric_label': label,
            'scope': scope,
            'scope_label': scope_label,
            'column': cols[scope],
            'is_float': is_float,
        })

# Headline metrics used for the leave-one-project-out robustness check.
HEADLINE = ['self_loc', 'helper_loc', 'total_loc',
            'self_cc', 'helper_cc', 'total_cc',
            'self_cctr', 'helper_cctr', 'total_cctr',
            'self_dupPerc', 'helper_dupPerc', 'total_dupPerc']


def value_of(row, meta):
    raw = row[meta['column']]
    if raw == '':
        return None
    return float(raw) if meta['is_float'] else int(raw)


def values(rows, meta):
    out = []
    for r in rows:
        v = value_of(r, meta)
        if v is not None:
            out.append(v)
    return out


def fmt(x, nd=4):
    if x is None or x != x:
        return ''
    return f'{x:.{nd}f}'


def two_group_row(meta, g1_rows, g2_rows, g1_name, g2_name):
    """g1 vs g2; positive Cliff's delta means g1 tends to be larger."""
    v1 = values(g1_rows, meta)
    v2 = values(g2_rows, meta)
    d1, d2 = describe(v1), describe(v2)
    delta, p = mann_whitney_u(v1, v2)
    return {
        'scope': meta['scope_label'],
        'metric': meta['metric_label'],
        f'n_{g1_name}': d1['n'], f'n_{g2_name}': d2['n'],
        f'median_{g1_name}': fmt(d1['median']), f'median_{g2_name}': fmt(d2['median']),
        f'iqr_{g1_name}': fmt(d1['iqr']), f'iqr_{g2_name}': fmt(d2['iqr']),
        f'mean_{g1_name}': fmt(d1['mean']), f'mean_{g2_name}': fmt(d2['mean']),
        'cliffs_delta': fmt(delta), 'magnitude': cliffs_magnitude(delta),
        'p_raw': fmt(p, 6),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix', default='rq32',
                    help="input/output filename prefix ('rq32' = validated sample, "
                         "'rq32_full' = full population)")
    args = ap.parse_args()
    prefix = args.prefix
    in_csv = os.path.join(RESULTS_DIR, f'{prefix}_methodsource_metrics.csv')

    rows = list(csv.DictReader(open(in_csv, newline='', encoding='utf-8')))
    print(f'loaded {len(rows)} joined MethodSource tests from {os.path.basename(in_csv)}', file=sys.stderr)

    # ---- analysis population filters -------------------------------------
    # The validated-sample table carries a dependency_status column whose
    # non-OK values mean the dependency label itself is unreliable. The full
    # table's `status` column instead reports failures of RQ2-side derived
    # metrics (hd: helper depth, cc: cognitive complexity) that RQ3.2 does not
    # use, so it is not a filter here -- unusable rows are excluded anyway by
    # the construction/dependency label filters below.
    if rows and 'dependency_status' in rows[0]:
        usable = [r for r in rows if r['dependency_status'].startswith('OK')]
    else:
        usable = rows
    dropped_status = len(rows) - len(usable)

    constr_rows = [r for r in usable if r['construction'] in ('Literal', 'Dynamic')]
    dep_rows = [r for r in usable if r['dependency'] in DEP_LEVELS]
    print(f'  dropped for dependency_status != OK*: {dropped_status}', file=sys.stderr)
    print(f'  construction population: {len(constr_rows)} '
          f'(Literal={sum(1 for r in constr_rows if r["construction"]=="Literal")}, '
          f'Dynamic={sum(1 for r in constr_rows if r["construction"]=="Dynamic")})', file=sys.stderr)
    print(f'  dependency population  : {len(dep_rows)} '
          f'({ {l: sum(1 for r in dep_rows if r["dependency"]==l) for l in DEP_LEVELS} })', file=sys.stderr)

    # ================= A. Construction: Literal vs Dynamic ================
    lit = [r for r in constr_rows if r['construction'] == 'Literal']
    dyn = [r for r in constr_rows if r['construction'] == 'Dynamic']
    # A2: same contrast with dependency held at L0
    lit_l0 = [r for r in lit if r['dependency'] == 'L0']
    dyn_l0 = [r for r in dyn if r['dependency'] == 'L0']

    constr_out = []
    p_all, p_l0 = [], []
    for meta in METRICS:
        base = two_group_row(meta, dyn, lit, 'dynamic', 'literal')
        strat = two_group_row(meta, dyn_l0, lit_l0, 'dynamic', 'literal')
        base['L0_only_n_dynamic'] = strat['n_dynamic']
        base['L0_only_n_literal'] = strat['n_literal']
        base['L0_only_cliffs_delta'] = strat['cliffs_delta']
        base['L0_only_magnitude'] = strat['magnitude']
        base['L0_only_p_raw'] = strat['p_raw']
        constr_out.append(base)
        p_all.append(float(base['p_raw']))
        p_l0.append(float(strat['p_raw']))

    # BH across the metric family (supplementary; the per-comparison p stays primary)
    for row, q, q_l0 in zip(constr_out, bh_adjust(p_all), bh_adjust(p_l0)):
        row['p_bh_across_metrics'] = fmt(q, 6)
        row['L0_only_p_bh'] = fmt(q_l0, 6)

    constr_fields = ['scope', 'metric', 'n_dynamic', 'n_literal',
                     'median_dynamic', 'median_literal', 'iqr_dynamic', 'iqr_literal',
                     'mean_dynamic', 'mean_literal',
                     'cliffs_delta', 'magnitude', 'p_raw', 'p_bh_across_metrics',
                     'L0_only_n_dynamic', 'L0_only_n_literal', 'L0_only_cliffs_delta',
                     'L0_only_magnitude', 'L0_only_p_raw', 'L0_only_p_bh']
    write_csv(os.path.join(RESULTS_DIR, f'{prefix}_construction_stats.csv'), constr_fields, constr_out)

    # ================= B. Dependency: L0..L4 ==============================
    by_level = {l: [r for r in dep_rows if r['dependency'] == l] for l in DEP_LEVELS}

    desc_out = []
    for meta in METRICS:
        for level in DEP_LEVELS:
            d = describe(values(by_level[level], meta))
            desc_out.append({
                'scope': meta['scope_label'], 'metric': meta['metric_label'], 'dependency': level,
                'n': d['n'], 'median': fmt(d['median']), 'q1': fmt(d['q1']), 'q3': fmt(d['q3']),
                'iqr': fmt(d['iqr']), 'mean': fmt(d['mean']),
            })
    write_csv(os.path.join(RESULTS_DIR, f'{prefix}_dependency_descriptives.csv'),
              ['scope', 'metric', 'dependency', 'n', 'median', 'q1', 'q3', 'iqr', 'mean'], desc_out)

    kw_out = []
    kw_p = []
    for meta in METRICS:
        groups = [values(by_level[l], meta) for l in DEP_LEVELS]
        H, df, p = kruskal_wallis(groups)
        kw_out.append({'scope': meta['scope_label'], 'metric': meta['metric_label'],
                       'H': fmt(H), 'df': df, 'p_raw': fmt(p, 6),
                       'n_total': sum(len(g) for g in groups)})
        kw_p.append(p)
    for row, q in zip(kw_out, bh_adjust(kw_p)):
        row['p_bh_across_metrics'] = fmt(q, 6)
        row['significant_005'] = 'yes' if float(row['p_raw']) < 0.05 else 'no'
    write_csv(os.path.join(RESULTS_DIR, f'{prefix}_dependency_kruskal.csv'),
              ['scope', 'metric', 'n_total', 'H', 'df', 'p_raw', 'p_bh_across_metrics', 'significant_005'], kw_out)

    kw_sig = {(r['scope'], r['metric']): r['significant_005'] for r in kw_out}

    pairs = [(a, b) for i, a in enumerate(DEP_LEVELS) for b in DEP_LEVELS[i + 1:]]
    pair_out = []
    for meta in METRICS:
        block = []
        for a, b in pairs:
            va = values(by_level[a], meta)
            vb = values(by_level[b], meta)
            # delta > 0 means the HIGHER level (b) is larger: compare b vs a
            delta, p = mann_whitney_u(vb, va)
            da, db = describe(va), describe(vb)
            block.append({
                'scope': meta['scope_label'], 'metric': meta['metric_label'],
                'comparison': f'{b} vs {a}', 'n_high': db['n'], 'n_low': da['n'],
                'median_high': fmt(db['median']), 'median_low': fmt(da['median']),
                'cliffs_delta': fmt(delta), 'magnitude': cliffs_magnitude(delta),
                'p_raw': fmt(p, 6), '_p': p,
            })
        ps = [r['_p'] for r in block]
        for r, h, q in zip(block, holm_adjust(ps), bh_adjust(ps)):
            r['p_holm'] = fmt(h, 6)
            r['p_bh'] = fmt(q, 6)
            r['kw_significant'] = kw_sig[(meta['scope_label'], meta['metric_label'])]
            del r['_p']
        pair_out.extend(block)
    write_csv(os.path.join(RESULTS_DIR, f'{prefix}_dependency_pairwise.csv'),
              ['scope', 'metric', 'comparison', 'n_high', 'n_low', 'median_high', 'median_low',
               'cliffs_delta', 'magnitude', 'p_raw', 'p_holm', 'p_bh', 'kw_significant'], pair_out)

    # ================= C. Leave-one-project-out robustness ================
    loo_out = []
    headline_metas = [m for m in METRICS if m['key'] in HEADLINE]
    projects = sorted({r['project'] for r in constr_rows})
    for meta in headline_metas:
        # construction contrast
        full_delta, _ = mann_whitney_u(values(dyn, meta), values(lit, meta))
        deltas = []
        for proj in projects:
            d, _ = mann_whitney_u(values([r for r in dyn if r['project'] != proj], meta),
                                  values([r for r in lit if r['project'] != proj], meta))
            deltas.append((proj, d))
        worst = min(deltas, key=lambda t: t[1])
        best = max(deltas, key=lambda t: t[1])
        loo_out.append({
            'comparison': 'Dynamic vs Literal', 'scope': meta['scope_label'], 'metric': meta['metric_label'],
            'delta_full': fmt(full_delta), 'delta_min_loo': fmt(worst[1]), 'delta_max_loo': fmt(best[1]),
            'min_when_dropping': worst[0], 'max_when_dropping': best[0],
            'sign_stable': 'yes' if worst[1] * best[1] > 0 else 'no',
        })
        # L4 vs L0 contrast
        l0, l4 = by_level['L0'], by_level['L4']
        full_delta, _ = mann_whitney_u(values(l4, meta), values(l0, meta))
        deltas = []
        for proj in sorted({r['project'] for r in dep_rows}):
            d, _ = mann_whitney_u(values([r for r in l4 if r['project'] != proj], meta),
                                  values([r for r in l0 if r['project'] != proj], meta))
            if d == d:
                deltas.append((proj, d))
        worst = min(deltas, key=lambda t: t[1])
        best = max(deltas, key=lambda t: t[1])
        loo_out.append({
            'comparison': 'L4 vs L0', 'scope': meta['scope_label'], 'metric': meta['metric_label'],
            'delta_full': fmt(full_delta), 'delta_min_loo': fmt(worst[1]), 'delta_max_loo': fmt(best[1]),
            'min_when_dropping': worst[0], 'max_when_dropping': best[0],
            'sign_stable': 'yes' if worst[1] * best[1] > 0 else 'no',
        })
    write_csv(os.path.join(RESULTS_DIR, f'{prefix}_robustness_loo.csv'),
              ['comparison', 'scope', 'metric', 'delta_full', 'delta_min_loo', 'delta_max_loo',
               'min_when_dropping', 'max_when_dropping', 'sign_stable'], loo_out)

    with open(os.path.join(RESULTS_DIR, f'{prefix}_population.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['group', 'n'])
        w.writerow(['joined', len(rows)])
        w.writerow(['usable', len(usable)])
        w.writerow(['construction_Dynamic', len(dyn)])
        w.writerow(['construction_Literal', len(lit)])
        w.writerow(['L0_Dynamic', len(dyn_l0)])
        w.writerow(['L0_Literal', len(lit_l0)])
        for l in DEP_LEVELS:
            w.writerow([f'dependency_{l}', len(by_level[l])])

    print('\n=== A. Construction (Dynamic vs Literal), DUP%=ratio ===', file=sys.stderr)
    for r in constr_out:
        if r['metric'] == 'DUP lines':
            continue
        print(f"  {r['scope']:>9s} {r['metric']:>5s}: delta={r['cliffs_delta']:>7s} "
              f"({r['magnitude']:>10s}) p={r['p_raw']:>8s} | L0-only delta={r['L0_only_cliffs_delta']:>7s} "
              f"({r['L0_only_magnitude']:>10s}) p={r['L0_only_p_raw']:>8s}", file=sys.stderr)
    print('\n=== B. Dependency Kruskal-Wallis ===', file=sys.stderr)
    for r in kw_out:
        if r['metric'] == 'DUP lines':
            continue
        print(f"  {r['scope']:>9s} {r['metric']:>5s}: H={r['H']:>8s} df={r['df']} "
              f"p={r['p_raw']:>8s} sig={r['significant_005']}", file=sys.stderr)


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {len(rows)} rows -> {os.path.basename(path)}', file=sys.stderr)


if __name__ == '__main__':
    main()
