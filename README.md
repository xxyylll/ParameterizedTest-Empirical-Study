# Replication Package — An Empirical Study of Parameterized Tests in Apache Java Projects

This package contains the code, data and results for our study of **parameterized tests (PTs)** in the
Java projects of the Apache Software Foundation. It covers three research questions:

| RQ | Question | Corpus |
|---|---|---|
| **RQ1** | How widely, and how intensively, are parameterized tests adopted, and what project characteristics are associated with adoption? | 175 projects |
| **RQ2** | Which parameter sources do developers use (RQ2.1), and how are those sources constructed and structured (RQ2.2)? | 175 projects (RQ2.1) / 46 projects (RQ2.2) |
| **RQ3** | Do parameterized tests differ from ordinary tests in size, complexity and duplication (RQ3.1), and how do parameter-source design choices shape where that complexity lives (RQ3.2)? | 46 projects |

Each RQ has its own directory with a `code/` folder (scripts) and a `results/` folder (every table, figure
and findings document those scripts produce). Every script runs from a plain clone of this repository, and
no script depends on absolute paths from the authors' machines.

---

## Contents

1. [Package layout](#1-package-layout)
2. [Quick start](#2-quick-start)
3. [Corpus](#3-corpus)
4. [RQ1 — Adoption](#4-rq1--adoption)
5. [RQ2 — Parameter sources](#5-rq2--parameter-sources)
6. [RQ3 — Complexity of parameterized tests](#6-rq3--complexity-of-parameterized-tests)
7. [Tools](#7-tools)
8. [External data and full recomputation](#8-external-data-and-full-recomputation)
9. [Reproducibility notes](#9-reproducibility-notes)

---

## 1. Package layout

```
.
├── README.md                    this file
├── METHOD_complete.md           full methodology and threats to validity (RQ1, RQ2, RQ3.1)
├── paths.py                     single place where every external path is resolved (env vars, see §8)
├── .env.example                 template for those env vars (copy to .env)
├── requirements.txt             Python dependencies (pandas must be < 3.0, see §9)
├── requirements-recompute.txt   extra dependency (tree-sitter), needed only to rebuild the RQ3 metric tables
├── project_name_map.json        repository directory name ↔ project display name
├── corpus/                      project lists: the 175 (RQ1/RQ2.1) and the 46 (RQ2.2/RQ3)
├── tools/                       lightweight parser jar + checksum; versions of the deep parser and CCFinderSW
├── rq1/  code/  results/        RQ1   adoption                               → rq1/README.md
├── rq2/  code/  results/        RQ2   parameter-source distribution/structure → rq2/README.md
└── rq3/  code/  results/        RQ3   complexity of PTs vs non-PTs            → rq3/README.md
```

Each `rq*/README.md` maps every script to the files it produces.

---

## 2. Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python paths.py                     # shows which external data sources are present (none are needed to check results)

cd rq1/code && ./run_rq1.sh && cd ../..     # RQ1: all analyses and figures; regenerates rq1/results/RQ1_RESULTS.md
cd rq2/code && ./run_rq2.sh && cd ../..     # RQ2: RQ2.1 distribution (if parser output is present) and RQ2.2 figures
cd rq3/code && ./run_rq3.sh && cd ../..     # RQ3: every RQ3.1 and RQ3.2 analysis and figure
```

All three scripts **finish without any external data**. Steps that need external data are skipped, and the
committed outputs are kept. Every other step reads only files inside the package. The two RQ3 metric tables
ship compressed (`rq3/results/rq3_1/*.csv.gz`), and `run_rq3.sh` unpacks them automatically.

Rerunning them reproduces the committed CSV and Markdown outputs byte for byte and the PNG figures pixel for pixel.

---

## 3. Corpus

The study uses **three nested corpus layers**. The layers differ in size because each step up in analysis
depth costs much more per project. This is a design decision, not missing data.

| Layer | Projects | Used by | Analysis depth | Cost per project |
|---|---:|---|---|---|
| Breadth | **175** | RQ1, RQ2.1 | annotation-level syntactic scan | seconds |
| … of which adopt PTs | 107 | RQ1 intensity (PAI, PDAR) | — | — |
| Depth | **46** | RQ2.2, RQ3 | full AAA call traces (Eclipse JDT) + CCFinderSW clone detection | hours (camel ≈ 40 h) |

All layers come from **one snapshot**: a single clone of every repository (HEADs between 2025-10-16 and
2025-10-21). Counts in all RQs therefore refer to the same code.

**From 263 candidates to 175** (`corpus/`):

| Step | Projects | Excluded |
|---|---:|---|
| Apache projects listed as Java | 263 | — |
| Successfully cloned | 243 | 20 repositories missing, renamed or not clonable |
| At least one annotated test method | 220 | 24 projects without `@Test`-style tests (JUnit 3 inheritance style); Commons-HttpClient has no separate clone (it shares HttpComponents-Client's repository) |
| Active projects | 177 | 43 retired or dormant projects: 40 moved to the Apache Attic, Fluo and Fluo Recipes (retired PMCs), Flume (dormant). Test code that is no longer maintained reflects abandonment rather than a choice about PTs |
| Consistent project-level data | **175** | Commons-HttpClient (same repository as HttpComponents-Client, counted twice), Lucene-Core (a sub-module of Lucene) |

**From 175 to 46**: the 47 projects for which the deep parser produced complete AAA traces
(`corpus/rq3_candidates_47.txt`), minus **hive**. Hive's file-level coverage is fine, but 23.8% of its sampled
traces are empty because of unresolved cross-module bindings, and it contains only 25 PTs (0.3% of the depth
corpus). The final list is `corpus/rq3_corpus_46.txt`.

---

## 4. RQ1 — Adoption

**All RQ1 numbers are in [`rq1/results/RQ1_RESULTS.md`](rq1/results/RQ1_RESULTS.md).** That file is
generated by `rq1/code/build_rq1_results.py` from the analysis outputs. Do not edit it by hand.

### Metrics

| Metric | Definition |
|---|---|
| **CAR** (community adoption rate) | share of projects with at least one PT |
| **Deep adoption** | share of projects whose PAI is ≥ 5% |
| **PAI** (parameterized adoption intensity) | PTs / test methods, per project |
| **PDAR** (parameterized-test developer adoption ratio) | developers who modified a PT / developers who modified test code, computed from git history, adopters only |

A PT is a JUnit 5 `@ParameterizedTest` method or a JUnit 4 `@RunWith(Parameterized.class)` class.
For PDAR, a commit counts as modifying a PT when its changed lines intersect the line span
of a parameterized test or of a same-file data source (`rq1/code/pdar/PDAR_METHOD.md`).

### Key results

| | Value |
|---|---|
| CAR | **107 / 175 = 61.1%** |
| Deep adoption | 35 / 175 = 20.0% |
| PAI, median (all 175 / adopters) | 0.282% / **2.221%** |
| PDAR, median (adopters, n = 107) | **15.62%** |
| PTs in total | 17,511 (JUnit 4 8,627 = 49.3%; JUnit 5 8,884 = 50.7%) |

- **Adoption is widespread but shallow.** Even among adopters, PTs are about 2% of tests.
- **Larger projects adopt more often**: 44.1% / 60.0% / 77.3% for Small / Medium / Large
  (χ² = 14.50, p = 7.1×10⁻⁴, Cramér's V = 0.288). Size cut points are fixed at 625 and 1,806 Java files.
- **Projects that use JUnit 5 adopt more often, but adopters do not use PTs significantly more.**
  Logistic regression: Large OR = 4.90, Has-JUnit-5 OR = 5.46 (both p < 0.001). Among adopters, JUnit-5-only
  vs JUnit-4-only PAI: p = 0.107, δ = 0.207.
- **Age and domain show no association** with adoption, PAI or PDAR. All 12 tests are non-significant,
  including the category logistic regression (N = 169).

### Code → results

| `rq1/code/` | `rq1/results/` |
|---|---|
| `rq1_bins.py` | — the **only** definition of corpus filtering, Size/Age bins and the Domain mapping |
| `build_merged_ssk.py` (+ `project_metadata.csv`) | `merged_data_219_ssk.csv` (project-level base table; filtered to the 175 by `rq1_bins.py`) |
| `dataset_stats.py` | `dataset_stats.csv` (Table 1) |
| `adoption_factors.py`, `category_logit.py` | `adoption_factors.csv`, `category_logit_results.csv` |
| `build_table3.py` | `table3_pai_pdar.csv` (Table 3) |
| `adoption_by_groups_figure.py`, `three_panel_figures.py` | `pt_adoption_by_groups.*`, `rq1_pai_three_panel.*`, `rq1_pdar_three_panel.*` |
| `pdar/` | `pdar_summary_ssk.csv`, `pdar/` (per-project PDAR outputs; 24 unit tests in `pdar/tests/`) |
| `parser_validation/` | `parser_validation/parser_validation_sample.csv` (200-item stratified sample for checking the lightweight parser by hand) |

---

## 5. RQ2 — Parameter sources

### RQ2.1 — Distribution (175 projects)

Of the 8,884 JUnit 5 PTs, the sources are distributed as follows (`rq2/results/rq2_1/rq2_1_source_distribution_ssk.csv`):

| Source | PTs | Share | Projects using it |
|---|---:|---:|---:|
| MethodSource | 5,598 | **63.0%** | 85.7% |
| ValueSource | 1,654 | **18.6%** | 76.6% |
| EnumSource | 881 | 9.9% | 42.9% |
| CsvSource | 390 | 4.4% | 45.5% |
| custom source annotation | 248 | 2.8% | 3.9% |
| CsvFileSource / FieldSource / ArgumentsSource / Null·Empty | 153 | 1.7% | — |

Nearly half of all PTs (49.3%) are still written in the JUnit 4 style, which has no source annotations.
Of the 248 custom-annotation PTs, 246 come from a single project (directory-studio, `@LdapServersSource`).

### RQ2.2 — Construction, dependency and structure (46 projects, 8,370 PTs)

Every JUnit 5 PT in the depth corpus is characterised along three dimensions.
The full rules are in `rq2/code/rq2_2/CRITERIA_construction_dependency.md`.

| Dimension | Values |
|---|---|
| **Construction** | *Literal* (the parameter sets are fully fixed at compile time) vs *Dynamic* |
| **Dependency** | L0 source-local · L1 enclosing class · L2 inheritance · L3 same package · L4 other package (farthest test-code artifact reached) |
| **Structure** | cognitive complexity of the provider, helper depth, distinct helpers, arity = `n_params × n_sets` |

| Source | Rows | Highlights |
|---|---:|---|
| MethodSource | 5,508 | 98.9% fully labelled; Dynamic 62.7%; L0 62.3%, L1–L4 37.7% |
| ValueSource | 1,537 | almost entirely literal and L0 |
| EnumSource | 843 | analysis set 814 (resolved `n_sets`, structure known, enum not external) |
| CsvSource | 366 | 100% L0 |
| ArgumentsSource / FieldSource | 66 | |
| CsvFileSource | 48 | |
| standalone Null/Empty source | 2 | |

The labels come from an automatic classifier (`rq2/code/rq2_2/pipeline/`). It was refined over five rounds
of review by hand (379 + 81 + 25 + 59 + 42 items; `rq2/code/rq2_2/TOOLCHAIN_FIXES_2026-09.md`), and the
weighted residual error is below 0.2%. On the hand-validated MethodSource sample (377 tests shared with the automatic table), the automatic labels
agree with the manual ones at κ = 0.972 (construction) and κ = 0.991 (dependency).
For 82.9% of MethodSource PTs, the number of parameter sets can be determined statically.

**Inter-rater reliability of the manual usage-intent coding.** Three external raters each coded 60 of 150
stratified items (15 shared, 45 unique per rater) with the rater guide (`rq2/code/rq2_2/irr/rater_guide.md`).
Each rater is compared with the authors' labels (Cohen's κ, all three raters pooled). An answer of `unclear`
(8.4% of all rater labels) is either counted as a disagreement or excluded:

| Dimension | n | κ (unclear = disagreement) | κ (unclear excluded) |
|---|---:|---:|---:|
| equivalence class | 180 | 0.66 | 0.78 |
| semantic role | 140 | 0.65 | 0.70 |
| MethodSource intent | 69 | 0.51 | 0.63 |
| type complexity | 43 | 0.58 | 0.75 |
| value complexity | 40 | 0.38 | 0.71 |
| behaviour carrying | 110 | 0.57 | 0.57 |
| enum structure | 39 | 0.90 | 0.90 |
| enum usage intent | 40 | 0.64 | 0.83 |

Per-rater values and the shared-item agreement are in `rq2/results/rq2_2/irr/`.

### Code → results

| `rq2/code/` | `rq2/results/` |
|---|---|
| `rq2_1/build_rq2_1_distribution.py` | `rq2_1/rq2_1_source_distribution_ssk.csv` |
| `rq2_2/pipeline/run_rq22.sh` (11 Python steps + 9 Java analyzers) | `rq2_2/`: the 9 delivered tables (`rq22_*_all.csv`, `pt_methodsource_structure.csv`, `pt_methodsource_helper_depth.csv`, …) |
| — (hand-validated, not generated) | `rq2_2/pt_methodsource_structure_validated379.csv` |
| `rq2_2/plot_{construction,dependency,nsets}_distribution.py` | `rq2_2/*_distribution.{png,pdf,csv}`, `nsets_summary.csv` |
| `rq2_2/irr/draw_irr_sample.py`, `build_packets.py` | `rq2_2/irr/sample_items.csv` (150 items with the authors' labels), review packets for the three raters |
| `rq2_2/irr/compute_irr.py` | `rq2_2/irr/irr_kappa.csv`, `irr_shared15.csv`, `irr_unclear.csv` (from `rater_answers.xlsx`) |

---

## 6. RQ3 — Complexity of parameterized tests

### Measures

For every test method, four measures are computed at three levels: **self** (the test body), **helper**
(all test-scope helpers it reaches, each counted once, resolved from the AAA call trace) and **total**
(self + helper).

| Measure | Definition |
|---|---|
| LOC | distinct source lines touched by a non-comment token |
| CC | McCabe: 1 + branching constructs (`&&`/`\|\|` not counted) |
| CCTR\* | test-specific complexity N + A + M + T (nesting-weighted control flow, assertions, mocks, test annotations). The **equal-weight** variant, used in the paper, scores `@ParameterizedTest` and `@Test` alike |
| DUP% | duplicated lines / lines, from CCFinderSW (`-t 50`, test code only) |

Full definitions are in `METHOD_complete.md` §4 and `rq3/results/rq3_1/RQ3_1_metrics_and_findings.md`.

### RQ3.1 — PTs vs non-PTs

The comparison is JUnit 5 PTs against **JUnit 5** non-PT tests: 179,133 tests (8,299 PT / 170,834 non-PT)
in 46 projects. We run one Mann-Whitney U test with Cliff's δ per project, then apply Benjamini–Hochberg
correction within each metric × level (12 families, q < 0.05).

The table below is `rq3/results/rq3_1/rq3_bh_final_eq.csv`. δ > 0 means the PT is larger.

| Level | LOC | CC | CCTR\* | DUP% |
|---|---|---|---|---|
| test | +0.16 small (27+/2−) | +0.11 negl. | −0.01 negl. (9+/10−) | −0.10 negl. (7+/24−) |
| helpers | **+0.49 large** (42+/0−) | **+0.44 medium** | +0.25 small | +0.31 small (37+/2−) |
| total | **+0.50 large** | **+0.45 medium** | +0.20 small | −0.22 small (3+/25−) |

- **The extra complexity of PTs lives in their helpers, not in the test body.**
- **Parameterization moves duplication instead of removing it.** PTs duplicate less in total but more in
  helpers. Providers are the most duplicated code (median DUP% 0.50, vs 0.00 for non-PT helpers;
  27 projects significant).
- With the original CCTR, which gives every PT a free +1, the test-level effect looks positive (δ = +0.23).
  That effect disappears entirely under the equal-weight variant.

### RQ3.2 — How source design shapes complexity

RQ3.2 has four sub-analyses, each with a findings document in `rq3/results/rq3_2/<sub>/`:

| Sub-analysis | Population | Main result | Document |
|---|---|---|---|
| `methodsource/` | **all 5,416 labelled MethodSource PTs** | Construction has no independent effect: the Dynamic > Literal gap vanishes within L0. Dependency has a threshold at **L2**: complexity rises once the provider leaves the test class, while duplication drops. Test-body control flow does not change | `RQ3_2_FULL_POPULATION.md` |
| `cross_source/` | 8,164 PTs, all sources | Source choice changes the helper layer, not the test body (provider vs inline helper LOC δ = 0.39). The effect persists in every data-volume quartile, and only MethodSource pays the cost | `RQ3_3_FINDINGS.md` |
| `enumsource/` | 810 EnumSource PTs | Data-carrying enums remove the helper layer (helper CC δ = −0.60, large) at the cost of more duplication. Only `enum_structure` is stable under leave-one-project-out | `ENUMSOURCE_FINDINGS.md` |
| `amortization/` | 118,744 tests with helpers | The complexity added at L2+ sits in helpers shared by hundreds of tests. When each test is charged only its share of a helper (helper / reuse), the dependency penalty shrinks or reverses for CCTR and CC | `AMORTIZATION_FINDINGS.md` |

`methodsource/` also contains the same analysis on the **379 hand-validated** tests (`rq32_*` outputs,
`RQ3_2_FINDINGS.md`). This sample validates the automatic labels used for the full population
(`rq32_label_agreement.csv`).

### Code → results

| `rq3/code/` | `rq3/results/` |
|---|---|
| `rq3_1/build_test_metrics_unified.py`, `build_test_dup_metrics.py`, `build_provider_dup_metrics.py`, `build_helper_detail.py`, `merge_metrics_and_dup_v2.py` | `rq3_1/test_metrics_all_46projects_v2.csv.gz` (199,437 tests), `rq3_1/test_helper_detail_46projects.csv.gz` |
| `rq3_1/rq3_bh_correction.py` | `rq3_1/rq3_bh_final_{eq,orig}.csv` (paper table), `rq3_bh_{eq,orig}.csv`, `rq3_bh_summary_*.csv` |
| `rq3_1/plot_rq3_forest.py`, `plot_rq3_heatmap_portrait.py` | `rq3_1/rq3_forest_junit5[_cctreq].*`, `rq3_heatmap_portrait_junit5[_cctreq].*` |
| `rq3_1/rq3_metrics.py` | — the only definition of the metric list, Mann-Whitney U and Cliff's δ |
| `rq3_2/<sub>/build_*` → `analyze_*` → `plot_*` | `rq3_2/<sub>/` (CSV tables, figures, findings) |
| `rq3_2/make_result_appendix.py` | the generated `APPENDIX` block at the end of each findings document |

---

## 7. Tools

| Role | Tool | Used for | In this package |
|---|---|---|---|
| Lightweight parser | `test-parser` (JavaParser, annotation level) | RQ1, RQ2.1 | jar + SHA-256 in `tools/` (source not included; the jar contains the full class files) |
| Deep parser | `Javalang-analyzing-cli` v1.3.2 (Eclipse JDT, full AAA traces) | RQ2.2, RQ3 | third-party; pinned version and commit in `tools/README.md` |
| Clone detection | CCFinderSW 1.0 (`-l java -t 50 -ccf`) | RQ3 DUP% | invocation in `tools/README.md` |

---

## 8. External data and full recomputation

External data is only needed to **rebuild intermediate tables from raw sources**. Every path goes through
`paths.py`. By default each data set is looked up under `data/` in the repository root (ignored by git);
alternatively, set the environment variables below, either in the shell or in a `.env` file at the repository
root (template: `.env.example`). When a path is missing, the scripts say which variable to set.

| Variable (default under `data/`) | Content | Size | Needed for |
|---|---|---:|---|
| `PT_PARSER_SSK` (`parser_result_ssk/`) | lightweight-parser JSON per project (243) | ~1.5 GB | RQ1 base table and Table 1, RQ2.1, RQ2.2 pipeline |
| `PT_SSD` (`ssd/`) | source snapshots `apache-projects/` (with AAA traces) and CCFinderSW output | ~55 GB | RQ2.2 pipeline, RQ3 metric tables |
| `PT_METRICS` (`metrics/`) | RQ3 metric tables | ~400 MB | optional; the bundled `.gz` files are used otherwise |
| `PT_PDAR_RESULT` (`pdar_stage1/`) | PDAR stage-1 per-commit table | 189 MB | recomputing the PDAR summary |
| `PT_MANUAL` (`ssd/rq2.2_manual/`) | RQ2.2 manual coding table (1,497 rows) | 0.6 MB | drawing the IRR sample |
| `PT_AAA_JAR`, `PT_JAVA` | deep-parser jar, JDK 21 | — | Java analyzers of the RQ2.2 pipeline |

These large data sets are archived separately (GitHub limits files to 100 MB).

Full recomputation order:

```
1. tools/: run both parsers over the snapshots     → per-project parser JSON and AAA traces
2. rq1/code/build_merged_ssk.py                     → RQ1 base table (PDAR: rq1/code/pdar/PDAR_METHOD.md §7)
3. rq2/code/rq2_2/pipeline/run_rq22.sh              → the 9 RQ2.2 tables (1–2 h)
4. rq3/code/run_rq3.sh --with-build                 → RQ3 metric tables (hours), then all RQ3 analyses
5. rq{1,2,3}/code/run_rq*.sh                        → all analyses, tables and figures
```

---

## 9. Reproducibility notes

- **pandas must be < 3.0.** pandas 3 removed an internal API that statsmodels 0.14 uses, so
  `rq1/code/category_logit.py` fails at import time. Install exactly from `requirements.txt`.
- **One definition per concept.** Grouping rules live only in `rq1/code/rq1_bins.py`, paths only in
  `paths.py`, RQ3 metrics and tests only in `rq3/code/rq3_1/rq3_metrics.py`. Other scripts import them.
- **Rebuilding from raw data.** A clean rerun of the RQ2.2 pipeline reproduces all 9 delivered tables.
  Rebuilding the RQ3 metric table on the snapshot differs from the bundled table in 3 rows (three non-PT
  tests in druid, each +1 in the helper-CCTR N component); no result changes.
