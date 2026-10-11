# Project corpus

本目录只放**项目清单**，不含被分析的源码。Apache 项目都可从
`https://github.com/apache/<repo>` 自行 clone。

| 文件 | 内容 |
|---|---|
| `apache_java_projects.txt` | 263 个候选：ASF 项目目录里标注为 Java 的全部条目 |
| `corpus_175.csv` | **RQ1 / RQ2.1 主语料**，175 个项目及其分组列 |
| `rq3_candidates_47.txt` | RQ3 候选：构建成功、能产出 AAA trace 的 47 个 |
| `rq3_excluded.txt` | 其中被排除的（`hive`，trace 不完整） |
| `rq3_corpus_46.txt` | **RQ3 实际语料**，46 个 |
| `../rq1/results/merged_data_219_ssk.csv` | 筛选前的 219 个项目全量指标（218 + Parquet），筛选可追溯 |

## 语料是怎么收窄到 175 的

1. **263** —— ASF 项目目录里标注为 Java 的全部条目（`apache_java_projects.txt`）。
   其中 59 个带 *in the Attic* / *Dormant* 标记，在建库阶段即排除。
2. **218** —— 实际 clone 成功、且能被注解级 parser 解析出测试方法的项目。
3. **174** —— 从 218 再去掉：
   - **42 个 retired**（ASF category 含 `retired`）；
   - **2 个 data integrity issues**：`Commons-HttpClient` 与 `Lucene-Core`
     （前者早已被 HttpComponents Client 取代、测试目录与后继项目重叠；
      后者是 Lucene 的一个 sub-module，与母项目重复计数）。
     判定写在 `../rq1/code/rq1_bins.py` 的 `DATA_INTEGRITY_EXCL`。
4. **175** —— 补回 **Parquet**（见下）。

## 第 2 步漏掉的 4 个项目

263 → 218 这一步有 4 个项目没有进入分析清单：parquet-mr、flume、fluo、fluo-recipes。
它们同时出现在前一版清单（`projects_副本.txt`，2025-10-14）与后一版清单（`projects.txt`，2025-10-27）中，
只在中间那份 `my_projects.txt`（2025-10-16）里缺失，更像整理清单时漏粘，而不是有意排除。

- **Parquet 已补回**（2026-10-10）。它是活跃项目，1,799 个测试、176 个 PT（全部 JUnit 4）。
  category 取自 projects.apache.org（`big-data`），首次提交年份与 PDAR 由全量 clone 得到。
- **其余 3 个按其状态不纳入**：Flume 已转入 dormant；Fluo 与 Fluo Recipes 自 2018 年后无更新。
  三者合计 29 个 PT（全部来自 Flume，JUnit 4）。

补回 Parquet 对各 RQ 的影响：RQ2.2 与 RQ3 只分析 JUnit 5 的 PT，**不受影响**；
RQ2.1 只变 JUnit 4 一侧（8,451 → 8,627），JUnit 5 内部的 source 分布一个数都不变；
RQ1 的 CAR 60.9% → 61.1%，没有任何检验的方向或显著性改变。

## 快照

计数（`total_tests`、`pt_total` 等）与 `files_java` 都取自 **ssk 快照** —— 外置盘 `apache-projects/`
上那次 clone（HEAD 在 2025-10-16 ~ 10-21），也是 RQ2 / RQ3 用的同一份。生成脚本是
`../rq1/code/build_merged_ssk.py`。

旧底表 `merged_data_218.csv` 的计数来自 2025-10-15 跑的一批 parser 输出，那批输出后来被部分重跑覆盖，
已不在磁盘上，无法复现；保留它只为追溯。从旧底表切换到 ssk 快照，174 个项目里 61 个计数有变，
但没有一个项目的采纳状态翻转，CAR、采纳者数、PAI 中位数都不变。

## 分组口径

Size / Age / Domain 的分档切点与 domain 映射规则**只在
`../rq1/code/rq1_bins.py` 中定义一处**（本项目早期因同一口径在多个脚本里各写一份
而反复出现数字不一致，故改为单一来源）。`corpus_175.csv` 里的
`size_grp` / `age_grp` / `domain_grp` 三列即由它生成。

Size 的切点 625 / 1806 是固定常量，不随语料重算。在 175 个项目上它们分出 59 / 50 / 66 个，
所以不应称作「本语料的三分位」。

项目名在不同数据源间的别名对照见 `../project_name_map.json`。
