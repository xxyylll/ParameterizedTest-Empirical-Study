#!/usr/bin/env python3
"""
Amortisation analysis: turn the descriptive "this design moves complexity into
the helper layer" into a normative statement about whether that complexity is
shared.

  A. Amortisation profile per design group -- complexity-weighted mean reuse,
     and the share of moved complexity that is single-use.
  B. THE HEADLINE: every earlier contrast recomputed under both accounting
     models, side by side.
       reader_total     = self + SUM helper            (the existing total_*)
       maintainer_total = self + SUM helper / reuse    (fair share of shared code)
     Where a group looks more complex under the reader model but not under the
     maintainer model, its extra complexity is amortised infrastructure rather
     than a cost it imposes on the suite.
  C. Convergent validity of the reuse measure. DUP is NOT amortised -- reuse
     and duplication are the same construct from opposite directions, so
     dividing duplicated lines by reuse would explain a measure with itself.
     Instead reuse is validated AGAINST duplication, which is measured by an
     entirely independent tool (CCFinderSW): if reuse captures what we think,
     test suites leaning on more-reused helpers should show less duplicated
     helper code.
  D. Leave-one-project-out robustness.
  F. Full distributions. Reuse is heavy-tailed and strongly right-skewed (the
     mean is several times the median and the top percentile is three orders of
     magnitude above the bottom), so every group is also reported as a full
     percentile ladder with SD, coefficient of variation and explicit tail
     shares, not as a single central-tendency number.

Population note: amortisation is only defined for tests that HAVE a helper
layer, so every number here is conditional on helper_count >= 1. Tests whose
helpers carry zero complexity (e.g. only implicit default constructors) are
excluded from the ratio metrics, where the ratio is undefined.

Outputs: amortization_profile.csv, amortization_model_comparison.csv,
         amortization_descriptives.csv, amortization_distributions.csv,
         amortization_reuse_dup_validity.csv, amortization_robustness_loo.csv
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'amortization')
_os_root.makedirs(RESULTS_DIR, exist_ok=True)

# pt_stats 位于 rq3_2/ 根目录，四个子分析共用
import sys as _s2, os as _o2
_s2.path.insert(0, _o2.path.dirname(_o2.path.dirname(_o2.path.abspath(__file__))))
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pt_stats import (mann_whitney_u, cliffs_magnitude, kruskal_wallis,
                      holm_adjust, bh_adjust, describe, describe_full,
                      share_at_most, share_at_least, spearman)

HERE = os.path.dirname(os.path.abspath(__file__))
IN_CSV = os.path.join(RESULTS_DIR, "amortization_metrics.csv")

DEP_LEVELS = ['L0', 'L1', 'L2', 'L3', 'L4']
FAMILIES = ['inline', 'type', 'file', 'provider']

# contrasts reused from RQ3.2 / RQ3.3 so the two accounting models can be
# compared on exactly the comparisons already reported
def junit5_only(r):
    """Every parameterized test in this corpus is JUnit 5 (8,299 of 8,299), while
    the non-parameterized pool still holds 20,093 JUnit 4 tests and 211
    TestNG/unknown ones. Comparing PT against that pool would mix the effect of
    parameterizing with the effect of changing test framework, so the PT vs
    non-PT contrast is restricted to JUnit 5 on both sides.

    The restriction applies to the *comparison* only. reuse(h) is still counted
    over every test that calls h, JUnit 4 included, because a helper shared with
    a JUnit 4 test is genuinely shared."""
    return r.get('junit_api') == 'junit5'


CONTRASTS = [
    ('construction', 'Dynamic vs Literal', 'construction', 'Dynamic', 'Literal', None),
    ('dependency', 'L2 vs L0', 'dependency', 'L2', 'L0', None),
    ('dependency', 'L3 vs L0', 'dependency', 'L3', 'L0', None),
    ('dependency', 'L4 vs L0', 'dependency', 'L4', 'L0', None),
    ('dependency', 'L1 vs L0', 'dependency', 'L1', 'L0', None),
    ('family', 'provider vs inline', 'family', 'provider', 'inline', None),
    ('family', 'provider vs type', 'family', 'provider', 'type', None),
    ('category', 'pt vs nonpt (JUnit 5 only)', 'category', 'pt', 'nonpt', junit5_only),
]

GROUPINGS = [('construction', ['Literal', 'Dynamic'], None),
             ('dependency', DEP_LEVELS, None),
             ('family', FAMILIES, None),
             ('category', ['nonpt', 'pt'], junit5_only)]

MEASURES = ['loc', 'cc', 'cctr', 'cctr_eq']


def fnum(r, col):
    v = r.get(col, '')
    if v == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None


def vals(rows, col):
    out = []
    for r in rows:
        v = fnum(r, col)
        if v is not None:
            out.append(v)
    return out


def fmt(x, nd=4):
    return '' if x is None or x != x else f'{x:.{nd}f}'


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {len(rows):4d} rows -> {os.path.basename(path)}', file=sys.stderr)


def main():
    rows = list(csv.DictReader(open(IN_CSV, newline='', encoding='utf-8')))
    print(f'loaded {len(rows)} tests with >=1 helper '
          f'({len({r["project"] for r in rows})} projects)', file=sys.stderr)

    # ---------------- A. amortisation profile per group ----------------
    prof = []
    for dim, groups, filt in GROUPINGS:
        for g in groups:
            sel = [r for r in rows if r[dim] == g and (filt is None or filt(r))]
            if not sel:
                continue
            a = describe(vals(sel, 'amortization_cctr'))
            p = describe(vals(sel, 'private_cctr_share'))
            hc = describe([float(r['helper_count']) for r in sel])
            su = describe([float(r['single_use_helper_count']) for r in sel])
            prof.append({
                'dimension': dim, 'group': g, 'n': len(sel),
                'median_helper_count': fmt(hc['median'], 2),
                'median_single_use_helpers': fmt(su['median'], 2),
                'amortization_cctr_median': fmt(a['median'], 2),
                'amortization_cctr_mean': fmt(a['mean'], 2),
                'private_cctr_share_median': fmt(p['median']),
                'private_cctr_share_mean': fmt(p['mean']),
                'n_with_defined_ratio': a['n'],
            })
    write_csv(os.path.join(RESULTS_DIR, 'amortization_profile.csv'),
              ['dimension', 'group', 'n', 'median_helper_count', 'median_single_use_helpers',
               'amortization_cctr_median', 'amortization_cctr_mean',
               'private_cctr_share_median', 'private_cctr_share_mean', 'n_with_defined_ratio'], prof)

    # ---------------- descriptives for both accounting models ----------------
    desc = []
    for dim, groups, filt in GROUPINGS:
        for g in groups:
            sel = [r for r in rows if r[dim] == g and (filt is None or filt(r))]
            if not sel:
                continue
            for m in MEASURES:
                rd = describe(vals(sel, f'reader_total_{m}'))
                md = describe(vals(sel, f'maintainer_total_{m}'))
                desc.append({'dimension': dim, 'group': g, 'measure': m.upper(), 'n': len(sel),
                             'reader_median': fmt(rd['median'], 2), 'reader_mean': fmt(rd['mean'], 2),
                             'maintainer_median': fmt(md['median'], 2), 'maintainer_mean': fmt(md['mean'], 2),
                             'median_ratio': fmt(rd['median'] / md['median'], 2) if md['median'] else ''})
    write_csv(os.path.join(RESULTS_DIR, 'amortization_descriptives.csv'),
              ['dimension', 'group', 'measure', 'n', 'reader_median', 'reader_mean',
               'maintainer_median', 'maintainer_mean', 'median_ratio'], desc)

    # ---------------- B. the two accounting models, side by side ----------------
    comp = []
    praw_reader, praw_maint = [], []
    for dim, name, col, a_label, b_label, filt in CONTRASTS:
        A = [r for r in rows if r[col] == a_label and (filt is None or filt(r))]
        B = [r for r in rows if r[col] == b_label and (filt is None or filt(r))]
        if not A or not B:
            continue
        for m in MEASURES:
            dr, pr = mann_whitney_u(vals(A, f'reader_total_{m}'), vals(B, f'reader_total_{m}'))
            dm, pm = mann_whitney_u(vals(A, f'maintainer_total_{m}'), vals(B, f'maintainer_total_{m}'))
            da, pa = mann_whitney_u(vals(A, f'amortization_{m}'), vals(B, f'amortization_{m}'))
            dp, pp = mann_whitney_u(vals(A, f'private_{m}_share'), vals(B, f'private_{m}_share'))
            comp.append({
                'dimension': dim, 'contrast': name, 'measure': m.upper(),
                'n_a': len(A), 'n_b': len(B),
                'delta_reader': fmt(dr), 'magnitude_reader': cliffs_magnitude(dr), 'p_reader': fmt(pr, 6),
                'delta_maintainer': fmt(dm), 'magnitude_maintainer': cliffs_magnitude(dm),
                'p_maintainer': fmt(pm, 6),
                'delta_shrinks': 'yes' if abs(dm) < abs(dr) else 'no',
                'crosses_to_negligible': 'yes' if (abs(dr) >= 0.147 and abs(dm) < 0.147) else 'no',
                'delta_amortization': fmt(da), 'magnitude_amortization': cliffs_magnitude(da),
                'p_amortization': fmt(pa, 6),
                'delta_private_share': fmt(dp), 'magnitude_private_share': cliffs_magnitude(dp),
                'p_private_share': fmt(pp, 6),
            })
            praw_reader.append(pr)
            praw_maint.append(pm)
    for r, q1, q2 in zip(comp, bh_adjust(praw_reader), bh_adjust(praw_maint)):
        r['p_reader_bh'] = fmt(q1, 6)
        r['p_maintainer_bh'] = fmt(q2, 6)
    write_csv(os.path.join(RESULTS_DIR, 'amortization_model_comparison.csv'),
              ['dimension', 'contrast', 'measure', 'n_a', 'n_b',
               'delta_reader', 'magnitude_reader', 'p_reader', 'p_reader_bh',
               'delta_maintainer', 'magnitude_maintainer', 'p_maintainer', 'p_maintainer_bh',
               'delta_shrinks', 'crosses_to_negligible',
               'delta_amortization', 'magnitude_amortization', 'p_amortization',
               'delta_private_share', 'magnitude_private_share', 'p_private_share'], comp)

    # ---------------- Kruskal-Wallis across dependency levels ----------------
    kw = []
    for m in MEASURES:
        for metric in (f'reader_total_{m}', f'maintainer_total_{m}',
                       f'amortization_{m}', f'private_{m}_share'):
            groups = [vals([r for r in rows if r['dependency'] == l], metric) for l in DEP_LEVELS]
            H, df, p = kruskal_wallis(groups)
            kw.append({'measure': m.upper(), 'metric': metric, 'H': fmt(H), 'df': df,
                       'p_raw': fmt(p, 6), 'n_total': sum(len(g) for g in groups)})
    write_csv(os.path.join(RESULTS_DIR, 'amortization_dependency_kruskal.csv'),
              ['measure', 'metric', 'n_total', 'H', 'df', 'p_raw'], kw)

    # ---------------- E. full distributions ----------------
    DIST_METRICS = ['amortization_cctr', 'amortization_loc', 'private_cctr_share',
                    'helper_count', 'single_use_helper_count',
                    'reader_total_cctr', 'maintainer_total_cctr',
                    'reader_total_cctr_eq', 'maintainer_total_cctr_eq']
    dist = []
    for dim, groups, filt in GROUPINGS:
        for g in groups:
            sel = [r for r in rows if r[dim] == g and (filt is None or filt(r))]
            if not sel:
                continue
            for metric in DIST_METRICS:
                v = vals(sel, metric)
                if not v:
                    continue
                d = describe_full(v)
                row = {'dimension': dim, 'group': g, 'metric': metric,
                       'n': d['n'], 'mean': fmt(d['mean'], 3), 'sd': fmt(d['sd'], 3),
                       'cv': fmt(d['cv'], 3), 'mean_over_median': fmt(d['mean_median_ratio'], 2),
                       'min': fmt(d['min'], 3), 'p5': fmt(d['p5'], 3), 'q1': fmt(d['q1'], 3),
                       'median': fmt(d['median'], 3), 'q3': fmt(d['q3'], 3),
                       'p90': fmt(d['p90'], 3), 'p95': fmt(d['p95'], 3),
                       'p99': fmt(d['p99'], 3), 'max': fmt(d['max'], 3),
                       'iqr': fmt(d['iqr'], 3)}
                if metric.startswith('amortization'):
                    # tail mass, stated explicitly: a weighted reuse of 1 means the
                    # complexity this test leans on is shared with nobody
                    row['share_eq_1'] = fmt(share_at_most(v, 1.0))
                    row['share_le_2'] = fmt(share_at_most(v, 2.0))
                    row['share_ge_10'] = fmt(share_at_least(v, 10.0))
                    row['share_ge_100'] = fmt(share_at_least(v, 100.0))
                else:
                    row['share_eq_1'] = row['share_le_2'] = ''
                    row['share_ge_10'] = row['share_ge_100'] = ''
                dist.append(row)
    write_csv(os.path.join(RESULTS_DIR, 'amortization_distributions.csv'),
              ['dimension', 'group', 'metric', 'n', 'mean', 'sd', 'cv', 'mean_over_median',
               'min', 'p5', 'q1', 'median', 'q3', 'p90', 'p95', 'p99', 'max', 'iqr',
               'share_eq_1', 'share_le_2', 'share_ge_10', 'share_ge_100'], dist)

    # ---------------- C. reuse vs duplication: convergent validity ----------
    val = []
    pairs = [('amortization_cctr', 'helper_dupPerc'),
             ('amortization_loc', 'helper_dupPerc'),
             ('amortization_cctr', 'total_dupPerc'),
             ('private_cctr_share', 'helper_dupPerc')]
    for xcol, ycol in pairs:
        xs, ys = [], []
        for r in rows:
            a, b = fnum(r, xcol), fnum(r, ycol)
            if a is not None and b is not None:
                xs.append(a)
                ys.append(b)
        rho, p = spearman(xs, ys)
        val.append({'x': xcol, 'y': ycol, 'n': len(xs), 'spearman_rho': fmt(rho),
                    'p_raw': fmt(p, 6), 'scope': 'all tests with >=1 helper'})
    # binned view: median helper duplication by reuse decile
    withboth = [r for r in rows
                if fnum(r, 'amortization_cctr') is not None and fnum(r, 'helper_dupPerc') is not None]
    withboth.sort(key=lambda r: fnum(r, 'amortization_cctr'))
    nb = 10
    size = max(1, len(withboth) // nb)
    for i in range(nb):
        chunk = withboth[i * size: (i + 1) * size if i < nb - 1 else len(withboth)]
        if not chunk:
            continue
        a = describe([fnum(r, 'amortization_cctr') for r in chunk])
        d = describe([fnum(r, 'helper_dupPerc') for r in chunk])
        val.append({'x': f'reuse decile {i+1}', 'y': 'helper_dupPerc', 'n': len(chunk),
                    'spearman_rho': '', 'p_raw': '',
                    'scope': f"weighted reuse {fmt(a['q1'],1)}-{fmt(a['q3'],1)} "
                             f"(median {fmt(a['median'],1)}) -> median dup {fmt(d['median'])}"})
    write_csv(os.path.join(RESULTS_DIR, 'amortization_reuse_dup_validity.csv'),
              ['x', 'y', 'n', 'spearman_rho', 'p_raw', 'scope'], val)

    # ---------------- D. leave-one-project-out ----------------
    loo = []
    for dim, name, col, a_label, b_label, filt in CONTRASTS:
        A = [r for r in rows if r[col] == a_label and (filt is None or filt(r))]
        B = [r for r in rows if r[col] == b_label and (filt is None or filt(r))]
        if not A or not B:
            continue
        projects = sorted({r['project'] for r in A + B})
        loo_metrics = []
        for m in MEASURES:
            loo_metrics += [f'reader_total_{m}', f'maintainer_total_{m}']
        loo_metrics += ['amortization_cctr', 'private_cctr_share']
        for metric in loo_metrics:
            full, _ = mann_whitney_u(vals(A, metric), vals(B, metric))
            ds = []
            for p_ in projects:
                d, _ = mann_whitney_u(vals([r for r in A if r['project'] != p_], metric),
                                      vals([r for r in B if r['project'] != p_], metric))
                if d == d:
                    ds.append(d)
            if not ds:
                continue
            loo.append({'contrast': name, 'metric': metric, 'delta_full': fmt(full),
                        'delta_min_loo': fmt(min(ds)), 'delta_max_loo': fmt(max(ds)),
                        'n_projects': len(projects),
                        'sign_stable': 'yes' if min(ds) * max(ds) > 0 else 'no'})
    write_csv(os.path.join(RESULTS_DIR, 'amortization_robustness_loo.csv'),
              ['contrast', 'metric', 'delta_full', 'delta_min_loo', 'delta_max_loo',
               'n_projects', 'sign_stable'], loo)

    print('\n=== weighted reuse distribution (CCTR) ===', file=sys.stderr)
    for r in dist:
        if r['metric'] == 'amortization_cctr' and r['dimension'] in ('category', 'dependency'):
            print(f"  {r['group']:<7s} n={r['n']:>6d}  mean={r['mean']:>9s} sd={r['sd']:>9s}  "
                  f"q1/med/q3={r['q1']:>7s}/{r['median']:>7s}/{r['q3']:>8s}  "
                  f"p99={r['p99']:>8s}  reuse=1:{r['share_eq_1']}", file=sys.stderr)

    print('\n=== reuse vs duplication (convergent validity) ===', file=sys.stderr)
    for r in val:
        if r['spearman_rho']:
            print(f"  rho({r['x']}, {r['y']}) = {r['spearman_rho']}  p={r['p_raw']}  n={r['n']}",
                  file=sys.stderr)

    print('\n=== amortisation profile (CCTR) ===', file=sys.stderr)
    for r in prof:
        print(f"  {r['dimension']:>12s}={r['group']:<10s} n={r['n']:>5d}  "
              f"加权复用={r['amortization_cctr_median']:>8s}(中位)  "
              f"单用途复杂度占比={r['private_cctr_share_mean']:>7s}(均值)".replace('  ', '  '),
              file=sys.stderr)
    print('\n=== reader vs maintainer accounting (CCTR) ===', file=sys.stderr)
    for r in comp:
        if r['measure'] == 'CCTR':
            print(f"  {r['contrast']:<22s} reader d={r['delta_reader']:>7s} ({r['magnitude_reader']:>10s})"
                  f"  ->  maintainer d={r['delta_maintainer']:>7s} ({r['magnitude_maintainer']:>10s})"
                  f"  {'[效应消失]' if r['crosses_to_negligible']=='yes' else ''}", file=sys.stderr)


if __name__ == '__main__':
    main()
