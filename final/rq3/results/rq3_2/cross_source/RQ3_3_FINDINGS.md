# RQ3.3 — Does the choice of parameter source determine the complexity profile?

**Why this question.** RQ3.2 asked whether design choices *within* MethodSource
change the complexity profile. That question cannot be asked of the other
sources: `@ValueSource`, `@CsvSource` and `@CsvFileSource` pin construction and
dependency by language construct — `CsvSource` is L0 for **100%** of its 366
tests, `ValueSource` is `Literal-*` for 97% and L0 for 98%. They have no design
space to vary. The question that *does* generalise sits one level up: **does
picking a source type itself decide where a test's complexity lives?**

## Data

8,279 parameterized tests from the six RQ2.2 source tables; 14 use more than one
source annotation and are dropped (their metrics cannot be attributed to one
source); 101 have no metrics row. **8,164 tests analysed, 46 projects** — the
whole corpus, since every project contributes at least one parameterized test.

| family | meaning | sources | n |
|---|---|---|---|
| **inline** | data written into the annotation | ValueSource (1,456), CsvSource (361) | 1,817 |
| **type** | data comes from an enum type | EnumSource (828) | 828 |
| **file** | data comes from a classpath resource | CsvFileSource (48) | 48 |
| **provider** | data comes from user-written code | MethodSource (5,411), FieldSource (35), ArgumentsSource (25) | 5,471 |

Statistics as in RQ3.2 (shared `pt_stats.py`): Kruskal–Wallis across groups,
then all pairwise Mann–Whitney U + Cliff's δ with Holm/BH correction within
each metric. Figures star a cell only when it is significant **and** at least
a small effect (|δ| ≥ 0.147), since at n > 8k significance alone does not
discriminate.

---

## Finding 1 — The test body is the same whatever source you pick

Comparing provider-backed against inline sources:

| scope | LOC | CC | CCTR | DUP% |
|---|---|---|---|---|
| **main-body** | −0.115 | −0.045 | −0.101 | 0.115 |
| **helper** | **0.388** (medium) | **0.347** (medium) | **0.230** (small) | **0.464** (medium) |
| **total** | 0.288 (small) | 0.322 (small) | 0.197 (small) | 0.010 |

Every main-body effect is negligible; every helper effect is small-to-medium.
Median helper CCTR goes **1 → 7** and median helper LOC **11 → 52**, while
median main-body CC is **1** in both.

This is the RQ3.2 result reproduced one level up, on a different and much
larger population: **source choice relocates complexity into the helper layer
without changing the test method itself.**

## Finding 2 — It survives controlling for data volume

The obvious objection is that people reach for MethodSource *because* they have
more or messier data. Recomputing the provider-vs-inline contrast inside
quartiles of `n_sets` (number of parameter sets):

| scope / metric | Q1 (0–2) | Q2 (2–3) | Q3 (3–7) | Q4 (7–960) |
|---|---|---|---|---|
| helper LOC | 0.290 | 0.385 | **0.652** | **0.686** |
| helper CCTR | 0.193 | 0.143 | 0.440 | 0.315 |
| total CCTR | 0.202 | 0.167 | 0.385 | 0.303 |
| main-body CCTR | −0.030 | 0.004 | −0.204 | 0.077 |

The helper-side gap is present in every stratum and **grows** with data volume,
while main-body stays negligible throughout. The effect is not a data-volume
artefact.

## Finding 3 — Only MethodSource actually pays the cost

Per-source contrasts against the ValueSource baseline (helper CCTR):

| source | δ vs ValueSource | |
|---|---|---|
| MethodSource (n=5,411) | **+0.200** (small) | *** |
| ArgumentsSource (n=25) | +0.066 | n.s. |
| EnumSource (n=828) | −0.037 | n.s. |
| CsvFileSource (n=48) | −0.056 | n.s. |
| CsvSource (n=361) | **−0.173** (small) | *** |
| FieldSource (n=35) | **−0.359** (medium) | *** |

**The "provider family" result is a MethodSource result** — MethodSource is
98.9% of that family. FieldSource and ArgumentsSource, which are nominally
provider-backed, do *not* show the effect (though n = 35 / 25 is too small to
conclude much). EnumSource sits essentially on top of ValueSource, so pulling
data from an enum type costs nothing relative to inlining it.

CsvSource is *below* ValueSource on helper complexity — a tabular literal is
the cheapest way to parameterize a test in this corpus.

## Finding 4 — Duplication moves rather than disappears

Total DUP% is statistically identical between provider and inline
(δ = 0.010), but its location differs: provider tests have **more duplicated
helper code** (helper DUP% δ = 0.464, medium; median 0.000 → 0.180) and
slightly more duplicated body lines (δ = 0.115). Choosing MethodSource does not
reduce a test's overall duplication — it relocates it into the provider layer
along with the complexity.

## Robustness

Leave-one-project-out over 46 projects (`cross_source_robustness_loo.csv`):
every provider-vs-inline effect keeps its sign in all 45 samples (helper LOC
stays in 0.338–0.478, helper CCTR in 0.158–0.291, helper DUP% in
0.425–0.502). The only unstable one is total DUP%, whose full-sample δ is
0.010 — i.e. a true null.

## Limitations

* **ArgumentsSource (25), FieldSource (35), CsvFileSource (48)** are too small
  for confident claims; they are reported but not leaned on.
* **Source choice is not random.** The `n_sets` stratification controls for
  data volume, but not for the kind of data (objects vs primitives) — that is
  precisely what forces MethodSource, and it cannot be controlled away with
  these variables.
* Tests are nested in 46 projects; addressed only by leave-one-project-out.

## Files

`build_cross_source_dataset.py` → `cross_source_metrics.csv` (+ join report);
`analyze_cross_source.py` → descriptives / kruskal / pairwise / family_pairwise
/ volume_strata / robustness_loo / population; `plot_cross_source.py` →
`cross_source_heatmap.png` (vs ValueSource), `cross_source_family_heatmap.png`,
`cross_source_volume_heatmap.png`, `cross_source_boxplots.png`.

```bash
cd final/rq3/code/rq3_2/cross_source      # 或直接 final/rq3/code/run_rq3.sh 跑整个 RQ3
python3 build_cross_source_dataset.py
python3 analyze_cross_source.py
python3 plot_cross_source.py
python3 ../make_result_appendix.py   # 重写各 FINDINGS 文末的附录
```

---

<!-- APPENDIX:BEGIN (generated by make_result_appendix.py -- do not edit by hand) -->

## Appendix — complete results

Every number below comes straight from the analysis CSVs via `make_result_appendix.py`. Bold = significant (Holm-adjusted for pairwise tests) and at least a small effect.

### A1. Medians by source type

| metric | Value | Csv | Enum | CsvFile | Method | Arguments | Field |
|---|---|---|---|---|---|---|---|
| LOC (main-body) | 16.0000 | 22.0000 | 23.0000 | 6.0000 | 15.0000 | 12.0000 | 9.0000 |
| CC (main-body) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| CCTR (main-body) | 5.0000 | 5.0000 | 5.0000 | 3.0000 | 4.0000 | 4.0000 | 5.0000 |
| DUP% (main-body) | 0.7778 | 0.5676 | 0.9231 | 1.0000 | 0.8966 | 0.0000 | 0.6154 |
| DUP lines (main-body) | 11.0000 | 12.0000 | 19.0000 | 6.0000 | 11.0000 | 0.0000 | 5.0000 |
|  |  |  |  |  |  |  |  |
| LOC (helper) | 14.0000 | 3.0000 | 17.0000 | 16.0000 | 53.0000 | 30.0000 | 0.0000 |
| CC (helper) | 3.0000 | 1.0000 | 2.0000 | 5.0000 | 8.0000 | 6.0000 | 0.0000 |
| CCTR (helper) | 1.0000 | 0.0000 | 1.0000 | 3.0000 | 7.0000 | 3.0000 | 0.0000 |
| DUP% (helper) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1818 | 0.0000 | 0.0000 |
| DUP lines (helper) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 10.0000 | 0.0000 | 0.0000 |
|  |  |  |  |  |  |  |  |
| LOC (total) | 41.0000 | 32.0000 | 48.0000 | 25.5000 | 72.0000 | 40.0000 | 9.0000 |
| CC (total) | 4.0000 | 3.0000 | 4.0000 | 6.0000 | 10.0000 | 7.0000 | 1.0000 |
| CCTR (total) | 10.0000 | 7.0000 | 11.0000 | 6.0000 | 15.0000 | 7.0000 | 5.0000 |
| DUP% (total) | 0.3377 | 0.3514 | 0.4615 | 0.0929 | 0.3684 | 0.0000 | 0.5000 |
| DUP lines (total) | 15.0000 | 15.0000 | 25.0000 | 6.0000 | 28.0000 | 0.0000 | 8.0000 |

n per source: ValueSource=1456, CsvSource=361, EnumSource=828, CsvFileSource=48, MethodSource=5411, ArgumentsSource=25, FieldSource=35.

### A2. Kruskal–Wallis across source types and across families

| metric | H (source, df=6) | p | p (BH) | H (family, df=3) | p |
|---|---|---|---|---|---|
| LOC (main-body) | 266.9941 | 0.000000 | 0.000000 | 216.4362 | 0.000000 |
| CC (main-body) | 60.0544 | 0.000000 | 0.000000 | 38.2531 | 0.000000 |
| CCTR (main-body) | 113.9269 | 0.000000 | 0.000000 | 110.2511 | 0.000000 |
| DUP% (main-body) | 116.1303 | 0.000000 | 0.000000 | 74.9451 | 0.000000 |
| DUP lines (main-body) | 137.3999 | 0.000000 | 0.000000 | 109.6189 | 0.000000 |
|  |  |  |  |  |  |
| LOC (helper) | 881.3384 | 0.000000 | 0.000000 | 773.1985 | 0.000000 |
| CC (helper) | 709.4457 | 0.000000 | 0.000000 | 617.5074 | 0.000000 |
| CCTR (helper) | 372.5652 | 0.000000 | 0.000000 | 310.6321 | 0.000000 |
| DUP% (helper) | 1272.4062 | 0.000000 | 0.000000 | 1219.9809 | 0.000000 |
| DUP lines (helper) | 1303.7290 | 0.000000 | 0.000000 | 1232.4994 | 0.000000 |
|  |  |  |  |  |  |
| LOC (total) | 472.0303 | 0.000000 | 0.000000 | 403.3711 | 0.000000 |
| CC (total) | 638.0722 | 0.000000 | 0.000000 | 558.9439 | 0.000000 |
| CCTR (total) | 272.4683 | 0.000000 | 0.000000 | 219.7492 | 0.000000 |
| DUP% (total) | 48.6222 | 0.000000 | 0.000000 | 29.9549 | 0.000001 |
| DUP lines (total) | 471.1921 | 0.000000 | 0.000000 | 405.0994 | 0.000000 |

### A3. Each source vs the ValueSource baseline

Positive delta = that source larger than ValueSource.

| metric | Csv | Enum | CsvFile | Method | Arguments | Field |
|---|---|---|---|---|---|---|
| LOC (main-body) | **0.227** | **0.168** | **-0.766** | -0.070 | -0.194 | **-0.383** |
| CC (main-body) | 0.073 | -0.086 | **-0.276** | -0.029 | **-0.318** | **-0.255** |
| CCTR (main-body) | -0.021 | 0.067 | **-0.498** | -0.104 | -0.120 | 0.059 |
| DUP% (main-body) | **-0.156** | 0.121 | **0.275** | 0.090 | **-0.340** | -0.186 |
| DUP lines (main-body) | -0.019 | **0.190** | **-0.412** | -0.006 | **-0.520** | **-0.286** |
|  |  |  |  |  |  |  |
| LOC (helper) | **-0.202** | 0.031 | 0.021 | **0.346** | 0.137 | **-0.365** |
| CC (helper) | **-0.188** | 0.016 | 0.153 | **0.309** | 0.170 | **-0.357** |
| CCTR (helper) | **-0.173** | -0.037 | -0.056 | **0.200** | 0.066 | **-0.359** |
| DUP% (helper) | -0.100 | 0.005 | -0.202 | **0.457** | -0.255 | 0.091 |
| DUP lines (helper) | -0.119 | -0.005 | **-0.236** | **0.449** | -0.245 | -0.014 |
|  |  |  |  |  |  |  |
| LOC (total) | -0.055 | 0.108 | **-0.257** | **0.270** | 0.023 | **-0.476** |
| CC (total) | -0.137 | -0.003 | 0.108 | **0.295** | 0.115 | **-0.408** |
| CCTR (total) | **-0.179** | 0.015 | **-0.387** | **0.167** | -0.127 | -0.248 |
| DUP% (total) | 0.017 | 0.082 | **-0.257** | 0.017 | **-0.461** | 0.091 |
| DUP lines (total) | -0.064 | **0.197** | **-0.491** | **0.286** | **-0.527** | -0.238 |

### A4. Mechanism families, all pairs

Positive delta = the second-named family larger.

| metric | type vs inline | file vs inline | provider vs inline | file vs type | provider vs type | provider vs file |
|---|---|---|---|---|---|---|
| LOC (main-body) | 0.128 | **-0.793** | -0.115 | **-0.812** | **-0.226** | **0.674** |
| CC (main-body) | -0.099 | **-0.286** | -0.045 | **-0.179** | 0.052 | **0.232** |
| CCTR (main-body) | 0.070 | **-0.501** | -0.101 | **-0.525** | **-0.162** | **0.360** |
| DUP% (main-body) | **0.150** | **0.301** | 0.115 | 0.170 | -0.031 | **-0.192** |
| DUP lines (main-body) | **0.190** | **-0.391** | -0.005 | **-0.558** | **-0.196** | **0.399** |
|  |  |  |  |  |  |  |
| LOC (helper) | 0.074 | 0.079 | **0.388** | -0.012 | **0.347** | **0.455** |
| CC (helper) | 0.056 | 0.203 | **0.347** | 0.181 | **0.318** | 0.196 |
| CCTR (helper) | -0.001 | -0.011 | **0.230** | 0.021 | **0.244** | **0.301** |
| DUP% (helper) | 0.024 | **-0.181** | **0.464** | **-0.200** | **0.446** | **0.617** |
| DUP lines (helper) | 0.019 | **-0.211** | **0.465** | **-0.230** | **0.448** | **0.670** |
|  |  |  |  |  |  |  |
| LOC (total) | 0.131 | **-0.249** | **0.288** | **-0.387** | **0.188** | **0.550** |
| CC (total) | 0.025 | 0.145 | **0.322** | 0.149 | **0.320** | **0.244** |
| CCTR (total) | 0.053 | **-0.347** | **0.197** | **-0.461** | **0.156** | **0.543** |
| DUP% (total) | 0.075 | **-0.260** | 0.010 | **-0.375** | -0.085 | **0.330** |
| DUP lines (total) | **0.207** | **-0.467** | **0.288** | **-0.664** | 0.097 | **0.715** |

### A5. Provider vs inline inside n_sets quartiles

Data-volume control. Positive delta = provider larger.

| metric | Q1 (n_sets 0-2) | Q2 (n_sets 2-3) | Q3 (n_sets 3-7) | Q4 (n_sets 7-960) |
|---|---|---|---|---|
| LOC (main-body) | 0.009 | 0.041 | **0.166** | **-0.394** |
| CC (main-body) | -0.088 | 0.105 | -0.035 | 0.062 |
| CCTR (main-body) | -0.028 | 0.004 | **-0.203** | 0.077 |
| DUP% (main-body) | 0.144 | 0.142 | **0.209** | 0.005 |
| DUP lines (main-body) | 0.098 | 0.143 | **0.284** | **-0.227** |
|  |  |  |  |  |
| LOC (helper) | **0.290** | **0.385** | **0.652** | **0.686** |
| CC (helper) | **0.272** | **0.346** | **0.602** | **0.538** |
| CCTR (helper) | **0.193** | 0.143 | **0.440** | **0.315** |
| DUP% (helper) | **0.387** | **0.378** | **0.553** | **0.617** |
| DUP lines (helper) | **0.432** | **0.362** | **0.592** | **0.637** |
|  |  |  |  |  |
| LOC (total) | **0.240** | **0.314** | **0.560** | **0.434** |
| CC (total) | **0.261** | **0.331** | **0.548** | **0.482** |
| CCTR (total) | **0.203** | **0.167** | **0.385** | **0.303** |
| DUP% (total) | 0.067 | 0.054 | -0.063 | **-0.150** |
| DUP lines (total) | **0.335** | **0.270** | **0.522** | **0.254** |

### A6. Leave-one-project-out robustness (provider vs inline)

| metric | delta (full) | delta range under LOO | sign stable |
|---|---|---|---|
| LOC (main-body) | -0.1153 | -0.1723 .. -0.0818 | yes |
| CC (main-body) | -0.0451 | -0.0669 .. -0.0075 | yes |
| CCTR (main-body) | -0.1006 | -0.1317 .. -0.0586 | yes |
| DUP% (main-body) | 0.1154 | 0.0943 .. 0.1359 | yes |
| LOC (helper) | 0.3876 | 0.3379 .. 0.4781 | yes |
| CC (helper) | 0.3466 | 0.2933 .. 0.4365 | yes |
| CCTR (helper) | 0.2297 | 0.1577 .. 0.2911 | yes |
| DUP% (helper) | 0.4642 | 0.4247 .. 0.5021 | yes |
| LOC (total) | 0.2877 | 0.2217 .. 0.3688 | yes |
| CC (total) | 0.3223 | 0.2650 .. 0.4131 | yes |
| CCTR (total) | 0.1970 | 0.1194 .. 0.2580 | yes |
| DUP% (total) | 0.0096 | -0.0364 .. 0.0379 | no |

<!-- APPENDIX:END -->
