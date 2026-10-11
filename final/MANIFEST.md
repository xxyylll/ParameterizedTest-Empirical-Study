# MANIFEST — 定稿产物清单

论文里的每个数字都应该能在这张表里找到出处。**写论文只引用 `final/`，不要去上层目录翻。**

整理于 2026-10-06。口径有变动时，改完数据**同时改这里**，否则这份清单很快就会变成下一个坑。

---

## 为什么要有这份清单

这个项目里同一个概念存在多套数字，彼此只差一点，肉眼分不出对错。已经踩过的坑：

| 数字 | 错的来源 | 对的来源 |
|---|---|---|
| RQ1 项目数 214 | `merged_data_ssk.csv` + 旧脚本 | `rq1/results/merged_data_219_ssk.csv`，筛后 **175**（174 + 补回的 Parquet） |
| PDAR 中位 20.0% / 14.52% | 20.0%：`result_v3_backup_20260602/`（43 行）；14.52%：v3 的 hunk 邻近判定（已被 v4 取代，见 `rq1/code/pdar/PDAR_METHOD.md`） | `rq1/results/pdar_summary_ssk.csv`（v4），n=107 → **15.62%** |
| RQ2.1 的 284 个 Unknown | `source_types_summary.csv`（旧 clone，且漏 JUnit4） | ssk 快照重算 → **248**，且 JUnit4 占 49.3% |
| 规模分档 ≤800 / 801–3000 | 旧脚本的硬编码阈值 | **三等分，切点 625 / 1806** |
| IRR 抽样 109 个项目 | 直接 `len(set(project))` | 大小写混用去重后 **79** |
| EnumSource n=834 | `status=OK` | **814**（n_sets 非空 + structure≠n/a + 非 External） |
| RQ3.2 `rq32_*` 的 N = 3,394 / 2,022 | 拿全量 `pt_methodsource_structure.csv`（5,508 行）当 379 条样本表跑出的 `rq32_*`（10-08 曾误入库） | `rq2/results/rq2_2/pt_methodsource_structure_validated379.csv` → **N = 223 / 150**，与 `RQ3_2_FINDINGS.md` 一致 |

这些的根因都不是文件乱，而是**同名异义的数字散在多处而没有权威索引**。

---

## 语料口径（先看这个）

| 层 | N | 用于 | 怎么来的 |
|---|---:|---|---|
| L1 广度 | **175** | RQ1、RQ2.1 | 218 初始 − 42 retired − 2 data integrity + Parquet（补回，见 `corpus/README.md`） |
| L2 含 PT | 107 | RQ1 的 PAI/PDAR 分母 | 175 中 pt_total > 0 |
| L3 深度 | **46** | RQ2.2、RQ3 | 47 可完成 AAA 解析 − hive |

剔除的 2 个 data integrity 项目：**Commons-HttpClient**（与 HttpComponents-Client 数据完全相同，同仓库重复计入）、**Lucene-Core**（子模块，files_java 5,934 但 total_tests 1,193）。

---

## rq1/（脚本在 `rq1/code/`，产出在 `rq1/results/`；明细见 `rq1/README.md`）

| 文件 | 内容 | 生成脚本 |
|---|---|---|
| `merged_data_219_ssk.csv` | 每项目一行，**219 行未筛选**（218 + Parquet）—— 筛选在分析时做。计数与 `files_java` 取自 ssk 快照 | `build_merged_ssk.py`（同目录） |
| `merged_data_218.csv` | 旧底表，**仅作追溯**：其计数来自 2025-10-15 的一批 parser 输出，那批输出已被覆盖、无法复现 | `trigger.sh` + `pt_summary.py` → 旧 `parser_result/`（已被后来的重跑部分覆盖） |
| `pdar_summary_ssk.csv` | **107 个采纳者**的 PDAR v4（主口径 `pdar` / `core_pdar`，另含 `pdar_pt_only`、`pdar_v3` 等对照列） | `rq1/code/pdar/calculate_pdar_v4.py` |
| `pt_adoption_by_groups.png/pdf` | 规模/年龄/领域分组的采纳率 | `adoption_by_groups_figure.py`（同目录） |
| `rq1_pai_three_panel` / `rq1_pdar_three_panel`（png/pdf） | PAI、PDAR 按 Size / Age / Domain 的三联图 | `three_panel_figures.py`（同目录） |
| `adoption_factors.csv` + `adoption_factors.py` | 影响因素：规模 × 采纳的卡方、规模 × PAI、JUnit 版本、套件规模、年龄，及多元 logistic 回归 | 同目录脚本 |
| **`RQ1_RESULTS.md`** | **RQ1 全部结果的汇总**：Table 1、描述统计、分组采纳率、影响因素、两个回归、Table 3、PDAR、图。**由脚本自动生成，不要手改** | `build_rq1_results.py`（同目录） |
| `run_rq1.sh` | 一键重跑 RQ1：底表 → PDAR 汇总 → 全部分析与图 → `RQ1_RESULTS.md`。缺外部数据的步骤自动跳过 | — |
| `rq1_bins.py` | **分组口径的唯一定义**：语料筛选、Size/Age 分档、Domain 映射。`load()` 直接返回带好分组列的 DataFrame | — |
| `table3_pai_pdar.csv` + `build_table3.py` | **Table 3**：107 个采纳者按 Size / Age / Domain 的 PAI 与 PDAR 中位数、IQR、KW 检验 | 同目录脚本 |
| `category_logit_results.csv` + `category_logit.py` | **category 逻辑回归**（N=169）。EPV 筛选去掉的是**变量**不是项目：只排除 6 个无 category 的项目，仅给项目数 ≥20 的类别设变量，其余项目留作参照组 | 同目录脚本 |

**关键数字**：CAR 107/175 = 61.1%｜Deep(≥5%) 35/175 = 20.0%｜PAI 中位 0.282%（采纳者 2.221%）｜PDAR 中位 **15.62%**（n=107，v4）

**规模分档切点是固定常量 625 / 1806**（在 175 个项目上分出 59 / 50 / 66，不应称作本语料的三分位），**左闭右开**：`[0,625) / [625,1806) / [1806,∞)`，
即 `<625` / `625–1805` / `**>=1806**`。全语料只有 Ranger 正好是 1806 个文件，归入 Large，
于是采纳者分组为 26 / 30 / 51（若改成右闭则是 26 / 31 / 50）。
采纳率 44.1% / 60.0% / 77.3%，χ²=14.50, p=0.00071, V=0.288。

**年龄分档一律是 `≤2005 / 2006–2011 / 2012–2017 / ≥2018`**，实现为
`AGE_BINS = [0, 2006, 2012, 2018, 2030]` + `right=False`。任何与此不同的都是旧的或错的。

> **`rq1_bins.py` 是 RQ1 所有分组口径的唯一定义处。** 这些常量曾经散在五个脚本里，
> 年龄分档有三套互不相同的版本（`<2004/2004–2010/…`、`≤2005/2006–2012/2013–2018/≥2019`、
> 正确的那套），规模分档的闭合方向有两套 —— 于是同一张表的不同图会给出不同的 n。
> 新增分析一律 `from rq1_bins import ...`，不要再各自写一遍。

**Domain 需要手工补充映射**：9 个采纳 PT 的项目其 ASF category 不落在四大类里
（cloud / javaee / testing / ide / observability / identity-management，以及 3 个 category 为空），
见 `build_table3.py` 的 `DOMAIN_MANUAL`。不补的话 Domain 一栏只覆盖 98 个而非 107 个。

> ⚠️ **Table 3 的 KW 检验口径必须在正文统一**。脚注写的是「n≤6 的组排除出 KW 检验」，
> 但表中报告的 H/p 实际是**含全部组**的结果（Age PAI H=2.60, p=0.458 对应 df=3，即 4 组）。
> `table3_pai_pdar.csv` 把两种口径都算出来了，选定一种后同步改脚注。

---

## RQ2.1（`rq2/code/rq2_1/` → `rq2/results/rq2_1/`；明细见 `rq2/README.md`）

| 文件 | 内容 | 生成脚本 |
|---|---|---|
| `rq2_1_source_distribution_ssk.csv` | source 分布，**JUnit4 与 JUnit5 分开** | `build_rq2_1_distribution.py`（同目录） |

**关键数字**：175 项目共 **17,511 个 PT** —— JUnit4 `@Parameters` **8,627（49.3%）** / JUnit5 **8,884（50.7%）**。
JUnit5 内部：MethodSource 63.0%｜ValueSource 18.6%｜EnumSource 9.9%｜CsvSource 4.4%｜**Unknown 248（2.8%，自定义 source 注解，246 条来自 directory-studio 的 `@LdapServersSource`）**。

> 旧的 `source_types_summary.csv` **只统计了 JUnit5**，漏掉近一半的 PT，已移入 `archive/rq2_1_old/`。

---

## RQ2.2（`rq2/code/rq2_2/` → `rq2/results/rq2_2/`）

| 文件 | 内容 |
|---|---|
| `rq22_*_all.csv` 等 9 张交付表 | 各 source 的交付表（construction / dependency / structure 三维度）。由 **`rq2/code/rq2_2/pipeline/run_rq22.sh`** 生成：10 个 Python 脚本 + 9 个 Java 分析器，此前留在 `rq2/rq2_2_structure/` 未入包，现已搬入并改为可移植；从零重跑 MethodSource 三张表逐字节复现 |
| `construction_distribution.{png,pdf,csv}` | 各 source 的 construction 分布 |
| `dependency_distribution.{png,pdf,csv}` | 各 source 的 dependency 分布 |
| `nsets_distribution.{png,pdf}` | n_sets 分布（含 runtime-dependent） |
| `CRITERIA_construction_dependency.md` | **三个维度的完整判定规则** |
| `TOOLCHAIN_FIXES_2026-09.md` | 五轮 review 的问题与修复记录 |
| `PAPER_NOTES_methodology.md` | hive 排除理由等需在论文交代的口径 |
| `plot_{construction,dependency,nsets}_distribution.py` | 三张分布图的生成脚本 |
| `irr/` | inter-rater 信度：抽样、材料包、评分者说明。`*_review_packet.md` 是发给三位评分者的材料，`packet_R*.csv` 是对应的答题表 |

**产出规模**（46 项目，合计 8,370 行）：MethodSource 5,508｜ValueSource 1,537｜EnumSource 843｜CsvSource 366｜Args/Field 66｜CsvFileSource 48｜Null/Empty 2

**EnumSource 的分析分母是 814**，不是 843 或 834：`n_sets` 非空 **且** `enum_structure != n/a` **且** `dependency != External`（External 的枚举声明不在项目里，无从刻画）。

`irr/` 的样本：**150 条**（3 位评分者 × 60 = 15 共享 + 45 独有），少数类已过采样（different-equivalence 从 7.7% 提到 20.7%）。

---

## RQ3.1（`rq3/code/rq3_1/` → `rq3/results/rq3_1/`；明细见 `rq3/README.md`）

| 文件 | 内容 |
|---|---|
| `rq3_forest_junit5.png` | 森林图，JUnit5 对照组，**原始 CCTR** |
| `rq3_forest_junit5_cctreq.png` | 同上，**同权 CCTR\***（建议正文用这版） |
| `rq3_heatmap_portrait_junit5*.png` | 竖版热力图，口径同上 |
| `test_metrics_all_46projects_v2.csv.gz` | **RQ3 的核心数据**（199,437 个测试 × LOC/CC/CCTR/DUP% 三层），7 MB。产出论文数字时用的那一版；`run_rq3.sh` 在缺 `PT_METRICS` 时自动解压使用 |
| `test_helper_detail_46projects.csv.gz` | 逐 helper 的复杂度明细，RQ3.2 摊销分析的输入，5.6 MB |
| `merge_metrics_and_dup_v2.py`、`build_helper_detail.py`（code/） | 生成上面两张表的最后一步，此前留在 `Complexity_Analysis/` 未入包，现已搬入。当前快照上重建只差 3 行（druid 的 3 个非 PT 测试，helper CCTR 的 N 分量 +1） |
| `rq3_bh_final_{eq,orig}.csv` 的生成 | 此前没有脚本；现由 `rq3_bh_correction.py` 从逐项目结果汇总写出，与原文件逐字节相同 |
| `RQ3_1_metrics_and_findings.md` | 指标定义与发现 |
| `RQ3_1_refinement_2026-09-29.md` | JUnit5 筛选、CCTR 偏置、provider-DUP 三项修订 |
| `rq3_bh_final_{eq,orig}.csv` | **正文用的结果表**：每个指标×层次的中位 Cliff's δ、效应量级、以及 q<0.05 下显著为正/为负/不显著的项目数 |
| `rq3_bh_{eq,orig}.csv` + `rq3_bh_summary_*.csv` | **BH 多重比较校正**。校正家族 = 一个指标 × 一个层次（组内 46 个项目的 p 值），共 12 组，显著性以 **q < 0.05** 判定 |
| `rq3_bh_correction.py` | 上表的生成脚本 |
| `build_test_metrics_unified.py` / `build_test_dup_metrics.py` / `build_provider_dup_metrics.py` | 指标与重复率的计算脚本 |
| `plot_rq3_forest.py` / `plot_rq3_heatmap_portrait.py` | 森林图与竖版热力图 |
| `rq3_metrics.py` | **METRICS / METRIC_LABELS / mann_whitney_u 的唯一定义处。** 原先住在 `heatmap_unified_44projects.py`（旧横向热图，已被 portrait 版取代）里，而那个模块无 `__main__` 保护 —— 只是 import 就会重画图。抽出后 forest / heatmap / BH 三个脚本统一导入，六张 BH 结果表字节级不变 |

**分析集合**：179,133 个测试（PT 8,299 / 非 PT 170,834），46 个项目，对照组**仅 JUnit5**。

**BH 校正后结论不变**：12 组里 6 组无变化，总共只有 12 个项目-指标组合从显著变为不显著，
其中 10 个的 Cliff's δ 本就是 negligible。这本身是一项有利的稳健性证据。

**CCTR 必须用同权口径报告**：原口径给 `@ParameterizedTest` 记 2 分而 `@Test` 记 1 分，PT 白得 1 分。
同权后 test 层 delta 从 0.23 降到 **−0.01**，显著项目从 34 正/2 负变成 11 正/11 负 —— 原口径下的 test 层结论站不住。

---

## RQ3.2（`rq3/code/rq3_2/` → `rq3/results/rq3_2/`；明细见 `rq3/README.md`）

| 子目录 | 内容 | FINDINGS |
|---|---|---|
| `methodsource/` | `rq32_*`：379 条人工核验样本；`rq32_full_*`：全量 5,508 条 | `RQ3_2_FINDINGS.md`、`RQ3_2_FULL_POPULATION.md` |
| `cross_source/` | 各 source 之间的对比 | `RQ3_3_FINDINGS.md` |
| `enumsource/` | EnumSource 的表示与利用方式（分母 814） | `ENUMSOURCE_FINDINGS.md` |
| `amortization/` | helper 复用的摊销效应，读 `cross_source/` 的产物 | `AMORTIZATION_FINDINGS.md` |

- **379 条样本表是单独的输入**：`rq2/results/rq2_2/pt_methodsource_structure_validated379.csv`，人工核验过，不由流水线生成。
  `build_rq32_dataset.py`（默认模式）与 `check_label_agreement.py` 读它；`--full` 模式读 `rq22_methodsource_all.csv`。
- 各 FINDINGS 文末的 `APPENDIX` 块由 `make_result_appendix.py` 从 CSV 生成，不要手改。
- 从随包指标表重跑，四个子目录的全部 CSV 与原工作目录逐字节一致；只有 `amortization_metrics.csv`
  的 8 个值在小数点后第 4 位差 1（浮点求和顺序），不影响任何统计结果。

---

## corpus/

| 文件 | 说明 |
|---|---|
| `corpus_175.csv` | RQ1/RQ2.1 主语料，175 行，含 `size_grp`/`age_grp`/`domain_grp` 三列 |
| `rq3_candidates_47.txt` | RQ3 候选 47 个（构建成功、有 AAA trace） |
| `rq3_excluded.txt` | 其中排除的 `hive`（trace 不完整） |
| `rq3_corpus_46.txt` | RQ3 实际语料 46 个 |

263 → 218 → 174 → 175 的收窄链条：第 2 步漏掉的 4 个项目中 Parquet 已补回，
其余 3 个（Flume / Fluo / Fluo Recipes）按其状态不纳入，见 `corpus/README.md`。

## tools/

| 文件 | 说明 |
|---|---|
| `test-parser-1.0-SNAPSHOT-jar-with-dependencies.jar` | 轻量 parser，2025-12-11 构建。**源码已遗失**，只剩 fat jar |
| `test-parser.jar.sha256` | 上述 jar 的校验和，供复现者确认同一二进制 |
| `README.md` | 两个 parser 的调用方式；深度 parser 钉在 `v1.3.2` / `46a90c6` |

深度 parser（`Codegass/Javalang-analyzing-cli`）是第三方开源工具，**未 vendor 进本包** ——
复制他人仓库会造成来源与许可的混乱，只钉版本与 commit。

## 其它

| 文件 | 说明 |
|---|---|
| `METHOD_complete.md` | 完整 Method + Threats（11 条） |
| `project_name_map.json` | ssk 目录名 ↔ RQ1 显示名。跨数据源 join 必须用它，否则会静默漏匹配 |
| `rq1/code/pdar/PDAR_METHOD.md` | **PDAR v4 的方法、验证、统计结果与复现**（论文 PDAR 数字的唯一方法说明） |
| `rq1/code/pdar/superseded_v2/` | PDAR 的 v2 方法（行号→方法身份→生命周期追踪，`-U0`）。**设计并实现过但未采用，无结果产物**，仅作方法学记录。代码逐字保留、未做可移植化 |
| `requirements.txt` | **pandas 必须 <3.0**：pandas 3.0 移除了 statsmodels 0.14.x 依赖的内部 API，装上后 `category_logit.py` 在 import 阶段即崩 |
| `requirements-recompute.txt` | 只有重算 RQ3.1 指标才需要（tree-sitter） |

---

## 不随包分发的外部数据

| 内容 | 环境变量 | 说明 |
|---|---|---|
| 轻量 parser 的逐项目 JSON | `PT_PARSER_SSK` | 243 个项目，~1.5 GB；RQ1 底表、RQ2.1、RQ2.2 流水线的输入 |
| 源码快照与 AAA 轨迹、CCFinderSW 输出 | `PT_SSD` | ~55 GB；RQ2.2 流水线与 RQ3 指标表的输入 |
| PDAR 第一阶段的逐提交表 | `PT_PDAR_RESULT` | 189 MB |
| RQ2.2 人工编码表 | `PT_MANUAL` | 1,497 行，IRR 的 gold standard |

旧的 `parser_result/`（另一次 clone）**不要用于分析**，仅供回溯旧数字。
RQ2.2 的生产代码（原 `rq2/rq2_2_structure/`）与 RQ3 指标表的最后两步（原 `Complexity_Analysis/`）都已搬入本包。

## archive/

废弃产物，**只为回溯，不要用于分析**。每个都在上面的「已经踩过的坑」表里有对应的正确来源。
