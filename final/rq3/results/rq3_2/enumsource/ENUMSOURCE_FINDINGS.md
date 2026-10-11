# EnumSource — design dimensions and complexity profiles

Kept separate from RQ3.2 because EnumSource's codebook has a different shape.
It has **no Literal/Dynamic construction dimension**, and its `dependency`
column turns out to be *fully determined* by where the enum type lives
(production → `Production`, test-scope → L1/L2/L3/L4, external → `External`),
so it carries no information beyond `enum_location`. What EnumSource does offer
is three design labels with no MethodSource analogue:

| dimension | groups | n |
|---|---|---|
| **enum_structure** | Data-carrying (constants carry fields) / Label-based (bare names) | 579 / 235 |
| **enum_location** | production 421 · test 382 · production(generated) 11 | 814 |
| **names_mode** | ALL constants / explicit `names=` SUBSET | 436 / 378 |

`enum_structure` is a property of the enum *type*, not a measurement of the
test, so — unlike MethodSource's Structure dimension — it is a legitimate
grouping variable rather than a restatement of the outcome.

**Data.** The population is **RQ2.2's analysable set, reproduced exactly**, so
the denominator here is the one RQ2.2 reports and no before/after discrepancy
needs explaining. RQ2.2 admits an EnumSource test when its `n_sets` resolved,
its `enum_structure` is not `n/a`, and the enum is not `External` — a JDK or
third-party enum is not declared in the project, so neither how it is
represented nor how it is used can be characterised. That is **814** tests.

**The population is 814 and stays 814.** Complexity metrics exist for **810**
of them, across 28 projects. The four without them are the only EnumSource
tests in the whole corpus that live under `src/main/java` rather than
`src/test/java` — Accumulo publishes its integration-test base classes as a
library, so `ExitCodesIT`, `ScannerIT` and `ManagerRepoIT_SimpleSuite` sit in
the `main` source root of a module named `test`. The measurement pipeline
parses only `src/test/java`, so those tests have no LOC/CC/CCTR/DUP of any
kind; the same path convention is why the RQ2 export leaves their `test_class`
blank, while their enum labels are unaffected because that analysis reads the
source file directly.

They are missing measurements, not a narrower definition; every comparison
below therefore runs on 810 of the 814.

(For reference, the 814 are a strict subset of the 834 rows with
`status = OK`: the 20 excluded are 15 External, 4 with an unresolved `n_sets`,
and 1 with structure `n/a`.) Statistics identical to RQ3.2/RQ3.3 (shared
`pt_stats.py`).

---

## ⚠️ Read the robustness column first

EnumSource usage is **extremely concentrated**: jena alone is 30% of all
EnumSource tests, **64% of all test-located enums**, and **62% of all
`names=` SUBSET tests**; hudi is 45% of Label-based tests.

A leave-one-project-out check over the 28 projects therefore decides which
contrasts mean anything (`enumsource_robustness_loo.csv`):

| dimension | effects keeping their sign across all 28 LOO samples |
|---|---|
| **enum_structure** | **10 / 12** (the 2 exceptions are near-zero main-body effects) |
| enum_location | 5 / 12 |
| names_mode | 2 / 12 |

**Only `enum_structure` supports a claim.** The location and names_mode
contrasts are largely "jena vs everyone else" and are reported below as
descriptive observations, not findings. In
`enumsource_dimensions_heatmap.png` a cell is starred only when it is
significant, at least small, *and* LOO-stable.

---

## Finding — A data-carrying enum removes the helper layer

Data-carrying vs Label-based (δ > 0 = Data-carrying larger):

| scope | LOC | CC | CCTR | DUP% |
|---|---|---|---|---|
| main-body | 0.062 | −0.243 (small) | 0.211 (small) | 0.143 |
| **helper** | **−0.578 (large)** | **−0.601 (large)** | **−0.523 (large)** | −0.123 |
| **total** | −0.465 (medium) | **−0.635 (large)** | −0.307 (small) | **0.458 (medium)** |

**Label-based enums carry substantially more helper-side complexity** — large
effects on every helper metric. The mechanism is plain: when the enum constants
carry their own data, the test reads values off the constant; when the enum is
a bare set of names, something has to map each name to its expected values, and
that something is helper code.

The effect **holds inside both location strata**, so it is not the
location confound in disguise — and it is *stronger* for test-declared enums:

| helper metric | within production enums | within test-declared enums |
|---|---|---|
| helper LOC | −0.416 (medium) | **−0.843 (large)** |
| helper CC | −0.419 (medium) | **−0.859 (large)** |
| helper CCTR | −0.427 (medium) | **−0.628 (large)** |

The trade-off is duplication: data-carrying enums show **higher total DUP%**
(δ = 0.458, medium; δ = 0.801, large, among test-declared enums). Putting the data in the enum removes helper logic but the
enum-constant tables themselves repeat.

This is the same shape as RQ3.3's inline-vs-provider result, one level down:
**a data-carrying enum is the "inline" option, a label-based enum forces a
provider-like helper layer.**

---

## Descriptive only (not LOO-stable)

* **enum_location (test vs production).** Raw contrasts suggest production
  enums carry more helper complexity (helper CC δ = −0.325) and test-declared
  enums duplicate more (total DUP% δ = 0.408, medium). But 7 of 12 effects flip
  sign when a single project is dropped, and 64% of test-located enums come
  from jena. Do not report as a finding.
* **names_mode (SUBSET vs ALL).** Only 3 of 12 effects are stable, and the
  stratified deltas reverse sign between Data-carrying and Label-based enums.
  Uninterpretable at this sample composition.
(The `dependency` dimension gets its own section below, because the reason it
is not reported is different in kind.)

---

## Why `dependency` is not reported as a dimension

This one is worth stating carefully, because the analysis *was* run and it
produced large, highly significant numbers — they are in
`enumsource_dependency_pairwise.csv` and in appendix A4. The reason they are
not a finding is not that they failed to reach significance.

**First: it is not an independent dimension.** EnumSource's `dependency` is
fully determined by `enum_location` —

| dependency | which enum_location it corresponds to |
|---|---|
| `Production` (432) | production 421 + production(generated) 11 |
| `L1` / `L2` / `L3` / `L4` (382) | all `test` |
| `External` (14) | external 14 |

Knowing where the enum lives tells you the dependency category. Its only
incremental information is that it subdivides the *test-declared* enums by
distance. This is unlike MethodSource, where construction and dependency vary
freely against each other (a Literal provider can be L0 or L4). So the contrast
was only run where it adds information: inside the 382 test-declared enums.

**Second: inside that subset, level and project are the same variable.**

| level | n | projects | largest project |
|---|---|---|---|
| L1 | 120 | 10 | hadoop 30%, avro 21% |
| L2 | 2 | 1 | — |
| **L3** | **247** | **2** | **jena 99% (244/247)** |
| L4 | 13 | 3 | hudi 77% |

"L3 vs L1" is, in substance, *jena versus hadoop + avro + eight others* wearing
a dependency-level label. The measured effects are real and large — helper CC
δ = −0.794, total CC δ = −0.803, total DUP% δ = 0.897, all Holm p < 1e-6 — but
what they measure is that jena writes its enum tests differently, not that
dependency depth drives complexity.

**The distinction matters.** The problem is not weak significance; it is that
significance here cannot attribute the effect to the dimension, because the
grouping variable is collinear with project identity. With n = 247 vs 120 a
test will report p < 1e-6 either way. This is exactly why leave-one-project-out
stability, not p, is the reporting gate throughout this document.

For contrast, MethodSource's L0–L4 hold 3,384 / 353 / 503 / 502 / 674 tests
across 45 projects with no level dominated by one project, which is why the
L2 threshold found there *can* be read as a property of dependency design.

## Limitations

* **Project concentration is the dominant threat** (jena 30%, hudi 18%) —
  quantified in `enumsource_project_concentration.csv` and handled by making
  LOO stability a condition for reporting.
* 28 projects; 810 of the 814 have metrics; `production(generated)` (11) is too small to
  contrast, and `External` enums are outside the analysable population by
  RQ2.2's definition.
* `enum_structure` is confounded with `enum_location` (Label-based skews
  production 67%); handled by stratification, which the finding survives.

## Files

`build_enumsource_dataset.py` → `enumsource_metrics.csv` (+ join report);
`analyze_enumsource.py` → descriptives, twogroup_stats (with strata),
location_kruskal, dependency_pairwise, project_concentration, robustness_loo,
population; `plot_enumsource.py` → `enumsource_structure_heatmap.png`,
`enumsource_dimensions_heatmap.png`, `enumsource_boxplots.png`.

```bash
cd final/rq3/code/rq3_2/enumsource        # 或直接 final/rq3/code/run_rq3.sh 跑整个 RQ3
python3 build_enumsource_dataset.py
python3 analyze_enumsource.py
python3 plot_enumsource.py
python3 ../make_result_appendix.py   # 重写各 FINDINGS 文末的附录
```

---

<!-- APPENDIX:BEGIN (generated by make_result_appendix.py -- do not edit by hand) -->

## Appendix — complete results

Every number below comes straight from the analysis CSVs via `make_result_appendix.py`. Bold = significant and at least a small effect; note that for the location, names_mode and dependency contrasts significance does **not** imply the effect is attributable to the design dimension (see the concentration table in A6).

### A1. enum_structure: Data-carrying vs Label-based

Positive delta = Data-carrying larger. Right-hand columns repeat the contrast inside each enum_location stratum.

| metric | n DC | n LB | median DC | median LB | delta | magnitude | p | delta (production only) | delta (test only) |
|---|---|---|---|---|---|---|---|---|---|
| LOC (main-body) | 578 | 232 | 23.0000 | 20.0000 | 0.062 | negligible | 0.169590 | **-0.161** | **0.365** |
| CC (main-body) | 578 | 232 | 1.0000 | 1.0000 | **-0.243** | small | 0.000000 | **-0.229** | **-0.209** |
| CCTR (main-body) | 578 | 232 | 6.0000 | 4.0000 | **0.211** | small | 0.000002 | 0.069 | **0.393** |
| DUP% (main-body) | 578 | 232 | 0.9767 | 0.8446 | 0.143 | negligible | 0.000820 | -0.042 | **0.279** |
| DUP lines (main-body) | 578 | 232 | 21.5000 | 14.0000 | 0.133 | negligible | 0.003025 | **-0.153** | **0.528** |
|  |  |  |  |  |  |  |  |  |  |
| LOC (helper) | 578 | 232 | 13.0000 | 71.5000 | **-0.578** | large | 0.000000 | **-0.416** | **-0.843** |
| CC (helper) | 578 | 232 | 2.0000 | 15.0000 | **-0.601** | large | 0.000000 | **-0.419** | **-0.859** |
| CCTR (helper) | 578 | 232 | 1.0000 | 9.0000 | **-0.523** | large | 0.000000 | **-0.427** | **-0.628** |
| DUP% (helper) | 578 | 232 | 0.0000 | 0.0000 | -0.123 | negligible | 0.001662 | -0.105 | -0.077 |
| DUP lines (helper) | 578 | 232 | 0.0000 | 0.0000 | **-0.176** | small | 0.000007 | -0.106 | **-0.171** |
|  |  |  |  |  |  |  |  |  |  |
| LOC (total) | 578 | 232 | 43.0000 | 102.5000 | **-0.465** | medium | 0.000000 | **-0.417** | **-0.545** |
| CC (total) | 578 | 232 | 3.0000 | 16.0000 | **-0.635** | large | 0.000000 | **-0.454** | **-0.863** |
| CCTR (total) | 578 | 232 | 9.0000 | 16.0000 | **-0.307** | small | 0.000000 | **-0.377** | -0.125 |
| DUP% (total) | 578 | 232 | 0.6364 | 0.2122 | **0.458** | medium | 0.000000 | **0.198** | **0.801** |
| DUP lines (total) | 578 | 232 | 27.0000 | 22.0000 | 0.081 | negligible | 0.071772 | -0.096 | **0.408** |

### A2. enum_location and names_mode contrasts

Reported for completeness only — both fail the leave-one-project-out check (A5).

| metric | delta test vs production | magnitude | p | delta SUBSET vs ALL | magnitude | p |
|---|---|---|---|---|---|---|
| LOC (main-body) | 0.090 | negligible | 0.027544 | **0.231** | small | 0.000000 |
| CC (main-body) | **-0.175** | small | 0.000000 | -0.142 | negligible | 0.000006 |
| CCTR (main-body) | 0.092 | negligible | 0.024157 | **0.166** | small | 0.000040 |
| DUP% (main-body) | **0.308** | small | 0.000000 | **0.302** | small | 0.000000 |
| DUP lines (main-body) | **0.212** | small | 0.000000 | **0.342** | medium | 0.000000 |
|  |  |  |  |  |  |  |
| LOC (helper) | **-0.317** | small | 0.000000 | **-0.266** | small | 0.000000 |
| CC (helper) | **-0.324** | small | 0.000000 | **-0.314** | small | 0.000000 |
| CCTR (helper) | **-0.262** | small | 0.000000 | **-0.211** | small | 0.000000 |
| DUP% (helper) | **-0.181** | small | 0.000000 | -0.076 | negligible | 0.030929 |
| DUP lines (helper) | **-0.193** | small | 0.000000 | -0.079 | negligible | 0.025425 |
|  |  |  |  |  |  |  |
| LOC (total) | **-0.247** | small | 0.000000 | -0.129 | negligible | 0.001480 |
| CC (total) | **-0.355** | medium | 0.000000 | **-0.348** | medium | 0.000000 |
| CCTR (total) | **-0.189** | small | 0.000004 | -0.067 | negligible | 0.101709 |
| DUP% (total) | **0.352** | medium | 0.000000 | **0.412** | medium | 0.000000 |
| DUP lines (total) | 0.061 | negligible | 0.138482 | **0.218** | small | 0.000000 |

### A3. Kruskal–Wallis across the four enum_location groups

| metric | n | H | df | p | p (BH) | sig at .05 |
|---|---|---|---|---|---|---|
| LOC (main-body) | 810 | 5.6266 | 2 | 0.060007 | 0.069239 | no |
| CC (main-body) | 810 | 37.3247 | 2 | 0.000000 | 0.000000 | yes |
| CCTR (main-body) | 810 | 5.3678 | 2 | 0.068296 | 0.073174 | no |
| DUP% (main-body) | 810 | 64.1528 | 2 | 0.000000 | 0.000000 | yes |
| DUP lines (main-body) | 810 | 27.7828 | 2 | 0.000001 | 0.000001 | yes |
|  |  |  |  |  |  |  |
| LOC (helper) | 810 | 61.1198 | 2 | 0.000000 | 0.000000 | yes |
| CC (helper) | 810 | 63.5704 | 2 | 0.000000 | 0.000000 | yes |
| CCTR (helper) | 810 | 44.4576 | 2 | 0.000000 | 0.000000 | yes |
| DUP% (helper) | 810 | 26.2182 | 2 | 0.000002 | 0.000003 | yes |
| DUP lines (helper) | 810 | 29.9894 | 2 | 0.000000 | 0.000001 | yes |
|  |  |  |  |  |  |  |
| LOC (total) | 810 | 36.3890 | 2 | 0.000000 | 0.000000 | yes |
| CC (total) | 810 | 76.2067 | 2 | 0.000000 | 0.000000 | yes |
| CCTR (total) | 810 | 21.8316 | 2 | 0.000018 | 0.000023 | yes |
| DUP% (total) | 810 | 74.5437 | 2 | 0.000000 | 0.000000 | yes |
| DUP lines (total) | 810 | 2.4281 | 2 | 0.296986 | 0.296986 | no |

### A4. dependency inside test-scope enums (L1 / L3 / L4)

Computed and reported in full, but **not interpretable as a dependency effect** — L3 is 99% jena, so these contrasts are largely project contrasts (see A6 and the discussion above). Positive delta = the higher level larger.

| metric | L3 vs L1 | L4 vs L1 | L4 vs L3 | KW p |
|---|---|---|---|---|
| LOC (main-body) | **0.652** | **0.538** | **-0.375** | 0.000000 |
| CC (main-body) | -0.127 | -0.033 | 0.101 | 0.007589 |
| CCTR (main-body) | **0.452** | **0.439** | -0.181 | 0.000000 |
| DUP% (main-body) | **0.388** | **0.396** | 0.054 | 0.000000 |
| DUP lines (main-body) | **0.802** | **0.672** | **-0.464** | 0.000000 |
|  |  |  |  |  |
| LOC (helper) | **-0.731** | **-0.506** | -0.033 | 0.000000 |
| CC (helper) | **-0.794** | **-0.533** | -0.033 | 0.000000 |
| CCTR (helper) | **-0.593** | **-0.565** | -0.096 | 0.000000 |
| DUP% (helper) | **-0.210** | **-0.450** | **-0.239** | 0.000019 |
| DUP lines (helper) | **-0.288** | **-0.450** | **-0.239** | 0.000000 |
|  |  |  |  |  |
| LOC (total) | **-0.374** | **-0.411** | -0.170 | 0.000000 |
| CC (total) | **-0.803** | **-0.540** | 0.012 | 0.000000 |
| CCTR (total) | -0.084 | -0.179 | -0.079 | 0.333468 |
| DUP% (total) | **0.897** | **0.644** | -0.006 | 0.000000 |
| DUP lines (total) | **0.579** | 0.308 | **-0.499** | 0.000000 |

### A5. Leave-one-project-out robustness

| contrast | metric | delta (full) | delta range under LOO | sign stable |
|---|---|---|---|---|
| Data-carrying vs Label-based | LOC (main-body) | 0.0617 | -0.1448 .. 0.2716 | no |
| Data-carrying vs Label-based | CC (main-body) | -0.2427 | -0.2908 .. -0.1886 | yes |
| Data-carrying vs Label-based | CCTR (main-body) | 0.2106 | 0.1091 .. 0.2486 | yes |
| Data-carrying vs Label-based | DUP% (main-body) | 0.1428 | -0.0499 .. 0.1881 | no |
| Data-carrying vs Label-based | LOC (helper) | -0.5775 | -0.6656 .. -0.4224 | yes |
| Data-carrying vs Label-based | CC (helper) | -0.6007 | -0.6731 .. -0.4422 | yes |
| Data-carrying vs Label-based | CCTR (helper) | -0.5232 | -0.5981 .. -0.3500 | yes |
| Data-carrying vs Label-based | DUP% (helper) | -0.1227 | -0.2031 .. -0.0356 | yes |
| Data-carrying vs Label-based | LOC (total) | -0.4651 | -0.5341 .. -0.2347 | yes |
| Data-carrying vs Label-based | CC (total) | -0.6352 | -0.7102 .. -0.4681 | yes |
| Data-carrying vs Label-based | CCTR (total) | -0.3066 | -0.4206 .. -0.0694 | yes |
| Data-carrying vs Label-based | DUP% (total) | 0.4580 | 0.2278 .. 0.5385 | yes |
| test vs production | LOC (main-body) | 0.0901 | -0.3079 .. 0.1883 | no |
| test vs production | CC (main-body) | -0.1746 | -0.2075 .. -0.0916 | yes |
| test vs production | CCTR (main-body) | 0.0916 | -0.1943 .. 0.1267 | no |
| test vs production | DUP% (main-body) | 0.3079 | 0.0627 .. 0.3926 | yes |
| test vs production | LOC (helper) | -0.3173 | -0.3933 .. 0.0393 | no |
| test vs production | CC (helper) | -0.3237 | -0.4072 .. 0.1268 | no |
| test vs production | CCTR (helper) | -0.2615 | -0.3350 .. 0.0388 | no |
| test vs production | DUP% (helper) | -0.1808 | -0.2682 .. -0.0903 | yes |
| test vs production | LOC (total) | -0.2470 | -0.3068 .. -0.0568 | yes |
| test vs production | CC (total) | -0.3549 | -0.4412 .. 0.1187 | no |
| test vs production | CCTR (total) | -0.1891 | -0.2384 .. -0.0253 | yes |
| test vs production | DUP% (total) | 0.3520 | -0.1150 .. 0.4454 | no |
| SUBSET vs ALL | LOC (main-body) | 0.2306 | -0.0683 .. 0.3524 | no |
| SUBSET vs ALL | CC (main-body) | -0.1423 | -0.1666 .. -0.0146 | yes |
| SUBSET vs ALL | CCTR (main-body) | 0.1659 | -0.0508 .. 0.2622 | no |
| SUBSET vs ALL | DUP% (main-body) | 0.3016 | 0.0473 .. 0.3835 | yes |
| SUBSET vs ALL | LOC (helper) | -0.2662 | -0.3565 .. 0.1739 | no |
| SUBSET vs ALL | CC (helper) | -0.3144 | -0.3873 .. 0.1753 | no |
| SUBSET vs ALL | CCTR (helper) | -0.2109 | -0.3020 .. 0.1470 | no |
| SUBSET vs ALL | DUP% (helper) | -0.0763 | -0.1252 .. 0.1062 | no |
| SUBSET vs ALL | LOC (total) | -0.1293 | -0.1731 .. 0.1446 | no |
| SUBSET vs ALL | CC (total) | -0.3476 | -0.4283 .. 0.1624 | no |
| SUBSET vs ALL | CCTR (total) | -0.0665 | -0.1110 .. 0.0991 | no |
| SUBSET vs ALL | DUP% (total) | 0.4125 | -0.0373 .. 0.5462 | no |

### A6. Project concentration per group

Why A2 and A4 are not reported as findings.

| dimension | group | n | projects | largest project | its share |
|---|---|---|---|---|---|
| enum_structure | Data-carrying | 578 | 22 | jena | 42% |
| enum_structure | Label-based | 232 | 15 | hudi | 46% |
| location_group | production | 417 | 25 | hudi | 31% |
| location_group | production_generated | 11 | 1 | ozone | 100% |
| location_group | test | 382 | 14 | jena | 64% |
| names_mode_group | ALL | 433 | 21 | hudi | 22% |
| names_mode_group | SUBSET | 377 | 18 | jena | 64% |
| dependency | L1 | 120 | 10 | hadoop | 30% |
| dependency | L2 | 2 | 1 | logging-log4j2 | 100% |
| dependency | L3 | 247 | 2 | jena | 99% |
| dependency | L4 | 13 | 3 | hudi | 77% |
| dependency | Production | 428 | 25 | hudi | 30% |

<!-- APPENDIX:END -->
