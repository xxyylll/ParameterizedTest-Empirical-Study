# Project corpus

本目录只放**项目清单**，不含被分析的源码。Apache 项目都可从
`https://github.com/apache/<repo>` 自行 clone。

| 文件 | 内容 |
|---|---|
| `corpus_174.csv` | **RQ1 / RQ2 主语料**，174 个项目及其分组列 |
| `rq3_candidates_47.txt` | RQ3 候选：构建成功、能产出 AAA trace 的 47 个 |
| `rq3_excluded.txt` | 其中被排除的（`hive`，trace 不完整） |
| `rq3_corpus_46.txt` | **RQ3 实际语料**，46 个 |
| `../rq1/merged_data_218.csv` | 筛选前的 218 个项目全量指标，筛选可追溯 |

## 语料是怎么收窄到 174 的

1. **263** —— ASF 项目目录里标注为 Java 的全部条目（`../../apache_java_projects.txt`）。
   其中 59 个带 *in the Attic* / *Dormant* 标记，在建库阶段即排除。
2. **218** —— 实际 clone 成功、且能被注解级 parser 解析出测试方法的项目，
   构成 `merged_data_218.csv`。
3. **174** —— 从 218 再去掉：
   - **42 个 retired**（ASF category 含 `retired`）；
   - **2 个 data integrity issues**：`Commons-HttpClient` 与 `Lucene-Core`
     （前者早已被 HttpComponents Client 取代、测试目录与后继项目重叠；
      后者是 Lucene 的一个 sub-module，与母项目重复计数）。
     判定写在 `../rq1/rq1_bins.py` 的 `DATA_INTEGRITY_EXCL`。

> **已知缺口**：第 2 步（263 → 218）中有 **4 个项目未被纳入**，当时的筛选理由
> 没有留下记录，无法事后重建。已量化其影响：这 4 个项目合计 3,180 个测试、
> 205 个 parameterized test，**全部是 JUnit 4**，因此 RQ2.2 与 RQ3（均为 JUnit 5
> 口径）不受影响；对 RQ1 的 CAR 影响为 60.9% → 60.7%。这一点在论文的
> Threats to Validity 中已如实说明。

## 分组口径

Size / Age / Domain 的分档切点与 domain 映射规则**只在
`../rq1/rq1_bins.py` 中定义一处**（本项目早期因同一口径在多个脚本里各写一份
而反复出现数字不一致，故改为单一来源）。`corpus_174.csv` 里的
`size_grp` / `age_grp` / `domain_grp` 三列即由它生成。

项目名在不同数据源间的别名对照见 `../project_name_map.json`。
