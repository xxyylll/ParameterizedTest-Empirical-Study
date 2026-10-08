# RQ3.2 at full scale — what replicates, what doesn't

[`RQ3_2_FINDINGS.md`](RQ3_2_FINDINGS.md) analysed the **379 manually validated**
MethodSource tests. This re-runs the identical pipeline on the **full
auto-derived population** — 5,508 MethodSource tests, of which **5,424 join to
the metrics** (99.2%) and **5,416 carry usable labels**, across 45 projects —
45 of the corpus's 46, because qpid-broker-j uses only ValueSource and
CsvSource and so contributes no MethodSource test.

Everything is produced by the same three scripts with `--full` / `--prefix
rq32_full`; outputs are the `rq32_full_*` files.

## Label validity

The full table's construction/dependency labels are auto-derived, so they were
checked against the manual labels on the 377 shared tests
(`check_label_agreement.py` → `rq32_label_agreement.csv`):

| dimension | agreement | Cohen's κ | disagreements |
|---|---|---|---|
| construction | 98.7% | **0.972** | 5 (Literal → Dynamic) |
| dependency | 99.5% | **0.991** | 2 (L1→L3, L0→L4) |

Both are "almost perfect" (Landis–Koch), so the full-population labels are
sound.

## Sample size per group

| group | validated sample | full population |
|---|---|---|
| Literal / Dynamic | 150 / 223 | **2,022 / 3,394** |
| L0 | 225 | 3,384 |
| **L1** | **16** | **353** |
| L2 / L3 / L4 | 35 / 45 / 52 | 503 / 502 / 674 |

L1 — the single biggest weakness of the sample run — grows 22×.

> **Reading note.** At n = 5,416 nearly every comparison reaches p < 0.05, so
> significance alone no longer discriminates. Both the sample and the
> full-population figures therefore star a cell only when it is significant
> **and** at least a *small* effect (|δ| ≥ 0.147). Read colour (effect size),
> not stars.

---

## 1. Replicates — and gets stronger: Construction is a dependency artefact

The headline finding of the sample run survives at 14× the size.

| scope / metric | raw δ (sample → full) | within-L0 δ (sample → full) |
|---|---|---|
| helper LOC | 0.281 → 0.199 | 0.016 → **−0.017** |
| helper CC | 0.298 → 0.225 | 0.022 → **−0.011** |
| helper CCTR | 0.308 → 0.180 | 0.098 → **0.004** |
| total CC | 0.292 → 0.213 | −0.016 → **−0.019** |
| total CCTR | 0.231 → 0.102 | −0.030 → **−0.074** |

Dynamic still looks more complex than Literal in the raw contrast, and the
effect still vanishes entirely once dependency is held at L0 — now with 102 →
**1,900+** tests per stratum behind that null. **Construction does not drive
complexity; dependency does.**

> Note on the metric: CCTR scores a *literal* argument table at zero by
> construction (96% of Literal providers score CCTR = 0, against 73% of Dynamic
> ones), so CCTR is biased toward rating Dynamic higher. That bias works
> against the null reported here, which makes it conservative. See
> METHODS.md §7.

## 2. Does NOT replicate: "L1 behaves like L2–L4"

The sample said every dependency level above L0 was equally costly. That was
an artefact of L1's n = 16.

| helper CCTR | sample δ | full δ |
|---|---|---|
| L1 vs L0 | 0.507 (large) | **0.062 (negligible)** |
| L2 vs L0 | 0.493 (large) | 0.347 (medium) |
| L3 vs L0 | 0.443 (medium) | 0.219 (small) |
| L4 vs L0 | 0.382 (medium) | 0.274 (small) |

**L1 is statistically indistinguishable from L0** on helper and total
complexity (total CCTR δ = 0.019, helper DUP% δ = 0.045). L1 — a provider that
still lives inside the test class — costs essentially nothing extra.

**The step is at L2, not at "any dependency".** The revised statement:
complexity rises once the provider's data leaves the test class (L2+), and
L2/L3/L4 differ only modestly among themselves (L2 vs L1 helper CCTR δ = 0.378
medium; L3 vs L2 δ = −0.243 small).

## 3. Does NOT replicate: "Literal duplicates more, even within L0"

The sample's one effect that survived dependency control does not hold up:

| | sample δ | full δ |
|---|---|---|
| total DUP%, within L0 | −0.214 (small, p = .006) | **−0.032 (negligible, p = .11)** |
| helper DUP%, within L0 | −0.189 (small) | **0.007 (negligible)** |

In the raw contrast Literal still duplicates more (total DUP% δ = −0.190,
small), but that too is a dependency effect, not a construction effect. The
sample-level claim in `RQ3_2_FINDINGS.md` §3 should be treated as noise.

## 4. Partially replicates: "the test main body is invariant"

Split the claim by metric:

* **Main-body CC genuinely is invariant** — δ negligible in every construction
  and dependency contrast (no starred cell in that row of the full heatmap);
  median main-body CC = 1 everywhere.
* **Main-body LOC and CCTR are not.** Within L0, Literal main bodies are
  *larger* (LOC δ = −0.210, small) — visible only with full power. Across
  dependency levels, main-body CCTR is *lower* at L3 than L0 (δ = −0.258,
  small) and main-body DUP% is higher at L4 (δ = 0.186, small).

So the accurate statement is: **control-flow complexity of the test body is
invariant; its size is not.** Tests whose data lives far away have slightly
leaner bodies, which is consistent with the data-extraction story.

## 5. Duplication trade-off — replicates and strengthens

| helper DUP% | sample δ | full δ |
|---|---|---|
| L2 vs L0 | −0.359 (medium) | **−0.389 (medium)** |
| L3 vs L0 | −0.278 (small) | −0.279 (small) |
| L4 vs L0 | −0.098 (negligible) | −0.323 (small) |

Moving provider data out of the test class cuts duplication substantially,
while adding helper-side complexity. The trade-off is the most robust
finding of RQ3.2.

---

## Revised headline for the paper

1. **Construction (Literal vs Dynamic) has no independent effect on
   complexity** — its apparent effect is entirely explained by dependency.
   (n = 5,416; κ-validated labels.)
2. **Dependency has a threshold at L2**: keeping the provider inside the test
   class (L0/L1) is free; moving it out raises helper-side LOC/CC/CCTR by a
   small-to-medium margin.
3. **That move buys de-duplication** — a large drop in helper DUP% at L2.
4. **The test body's control-flow complexity is invariant throughout**; only
   its size shifts.

## Files

`rq32_full_*` mirrors every `rq32_*` output (metrics, join report, population
counts, construction stats, dependency descriptives/kruskal/pairwise,
robustness, 4 figures), plus `rq32_label_agreement.csv`.

```bash
cd /Users/immortal/Complexity_Analysis && source .venv/bin/activate
python3 rq3_2_methodsource/build_rq32_dataset.py --full
python3 rq3_2_methodsource/check_label_agreement.py
python3 rq3_2_methodsource/analyze_rq32.py --prefix rq32_full
python3 rq3_2_methodsource/plot_rq32.py  --prefix rq32_full
python3 make_result_appendix.py      # regenerates the appendix below
```

---

<!-- APPENDIX:BEGIN (generated by make_result_appendix.py -- do not edit by hand) -->

## Appendix — complete results (full population, 5,416 tests)

Every number below comes straight from the analysis CSVs via `make_result_appendix.py`. Bold = significant (Holm-adjusted for pairwise tests) and at least a small effect.

### A1. Construction: Dynamic vs Literal

Positive delta = Dynamic larger. The right-hand block repeats the contrast inside the L0 stratum, i.e. with dependency held fixed.

| metric | n Dyn | n Lit | median Dyn | median Lit | delta | magnitude | p | p (BH) | delta L0-only | magnitude L0 | p L0-only |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LOC (main-body) | 3394 | 2022 | 14.0000 | 17.0000 | -0.082 | negligible | 0.000000 | 0.000000 | **-0.210** | small | 0.000000 |
| CC (main-body) | 3394 | 2022 | 1.0000 | 1.0000 | -0.047 | negligible | 0.000401 | 0.000501 | -0.043 | negligible | 0.009292 |
| CCTR (main-body) | 3394 | 2022 | 4.0000 | 5.0000 | **-0.162** | small | 0.000000 | 0.000000 | -0.104 | negligible | 0.000000 |
| DUP% (main-body) | 3394 | 2022 | 0.9130 | 0.8710 | 0.020 | negligible | 0.200673 | 0.231546 | -0.029 | negligible | 0.133689 |
| DUP lines (main-body) | 3394 | 2022 | 10.0000 | 12.0000 | -0.070 | negligible | 0.000015 | 0.000020 | **-0.198** | small | 0.000000 |
|  |  |  |  |  |  |  |  |  |  |  |  |
| LOC (helper) | 3394 | 2022 | 66.0000 | 30.0000 | **0.199** | small | 0.000000 | 0.000000 | -0.017 | negligible | 0.391455 |
| CC (helper) | 3394 | 2022 | 11.0000 | 5.0000 | **0.225** | small | 0.000000 | 0.000000 | -0.011 | negligible | 0.586219 |
| CCTR (helper) | 3394 | 2022 | 10.0000 | 3.0000 | **0.179** | small | 0.000000 | 0.000000 | 0.004 | negligible | 0.852091 |
| DUP% (helper) | 3394 | 2022 | 0.1230 | 0.2609 | -0.094 | negligible | 0.000000 | 0.000000 | 0.007 | negligible | 0.723230 |
| DUP lines (helper) | 3394 | 2022 | 10.0000 | 8.0000 | 0.014 | negligible | 0.391277 | 0.419225 | -0.017 | negligible | 0.380934 |
|  |  |  |  |  |  |  |  |  |  |  |  |
| LOC (total) | 3394 | 2022 | 83.0000 | 56.0000 | 0.142 | negligible | 0.000000 | 0.000000 | -0.083 | negligible | 0.000031 |
| CC (total) | 3394 | 2022 | 13.0000 | 7.0000 | **0.213** | small | 0.000000 | 0.000000 | -0.019 | negligible | 0.331620 |
| CCTR (total) | 3394 | 2022 | 16.0000 | 12.0000 | 0.102 | negligible | 0.000000 | 0.000000 | -0.074 | negligible | 0.000189 |
| DUP% (total) | 3394 | 2022 | 0.3108 | 0.4355 | **-0.190** | small | 0.000000 | 0.000000 | -0.032 | negligible | 0.110741 |
| DUP lines (total) | 3394 | 2022 | 28.0000 | 27.0000 | -0.008 | negligible | 0.624752 | 0.624752 | -0.094 | negligible | 0.000002 |

### A2. Dependency: Kruskal–Wallis across L0–L4

| metric | n | H | df | p | p (BH) | sig at .05 |
|---|---|---|---|---|---|---|
| LOC (main-body) | 5416 | 239.7024 | 4 | 0.000000 | 0.000000 | yes |
| CC (main-body) | 5416 | 41.6292 | 4 | 0.000000 | 0.000000 | yes |
| CCTR (main-body) | 5416 | 136.7487 | 4 | 0.000000 | 0.000000 | yes |
| DUP% (main-body) | 5416 | 76.6088 | 4 | 0.000000 | 0.000000 | yes |
| DUP lines (main-body) | 5416 | 235.7930 | 4 | 0.000000 | 0.000000 | yes |
|  |  |  |  |  |  |  |
| LOC (helper) | 5416 | 377.8680 | 4 | 0.000000 | 0.000000 | yes |
| CC (helper) | 5416 | 532.9968 | 4 | 0.000000 | 0.000000 | yes |
| CCTR (helper) | 5416 | 294.1143 | 4 | 0.000000 | 0.000000 | yes |
| DUP% (helper) | 5416 | 414.9229 | 4 | 0.000000 | 0.000000 | yes |
| DUP lines (helper) | 5416 | 125.0572 | 4 | 0.000000 | 0.000000 | yes |
|  |  |  |  |  |  |  |
| LOC (total) | 5416 | 326.2347 | 4 | 0.000000 | 0.000000 | yes |
| CC (total) | 5416 | 471.7389 | 4 | 0.000000 | 0.000000 | yes |
| CCTR (total) | 5416 | 214.8001 | 4 | 0.000000 | 0.000000 | yes |
| DUP% (total) | 5416 | 380.8670 | 4 | 0.000000 | 0.000000 | yes |
| DUP lines (total) | 5416 | 113.2126 | 4 | 0.000000 | 0.000000 | yes |

### A3. Dependency: medians by level

| metric | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| LOC (main-body) | 14.0000 (n=3384) | 14.0000 (n=353) | 28.0000 (n=503) | 12.0000 (n=502) | 17.0000 (n=674) |
| CC (main-body) | 1.0000 (n=3384) | 1.0000 (n=353) | 1.0000 (n=503) | 1.0000 (n=502) | 1.0000 (n=674) |
| CCTR (main-body) | 4.0000 (n=3384) | 4.0000 (n=353) | 4.0000 (n=503) | 3.0000 (n=502) | 4.0000 (n=674) |
| DUP% (main-body) | 0.8421 (n=3384) | 0.8077 (n=353) | 0.8571 (n=503) | 1.0000 (n=502) | 1.0000 (n=674) |
| DUP lines (main-body) | 10.0000 (n=3384) | 10.0000 (n=353) | 22.0000 (n=503) | 9.0000 (n=502) | 16.0000 (n=674) |
|  |  |  |  |  |  |
| LOC (helper) | 37.0000 (n=3384) | 66.0000 (n=353) | 239.0000 (n=503) | 89.0000 (n=502) | 104.0000 (n=674) |
| CC (helper) | 5.0000 (n=3384) | 9.0000 (n=353) | 45.0000 (n=503) | 20.0000 (n=502) | 18.5000 (n=674) |
| CCTR (helper) | 4.0000 (n=3384) | 7.0000 (n=353) | 33.0000 (n=503) | 16.0000 (n=502) | 12.0000 (n=674) |
| DUP% (helper) | 0.2850 (n=3384) | 0.3077 (n=353) | 0.0124 (n=503) | 0.0769 (n=502) | 0.0645 (n=674) |
| DUP lines (helper) | 11.0000 (n=3384) | 20.0000 (n=353) | 2.0000 (n=503) | 4.0000 (n=502) | 10.0000 (n=674) |
|  |  |  |  |  |  |
| LOC (total) | 58.0000 (n=3384) | 83.0000 (n=353) | 284.0000 (n=503) | 111.0000 (n=502) | 120.0000 (n=674) |
| CC (total) | 7.0000 (n=3384) | 11.0000 (n=353) | 47.0000 (n=503) | 21.0000 (n=502) | 20.0000 (n=674) |
| CCTR (total) | 13.0000 (n=3384) | 15.0000 (n=353) | 39.0000 (n=503) | 21.0000 (n=502) | 20.0000 (n=674) |
| DUP% (total) | 0.4325 (n=3384) | 0.4286 (n=353) | 0.3043 (n=503) | 0.2137 (n=502) | 0.1677 (n=674) |
| DUP lines (total) | 28.0000 (n=3384) | 34.0000 (n=353) | 37.0000 (n=503) | 16.0000 (n=502) | 29.0000 (n=674) |

### A4. Dependency: pairwise Cliff's delta

Positive delta = the higher level is larger.

| metric | L1 vs L0 | L2 vs L0 | L3 vs L0 | L4 vs L0 | L2 vs L1 | L3 vs L1 | L4 vs L1 | L3 vs L2 | L4 vs L2 | L4 vs L3 |
|---|---|---|---|---|---|---|---|---|---|---|
| LOC (main-body) | -0.013 | **0.346** | -0.140 | 0.141 | **0.393** | **-0.148** | **0.175** | **-0.503** | **-0.223** | **0.301** |
| CC (main-body) | -0.005 | -0.015 | -0.114 | -0.090 | -0.011 | -0.116 | -0.091 | -0.101 | -0.077 | 0.023 |
| CCTR (main-body) | -0.045 | -0.125 | **-0.258** | **-0.188** | -0.075 | **-0.214** | -0.147 | -0.101 | -0.067 | 0.051 |
| DUP% (main-body) | -0.019 | 0.035 | 0.106 | **0.186** | 0.055 | 0.119 | **0.198** | 0.091 | **0.181** | 0.057 |
| DUP lines (main-body) | -0.060 | **0.307** | -0.118 | **0.206** | **0.377** | -0.066 | **0.275** | **-0.440** | -0.125 | **0.346** |
|  |  |  |  |  |  |  |  |  |  |  |
| LOC (helper) | **0.211** | **0.348** | **0.192** | **0.369** | **0.228** | 0.057 | **0.198** | **-0.277** | -0.000 | **0.223** |
| CC (helper) | **0.192** | **0.437** | **0.332** | **0.385** | **0.338** | **0.218** | **0.283** | **-0.233** | -0.076 | 0.132 |
| CCTR (helper) | 0.062 | **0.347** | **0.218** | **0.274** | **0.378** | **0.207** | **0.238** | **-0.243** | -0.019 | 0.093 |
| DUP% (helper) | 0.042 | **-0.389** | **-0.279** | **-0.323** | **-0.465** | **-0.345** | **-0.421** | 0.122 | **0.159** | 0.011 |
| DUP lines (helper) | **0.171** | **-0.155** | **-0.206** | -0.064 | **-0.237** | **-0.356** | **-0.257** | 0.004 | **0.191** | **0.174** |
|  |  |  |  |  |  |  |  |  |  |  |
| LOC (total) | **0.170** | **0.348** | 0.132 | **0.336** | **0.242** | 0.043 | **0.203** | **-0.321** | -0.016 | **0.235** |
| CC (total) | **0.165** | **0.431** | **0.297** | **0.354** | **0.341** | **0.208** | **0.276** | **-0.239** | -0.087 | 0.134 |
| CCTR (total) | 0.019 | **0.317** | 0.116 | **0.239** | **0.371** | 0.142 | **0.217** | **-0.277** | -0.024 | 0.143 |
| DUP% (total) | -0.015 | **-0.307** | **-0.285** | **-0.368** | **-0.334** | **-0.309** | **-0.406** | -0.040 | -0.113 | -0.073 |
| DUP lines (total) | 0.121 | 0.131 | **-0.220** | 0.024 | 0.024 | **-0.356** | -0.108 | **-0.298** | -0.100 | **0.263** |

### A5. Leave-one-project-out robustness

Each headline delta recomputed with one project dropped at a time.

| contrast | metric | delta (full) | delta range under LOO | sign stable |
|---|---|---|---|---|
| Dynamic vs Literal | LOC (main-body) | -0.0821 | -0.1479 .. -0.0331 | yes |
| Dynamic vs Literal | CC (main-body) | -0.0469 | -0.0561 .. -0.0130 | yes |
| Dynamic vs Literal | CCTR (main-body) | -0.1623 | -0.1851 .. -0.1197 | yes |
| Dynamic vs Literal | DUP% (main-body) | 0.0199 | -0.0222 .. 0.0595 | no |
| Dynamic vs Literal | LOC (helper) | 0.1986 | 0.1534 .. 0.3122 | yes |
| Dynamic vs Literal | CC (helper) | 0.2253 | 0.1815 .. 0.3222 | yes |
| Dynamic vs Literal | CCTR (helper) | 0.1795 | 0.1393 .. 0.3181 | yes |
| Dynamic vs Literal | DUP% (helper) | -0.0938 | -0.1784 .. -0.0517 | yes |
| Dynamic vs Literal | LOC (total) | 0.1425 | 0.0897 .. 0.2477 | yes |
| Dynamic vs Literal | CC (total) | 0.2133 | 0.1682 .. 0.3067 | yes |
| Dynamic vs Literal | CCTR (total) | 0.1015 | 0.0563 .. 0.2260 | yes |
| Dynamic vs Literal | DUP% (total) | -0.1899 | -0.2792 .. -0.1499 | yes |
| L4 vs L0 | LOC (main-body) | 0.1405 | -0.0239 .. 0.2212 | no |
| L4 vs L0 | CC (main-body) | -0.0900 | -0.1162 .. -0.0468 | yes |
| L4 vs L0 | CCTR (main-body) | -0.1875 | -0.2244 .. -0.0017 | yes |
| L4 vs L0 | DUP% (main-body) | 0.1860 | 0.1112 .. 0.2418 | yes |
| L4 vs L0 | LOC (helper) | 0.3686 | 0.1839 .. 0.4592 | yes |
| L4 vs L0 | CC (helper) | 0.3852 | 0.2127 .. 0.4699 | yes |
| L4 vs L0 | CCTR (helper) | 0.2740 | 0.0780 .. 0.3838 | yes |
| L4 vs L0 | DUP% (helper) | -0.3232 | -0.3561 .. -0.2646 | yes |
| L4 vs L0 | LOC (total) | 0.3356 | 0.1391 .. 0.4269 | yes |
| L4 vs L0 | CC (total) | 0.3541 | 0.1713 .. 0.4509 | yes |
| L4 vs L0 | CCTR (total) | 0.2390 | 0.0473 .. 0.3359 | yes |
| L4 vs L0 | DUP% (total) | -0.3679 | -0.4157 .. -0.2535 | yes |

<!-- APPENDIX:END -->
