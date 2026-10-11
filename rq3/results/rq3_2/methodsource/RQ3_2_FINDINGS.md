# RQ3.2 — MethodSource design patterns and complexity profiles

> ⚠️ **Read with [`RQ3_2_FULL_POPULATION.md`](RQ3_2_FULL_POPULATION.md).** This
> document analyses the 379 manually validated tests. The same pipeline has
> since been run on the full 5,416-test population, which **confirms Finding 2**
> (construction is a dependency artefact) but **overturns two claims below**:
> L1 does *not* behave like L2–L4 (§4), and Literal's excess duplication does
> *not* survive dependency control (§3).

**Question.** For `@MethodSource` parameterized tests, do the two reliably
quantifiable dimensions of the RQ2 codebook — *Construction* (Literal vs
Dynamic) and *Dependency* (L0–L4) — correspond to different complexity
profiles, and does any difference sit in the test **main body** or in the
**helper/provider logic** behind it?

---

## 1. Data and method

**Sample.** The 379 manually validated MethodSource tests of the RQ2.2
structure table (`pt_methodsource_structure.csv`, 31 Apache projects) joined
to the unified metric pipeline (`test_metrics_all_44projects.csv`) on
`(project, test_class, test_name)`.

| Step | n |
|---|---|
| RQ2.2 MethodSource tests | 379 |
| joined to metrics | **374** (5 dropped: no metrics row — the metric run and the RQ2 run were taken from different project snapshots) |
| usable (`dependency_status` = `OK*`) | 373 (1 `EXTERNAL_PROVIDER` excluded) |
| Construction population | 373 — Dynamic 223, Literal 150 |
| Dependency population | 373 — L0 225, L1 16, L2 35, L3 45, L4 52 |

Seven keys matched both a `pt` and a `nonpt` metrics row (a test class
declaring an overloaded method name, e.g. `@Test void f()` beside
`@ParameterizedTest void f(X)`); the parameterized row was kept. All join
deviations are itemised in `rq32_join_report.csv`.

**Metrics.** Every comparison is run on 3 scopes × 4 metrics: main-body /
helper / total × LOC / CC / CCTR / DUP%. DUP% is the CCFinderSW-derived
duplicated-line ratio; `dupLines` is also tabulated as a supplement.

**Statistics.** Construction (2 groups): Mann–Whitney U + Cliff's δ.
Dependency (5 groups): Kruskal–Wallis, then, where significant, all 10
pairwise Mann–Whitney U tests with Holm (FWER) and Benjamini–Hochberg (FDR)
correction *within each metric*. All tests are implemented in pure Python
(`rq32_stats.py`) for consistency with the RQ3.1 pipeline and were validated
against `scipy`/`statsmodels` to machine precision (max |Δ| ≈ 1e-13).

---

## 2. Finding 1 — the test main body is invariant

Nothing in either design dimension moves the test method's own body.

* **Construction:** main-body LOC δ = 0.009 (p = .89), CC δ = −0.004 (p = .93),
  CCTR δ = −0.122 (p = .042, negligible), DUP% δ = −0.027 (p = .65).
* **Dependency:** Kruskal–Wallis is **non-significant for every main-body
  metric** — LOC p = .075, CC p = .44, CCTR p = .63, DUP% p = .079.
* Median main-body CC is **1 at every dependency level** — MethodSource test
  bodies essentially never contain control flow.

> Whatever a MethodSource design costs a reader, it is not paid in the test
> method itself.

---

## 3. Finding 2 — Construction: the raw effect is a dependency artefact

Taken at face value, Dynamic construction looks more complex than Literal:

| scope / metric | median Dynamic | median Literal | Cliff's δ | p |
|---|---|---|---|---|
| helper LOC | 39 | 21 | 0.281 (small) | 4e-6 |
| helper CC | 8 | 3 | 0.298 (small) | 1e-6 |
| helper CCTR | 7 | 1 | 0.308 (small) | <1e-6 |
| total CCTR | 13 | 7 | 0.231 (small) | 1.5e-4 |

But Construction and Dependency are **strongly confounded**: 123 of 150
Literal tests (82%) are L0, whereas Dynamic spreads across L0–L4 (L0 102,
L4 48). Re-running the same contrast **within the L0 stratum only**
(102 Dynamic vs 123 Literal) collapses every one of those effects:

| scope / metric | δ (all) | δ (L0 only) | p (L0 only) |
|---|---|---|---|
| helper LOC | 0.281 *** | **0.016** | .84 |
| helper CC | 0.298 *** | **0.022** | .78 |
| helper CCTR | 0.308 *** | **0.098** | .18 |
| total CCTR | 0.231 *** | **−0.030** | .70 |
| **total DUP%** | **−0.297** *** | **−0.214 (small)** | **.0057** |

**Construction does not drive size or structural complexity — dependency
does.** The one effect that survives dependency control runs the *other*
way: **Literal constructions duplicate more** (total DUP% median 0.458 vs
0.221; δ = −0.214 within L0). Literal argument tables are copy-paste
artefacts; that is their maintenance cost, not complexity.

---

## 4. Finding 3 — Dependency: a binary step at L0, not a gradient

Kruskal–Wallis is highly significant for every helper and total metric and
for none of the main-body metrics:

| metric | helper H (p) | total H (p) | main-body p |
|---|---|---|---|
| LOC | 46.7 (<1e-6) | 42.6 (<1e-6) | .075 n.s. |
| CC | 66.8 (<1e-6) | 61.8 (<1e-6) | .44 n.s. |
| CCTR | 54.9 (<1e-6) | 50.9 (<1e-6) | .63 n.s. |
| DUP% | 29.1 (8e-6) | 24.2 (7e-5) | .079 n.s. |

The pairwise structure is the important part. For LOC/CC/CCTR, **every
`L{1,2,3,4}` vs `L0` contrast is significant after Holm correction** — all of
them on helper LOC/CC/CCTR and on total CC/CCTR (helper CCTR δ = 0.51 / 0.49 /
0.44 / 0.38, large to medium); the single exception is total LOC for L3 vs L0,
which is marginal (Holm p = .057). Meanwhile **not one L1–L4 contrast survives
correction** (all negligible–small, smallest Holm p = .45). Median helper CCTR
goes 1 (L0) → 7–13 (L1–L4) and then flattens.

> The cost is incurred by *having* an out-of-method dependency at all, not by
> how far away that dependency lives.

**Duplication moves in the opposite direction.** L0 and L1 are the
*most* duplicated groups; pulling provider data into shared or external
artifacts (L2–L4) cuts duplication sharply: helper DUP% median 0.157 (L0) /
0.401 (L1) → 0.012 (L2) / 0.000 (L3) / 0.069 (L4); L2-vs-L1 δ = −0.86
(large, Holm p < 1e-5), and L2/L3/L4 vs L0 are all significantly lower on
total DUP%.

**Net picture: a trade-off.** Dependency buys de-duplication and pays for it
in helper-side size and structural complexity. Neither side of the trade
touches the test body.

---

## 5. Robustness

`rq32_robustness_loo.csv` recomputes each headline δ 31 times, dropping one
project each time (tests are nested in projects and therefore not fully
independent). Every helper- and total-scope effect keeps its sign across all
31 leave-one-out samples (e.g. Dynamic-vs-Literal helper CCTR stays within
0.275–0.359; L4-vs-L0 helper CC within 0.359–0.504). The only sign flips
occur among the main-body effects that are negligible and non-significant
anyway.

## 6. Limitations

* **L1 is small (n = 16).** L1 contrasts are underpowered, and its high
  DUP% median rests on few observations.
* **Confounding is handled only for construction.** The L0 stratification
  isolates construction; no equivalent control exists for dependency (there
  is no design dimension to hold fixed that is not itself part of RQ2).
* **Project clustering** is addressed only by the leave-one-project-out
  check, not by a mixed-effects model.
* **Main-body DUP% is close to bimodal** (medians 0.50–1.00 across levels,
  boxes spanning 0–1): MethodSource test bodies are short enough that a clone
  either covers the whole body or none of it. Read main-body DUP%
  qualitatively.
* 5 of 379 tests (1.3%) are missing from the metric join, and 1 further test
  used an external provider; see `rq32_join_report.csv`.

---

## 7. Files

| File | Contents |
|---|---|
| `build_rq32_dataset.py` | joins RQ2.2 codebook to the unified metrics |
| `rq32_methodsource_metrics.csv` | 374 joined tests — the analysis dataset |
| `rq32_join_report.csv` | every dropped / flagged key with a reason |
| `rq32_stats.py` | MWU + Cliff's δ, Kruskal–Wallis, Holm/BH, descriptives |
| `analyze_rq32.py` | runs analyses A, A2, B, C |
| `rq32_construction_stats.csv` | Construction: full sample **and** L0 stratum |
| `rq32_dependency_descriptives.csv` | per level, per metric distributions |
| `rq32_dependency_kruskal.csv` | Kruskal–Wallis per metric |
| `rq32_dependency_pairwise.csv` | 10 pairs × metric, raw/Holm/BH p |
| `rq32_robustness_loo.csv` | leave-one-project-out δ ranges |
| `plot_rq32.py` | builds the four figures |
| `rq32_construction_heatmap.png` | δ for full sample vs L0 stratum |
| `rq32_dependency_heatmap.png` | δ for all 10 level pairs |
| `rq32_construction_boxplots.png` / `rq32_dependency_boxplots.png` | distributions |

Reproduce with:

```bash
cd rq3/code/rq3_2/methodsource      # 或直接 rq3/code/run_rq3.sh 跑整个 RQ3
python3 build_rq32_dataset.py
python3 analyze_rq32.py
python3 plot_rq32.py
python3 ../make_result_appendix.py   # 重写各 FINDINGS 文末的附录
```

---

<!-- APPENDIX:BEGIN (generated by make_result_appendix.py -- do not edit by hand) -->

## Appendix — complete results (379 manually validated tests)

Every number below comes straight from the analysis CSVs via `make_result_appendix.py`. Bold = significant (Holm-adjusted for pairwise tests) and at least a small effect.

### A1. Construction: Dynamic vs Literal

Positive delta = Dynamic larger. The right-hand block repeats the contrast inside the L0 stratum, i.e. with dependency held fixed.

| metric | n Dyn | n Lit | median Dyn | median Lit | delta | magnitude | p | p (BH) | delta L0-only | magnitude L0 | p L0-only |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LOC (main-body) | 223 | 150 | 11.0000 | 10.5000 | 0.009 | negligible | 0.885254 | 0.980452 | -0.111 | negligible | 0.150833 |
| CC (main-body) | 223 | 150 | 1.0000 | 1.0000 | -0.004 | negligible | 0.933108 | 0.980452 | -0.051 | negligible | 0.402828 |
| CCTR (main-body) | 223 | 150 | 3.0000 | 4.0000 | -0.122 | negligible | 0.041898 | 0.069830 | -0.071 | negligible | 0.345958 |
| DUP% (main-body) | 223 | 150 | 0.9153 | 0.9045 | -0.027 | negligible | 0.645540 | 0.886139 | -0.121 | negligible | 0.103756 |
| DUP lines (main-body) | 223 | 150 | 7.0000 | 8.0000 | -0.028 | negligible | 0.649835 | 0.886139 | -0.145 | negligible | 0.058587 |
|  |  |  |  |  |  |  |  |  |  |  |  |
| LOC (helper) | 223 | 150 | 39.0000 | 21.0000 | **0.281** | small | 0.000004 | 0.000012 | 0.016 | negligible | 0.840918 |
| CC (helper) | 223 | 150 | 8.0000 | 3.0000 | **0.298** | small | 0.000001 | 0.000005 | 0.021 | negligible | 0.778337 |
| CCTR (helper) | 223 | 150 | 7.0000 | 1.0000 | **0.308** | small | 0.000000 | 0.000000 | 0.098 | negligible | 0.184901 |
| DUP% (helper) | 223 | 150 | 0.0750 | 0.1579 | -0.139 | negligible | 0.020392 | 0.038235 | **-0.189** | small | 0.013096 |
| DUP lines (helper) | 223 | 150 | 4.0000 | 3.5000 | -0.002 | negligible | 0.976542 | 0.980452 | -0.122 | negligible | 0.110756 |
|  |  |  |  |  |  |  |  |  |  |  |  |
| LOC (total) | 223 | 150 | 58.0000 | 34.0000 | **0.236** | small | 0.000113 | 0.000282 | -0.037 | negligible | 0.630894 |
| CC (total) | 223 | 150 | 9.0000 | 5.0000 | **0.292** | small | 0.000002 | 0.000007 | -0.015 | negligible | 0.840390 |
| CCTR (total) | 223 | 150 | 13.0000 | 7.0000 | **0.231** | small | 0.000145 | 0.000311 | -0.030 | negligible | 0.696515 |
| DUP% (total) | 223 | 150 | 0.2210 | 0.4576 | **-0.296** | small | 0.000001 | 0.000005 | **-0.214** | small | 0.005702 |
| DUP lines (total) | 223 | 150 | 14.0000 | 15.0000 | 0.002 | negligible | 0.980452 | 0.980452 | -0.149 | small | 0.054427 |

### A2. Dependency: Kruskal–Wallis across L0–L4

| metric | n | H | df | p | p (BH) | sig at .05 |
|---|---|---|---|---|---|---|
| LOC (main-body) | 373 | 8.4965 | 4 | 0.074993 | 0.091485 | no |
| CC (main-body) | 373 | 3.7302 | 4 | 0.443753 | 0.475449 | no |
| CCTR (main-body) | 373 | 2.5638 | 4 | 0.633255 | 0.633255 | no |
| DUP% (main-body) | 373 | 8.3587 | 4 | 0.079287 | 0.091485 | no |
| DUP lines (main-body) | 373 | 10.6385 | 4 | 0.030942 | 0.042193 | yes |
|  |  |  |  |  |  |  |
| LOC (helper) | 373 | 46.7415 | 4 | 0.000000 | 0.000000 | yes |
| CC (helper) | 373 | 66.8422 | 4 | 0.000000 | 0.000000 | yes |
| CCTR (helper) | 373 | 54.9271 | 4 | 0.000000 | 0.000000 | yes |
| DUP% (helper) | 373 | 29.0755 | 4 | 0.000008 | 0.000014 | yes |
| DUP lines (helper) | 373 | 43.6324 | 4 | 0.000000 | 0.000000 | yes |
|  |  |  |  |  |  |  |
| LOC (total) | 373 | 42.5992 | 4 | 0.000000 | 0.000000 | yes |
| CC (total) | 373 | 61.7533 | 4 | 0.000000 | 0.000000 | yes |
| CCTR (total) | 373 | 50.8769 | 4 | 0.000000 | 0.000000 | yes |
| DUP% (total) | 373 | 24.2490 | 4 | 0.000071 | 0.000119 | yes |
| DUP lines (total) | 373 | 17.4077 | 4 | 0.001610 | 0.002416 | yes |

### A3. Dependency: medians by level

| metric | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| LOC (main-body) | 9.0000 (n=225) | 7.5000 (n=16) | 18.0000 (n=35) | 12.0000 (n=45) | 13.0000 (n=52) |
| CC (main-body) | 1.0000 (n=225) | 1.0000 (n=16) | 1.0000 (n=35) | 1.0000 (n=45) | 1.0000 (n=52) |
| CCTR (main-body) | 4.0000 (n=225) | 3.5000 (n=16) | 3.0000 (n=35) | 3.0000 (n=45) | 4.0000 (n=52) |
| DUP% (main-body) | 0.8364 (n=225) | 0.5000 (n=16) | 1.0000 (n=35) | 1.0000 (n=45) | 1.0000 (n=52) |
| DUP lines (main-body) | 7.0000 (n=225) | 6.5000 (n=16) | 11.0000 (n=35) | 10.0000 (n=45) | 8.5000 (n=52) |
|  |  |  |  |  |  |
| LOC (helper) | 21.0000 (n=225) | 107.0000 (n=16) | 34.0000 (n=35) | 44.0000 (n=45) | 60.0000 (n=52) |
| CC (helper) | 3.0000 (n=225) | 20.0000 (n=16) | 10.0000 (n=35) | 10.0000 (n=45) | 15.0000 (n=52) |
| CCTR (helper) | 1.0000 (n=225) | 13.0000 (n=16) | 12.0000 (n=35) | 7.0000 (n=45) | 9.0000 (n=52) |
| DUP% (helper) | 0.1566 (n=225) | 0.4009 (n=16) | 0.0124 (n=35) | 0.0000 (n=45) | 0.0686 (n=52) |
| DUP lines (helper) | 5.0000 (n=225) | 45.0000 (n=16) | 2.0000 (n=35) | 0.0000 (n=45) | 6.0000 (n=52) |
|  |  |  |  |  |  |
| LOC (total) | 37.0000 (n=225) | 114.0000 (n=16) | 54.0000 (n=35) | 56.0000 (n=45) | 67.0000 (n=52) |
| CC (total) | 5.0000 (n=225) | 21.0000 (n=16) | 11.0000 (n=35) | 13.0000 (n=45) | 16.0000 (n=52) |
| CCTR (total) | 6.0000 (n=225) | 15.0000 (n=16) | 18.0000 (n=35) | 17.0000 (n=45) | 14.0000 (n=52) |
| DUP% (total) | 0.4114 (n=225) | 0.4380 (n=16) | 0.1707 (n=35) | 0.2088 (n=45) | 0.1629 (n=52) |
| DUP lines (total) | 14.0000 (n=225) | 53.0000 (n=16) | 16.0000 (n=35) | 14.0000 (n=45) | 13.5000 (n=52) |

### A4. Dependency: pairwise Cliff's delta

Positive delta = the higher level is larger.

| metric | L1 vs L0 | L2 vs L0 | L3 vs L0 | L4 vs L0 | L2 vs L1 | L3 vs L1 | L4 vs L1 | L3 vs L2 | L4 vs L2 | L4 vs L3 |
|---|---|---|---|---|---|---|---|---|---|---|
| LOC (main-body) | -0.045 | 0.227 | 0.103 | 0.172 | 0.268 | 0.138 | 0.248 | -0.199 | -0.061 | 0.099 |
| CC (main-body) | 0.049 | -0.054 | -0.118 | 0.024 | -0.102 | -0.168 | -0.023 | -0.070 | 0.079 | 0.141 |
| CCTR (main-body) | -0.102 | -0.153 | -0.063 | -0.038 | -0.032 | 0.065 | 0.031 | 0.098 | 0.080 | 0.012 |
| DUP% (main-body) | -0.055 | 0.171 | 0.124 | 0.191 | 0.227 | 0.175 | 0.244 | -0.042 | 0.028 | 0.064 |
| DUP lines (main-body) | -0.133 | 0.267 | 0.083 | 0.157 | 0.407 | 0.254 | 0.297 | -0.234 | -0.096 | 0.077 |
|  |  |  |  |  |  |  |  |  |  |  |
| LOC (helper) | **0.651** | **0.378** | **0.271** | **0.431** | -0.250 | -0.296 | -0.167 | -0.143 | 0.109 | 0.201 |
| CC (helper) | **0.578** | **0.503** | **0.499** | **0.464** | -0.037 | -0.100 | -0.094 | -0.076 | 0.063 | 0.061 |
| CCTR (helper) | **0.507** | **0.493** | **0.443** | **0.382** | -0.043 | -0.138 | -0.062 | -0.194 | -0.085 | 0.007 |
| DUP% (helper) | 0.299 | **-0.359** | **-0.278** | -0.098 | **-0.864** | **-0.642** | **-0.562** | 0.029 | **0.335** | 0.247 |
| DUP lines (helper) | **0.707** | **-0.299** | **-0.253** | 0.090 | **-0.909** | **-0.854** | **-0.678** | 0.050 | **0.435** | **0.361** |
|  |  |  |  |  |  |  |  |  |  |  |
| LOC (total) | **0.636** | **0.366** | 0.250 | **0.405** | -0.246 | -0.303 | -0.158 | -0.165 | 0.110 | 0.187 |
| CC (total) | **0.559** | **0.547** | **0.429** | **0.442** | -0.025 | -0.104 | -0.082 | -0.109 | 0.046 | 0.075 |
| CCTR (total) | **0.519** | **0.524** | **0.361** | **0.390** | 0.062 | -0.146 | -0.055 | -0.180 | -0.080 | 0.054 |
| DUP% (total) | -0.046 | **-0.359** | **-0.276** | **-0.283** | **-0.496** | -0.344 | -0.339 | 0.044 | 0.007 | -0.001 |
| DUP lines (total) | **0.577** | 0.052 | -0.096 | 0.083 | **-0.566** | **-0.701** | -0.421 | -0.154 | 0.059 | 0.157 |

### A5. Leave-one-project-out robustness

Each headline delta recomputed with one project dropped at a time.

| contrast | metric | delta (full) | delta range under LOO | sign stable |
|---|---|---|---|---|
| Dynamic vs Literal | LOC (main-body) | 0.0088 | -0.0655 .. 0.0721 | no |
| Dynamic vs Literal | CC (main-body) | -0.0039 | -0.0271 .. 0.0541 | no |
| Dynamic vs Literal | CCTR (main-body) | -0.1220 | -0.1572 .. -0.0673 | yes |
| Dynamic vs Literal | DUP% (main-body) | -0.0266 | -0.0699 .. 0.0037 | no |
| Dynamic vs Literal | LOC (helper) | 0.2807 | 0.2458 .. 0.3234 | yes |
| Dynamic vs Literal | CC (helper) | 0.2977 | 0.2664 .. 0.3423 | yes |
| Dynamic vs Literal | CCTR (helper) | 0.3080 | 0.2751 .. 0.3587 | yes |
| Dynamic vs Literal | DUP% (helper) | -0.1392 | -0.1849 .. -0.0991 | yes |
| Dynamic vs Literal | LOC (total) | 0.2357 | 0.1991 .. 0.2834 | yes |
| Dynamic vs Literal | CC (total) | 0.2916 | 0.2594 .. 0.3350 | yes |
| Dynamic vs Literal | CCTR (total) | 0.2314 | 0.1959 .. 0.2759 | yes |
| Dynamic vs Literal | DUP% (total) | -0.2965 | -0.3473 .. -0.2572 | yes |
| L4 vs L0 | LOC (main-body) | 0.1719 | 0.0236 .. 0.3028 | yes |
| L4 vs L0 | CC (main-body) | 0.0239 | -0.0796 .. 0.1111 | no |
| L4 vs L0 | CCTR (main-body) | -0.0376 | -0.1204 .. 0.0866 | no |
| L4 vs L0 | DUP% (main-body) | 0.1909 | 0.0812 .. 0.2730 | yes |
| L4 vs L0 | LOC (helper) | 0.4308 | 0.3179 .. 0.4668 | yes |
| L4 vs L0 | CC (helper) | 0.4640 | 0.3586 .. 0.5036 | yes |
| L4 vs L0 | CCTR (helper) | 0.3815 | 0.2594 .. 0.4634 | yes |
| L4 vs L0 | DUP% (helper) | -0.0975 | -0.1623 .. -0.0258 | yes |
| L4 vs L0 | LOC (total) | 0.4045 | 0.2864 .. 0.4464 | yes |
| L4 vs L0 | CC (total) | 0.4417 | 0.3312 .. 0.5002 | yes |
| L4 vs L0 | CCTR (total) | 0.3897 | 0.2713 .. 0.4591 | yes |
| L4 vs L0 | DUP% (total) | -0.2829 | -0.3336 .. -0.1985 | yes |

<!-- APPENDIX:END -->
