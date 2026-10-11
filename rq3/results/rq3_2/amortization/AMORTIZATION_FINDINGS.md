# Amortisation — is the complexity moved into helpers actually shared?

**Why this analysis exists.** RQ3.2 and RQ3.3 are descriptive: they establish
that certain designs move complexity out of the test body and into the helper
layer, but say nothing about whether that is good or bad. Helper reuse supplies
a normative anchor that needs no external data (no git history, no developer
study, no readability model):

* complexity sitting in a helper that 200 tests call is **amortised
  infrastructure** — the suite pays for it once;
* complexity sitting in a helper that exactly one test calls was **displaced,
  not shared** — the test paid the indirection cost without the benefit.

## Data and the two accounting models

A new per-helper table (`build_helper_detail.py` →
`test_helper_detail_46projects.csv`) attributes LOC/CC/CCTR to each individual
helper: **819,125 (test, helper) pairs, 118,744 tests, 69,858 distinct helpers,
46 projects**. It is calibrated against the main table — per-helper CCTR sums
back to `helper_cctr_sum` for 118,686 of 118,686 comparable tests, with the
only exclusions being the 58 known overloaded-method key collisions.

`reuse(h)` = how many distinct tests in that project call `h`, counted over the
**whole** test population (parameterized and not), since a helper shared with
ordinary tests is just as amortised. Overall: median reuse 2, max 2,701, and
**34% of helpers are called by exactly one test**.

Two accounting models are reported because which one is "right" is a design
argument, not a measurement question, and they bracket the truth:

| model | definition | whose cost it is |
|---|---|---|
| **reader** | `self + Σ helper` | reading *this* test means understanding every helper it calls, in full. This is the existing `total_*`. |
| **maintainer** | `self + Σ helper / reuse` | the suite holds each helper once; charge each test its share. |

Plus two descriptive measures: **amortisation** = `Σ cctr(h)·reuse(h) / Σ cctr(h)`
(complexity-weighted mean reuse) and **private share** =
`Σ_{reuse=1} cctr(h) / Σ cctr(h)`.

> **Population caveat.** Amortisation is only defined for tests that *have* a
> helper layer, so everything here is conditional on `helper_count ≥ 1`
> (118,744 of 199,437 tests). This matters a great deal for one comparison —
> see Finding 3.

> **Two conventions for the PT vs non-PT contrast**, both of which bite only
> when a comparison crosses the parameterized boundary:
>
> 1. **JUnit 5 on both sides.** Every parameterized test in the corpus is
>    JUnit 5 (8,299 of 8,299), while the non-parameterized pool also holds
>    20,093 JUnit 4 tests and 211 TestNG/unknown ones. Comparing against the
>    unrestricted pool would mix the effect of parameterizing with the effect of
>    changing test framework. Note the restriction applies to the *comparison*
>    only — `reuse(h)` is still counted over every test that calls `h`, JUnit 4
>    included, because a helper shared with a JUnit 4 test is genuinely shared.
> 2. **Read it on `cctr_eq`.** Plain CCTR scores `@ParameterizedTest` at 2 and
>    `@Test` at 1, so every parameterized test receives a fixed +1 no ordinary
>    test can earn. `cctr_eq` scores them equally. Within-PT contrasts are
>    unaffected — the +1 is constant on both sides there, so Cliff's δ is
>    identical either way, which the re-run confirms to the digit.

---

## Finding 1 — The complexity dependency "costs" is heavily shared

Complexity-weighted helper reuse, by MethodSource dependency level
(`amortization_reuse_profile.png`):

| level | weighted reuse (median) | private CCTR share (mean) |
|---|---|---|
| L0 | 18.0 | 0.092 |
| L1 | 11.0 | 0.157 |
| **L2** | **267.9** | 0.037 |
| L3 | 25.8 | 0.085 |
| **L4** | **125.6** | 0.053 |

L2 vs L0 on weighted reuse is **δ = 0.612 (large)**, L4 vs L0 δ = 0.329 (small).
The helper complexity that appears at L2+ sits in methods shared by *hundreds*
of tests. L1 is the opposite: its weighted reuse (11) is **lower** than L0's
(δ = −0.242, small) and its private share is the highest of any level (0.157).

## Finding 2 — Under maintainer accounting the dependency penalty disappears — cleanly for CCTR and CC, only partly for LOC

The headline (`amortization_effect_reversal.png`), and it is **measure-dependent**,
so all three are reported. δ > 0 = that level more complex than L0;
† = the sign flips if one project is dropped.

| contrast | LOC raw → adj | CC raw → adj | CCTR raw → adj |
|---|---|---|---|
| L1 vs L0 | +0.17 → **+0.21** | +0.17 → **+0.25** | +0.02 → +0.06 |
| L2 vs L0 | +0.40 → **+0.22** (no reversal) | +0.48 → −0.16 † | +0.34 → −0.21 † |
| L3 vs L0 | +0.13 → **−0.19** | +0.30 → −0.05 † | +0.12 → **−0.20** |
| L4 vs L0 | +0.34 → +0.05 † | +0.36 → **−0.13** | +0.24 → **−0.22** |

What is common to all three measures: **adjusting for reuse always shrinks the
dependency penalty**, usually to nothing. What differs is whether it crosses
zero:

* **CCTR** reverses at L2, L3 and L4 (L3 and L4 robustly).
* **CC** reverses at all three too, but two of them (L2, L3) are not
  LOO-stable and L3's lands at −0.05, i.e. "the gap vanishes" rather than
  "it inverts".
* **LOC resists.** At L2 it stays clearly positive (+0.22, small) and at L4 it
  lands at +0.05 with an unstable sign. Only L3 reverses.

So the defensible statement is **"the apparent complexity penalty of
out-of-class dependency is an artefact of counting shared helpers once per
test"**, not "distant dependencies are simpler". The strong version holds for
CCTR; for LOC the honest reading is that the gap shrinks by roughly half but
does not invert.

Why LOC behaves differently is **open**. The obvious explanation — that
heavily reused helpers are also larger, so LOC's helper term survives the
division — was tested against the per-helper data and **does not hold**: helper
size and reuse are essentially uncorrelated across all 69,858 distinct helpers
(Spearman ρ = +0.002 for LOC, −0.000 for CCTR; median helper LOC is 5–7 in every
reuse bin from 1 to 2,701). Something else drives the asymmetry, and this
analysis does not identify it.

**A result the CCTR-only reading hid:** L1 is *not* flat. On LOC and CC, L1
tests are a small but real step above L0 (δ = +0.17 / +0.17) and the gap
**grows** under adjustment (+0.21 / +0.25, both LOO-stable). Only on CCTR is L1
negligible. That is consistent with Finding 1 — L1 has the least-reused helpers
and the most private complexity of any level — and it means a provider kept
inside the test class is the one arrangement whose extra size is genuinely the
test's own.

## Finding 3 — RQ3.3's provider-vs-inline gap is mostly about *having* a helper layer

Within this population, provider vs inline on reader CCTR is δ = −0.015
(negligible) — but RQ3.3 reported +0.197 (small) for the same contrast. The two
are not in conflict; the difference is the conditioning:

| family | share of tests with ≥1 helper |
|---|---|
| inline | **65%** |
| type | 76% |
| file | 96% |
| provider | **99%** |

Nearly every provider-backed test has a helper layer (the provider itself is
one), while a third of inline tests have none at all. Once you restrict to
tests that *have* helpers, provider and inline helper layers look alike.

**So RQ3.3's effect is better stated as: choosing a provider-backed source
makes it near-certain that the test acquires a helper layer, not that its
helper layer is heavier than anyone else's.** That is a sharper and more
defensible claim than the original phrasing.

(The dependency analysis is not affected by this conditioning: 95–100% of tests
at every level have a helper layer.)

## Finding 4 — Parameterization does cost more, but on CCTR most of the "it gets worse" was the metric

Restricted to JUnit 5 on both sides (7,345 PT vs 100,088 non-PT), all four
measures agree that parameterized tests carry more complexity. They disagree
about what amortisation does to that gap:

| measure | reader δ | maintainer δ | |
|---|---|---|---|
| LOC | 0.333 (medium) | **0.382 (medium)** | strengthens |
| CC | 0.271 (small) | **0.441 (medium)** | strengthens |
| CCTR (plain) | 0.299 (small) | 0.362 (medium) | strengthens |
| **CCTR_eq (de-biased)** | **0.229 (small)** | **0.195 (small)** | **weakens** |

All eight figures are LOO-stable across all 46 projects.

**The earlier claim that PT is the one contrast that strengthens under
maintainer accounting survives on LOC and CC, but not on CCTR.** On the
de-biased variant the gap is smaller to begin with (0.229, not 0.299) and it
*shrinks* under amortisation (0.195) rather than growing to medium.

The mechanism is straightforward: the `@ParameterizedTest` bonus sits in the
**self** term, which neither model divides. Under maintainer accounting the
helper term is divided by reuse and so contributes less, which makes the
undivided self term — carrying that constant +1 — weigh more. The bias
therefore inflates the maintainer δ more than the reader δ, and removing it
pulls the maintainer figure down the furthest.

So the defensible statement is: **parameterized tests are larger and more
branching than matched non-parameterized ones even after shared helpers are
charged once (LOC δ = 0.38, CC δ = 0.44), and their helpers are less reused
(weighted reuse 24.0 vs 37.5) with more private complexity (0.078 vs 0.045).
On CCTR specifically the gap is small and does not grow under amortisation
once the annotation bonus is removed.**

## Finding 5 — The reuse measure checks out against an independent tool

Reuse is the load-bearing construct here, so it is worth validating against
something measured by entirely different machinery. **DUP is deliberately not
amortised** — reuse and duplication are the same construct from opposite
directions (a helper called by 200 tests is, by definition, code that was not
copy-pasted 200 times), so dividing duplicated lines by reuse would explain a
measure with itself. Instead reuse is tested *against* duplication, as judged by
CCFinderSW clone detection:

| | Spearman ρ | n |
|---|---|---|
| weighted reuse (CCTR) vs helper DUP% | **−0.269** | 91,514 |
| weighted reuse (LOC) vs helper DUP% | −0.207 | 117,331 |
| weighted reuse (CCTR) vs total DUP% | −0.248 | 91,514 |
| **private** CCTR share vs helper DUP% | **+0.082** | 91,514 |

All p < 1e-12. The signs are exactly what the construct predicts: more reuse →
less duplicated helper code; more *private* complexity → more duplication.

The decile view is the clearer picture — median helper duplication falls
almost monotonically as weighted reuse rises:

| reuse decile (median weighted reuse) | median helper DUP% |
|---|---|
| 1 (2×) | **0.246** |
| 3 (8×) | 0.140 |
| 5 (26×) | 0.118 |
| 7 (101×) | 0.000 |
| 10 (1,644×) | **0.000** |

ρ of −0.27 is modest, but the practical spread — a quarter of the helper code
duplicated at the bottom, none at the top — is not. Reuse is measuring what the
analysis assumes it measures.

## What this does and does not license

It licenses saying that the extra helper complexity at L3/L4 is shared
infrastructure rather than a per-test burden, and that PT's extra complexity is
not.

It does **not** license calling either "good" outright. Reuse has two faces: a
helper called by 2,701 tests is amortised, but it is also a change-amplification
point — editing it touches 2,701 tests. Separating "good abstraction" from
"risk concentration" needs change history, which is not available here (the
local clones are shallow, one commit each). That remains the natural next step.

## Future work — separating the provider from ordinary helpers

The helper layer currently mixes two things that mean different things: the
`@MethodSource` **provider**, which exists only because the test is
parameterized, and **ordinary helpers** (assertion utilities, fixture builders)
that a non-parameterized test would call just as readily. Summing them conflates
the cost of parameterizing with the cost of the test's general infrastructure.

This matters most for the cross-source comparison, where it is partly
definitional: a MethodSource test *must* have a provider, and the provider is a
helper, so "MethodSource tests carry more helper complexity" is in part built
into the measurement rather than discovered. RQ3.3's Finding 3 already addresses
the largest part of that — conditioning on having a helper layer collapses the
provider-vs-inline gap — but a clean four-level split (self / provider / other
helpers / total) would settle it directly.

The split is feasible: the provider is identifiable from the AAA
`parameterSources` field (`@MethodSource("name")`) together with
`provider_declaring_class`, matching a test-scope helper for **97%** of
MethodSource tests, with the remainder being external providers such as
`java.util.Locale#getISOCountries` that are out of scope by design. A further
958 tests use the no-argument `@MethodSource` form, where the provider shares
the test's name and the pipeline's existing same-name disambiguation applies.

It is left as future work: the decomposition exists only for provider-backed
sources, so it cannot carry the cross-source comparison, and the registered
report commits to comparing LOC/CC/CCTR/DUP across source patterns rather than
to any decomposition of the helper layer.

## Limitations

* **The maintainer model assumes equal division** of a helper's complexity
  among its callers. It is a defensible convention, not a measured fact; the
  reader model is the opposite extreme, and the two are reported together for
  that reason.
* **`reuse` counts callers across the whole suite**, including non-PT tests not
  in any contrast. That is intended (suite-level accounting) but means a
  group's maintainer total depends on tests outside the comparison.
* **Conditional on `helper_count ≥ 1`** — see Finding 3.
* **The PT vs non-PT contrast is JUnit 5 only and read on `cctr_eq`** — see the
  conventions note above. On plain CCTR against the unrestricted non-PT pool the
  same contrast reads 0.303 → 0.370; most of the difference is the annotation
  bonus rather than the tests.
* **The reversal is measure-dependent** — it is clean for CCTR, partial for CC,
  and largely absent for LOC. Several of the individual reversals are also not
  LOO-stable (marked † in Finding 2). The robust claim is that the penalty
  shrinks under reuse adjustment, not that it inverts for every measure.
* **DUP is not amortised** by design — see Finding 5.
* Ratio metrics are undefined where a test's helpers carry zero complexity
  (e.g. only implicit default constructors); those rows are excluded from the
  ratios but kept for the totals.

## Files

| file | contents |
|---|---|
| `../build_helper_detail.py` | per-(test, helper) LOC/CC/CCTR, reusing the main pipeline's resolution |
| `build_amortization_dataset.py` | reuse counts + both accounting models per test |
| `amortization_metrics.csv` | 118,744 tests, the analysis dataset |
| `analyze_amortization.py` | profile, model comparison, Kruskal–Wallis, LOO |
| `amortization_profile.csv` | weighted reuse + private share per design group |
| `amortization_model_comparison.csv` | **every contrast under both models** |
| `amortization_reuse_dup_validity.csv` | reuse vs CCFinderSW duplication, with the decile view |
| `amortization_robustness_loo.csv` | leave-one-project-out ranges, all three measures |
| `amortization_effect_reversal.png` | raw vs reuse-adjusted δ, L1–L4 vs L0, with LOO ranges |
| `amortization_reuse_profile.png` | the mechanism: weighted reuse and single-use share per level |

```bash
# 前置：test_helper_detail_46projects.csv（随包 .gz；或 rq3/code/rq3_1/build_helper_detail.py 重建，约 25 分钟）
cd rq3/code/rq3_2/amortization      # 须在 cross_source 之后跑；或直接 rq3/code/run_rq3.sh
python3 build_amortization_dataset.py
python3 analyze_amortization.py
python3 plot_amortization.py
python3 ../make_result_appendix.py   # 重写各 FINDINGS 文末的附录
```

---

<!-- APPENDIX:BEGIN (generated by make_result_appendix.py -- do not edit by hand) -->

## Appendix — complete results

Generated from the analysis CSVs by `make_result_appendix.py`; no number here is hand-typed. Bold = significant and at least a small effect.

### A1. Full distribution of complexity-weighted helper reuse

The central tendency alone is misleading here: these distributions are strongly right-skewed and heavy-tailed, with the mean several times the median. `share = 1` is the fraction of tests whose helper complexity is shared with no other test at all.

| group | n | mean | SD | CV | min | p5 | q1 | median | q3 | p90 | p95 | p99 | max | share =1 | share <=2 | share >=100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| category=nonpt | 77469 | 341.946 | 645.448 | 1.888 | 1.000 | 2.000 | 8.000 | 37.500 | 330.000 | 1230.143 | 2353.600 | 2701.000 | 2701.000 | 0.0317 | 0.0769 | 0.3753 |
| category=pt | 5606 | 163.167 | 388.462 | 2.381 | 1.000 | 1.000 | 7.000 | 23.971 | 118.850 | 442.329 | 658.764 | 2361.378 | 2576.780 | 0.0544 | 0.0999 | 0.2908 |
| dependency=L0 | 2261 | 106.155 | 233.193 | 2.197 | 1.000 | 1.000 | 6.000 | 18.000 | 74.435 | 309.000 | 544.803 | 1073.283 | 2576.780 | 0.0708 | 0.1137 | 0.2163 |
| dependency=L1 | 283 | 62.023 | 166.204 | 2.680 | 1.000 | 1.000 | 4.278 | 11.000 | 19.667 | 77.295 | 524.303 | 718.037 | 828.711 | 0.1060 | 0.1590 | 0.0883 |
| dependency=L2 | 434 | 761.112 | 957.832 | 1.258 | 1.000 | 7.950 | 60.000 | 267.882 | 2084.863 | 2361.378 | 2361.378 | 2576.780 | 2576.780 | 0.0069 | 0.0069 | 0.6359 |
| dependency=L3 | 445 | 63.185 | 97.384 | 1.541 | 1.000 | 1.000 | 5.750 | 25.814 | 100.294 | 107.857 | 144.875 | 605.500 | 658.444 | 0.0674 | 0.1303 | 0.2629 |
| dependency=L4 | 547 | 158.789 | 214.261 | 1.349 | 1.000 | 2.000 | 14.000 | 125.558 | 171.927 | 465.868 | 546.543 | 1140.364 | 1267.600 | 0.0329 | 0.0530 | 0.5210 |
| family=inline | 1005 | 163.323 | 308.727 | 1.890 | 1.000 | 2.000 | 5.111 | 31.000 | 167.929 | 470.288 | 593.118 | 1643.500 | 1761.000 | 0.0388 | 0.1114 | 0.3393 |
| family=type | 506 | 79.742 | 173.974 | 2.182 | 1.000 | 1.961 | 8.934 | 21.000 | 48.000 | 247.473 | 444.872 | 800.015 | 1559.750 | 0.0435 | 0.0672 | 0.1640 |
| family=file | 35 | 87.838 | 237.263 | 2.701 | 2.000 | 2.000 | 8.000 | 21.667 | 21.667 | 31.000 | 851.000 | 851.000 | 851.000 | 0.0000 | 0.1714 | 0.0857 |
| family=provider | 3990 | 175.517 | 426.204 | 2.428 | 1.000 | 1.000 | 7.000 | 24.619 | 124.960 | 448.122 | 863.655 | 2361.378 | 2576.780 | 0.0604 | 0.0985 | 0.2992 |
| construction=Literal | 1290 | 110.294 | 225.586 | 2.045 | 1.000 | 1.445 | 7.000 | 20.000 | 100.137 | 364.448 | 558.978 | 1157.936 | 1568.245 | 0.0450 | 0.0884 | 0.2512 |
| construction=Dynamic | 2680 | 209.174 | 493.411 | 2.359 | 1.000 | 1.000 | 6.500 | 34.000 | 151.937 | 479.299 | 1010.540 | 2361.378 | 2576.780 | 0.0683 | 0.1037 | 0.3239 |

### A2. Full distribution of the other amortisation measures

**private CCTR share**

| group | n | mean | SD | min | q1 | median | q3 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| category=nonpt | 77469 | 0.045 | 0.192 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| category=pt | 5606 | 0.078 | 0.248 | 0.000 | 0.000 | 0.000 | 0.000 | 0.126 | 1.000 | 1.000 |
| dependency=L0 | 2261 | 0.092 | 0.272 | 0.000 | 0.000 | 0.000 | 0.000 | 0.240 | 1.000 | 1.000 |
| dependency=L1 | 283 | 0.157 | 0.340 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| dependency=L2 | 434 | 0.037 | 0.156 | 0.000 | 0.000 | 0.000 | 0.000 | 0.008 | 0.871 | 1.000 |
| dependency=L3 | 445 | 0.085 | 0.264 | 0.000 | 0.000 | 0.000 | 0.000 | 0.129 | 1.000 | 1.000 |
| dependency=L4 | 547 | 0.053 | 0.199 | 0.000 | 0.000 | 0.000 | 0.000 | 0.015 | 1.000 | 1.000 |
| family=inline | 1005 | 0.063 | 0.218 | 0.000 | 0.000 | 0.000 | 0.000 | 0.083 | 1.000 | 1.000 |
| family=type | 506 | 0.064 | 0.228 | 0.000 | 0.000 | 0.000 | 0.000 | 0.040 | 1.000 | 1.000 |
| family=file | 35 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| family=provider | 3990 | 0.084 | 0.259 | 0.000 | 0.000 | 0.000 | 0.000 | 0.188 | 1.000 | 1.000 |
| construction=Literal | 1290 | 0.068 | 0.230 | 0.000 | 0.000 | 0.000 | 0.000 | 0.100 | 1.000 | 1.000 |
| construction=Dynamic | 2680 | 0.092 | 0.272 | 0.000 | 0.000 | 0.000 | 0.000 | 0.277 | 1.000 | 1.000 |

**helper count**

| group | n | mean | SD | min | q1 | median | q3 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| category=nonpt | 100088 | 6.576 | 10.682 | 1.000 | 1.000 | 3.000 | 6.000 | 17.000 | 59.000 | 135.000 |
| category=pt | 7345 | 12.836 | 19.893 | 1.000 | 2.000 | 4.000 | 15.000 | 34.000 | 109.000 | 131.000 |
| dependency=L0 | 3383 | 9.050 | 14.658 | 1.000 | 1.000 | 3.000 | 9.000 | 23.000 | 73.180 | 103.000 |
| dependency=L1 | 353 | 8.513 | 12.098 | 1.000 | 4.000 | 6.000 | 9.000 | 13.000 | 78.320 | 95.000 |
| dependency=L2 | 480 | 36.692 | 40.560 | 1.000 | 4.000 | 25.500 | 45.000 | 112.000 | 126.630 | 131.000 |
| dependency=L3 | 502 | 13.151 | 10.477 | 1.000 | 3.000 | 11.000 | 25.000 | 27.000 | 32.000 | 37.000 |
| dependency=L4 | 670 | 22.403 | 22.256 | 1.000 | 3.000 | 11.000 | 39.000 | 54.000 | 80.000 | 93.000 |
| family=inline | 1178 | 11.330 | 15.485 | 1.000 | 2.000 | 5.000 | 13.000 | 32.000 | 65.000 | 87.000 |
| family=type | 629 | 11.711 | 20.584 | 1.000 | 2.000 | 3.000 | 11.000 | 28.200 | 91.000 | 104.000 |
| family=file | 46 | 4.935 | 4.041 | 1.000 | 1.000 | 2.500 | 10.000 | 10.000 | 10.000 | 10.000 |
| family=provider | 5415 | 13.469 | 20.803 | 1.000 | 2.000 | 5.000 | 17.000 | 37.000 | 112.000 | 131.000 |
| construction=Literal | 2015 | 10.044 | 16.014 | 1.000 | 2.000 | 4.000 | 11.000 | 27.000 | 81.580 | 103.000 |
| construction=Dynamic | 3373 | 15.597 | 23.003 | 1.000 | 2.000 | 5.000 | 21.000 | 43.000 | 114.000 | 131.000 |

**single-use helper count**

| group | n | mean | SD | min | q1 | median | q3 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| category=nonpt | 100088 | 0.187 | 0.820 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 3.000 | 48.000 |
| category=pt | 7345 | 0.481 | 1.425 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 6.000 | 38.000 |
| dependency=L0 | 3383 | 0.494 | 1.124 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 4.000 | 28.000 |
| dependency=L1 | 353 | 1.093 | 2.203 | 0.000 | 0.000 | 0.000 | 1.000 | 3.000 | 11.480 | 15.000 |
| dependency=L2 | 480 | 0.379 | 1.113 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 6.000 | 11.000 |
| dependency=L3 | 502 | 0.422 | 0.991 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 4.990 | 9.000 |
| dependency=L4 | 670 | 0.561 | 2.344 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 8.620 | 30.000 |
| family=inline | 1178 | 0.368 | 1.567 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 4.230 | 38.000 |
| family=type | 629 | 0.355 | 1.205 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 5.000 | 18.000 |
| family=file | 46 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| family=provider | 5415 | 0.524 | 1.419 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 6.000 | 30.000 |
| construction=Literal | 2015 | 0.472 | 1.022 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 5.000 | 11.000 |
| construction=Dynamic | 3373 | 0.556 | 1.612 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 6.000 | 30.000 |

**maintainer total CCTR**

| group | n | mean | SD | min | q1 | median | q3 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| category=nonpt | 100088 | 5.857 | 8.113 | 1.000 | 2.000 | 3.500 | 7.000 | 12.200 | 35.287 | 427.300 |
| category=pt | 7345 | 9.003 | 12.642 | 2.000 | 3.841 | 6.000 | 10.200 | 17.956 | 48.673 | 657.000 |
| dependency=L0 | 3383 | 9.532 | 15.225 | 2.000 | 4.000 | 6.000 | 11.000 | 18.534 | 50.307 | 657.000 |
| dependency=L1 | 353 | 10.940 | 19.734 | 2.067 | 4.105 | 6.436 | 10.500 | 18.333 | 101.648 | 215.727 |
| dependency=L2 | 480 | 7.383 | 7.668 | 2.000 | 3.000 | 4.749 | 8.667 | 15.368 | 40.230 | 60.200 |
| dependency=L3 | 502 | 7.413 | 7.790 | 2.143 | 3.249 | 4.442 | 8.181 | 16.400 | 41.800 | 78.000 |
| dependency=L4 | 670 | 7.276 | 7.951 | 2.000 | 3.000 | 4.333 | 8.000 | 14.004 | 42.261 | 73.011 |
| family=inline | 1178 | 9.020 | 7.745 | 2.000 | 4.000 | 6.727 | 11.000 | 18.052 | 40.268 | 64.000 |
| family=type | 629 | 10.073 | 10.482 | 2.041 | 4.000 | 7.000 | 12.048 | 19.005 | 58.135 | 75.167 |
| family=file | 46 | 3.568 | 1.049 | 3.000 | 3.032 | 3.316 | 3.458 | 4.000 | 8.000 | 8.000 |
| family=provider | 5415 | 8.959 | 13.796 | 2.000 | 3.841 | 5.667 | 10.000 | 17.797 | 48.979 | 657.000 |
| construction=Literal | 2015 | 9.766 | 11.680 | 2.000 | 4.000 | 6.143 | 11.000 | 19.747 | 52.608 | 192.000 |
| construction=Dynamic | 3373 | 8.470 | 14.931 | 2.000 | 3.410 | 5.196 | 9.417 | 17.000 | 46.140 | 657.000 |

**reader total CCTR**

| group | n | mean | SD | min | q1 | median | q3 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| category=nonpt | 100088 | 16.835 | 27.954 | 1.000 | 4.000 | 8.000 | 17.000 | 42.000 | 136.000 | 581.000 |
| category=pt | 7345 | 30.149 | 40.317 | 2.000 | 6.000 | 15.000 | 35.000 | 78.000 | 183.480 | 657.000 |
| dependency=L0 | 3383 | 26.861 | 36.217 | 2.000 | 5.000 | 13.000 | 30.000 | 68.000 | 161.000 | 657.000 |
| dependency=L1 | 353 | 23.465 | 43.468 | 3.000 | 8.000 | 15.000 | 26.000 | 34.000 | 231.000 | 467.000 |
| dependency=L2 | 480 | 41.606 | 32.258 | 2.000 | 14.750 | 44.000 | 53.000 | 88.000 | 128.000 | 187.000 |
| dependency=L3 | 502 | 25.492 | 26.746 | 3.000 | 7.000 | 21.000 | 36.000 | 50.000 | 112.000 | 205.000 |
| dependency=L4 | 670 | 53.972 | 61.930 | 2.000 | 7.250 | 20.000 | 93.000 | 152.000 | 264.310 | 266.000 |
| family=inline | 1178 | 27.913 | 34.076 | 2.000 | 7.000 | 16.000 | 33.000 | 60.000 | 147.460 | 233.000 |
| family=type | 629 | 29.641 | 48.142 | 3.000 | 7.000 | 12.000 | 23.000 | 74.400 | 218.000 | 265.000 |
| family=file | 46 | 6.370 | 2.645 | 3.000 | 4.000 | 6.000 | 9.000 | 9.000 | 11.000 | 11.000 |
| family=provider | 5415 | 31.094 | 40.875 | 2.000 | 6.000 | 15.000 | 38.000 | 80.600 | 178.000 | 657.000 |
| construction=Literal | 2015 | 28.050 | 35.858 | 2.000 | 5.000 | 12.000 | 34.000 | 75.000 | 162.000 | 217.000 |
| construction=Dynamic | 3373 | 33.075 | 43.576 | 2.000 | 7.000 | 16.000 | 40.000 | 91.000 | 187.000 | 657.000 |

### A3. Both accounting models, every contrast and measure

Positive delta = the first-named group larger.

| contrast | measure | n (a) | n (b) | delta reader | magnitude | delta maintainer | magnitude | gap shrinks | to negligible |
|---|---|---|---|---|---|---|---|---|---|
| Dynamic vs Literal | LOC | 3373 | 2015 | 0.145 | negligible | -0.027 | negligible | yes | no |
| Dynamic vs Literal | CC | 3373 | 2015 | **0.216** | small | 0.011 | negligible | yes | yes |
| Dynamic vs Literal | CCTR | 3373 | 2015 | 0.103 | negligible | -0.121 | negligible | no | no |
| L2 vs L0 | LOC | 480 | 3383 | **0.396** | medium | **0.216** | small | yes | no |
| L2 vs L0 | CC | 480 | 3383 | **0.483** | large | **-0.163** | small | yes | no |
| L2 vs L0 | CCTR | 480 | 3383 | **0.345** | medium | **-0.205** | small | yes | no |
| L3 vs L0 | LOC | 502 | 3383 | 0.131 | negligible | **-0.195** | small | no | no |
| L3 vs L0 | CC | 502 | 3383 | **0.297** | small | -0.051 | negligible | yes | yes |
| L3 vs L0 | CCTR | 502 | 3383 | 0.116 | negligible | **-0.200** | small | no | no |
| L4 vs L0 | LOC | 670 | 3383 | **0.342** | medium | 0.052 | negligible | yes | yes |
| L4 vs L0 | CC | 670 | 3383 | **0.361** | medium | -0.130 | negligible | yes | yes |
| L4 vs L0 | CCTR | 670 | 3383 | **0.244** | small | **-0.219** | small | yes | no |
| L1 vs L0 | LOC | 353 | 3383 | **0.170** | small | **0.212** | small | no | no |
| L1 vs L0 | CC | 353 | 3383 | **0.166** | small | **0.254** | small | no | no |
| L1 vs L0 | CCTR | 353 | 3383 | 0.019 | negligible | 0.056 | negligible | no | no |
| provider vs inline | LOC | 5415 | 1178 | -0.001 | negligible | -0.066 | negligible | no | no |
| provider vs inline | CC | 5415 | 1178 | 0.005 | negligible | 0.009 | negligible | no | no |
| provider vs inline | CCTR | 5415 | 1178 | -0.015 | negligible | -0.092 | negligible | no | no |
| provider vs type | LOC | 5415 | 629 | 0.038 | negligible | -0.081 | negligible | no | no |
| provider vs type | CC | 5415 | 629 | 0.134 | negligible | **0.164** | small | no | no |
| provider vs type | CCTR | 5415 | 629 | 0.063 | negligible | -0.110 | negligible | no | no |
| pt vs nonpt (JUnit 5 only) | LOC | 7345 | 100088 | **0.333** | medium | **0.382** | medium | no | no |
| pt vs nonpt (JUnit 5 only) | CC | 7345 | 100088 | **0.271** | small | **0.441** | medium | no | no |
| pt vs nonpt (JUnit 5 only) | CCTR | 7345 | 100088 | **0.299** | small | **0.362** | medium | no | no |

### A4. Amortisation and private share, by contrast (CCTR)

| contrast | delta weighted reuse | magnitude | p | delta private share | magnitude | p |
|---|---|---|---|---|---|---|
| Dynamic vs Literal | 0.082 | negligible | 0.000026 | 0.021 | negligible | 0.073270 |
| L2 vs L0 | **0.612** | large | 0.000000 | -0.052 | negligible | 0.004380 |
| L3 vs L0 | 0.045 | negligible | 0.129492 | -0.021 | negligible | 0.262119 |
| L4 vs L0 | **0.329** | small | 0.000000 | -0.027 | negligible | 0.104616 |
| L1 vs L0 | **-0.242** | small | 0.000000 | 0.057 | negligible | 0.012596 |
| provider vs inline | -0.007 | negligible | 0.736081 | 0.016 | negligible | 0.194635 |
| provider vs type | 0.080 | negligible | 0.003463 | 0.036 | negligible | 0.028987 |
| pt vs nonpt (JUnit 5 only) | -0.125 | negligible | 0.000000 | 0.061 | negligible | 0.000000 |

### A5. Per-group amortisation profile

| group | n | median helpers | median single-use helpers | weighted reuse (median) | weighted reuse (mean) | private share (median) | private share (mean) | n with defined ratio |
|---|---|---|---|---|---|---|---|---|
| construction=Literal | 2015 | 4.00 | 0.00 | 20.00 | 110.29 | 0.0000 | 0.0681 | 1290 |
| construction=Dynamic | 3373 | 5.00 | 0.00 | 34.00 | 209.17 | 0.0000 | 0.0924 | 2680 |
| dependency=L0 | 3383 | 3.00 | 0.00 | 18.00 | 106.15 | 0.0000 | 0.0920 | 2261 |
| dependency=L1 | 353 | 6.00 | 0.00 | 11.00 | 62.02 | 0.0000 | 0.1574 | 283 |
| dependency=L2 | 480 | 25.50 | 0.00 | 267.88 | 761.11 | 0.0000 | 0.0373 | 434 |
| dependency=L3 | 502 | 11.00 | 0.00 | 25.81 | 63.18 | 0.0000 | 0.0849 | 445 |
| dependency=L4 | 670 | 11.00 | 0.00 | 125.56 | 158.79 | 0.0000 | 0.0532 | 547 |
| family=inline | 1178 | 5.00 | 0.00 | 31.00 | 163.32 | 0.0000 | 0.0629 | 1005 |
| family=type | 629 | 3.00 | 0.00 | 21.00 | 79.74 | 0.0000 | 0.0645 | 506 |
| family=file | 46 | 2.50 | 0.00 | 21.67 | 87.84 | 0.0000 | 0.0000 | 35 |
| family=provider | 5415 | 5.00 | 0.00 | 24.62 | 175.52 | 0.0000 | 0.0843 | 3990 |
| category=nonpt | 100088 | 3.00 | 0.00 | 37.50 | 341.95 | 0.0000 | 0.0453 | 77469 |
| category=pt | 7345 | 4.00 | 0.00 | 23.97 | 163.17 | 0.0000 | 0.0779 | 5606 |

### A6. Reuse vs duplication — convergent validity

DUP is deliberately not amortised; it is used to validate the reuse measure against an independent tool (CCFinderSW).

| x | y | n | Spearman rho | p |
|---|---|---|---|---|
| amortization_cctr | helper_dupPerc | 91514 | -0.2688 | 0.000000 |
| amortization_loc | helper_dupPerc | 117331 | -0.2068 | 0.000000 |
| amortization_cctr | total_dupPerc | 91514 | -0.2477 | 0.000000 |
| private_cctr_share | helper_dupPerc | 91514 | 0.0817 | 0.000000 |

Binned view — median helper duplication by reuse decile:

| decile | n | weighted reuse range -> median helper DUP% |
|---|---|---|
| reuse decile 1 | 9151 | weighted reuse 1.0-2.0 (median 2.0) -> median dup 0.2462 |
| reuse decile 2 | 9151 | weighted reuse 4.0-5.0 (median 4.0) -> median dup 0.1818 |
| reuse decile 3 | 9151 | weighted reuse 7.0-9.0 (median 8.0) -> median dup 0.1395 |
| reuse decile 4 | 9151 | weighted reuse 12.0-16.0 (median 14.0) -> median dup 0.1667 |
| reuse decile 5 | 9151 | weighted reuse 22.0-29.0 (median 25.7) -> median dup 0.1176 |
| reuse decile 6 | 9151 | weighted reuse 41.8-59.0 (median 49.0) -> median dup 0.0476 |
| reuse decile 7 | 9151 | weighted reuse 80.0-124.9 (median 101.0) -> median dup 0.0000 |
| reuse decile 8 | 9151 | weighted reuse 207.8-313.8 (median 260.8) -> median dup 0.0068 |
| reuse decile 9 | 9151 | weighted reuse 491.8-765.0 (median 640.0) -> median dup 0.0200 |
| reuse decile 10 | 9155 | weighted reuse 1281.5-2550.5 (median 1643.5) -> median dup 0.0000 |

### A7. Leave-one-project-out robustness

| contrast | metric | delta (full) | delta range under LOO | projects | sign stable |
|---|---|---|---|---|---|
| Dynamic vs Literal | reader_total_loc | 0.1455 | 0.0927 .. 0.2512 | 45 | yes |
| Dynamic vs Literal | maintainer_total_loc | -0.0270 | -0.0668 .. 0.0166 | 45 | no |
| Dynamic vs Literal | reader_total_cc | 0.2162 | 0.1711 .. 0.3097 | 45 | yes |
| Dynamic vs Literal | maintainer_total_cc | 0.0109 | -0.0146 .. 0.0571 | 45 | no |
| Dynamic vs Literal | reader_total_cctr | 0.1027 | 0.0573 .. 0.2275 | 45 | yes |
| Dynamic vs Literal | maintainer_total_cctr | -0.1207 | -0.1491 .. -0.0612 | 45 | yes |
| Dynamic vs Literal | reader_total_cctr_eq | 0.1028 | 0.0574 .. 0.2276 | 45 | yes |
| Dynamic vs Literal | maintainer_total_cctr_eq | -0.1206 | -0.1490 .. -0.0612 | 45 | yes |
| Dynamic vs Literal | amortization_cctr | 0.0823 | 0.0027 .. 0.1406 | 45 | yes |
| Dynamic vs Literal | private_cctr_share | 0.0213 | 0.0073 .. 0.0386 | 45 | yes |
| L2 vs L0 | reader_total_loc | 0.3962 | 0.2536 .. 0.4951 | 43 | yes |
| L2 vs L0 | maintainer_total_loc | 0.2164 | 0.0991 .. 0.2801 | 43 | yes |
| L2 vs L0 | reader_total_cc | 0.4829 | 0.3763 .. 0.6080 | 43 | yes |
| L2 vs L0 | maintainer_total_cc | -0.1627 | -0.2826 .. 0.0164 | 43 | no |
| L2 vs L0 | reader_total_cctr | 0.3448 | 0.2484 .. 0.4733 | 43 | yes |
| L2 vs L0 | maintainer_total_cctr | -0.2054 | -0.3434 .. 0.0233 | 43 | no |
| L2 vs L0 | reader_total_cctr_eq | 0.3448 | 0.2485 .. 0.4734 | 43 | yes |
| L2 vs L0 | maintainer_total_cctr_eq | -0.2052 | -0.3431 .. 0.0235 | 43 | no |
| L2 vs L0 | amortization_cctr | 0.6115 | 0.4792 .. 0.6814 | 43 | yes |
| L2 vs L0 | private_cctr_share | -0.0524 | -0.0993 .. -0.0232 | 43 | yes |
| L3 vs L0 | reader_total_loc | 0.1312 | 0.0246 .. 0.2333 | 43 | yes |
| L3 vs L0 | maintainer_total_loc | -0.1946 | -0.2160 .. -0.1460 | 43 | yes |
| L3 vs L0 | reader_total_cc | 0.2972 | 0.2070 .. 0.3896 | 43 | yes |
| L3 vs L0 | maintainer_total_cc | -0.0509 | -0.1459 .. 0.0304 | 43 | no |
| L3 vs L0 | reader_total_cctr | 0.1161 | 0.0571 .. 0.2306 | 43 | yes |
| L3 vs L0 | maintainer_total_cctr | -0.1998 | -0.2365 .. -0.1089 | 43 | yes |
| L3 vs L0 | reader_total_cctr_eq | 0.1159 | 0.0568 .. 0.2305 | 43 | yes |
| L3 vs L0 | maintainer_total_cctr_eq | -0.2011 | -0.2367 .. -0.1104 | 43 | yes |
| L3 vs L0 | amortization_cctr | 0.0454 | -0.0579 .. 0.1133 | 43 | no |
| L3 vs L0 | private_cctr_share | -0.0206 | -0.0421 .. 0.0052 | 43 | no |
| L4 vs L0 | reader_total_loc | 0.3421 | 0.1464 .. 0.4344 | 44 | yes |
| L4 vs L0 | maintainer_total_loc | 0.0517 | -0.0850 .. 0.1324 | 44 | no |
| L4 vs L0 | reader_total_cc | 0.3610 | 0.1791 .. 0.4600 | 44 | yes |
| L4 vs L0 | maintainer_total_cc | -0.1303 | -0.1714 .. -0.0674 | 44 | yes |
| L4 vs L0 | reader_total_cctr | 0.2442 | 0.0528 .. 0.3429 | 44 | yes |
| L4 vs L0 | maintainer_total_cctr | -0.2193 | -0.2423 .. -0.0350 | 44 | yes |
| L4 vs L0 | reader_total_cctr_eq | 0.2442 | 0.0528 .. 0.3429 | 44 | yes |
| L4 vs L0 | maintainer_total_cctr_eq | -0.2194 | -0.2424 .. -0.0355 | 44 | yes |
| L4 vs L0 | amortization_cctr | 0.3288 | 0.1644 .. 0.4106 | 44 | yes |
| L4 vs L0 | private_cctr_share | -0.0274 | -0.0532 .. 0.0261 | 44 | no |
| L1 vs L0 | reader_total_loc | 0.1696 | 0.1417 .. 0.2695 | 44 | yes |
| L1 vs L0 | maintainer_total_loc | 0.2122 | 0.1623 .. 0.2512 | 44 | yes |
| L1 vs L0 | reader_total_cc | 0.1656 | 0.1479 .. 0.2571 | 44 | yes |
| L1 vs L0 | maintainer_total_cc | 0.2541 | 0.2109 .. 0.2956 | 44 | yes |
| L1 vs L0 | reader_total_cctr | 0.0190 | -0.0045 .. 0.0975 | 44 | no |
| L1 vs L0 | maintainer_total_cctr | 0.0560 | 0.0238 .. 0.0981 | 44 | yes |
| L1 vs L0 | reader_total_cctr_eq | 0.0187 | -0.0048 .. 0.0972 | 44 | no |
| L1 vs L0 | maintainer_total_cctr_eq | 0.0558 | 0.0236 .. 0.0979 | 44 | yes |
| L1 vs L0 | amortization_cctr | -0.2422 | -0.2914 .. -0.1990 | 44 | yes |
| L1 vs L0 | private_cctr_share | 0.0573 | 0.0447 .. 0.0730 | 44 | yes |
| provider vs inline | reader_total_loc | -0.0012 | -0.0871 .. 0.0794 | 46 | no |
| provider vs inline | maintainer_total_loc | -0.0659 | -0.1056 .. -0.0129 | 46 | yes |
| provider vs inline | reader_total_cc | 0.0048 | -0.0751 .. 0.0897 | 46 | no |
| provider vs inline | maintainer_total_cc | 0.0093 | -0.0127 .. 0.0865 | 46 | no |
| provider vs inline | reader_total_cctr | -0.0152 | -0.1032 .. 0.0476 | 46 | no |
| provider vs inline | maintainer_total_cctr | -0.0922 | -0.1374 .. -0.0492 | 46 | yes |
| provider vs inline | reader_total_cctr_eq | -0.0151 | -0.1031 .. 0.0478 | 46 | no |
| provider vs inline | maintainer_total_cctr_eq | -0.0919 | -0.1372 .. -0.0489 | 46 | yes |
| provider vs inline | amortization_cctr | -0.0069 | -0.0796 .. 0.0472 | 46 | no |
| provider vs inline | private_cctr_share | 0.0159 | 0.0022 .. 0.0274 | 46 | yes |
| provider vs type | reader_total_loc | 0.0384 | -0.0421 .. 0.1480 | 45 | no |
| provider vs type | maintainer_total_loc | -0.0805 | -0.1232 .. -0.0215 | 45 | yes |
| provider vs type | reader_total_cc | 0.1342 | -0.0124 .. 0.2655 | 45 | no |
| provider vs type | maintainer_total_cc | 0.1639 | 0.0327 .. 0.2418 | 45 | yes |
| provider vs type | reader_total_cctr | 0.0629 | -0.0133 .. 0.1659 | 45 | no |
| provider vs type | maintainer_total_cctr | -0.1097 | -0.1605 .. -0.0699 | 45 | yes |
| provider vs type | reader_total_cctr_eq | 0.0627 | -0.0135 .. 0.1658 | 45 | no |
| provider vs type | maintainer_total_cctr_eq | -0.1100 | -0.1609 .. -0.0703 | 45 | yes |
| provider vs type | amortization_cctr | 0.0796 | 0.0141 .. 0.1671 | 45 | yes |
| provider vs type | private_cctr_share | 0.0358 | 0.0228 .. 0.0574 | 45 | yes |
| pt vs nonpt (JUnit 5 only) | reader_total_loc | 0.3326 | 0.2972 .. 0.3490 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | maintainer_total_loc | 0.3822 | 0.3332 .. 0.4152 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | reader_total_cc | 0.2705 | 0.2434 .. 0.2839 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | maintainer_total_cc | 0.4411 | 0.4182 .. 0.4816 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | reader_total_cctr | 0.2991 | 0.2661 .. 0.3127 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | maintainer_total_cctr | 0.3618 | 0.3099 .. 0.3898 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | reader_total_cctr_eq | 0.2286 | 0.1979 .. 0.2426 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | maintainer_total_cctr_eq | 0.1947 | 0.1360 .. 0.2165 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | amortization_cctr | -0.1250 | -0.1573 .. -0.0888 | 46 | yes |
| pt vs nonpt (JUnit 5 only) | private_cctr_share | 0.0610 | 0.0542 .. 0.0754 | 46 | yes |

<!-- APPENDIX:END -->
