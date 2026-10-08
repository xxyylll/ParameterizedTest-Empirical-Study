#!/usr/bin/env python3
"""
Amortisation dataset: is the complexity a test pushes into its helper layer
SHARED with other tests, or merely displaced out of the test body?

Everything measured so far is descriptive -- "this design moves complexity into
the helper layer" -- with no way to say whether that is good or bad. Helper
reuse supplies a normative anchor that needs no external data:

  * complexity sitting in a helper that 200 tests call is amortised
    infrastructure; the suite pays for it once.
  * complexity sitting in a helper that exactly one test calls was not shared
    at all -- the test paid the indirection cost of a method call and a jump
    without the benefit.

Two accounting models are computed, because they bracket the truth and
disagreeing about which to use is a design argument, not a measurement one:

  reader_total_X      = self_X + SUM over helpers of X(h)
                        Reading this one test means understanding every helper
                        it calls, in full. This is the existing `total_X`.

  maintainer_total_X  = self_X + SUM over helpers of X(h) / reuse(h)
                        The suite contains each helper once; charge each test
                        only its share. Assumes equal division among callers.

  amortisation        = SUM X(h)*reuse(h) / SUM X(h)
                        Complexity-weighted mean reuse: for each unit of helper
                        complexity this test leans on, how many tests share it.

  private_X_share     = SUM over single-use helpers X(h) / SUM X(h)
                        Fraction of the moved complexity that is this test's
                        alone. The displacement measure.

DUP is deliberately NOT amortised. Reuse and duplication are the same construct
measured from opposite directions -- a helper called by 200 tests is, by
definition, code that was not copy-pasted 200 times -- so dividing duplicated
lines by reuse would explain a measure with itself. DUP is instead carried
through unchanged so that reuse can be validated AGAINST it: if the reuse
measure is capturing what we think, more-reused helper layers should show less
duplication, as judged by an entirely independent tool (CCFinderSW). That is a
convergent-validity check, not an amortisation.

reuse(h) is counted over the WHOLE test population of the project — every test
that calls a helper shares its cost, including JUnit 4 ones, so the reuse count
must not be restricted even though the PT-vs-non-PT *comparison* is (see
analyze_amortization.py).

CCTR is carried in two variants. Plain `cctr` scores @ParameterizedTest at 2 and
@Test at 1, so every parameterized test receives a fixed +1 that no ordinary
test can get; `cctr_eq` scores them equally. Any comparison that crosses the PT
boundary uses `cctr_eq`, because on plain `cctr` part of the gap is the metric's
own definition rather than anything about the tests.

Inputs : test_helper_detail_46projects.csv (per (test, helper) complexity)
         test_metrics_all_44projects.csv   (per-test self/total metrics)
         the RQ3.2 and RQ3.3 label tables
Output : amortization_metrics.csv
"""
import csv
import os
import sys
from collections import defaultdict
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
from paths import METRICS_DIR, FINAL  # noqa: E402


csv.field_size_limit(10 ** 9)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DETAIL_CSV = _os.path.join(METRICS_DIR, "test_helper_detail_46projects.csv")
METRICS_CSV = _os.path.join(METRICS_DIR, "test_metrics_all_46projects_v2.csv")
MS_CSV = _os.path.join(FINAL, "rq3_2", "methodsource", "rq32_full_methodsource_metrics.csv")
CS_CSV = os.path.join(ROOT, "cross_source", "cross_source_metrics.csv")
OUT_CSV = os.path.join(HERE, "amortization_metrics.csv")

MEASURES = ('loc', 'cc', 'cctr', 'cctr_eq')


def main():
    # ---- 1. per-helper complexity, deduplicated per (test, helper) ----
    helper_cost = {}                      # (project, helper) -> {loc, cc, cctr}
    test_helpers = defaultdict(dict)      # test key -> {helper -> cost}
    for r in csv.DictReader(open(DETAIL_CSV, newline='', encoding='utf-8')):
        tk = (r['project'], r['test_class'], r['test_name'])
        hk = (r['project'], r['helper_name'])
        cost = {m: int(r[f'helper_{m}']) for m in MEASURES}
        helper_cost[hk] = cost
        test_helpers[tk][r['helper_name']] = cost     # dedup: same helper once per test
    print(f'{len(test_helpers)} tests with >=1 helper, '
          f'{len(helper_cost)} distinct helpers', file=sys.stderr)

    # ---- 2. reuse, counted over the whole test population ----
    reuse = defaultdict(int)
    for (proj, tc, tn), hs in test_helpers.items():
        for h in hs:
            reuse[(proj, h)] += 1
    rv = sorted(reuse.values())
    print(f'reuse: median={rv[len(rv)//2]} max={max(rv)} '
          f'single-use={sum(1 for v in rv if v == 1)}/{len(rv)}', file=sys.stderr)

    # ---- 3. self metrics + category from the main table ----
    self_of = {}
    with open(METRICS_CSV, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            k = (r['project'], r['test_class'], r['test_name'])
            # a handful of overloaded test methods collide on this key; prefer
            # the parameterized row, matching the other builders
            if k in self_of and self_of[k]['category'] == 'pt':
                continue
            self_of[k] = {'category': r['category'],
                          'junit_api': r.get('junit_api', ''),
                          **{m: int(r[f'self_{m}']) for m in MEASURES},
                          # DUP is carried through unchanged, NOT amortised: see
                          # the note below on why dividing duplication by reuse
                          # would be circular.
                          'self_dupPerc': r['self_dupPerc'],
                          'helper_dupPerc': r['helper_dupPerc'],
                          'total_dupPerc': r['total_dupPerc']}

    # ---- 4. labels ----
    ms_label = {(r['project'], r['test_class'], r['test_name']):
                (r['construction'], r['dependency'])
                for r in csv.DictReader(open(MS_CSV, newline='', encoding='utf-8'))}
    cs_label = {(r['project'], r['test_class'], r['test_name']):
                (r['source_type'], r['family'])
                for r in csv.DictReader(open(CS_CSV, newline='', encoding='utf-8'))}

    # ---- 5. per-test amortisation ----
    out = []
    for tk, hs in test_helpers.items():
        s = self_of.get(tk)
        if s is None:
            continue
        proj = tk[0]
        row = {'project': proj, 'test_class': tk[1], 'test_name': tk[2],
               'category': s['category'], 'junit_api': s['junit_api'],
               'helper_count': len(hs),
               'self_dupPerc': s['self_dupPerc'], 'helper_dupPerc': s['helper_dupPerc'],
               'total_dupPerc': s['total_dupPerc']}
        constr, dep = ms_label.get(tk, ('', ''))
        src, fam = cs_label.get(tk, ('', ''))
        row.update({'construction': constr, 'dependency': dep,
                    'source_type': src, 'family': fam})

        reuses = [reuse[(proj, h)] for h in hs]
        row['max_reuse'] = max(reuses)
        row['min_reuse'] = min(reuses)
        row['single_use_helper_count'] = sum(1 for v in reuses if v == 1)

        for m in MEASURES:
            tot = sum(c[m] for c in hs.values())
            fair = sum(c[m] / reuse[(proj, h)] for h, c in hs.items())
            priv = sum(c[m] for h, c in hs.items() if reuse[(proj, h)] == 1)
            wsum = sum(c[m] * reuse[(proj, h)] for h, c in hs.items())
            row[f'self_{m}'] = s[m]
            row[f'helper_{m}_sum'] = tot
            row[f'reader_total_{m}'] = s[m] + tot
            row[f'maintainer_total_{m}'] = round(s[m] + fair, 4)
            row[f'fair_share_{m}'] = round(fair, 4)
            # ratios are undefined when a test's helpers carry no complexity at
            # all (e.g. every helper is an implicit default constructor)
            row[f'amortization_{m}'] = round(wsum / tot, 4) if tot else ''
            row[f'private_{m}_share'] = round(priv / tot, 4) if tot else ''
        out.append(row)

    fields = ['project', 'test_class', 'test_name', 'category', 'junit_api',
              'construction', 'dependency', 'source_type', 'family',
              'helper_count', 'single_use_helper_count', 'max_reuse', 'min_reuse',
              'self_dupPerc', 'helper_dupPerc', 'total_dupPerc']
    for m in MEASURES:
        fields += [f'self_{m}', f'helper_{m}_sum', f'reader_total_{m}',
                   f'maintainer_total_{m}', f'fair_share_{m}',
                   f'amortization_{m}', f'private_{m}_share']

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f'\nWrote {len(out)} rows -> {os.path.basename(OUT_CSV)}', file=sys.stderr)
    labelled = sum(1 for r in out if r['family'])
    print(f'  with a cross-source label: {labelled}; '
          f'with a MethodSource label: {sum(1 for r in out if r["dependency"])}', file=sys.stderr)


if __name__ == '__main__':
    main()
