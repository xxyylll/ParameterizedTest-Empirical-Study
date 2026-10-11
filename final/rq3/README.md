# RQ3 — PT 与非 PT 的复杂度，以及各 parameter source 的收益

46 个项目（`../corpus/rq3_corpus_46.txt`）、199,437 个测试。对照组为 **JUnit 5 的非 PT 测试**。

- **RQ3.1**：PT 与非 PT 在 LOC、CC、CCTR、重复率上的差异，分 test / helper / total 三层，逐项目 Mann-Whitney U
  与 Cliff's δ，按「指标 × 层次」分 12 组做 BH 多重比较校正（q < 0.05）。
- **RQ3.2**：MethodSource 的结构与收益、跨 source 对比、EnumSource 的表示与利用方式、helper 复用的摊销效应。

## 运行

```bash
cd code
./run_rq3.sh                 # 从指标表开始重跑 RQ3.1 与 RQ3.2 的全部分析与作图
./run_rq3.sh --with-build    # 先从源码快照与 AAA 轨迹重建指标表（小时级，需 PT_SSD 与 tree-sitter）
```

**RQ3 的全部分析只依赖两张指标表**，二者以 `.gz` 随包附带（`results/rq3_1/`）。`PT_METRICS` 下没有时，
`run_rq3.sh` 自动解压使用，因此不需要任何外部数据即可复现 RQ3 的全部结果。

| 指标表 | 内容 |
|---|---|
| `test_metrics_all_46projects_v2.csv` | 每个测试一行：LOC / CC / CCTR / DUP%，self / helper / total 三层 |
| `test_helper_detail_46projects.csv` | 每个（测试, helper）一行，RQ3.2 摊销分析用 |

随包的是产出论文数字时用的那一版。在当前快照上用 `--with-build` 重建，只有 3 行不同（druid 的 3 个非 PT 测试，
helper CCTR 的 N 分量各 +1），不影响任何结果。

## RQ3.1

| `code/rq3_1/` | `results/rq3_1/` | 说明 |
|---|---|---|
| `build_test_metrics_unified.py` | （→ `PT_METRICS`） | 从 AAA 轨迹用 tree-sitter 算 LOC / CC / CCTR，含 helper 解析 |
| `build_test_dup_metrics.py`、`build_provider_dup_metrics.py` | （→ `PT_METRICS`） | 从 CCFinderSW 输出算重复率 |
| `build_helper_detail.py` | （→ `PT_METRICS`） | 逐 helper 的复杂度明细 |
| `merge_metrics_and_dup_v2.py` | （→ `PT_METRICS`） | 合并成 `test_metrics_all_46projects_v2.csv` |
| `rq3_bh_correction.py` | `rq3_bh_{eq,orig}.csv`、`rq3_bh_summary_*.csv`、**`rq3_bh_final_*.csv`** | BH 校正。`rq3_bh_final_*` 是正文用的结果表 |
| `plot_rq3_forest.py` | `rq3_forest_junit5[_cctreq].{png,pdf}` | 森林图（正文） |
| `plot_rq3_heatmap_portrait.py` | `rq3_heatmap_portrait_junit5[_cctreq].{png,pdf}` | 竖版热力图（附录） |
| `parse_success_rate.py` | `parse_success_rate.csv` | AAA 解析覆盖率，分 PT / 非 PT（需 `PT_PARSER_SSK`） |
| `rq3_metrics.py` | — | 指标清单与 Mann-Whitney U / Cliff's δ 的唯一定义 |

`eq` / `_cctreq` 是 CCTR 的同权口径：原始计分给 `@ParameterizedTest` 记 2 分、`@Test` 记 1 分，每个 PT 白得 1 分；
**正文应报同权口径**。指标定义与发现见 `results/rq3_1/RQ3_1_metrics_and_findings.md`、`RQ3_1_refinement_2026-09-29.md`。

## RQ3.2

四个子分析，每个都是 `build_*_dataset.py` → `analyze_*.py` → `plot_*.py`，产出与 FINDINGS 文档在
`results/rq3_2/<子分析>/`：

| 子分析 | 内容 | FINDINGS |
|---|---|---|
| `methodsource/` | MethodSource 的结构与收益；`rq32_*` 基于 379 条人工核验样本（`../rq2/results/rq2_2/pt_methodsource_structure_validated379.csv`），`rq32_full_*` 基于全量 5,508 条（`rq22_methodsource_all.csv`） | `RQ3_2_FINDINGS.md`、`RQ3_2_FULL_POPULATION.md` |
| `cross_source/` | 跨 source 对比 | `RQ3_3_FINDINGS.md` |
| `enumsource/` | EnumSource 的表示方式与利用方式 | `ENUMSOURCE_FINDINGS.md` |
| `amortization/` | helper 复用的摊销效应（读 `cross_source/` 的产物，须排在其后） | `AMORTIZATION_FINDINGS.md` |

`code/rq3_2/make_result_appendix.py` 用最新产物重写 5 份 FINDINGS 文末 `APPENDIX` 块，`run_rq3.sh` 最后一步自动调用。
`code/rq3_2/pt_stats.py` 是四者共用的统计工具。四个子目录原先命名为 rq3_2 ~ rq3_5，但都属于 RQ3.2；
FINDINGS 文档里沿用的旧编号（如 `RQ3_3_FINDINGS.md`）指的就是这里的子分析。
