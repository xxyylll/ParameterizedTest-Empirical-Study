# Project corpus

本目录只放**项目清单**，不含被分析的源码。Apache 项目都可从 `https://github.com/apache/<repo>` 自行 clone。

| 文件 | 内容 |
|---|---|
| `apache_java_projects.txt` | 263 个候选：ASF 项目目录里标注为 Java 的全部条目 |
| `corpus_175.csv` | **RQ1 / RQ2.1 语料**，175 个项目及其分组列（`size_grp` / `age_grp` / `domain_grp`） |
| `rq3_candidates_47.txt` | RQ2.2 / RQ3 候选：深度 parser 能产出完整 AAA 轨迹的 47 个 |
| `rq3_excluded.txt` | 其中排除的 `hive` |
| `rq3_corpus_46.txt` | **RQ2.2 / RQ3 语料**，46 个 |

## 从 263 到 175

| 步骤 | 项目数 | 去掉的 |
|---|---:|---|
| ASF 项目目录里标注为 Java | 263 | — |
| clone 成功 | 243 | 20 个仓库不存在、已改名或无法 clone |
| 至少有一个注解式测试方法 | 220 | 24 个没有 `@Test` 式测试（JUnit 3 继承写法）；Commons-HttpClient 与 HttpComponents-Client 同一仓库，没有单独的 clone |
| 仍在维护 | 177 | 43 个已退役或休眠：40 个已移入 Apache Attic，Fluo 与 Fluo Recipes（PMC 已退役），Flume（dormant）。不再维护的测试代码反映的是停止维护，而不是对 PT 的取舍 |
| 项目级数据一致 | **175** | Commons-HttpClient（与 HttpComponents-Client 同一仓库，重复计入）、Lucene-Core（Lucene 的子模块） |

项目级底表是 `../rq1/results/merged_data_219_ssk.csv`，筛选写在 `../rq1/code/rq1_bins.py`
（ASF category 含 `retired` 的项目，以及 `DATA_INTEGRITY_EXCL`）。

## 从 175 到 46

47 个深度 parser 能产出完整 AAA 轨迹的项目，去掉 hive：它的文件级覆盖正常，但抽样的轨迹中 23.8% 为空
（跨模块类型绑定无法解析），且只有 25 个 PT（占深度语料的 0.3%）。

## 快照

全部计数都取自同一次 clone（HEAD 在 2025-10-16 ~ 10-21），RQ1、RQ2、RQ3 共用。

## 分组口径

Size / Age / Domain 的分档切点与 domain 映射**只在 `../rq1/code/rq1_bins.py` 中定义**。
Size 的切点 625 / 1806 是固定常量，在 175 个项目上分出 59 / 50 / 66 个，不是本语料的三分位。

项目名在不同数据源间的别名对照见 `../project_name_map.json`。
