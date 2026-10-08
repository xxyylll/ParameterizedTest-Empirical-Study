# MANIFEST — 定稿产物清单

论文里的每个数字都应该能在这张表里找到出处。**写论文只引用 `final/`，不要去上层目录翻。**

整理于 2026-10-06。口径有变动时，改完数据**同时改这里**，否则这份清单很快就会变成下一个坑。

---

## 为什么要有这份清单

这个项目里同一个概念存在多套数字，彼此只差一点，肉眼分不出对错。已经踩过的坑：

| 数字 | 错的来源 | 对的来源 |
|---|---|---|
| RQ1 项目数 214 | `merged_data_ssk.csv` + 旧脚本 | `rq1_new/merged_data.csv`，筛后 **174** |
| PDAR 中位 20.0% | `result_v3_backup_20260602/`（43 行） | `result_v3/pdar_summary_ssk.csv`，n=106 → **14.52%** |
| RQ2.1 的 284 个 Unknown | `source_types_summary.csv`（旧 clone，且漏 JUnit4） | ssk 快照重算 → **248**，且 JUnit4 占 48.8% |
| 规模分档 ≤800 / 801–3000 | 旧脚本的硬编码阈值 | **三等分，切点 625 / 1806** |
| IRR 抽样 109 个项目 | 直接 `len(set(project))` | 大小写混用去重后 **79** |
| EnumSource n=834 | `status=OK` | **814**（n_sets 非空 + structure≠n/a + 非 External） |

这些的根因都不是文件乱，而是**同名异义的数字散在多处而没有权威索引**。

---

## 语料口径（先看这个）

| 层 | N | 用于 | 怎么来的 |
|---|---:|---|---|
| L1 广度 | **174** | RQ1、RQ2.1 | 218 初始 − 42 retired − 2 data integrity |
| L2 含 PT | 106 | RQ1 的 PAI/PDAR 分母 | 174 中 pt_total > 0 |
| L3 深度 | **46** | RQ2.2、RQ3 | 47 可完成 AAA 解析 − hive |

剔除的 2 个 data integrity 项目：**Commons-HttpClient**（与 HttpComponents-Client 数据完全相同，同仓库重复计入）、**Lucene-Core**（子模块，files_java 5,934 但 total_tests 1,193）。

---

## rq1/

| 文件 | 内容 | 生成脚本 |
|---|---|---|
| `merged_data_218.csv` | 每项目一行，**218 行未筛选** —— 筛选在分析时做 | `analyzer.py` + `batch_parse_all_projects.sh` → `parser_result_ssk/` |
| `pdar_summary_ssk.csv` | 115 个项目的 PDAR，取 174 口径内有 PT 的 **106 个**算中位数 | `developer/find_pt_developers_v3.py` |
| `pt_adoption_by_groups.png/pdf` | 规模/年龄分组的采纳率 | `rq1_new/scale_age_adoption/regen_adoption_by_groups.py` |
| `SUMMARY.md` | retired vs active 对比、各分组结果 | — |
| `COMPARISON_sample_size_filtering.md` | 领域分析的 EPV 筛选（10 → 4 个 category） | — |
| `rq1_bins.py` | **分组口径的唯一定义**：语料筛选、Size/Age 分档、Domain 映射。`load()` 直接返回带好分组列的 DataFrame | — |
| `table3_pai_pdar.csv` + `build_table3.py` | **Table 3**：106 个采纳者按 Size / Age / Domain 的 PAI 与 PDAR 中位数、IQR、KW 检验 | 同目录脚本 |
| `category_logit_results.csv` + `category_logit.py` | **category 逻辑回归**（N=168）。EPV 筛选去掉的是**变量**不是项目：只排除 6 个无 category 的项目，仅给项目数 ≥20 的类别设变量，其余项目留作参照组 | 同目录脚本 |

**关键数字**：CAR 106/174 = 60.9%｜Deep(≥5%) 34/174 = 19.5%｜PAI 中位 0.281%（采纳者 2.211%）｜PDAR 中位 **14.52%**（n=106）

**规模分档是三等分**，切点 **625 / 1806**，**左闭右开**：`[0,625) / [625,1806) / [1806,∞)`，
即 `<625` / `625–1805` / `**>=1806**`。全语料只有 Ranger 正好是 1806 个文件，归入 Large，
于是采纳者分组为 26 / 29 / 51（若改成右闭则是 26 / 30 / 50）。
采纳率 44.1% / 59.2% / 77.3%，χ²=14.51, p=0.00071, V=0.289。

**年龄分档一律是 `≤2005 / 2006–2011 / 2012–2017 / ≥2018`**，实现为
`AGE_BINS = [0, 2006, 2012, 2018, 2030]` + `right=False`。任何与此不同的都是旧的或错的。

> **`rq1_bins.py` 是 RQ1 所有分组口径的唯一定义处。** 这些常量曾经散在五个脚本里，
> 年龄分档有三套互不相同的版本（`<2004/2004–2010/…`、`≤2005/2006–2012/2013–2018/≥2019`、
> 正确的那套），规模分档的闭合方向有两套 —— 于是同一张表的不同图会给出不同的 n。
> 新增分析一律 `from rq1_bins import ...`，不要再各自写一遍。

**Domain 需要手工补充映射**：9 个采纳 PT 的项目其 ASF category 不落在四大类里
（cloud / javaee / testing / ide / observability / identity-management，以及 3 个 category 为空），
见 `build_table3.py` 的 `DOMAIN_MANUAL`。不补的话 Domain 一栏只覆盖 97 个而非 106 个。

> ⚠️ **Table 3 的 KW 检验口径必须在正文统一**。脚注写的是「n≤6 的组排除出 KW 检验」，
> 但表中报告的 H/p 实际是**含全部组**的结果（Age PAI H=2.33, p=0.508 对应 df=3，即 4 组）。
> `table3_pai_pdar.csv` 把两种口径都算出来了，选定一种后同步改脚注。

---

## rq2_1/

| 文件 | 内容 | 生成脚本 |
|---|---|---|
| `rq2_1_source_distribution_ssk.csv` | source 分布，**JUnit4 与 JUnit5 分开** | `build_rq2_1_distribution.py`（同目录） |

**关键数字**：174 项目共 **17,335 个 PT** —— JUnit4 `@Parameters` **8,451（48.8%）** / JUnit5 **8,884（51.2%）**。
JUnit5 内部：MethodSource 63.0%｜ValueSource 18.6%｜EnumSource 9.9%｜CsvSource 4.4%｜**Unknown 248（2.8%，自定义 source 注解，246 条来自 directory-studio 的 `@LdapServersSource`）**。

> 旧的 `source_types_summary.csv` **只统计了 JUnit5**，漏掉近一半的 PT，已移入 `archive/rq2_1_old/`。

---

## rq2_2/

| 文件 | 内容 |
|---|---|
| `rq22_*_all.csv` | 六个 source 的交付表（construction / dependency / structure 三维度） |
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

## rq3_1/

| 文件 | 内容 |
|---|---|
| `rq3_forest_junit5.png` | 森林图，JUnit5 对照组，**原始 CCTR** |
| `rq3_forest_junit5_cctreq.png` | 同上，**同权 CCTR\***（建议正文用这版） |
| `rq3_heatmap_portrait_junit5*.png` | 竖版热力图，口径同上 |
| `RQ3_1_metrics_and_findings.md` | 指标定义与发现 |
| `RQ3_1_refinement_2026-09-29.md` | JUnit5 筛选、CCTR 偏置、provider-DUP 三项修订 |
| `rq3_bh_final_{eq,orig}.csv` | **正文用的结果表**：每个指标×层次的中位 Cliff's δ、效应量级、以及 q<0.05 下显著为正/为负/不显著的项目数 |
| `rq3_bh_{eq,orig}.csv` + `rq3_bh_summary_*.csv` | **BH 多重比较校正**。校正家族 = 一个指标 × 一个层次（组内 46 个项目的 p 值），共 12 组，显著性以 **q < 0.05** 判定 |
| `rq3_bh_correction.py` | 上表的生成脚本 |
| `build_test_metrics_unified.py` / `build_test_dup_metrics.py` / `build_provider_dup_metrics.py` | 指标与重复率的计算脚本 |
| `plot_rq3_forest.py` / `plot_rq3_heatmap_portrait.py` | 森林图与竖版热力图 |

**分析集合**：179,133 个测试（PT 8,299 / 非 PT 170,834），46 个项目，对照组**仅 JUnit5**。

**BH 校正后结论不变**：12 组里 6 组无变化，总共只有 12 个项目-指标组合从显著变为不显著，
其中 10 个的 Cliff's δ 本就是 negligible。这本身是一项有利的稳健性证据。

**CCTR 必须用同权口径报告**：原口径给 `@ParameterizedTest` 记 2 分而 `@Test` 记 1 分，PT 白得 1 分。
同权后 test 层 delta 从 0.23 降到 **−0.01**，显著项目从 34 正/2 负变成 11 正/11 负 —— 原口径下的 test 层结论站不住。

---

## 其它

| 文件 | 说明 |
|---|---|
| `METHOD_complete.md` | 完整 Method + Threats（11 条） |
| `project_name_map.json` | ssk 目录名 ↔ RQ1 显示名。跨数据源 join 必须用它，否则会静默漏匹配 |

---

## 仍在上层目录的（没复制进来，太大或是原始数据）

| 路径 | 为什么留在原地 |
|---|---|
| `parser_result_ssk/` | 243 个项目的 parser 产物，RQ1/RQ2.1 的原始输入 |
| `parser_result/` | 624M，旧 clone。**不要用于分析**，仅供回溯旧数字 |
| `/Volumes/SSKSSD/apache-projects/` | 源码快照，RQ2.2/RQ3 的输入 |
| `/Volumes/SSKSSD/rq2.2_manual/` | 人工编码表（1,497 行），IRR 的 gold standard |
| `Complexity_Analysis/` | RQ3 的脚本与中间产物 |

## archive/

废弃产物，**只为回溯，不要用于分析**。每个都在上面的「已经踩过的坑」表里有对应的正确来源。
