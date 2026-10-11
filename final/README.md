# Replication Package — An Empirical Study of Parameterized Tests in Apache Java Projects

本目录是论文的复现包。**所有脚本均可在本目录内直接运行**，不依赖原作者机器上的绝对路径。

数值结论的出处、口径与已知坑见 [`MANIFEST.md`](MANIFEST.md)；完整方法学见
[`METHOD_complete.md`](METHOD_complete.md)。

---

## 快速开始

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env    # 按需改路径；只核对数字的话可跳过
source .env

python paths.py                          # 检查哪些数据源可用
cd rq1 && python rq1_bins.py             # 自检：应输出 N=175 / 采纳者 107
./run_rq1.sh                             # 一键重跑 RQ1 全部分析与图，并重新生成 RQ1_RESULTS.md
```

> **`requirements.txt` 的 pandas 上限是必需的，不是保守。** pandas 3.0 移除了
> statsmodels 0.14.x 依赖的内部 API，装上 pandas 3 后 `rq1/category_logit.py`
> 会在 import 阶段就抛 `TypeError`。请照 `requirements.txt` 装，不要 `--upgrade`。
>
> 从原始数据重算 RQ3.1 指标还需要 tree-sitter：
> `pip install -r requirements-recompute.txt`。

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
| `corpus_175.csv` | RQ1/RQ2.1 主语料，175 个项目及分组列 |
| `rq3_corpus_46.txt` | RQ3 语料，46 个 |

263 → 218 → 174 → 175 的收窄链条（含补回 Parquet 的说明），
见 [`corpus/README.md`](corpus/README.md)。被分析的 Apache 源码本身不随包分发。

### `rq1/` — 采纳情况（175 个项目）

| 脚本 | 产出 | 自足 |
|---|---|---|
| **`run_rq1.sh`** | **一键重跑 RQ1**，最后由 `build_rq1_results.py` 生成 **`RQ1_RESULTS.md`**（全部结果汇总，不要手改） | 缺外部数据的步骤自动跳过 |
| `rq1_bins.py` | **分组口径的唯一定义**：语料筛选、Size/Age 分档、Domain 映射 | ✅ |
| `build_table3.py` | `table3_pai_pdar.csv` — PAI/PDAR 按 Size/Age/Domain 分组 | ✅ |
| `category_logit.py` | `category_logit_results.csv` — category 逻辑回归（N=169） | ✅ |
| `adoption_factors.py` | `adoption_factors.csv` — 影响因素：规模 / JUnit 版本 / 套件规模 / 年龄，及多元 logistic 回归 | ✅ |
| `three_panel_figures.py` | `rq1_pai_three_panel` / `rq1_pdar_three_panel` — PAI、PDAR 按 Size / Age / Domain | ✅ |
| `adoption_by_groups_figure.py` | `pt_adoption_by_groups` — 采纳率按 Size / Age / Domain | ✅ |
| `build_merged_ssk.py` | `merged_data_219_ssk.csv` — 项目级底表（从 ssk 快照重建） | 需 `PT_PARSER_SSK`、`PT_SSD` |
| `dataset_stats.py` | `dataset_stats.csv` — 论文 Table 1 | 需 `PT_PARSER_SSK` |
| `parser_validation/` | 200 条 parser 人工验证样本（PT/非 PT 各 100，含源码） | ✅ |
| `pdar/` | **PDAR v4 流水线**，见下节与 `pdar/PDAR_METHOD.md` | 需全量 git 克隆 |

数据：`merged_data_219_ssk.csv`（ssk 快照，218 + Parquet）、`pdar_summary_ssk.csv`。旧底表 `merged_data_218.csv` 的来源快照已不在磁盘上，只保留作追溯。

> **`rq1_bins.py` 是所有 RQ1 分组口径的唯一来源。** 这些常量曾散在五个脚本里，
> 年龄分档有三套互不相同的版本，导致同一张表的不同图给出不同的 n。新增分析一律从它导入。

#### `rq1/pdar/` — PDAR

**PDAR = 改过 PT 的开发者 / 改过测试代码的开发者**（×100，%）。采纳者中位数 **15.62%**（n=107）。
论文数字来自 **v4** 两阶段流水线（改动行 ∩ 参数化测试区间：JUnit 5 是 PT 方法及其同文件数据源，JUnit 4 是参数化类）。
方法定义、实现细节、验证、统计结果与复现命令全部见
[`rq1/pdar/PDAR_METHOD.md`](rq1/pdar/PDAR_METHOD.md)。

逐项目结果：`rq1/pdar_summary_ssk.csv`（含 v4 主口径、只算 PT 方法的敏感性口径、v3 对照列）。

### `rq2_1/` — parameter source 的总体分布

`build_rq2_1_distribution.py` → `rq2_1_source_distribution_ssk.csv`（需 `PT_PARSER_SSK`）

**JUnit4 与 JUnit5 分开统计** —— 175 个项目共 17,511 个 PT，其中 JUnit4 `@Parameters`
8,627（49.3%）、JUnit5 八种 source 8,884（50.7%）。

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

`amortization/amortization_metrics.csv`（118,744 行 × 44 列，30 MB，Git 内约 4 MB）
**随包提供**：它是 `analyze_amortization.py` 与 `plot_amortization.py` 唯一缺的输入，
排除它会让这两个脚本在干净 clone 里直接跑不了，而代价只有 4 MB。
要从原始数据重建它，用 `build_amortization_dataset.py`（需 `PT_METRICS`）。

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
