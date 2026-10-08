# Replication Package — An Empirical Study of Parameterized Tests in Apache Java Projects

本目录是论文的复现包。**所有脚本均可在本目录内直接运行**，不依赖原作者机器上的绝对路径。

数值结论的出处、口径与已知坑见 [`MANIFEST.md`](MANIFEST.md)；完整方法学见
[`METHOD_complete.md`](METHOD_complete.md)。

---

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env    # 按需改路径
source .env

python paths.py                          # 检查哪些数据源可用
cd rq1 && python rq1_bins.py             # 自检：应输出 N=174 / 采纳者 106
```

`paths.py` 会列出每个数据源的解析结果与存在状态。**只依赖本目录内数据的脚本**
（下表标 ✅ 自足）不需要任何配置即可运行。

---

## 需要的外部数据

四个环境变量都可选；不设则用默认值。缺失时脚本会明确提示该设哪一个，而不是抛裸异常。

| 变量 | 内容 | 体积 | 没有它会怎样 |
|---|---|---:|---|
| `PT_SSD` | 源码快照 `apache-projects/`、AAA 轨迹、CCFinderSW 输出、人工标注表 | **~55 GB** | RQ3.1 指标重算、IRR 材料包生成不可用 |
| `PT_PARSER_SSK` | 轻量 parser 的逐项目 JSON（243 个） | ~1.5 GB | RQ2.1 分布、Table 1 的 Test files 一列不可用 |
| `PT_METRICS` | RQ3 指标中间表 | ~400 MB | RQ3.1/3.2 的分析与绘图不可用 |
| `PT_MANUAL` | 人工标注表（4 个 CSV，1,497 行） | ~0.6 MB | IRR 抽样不可用 |

大体积数据不随本仓库分发（GitHub 单文件上限 100 MB），见 DOI 链接。
**所有最终结果表与图已包含在本目录内**，无需重算即可核对论文中的每个数字。

---

## 目录

### `corpus/` — 项目清单

| 文件 | 内容 |
|---|---|
| `corpus_174.csv` | RQ1/RQ2 主语料，174 个项目及分组列 |
| `rq3_corpus_46.txt` | RQ3 语料，46 个 |

263 → 218 → 174 的收窄链条、以及 4 个项目未被纳入的已知缺口，
见 [`corpus/README.md`](corpus/README.md)。被分析的 Apache 源码本身不随包分发。

### `rq1/` — 采纳情况（174 个项目）

| 脚本 | 产出 | 自足 |
|---|---|---|
| `rq1_bins.py` | **分组口径的唯一定义**：语料筛选、Size/Age 分档、Domain 映射 | ✅ |
| `build_table3.py` | `table3_pai_pdar.csv` — PAI/PDAR 按 Size/Age/Domain 分组 | ✅ |
| `category_logit.py` | `category_logit_results.csv` — category 逻辑回归（N=168） | ✅ |
| `dataset_stats.py` | `dataset_stats.csv` — 论文 Table 1 | 需 `PT_PARSER_SSK` |
| `parser_validation/` | 200 条 parser 人工验证样本（PT/非 PT 各 100，含源码） | ✅ |

数据：`merged_data_218.csv`、`pdar_summary_ssk.csv`。

> **`rq1_bins.py` 是所有 RQ1 分组口径的唯一来源。** 这些常量曾散在五个脚本里，
> 年龄分档有三套互不相同的版本，导致同一张表的不同图给出不同的 n。新增分析一律从它导入。

### `rq2_1/` — parameter source 的总体分布

`build_rq2_1_distribution.py` → `rq2_1_source_distribution_ssk.csv`（需 `PT_PARSER_SSK`）

**JUnit4 与 JUnit5 分开统计** —— 174 个项目共 17,335 个 PT，其中 JUnit4 `@Parameters`
8,451（48.8%）、JUnit5 八种 source 8,884（51.2%）。

### `rq2_2/` — parameter source 的结构刻画（46 个项目）

六张交付表 `rq22_*_all.csv`（合计 8,370 行）+ 三张分布图的生成脚本。
判定规则见 `CRITERIA_construction_dependency.md`，五轮 review 记录见 `TOOLCHAIN_FIXES_2026-09.md`。

`irr/` 是 inter-rater 信度材料：150 条抽样、三份评分包、评分者说明。
`draw_irr_sample.py` 需 `PT_MANUAL`，`build_packets.py` 需 `PT_SSD`（要读源码）。

### `rq3_1/` — PT 与非 PT 的规模、复杂度与重复率

| 脚本 | 说明 |
|---|---|
| `build_test_metrics_unified.py` | 从 AAA 轨迹算 LOC/CC/CCTR（需 `PT_SSD`） |
| `build_test_dup_metrics.py` | 从 CCFinderSW 输出算重复率（需 `PT_SSD`） |
| `rq3_bh_correction.py` | **BH 多重比较校正**，12 组（指标 × 层次），q<0.05 判显著 |
| `parse_success_rate.py` | AAA 解析覆盖率，分 PT/非 PT |
| `plot_rq3_forest.py` / `plot_rq3_heatmap_portrait.py` | 森林图与竖版热力图 |

> **CCTR 请用同权口径（`--cctr eq`）报告。** 原始计分给 `@ParameterizedTest` 2 分而
> `@Test` 1 分，PT 白得 1 分；同权后 test 层 delta 从 0.23 降到 −0.01。

### `rq3_2/` — 各 source 的收益分析

四个子分析，每个都是 `build_*_dataset.py` → `analyze_*.py` → `plot_*.py` + FINDINGS：

| 目录 | 分析对象 |
|---|---|
| `methodsource/` | MethodSource 的结构与收益 |
| `cross_source/` | 跨 source 对比 |
| `enumsource/` | EnumSource 的表示方式与利用方式 |
| `amortization/` | helper 复用带来的摊销效应 |

`pt_stats.py` 是四者共用的统计工具。

> 这四个目录原先命名为 `rq3_2` ~ `rq3_5`，**但它们全部属于 RQ3.2**，已按分析对象重命名。

---

## 两个 parser — `tools/`

| | 工具 | 解析深度 | 用于 | 本仓库内 |
|---|---|---|---|---|
| 轻量 | `test-parser`（JavaParser） | 注解级，不解析类型绑定 | RQ1、RQ2.1 | ✅ JAR + SHA-256 |
| 深度 | `Javalang-analyzing-cli`（Eclipse JDT） | 完整 AAA 轨迹 + 类型绑定 | RQ2.2、RQ3 | 第三方仓库，钉版本 |

轻量 parser 以**预编译 fat JAR** 随包提供（源码在工作区整理中遗失，jar 可反编译核验，
校验和已固定）。其输出另经 200 条分层人工样本验证，见 `rq1/parser_validation/`。

深度 parser 是第三方开源工具，不随本包分发；`tools/README.md` 钉了确切的
版本与 commit，照着 clone 并自行构建即可。

调用方式、构建命令、CCFinderSW 的参数：见 [`tools/README.md`](tools/README.md)。

---

## 复现顺序

多数结果可直接核对已有产物。若要从原始数据重算：

```
1. tools/ 的两个 parser → parser_result_ssk/ + 各项目的 AAA/
2. rq2_2/               → 六张 rq22_*_all.csv
3. rq3_1/build_*.py     → 指标中间表（需 PT_SSD）
4. 其余 analyze/plot    → 表与图
```

第 1 步需要完整的源码快照（~54 GB），第 3 步耗时以小时计。
**只核对数字的话，直接读各目录下的 CSV 即可。**
