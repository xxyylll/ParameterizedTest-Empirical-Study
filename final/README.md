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
cd rq1 && python rq1_bins.py             # 自检：应输出 N=174 / 采纳者 106
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
| `pdar/` | **PDAR 的完整流水线**，见下节 | 需全量 git 克隆 |

数据：`merged_data_218.csv`、`pdar_summary_ssk.csv`。

> **`rq1_bins.py` 是所有 RQ1 分组口径的唯一来源。** 这些常量曾散在五个脚本里，
> 年龄分档有三套互不相同的版本，导致同一张表的不同图给出不同的 n。新增分析一律从它导入。

#### `rq1/pdar/` — PDAR

**PDAR = 改过 PT 的开发者 / 改过测试代码的开发者**（×100，单位 %）。
是**开发者比例，不是提交比例**；两个计数都按 author email 去重并转小写。
分母用「碰过测试的人」而非「所有提交者」，使比例回答「在碰测试的人里有多少碰过 PT」，
不被只改生产代码的贡献者稀释。采纳者中位数 **14.52%**（n=106）。
另报 `core_pdar`：分子换成**新增或删除**过 PT 注解的人（Layer 3 判定）。

| 文件 | 作用 |
|---|---|
| `find_pt_developers.py` | 逐项目、逐提交的三层检测，产出 `{project}_commits.csv` |
| `calculate_pdar.py` | 把提交表汇总成项目级 PDAR |
| `batch_pdar.sh` | 整张清单：clone 全量 → 分析 → **立刻删除** |
| `pdar_repo_map.csv` | **仓库名的唯一来源**（117 项目 → git URL） |
| `pdar_layer_attribution.py` | 三层各自的独有贡献；纯粹从已有逐提交表算，不碰 git |
| `pdar_context_sensitivity.py` | diff 上下文行数的敏感性；复用已发表表作 U3 基线，只重算大上下文 |
| `pt_projects_ssk.txt` | 项目清单（117 个；最终结果 115 个，少的两个是设计上排除的 `Commons-HttpClient` / `Lucene-Core`） |

**三层检测**（逐提交判 `modifiedPT`）：

1. **JUnit 5 hunk** —— diff 里定位 `@ParameterizedTest`，检查它**前一行**
   （可能是 `@MethodSource`/`@ValueSource` 被改）与**后续行**直到下一个
   `@Test`/`@ParameterizedTest`/新 hunk；其间有 `+`/`-` 即判定。
2. **JUnit 4 文件** —— 若 Layer 1 未命中，对 diff 里每个改动的 `.java`
   用 `git show commit:file` 看是否含 `@RunWith(Parameterized`。
3. **Pickaxe** —— `git log --all -G @ParameterizedTest`（及 JUnit 4 版）找出
   **新增/删除** PT 注解的提交，同时置 `is_core`。

**必须是全量克隆。** `git log --all` 与 `git diff-tree` 在 `--depth 1` 的浅克隆上
只能看到 1 个提交，PDAR 会算成 0。`PT_SSD/apache-projects/` 里的是浅克隆
（本研究其余部分不需要历史），**不能用于 PDAR**；脚本会检查 `.git/shallow`
并直接报错而不是给出错误数字。117 个项目的全量克隆合计几十 GB，
所以 `batch_pdar.sh` 一次只落地一个仓库、分析完即删。

> **已知局限：diff 上下文行数。** Layer 1 是在 diff **文本**上做的，因此它能看到
> 多少周围代码完全由 git 的上下文行数决定。`git diff-tree` 默认给 3 行，于是
> 同一个 PT 方法内部的改动只要离注解超过 3 行，就不与注解同处一个 hunk ——
> Layer 1 看不到，只能靠 Layer 2/3 兜。论文报告的数字用的就是这个默认口径。
>
> 注意影响方向并不单一：`check_touched_test` 是在 diff 的**所有行**（含上下文行）
> 上找 `@Test`，所以上下文调大时**分母也会变大**；同时 Layer 1 的前向扫描
> 只在 `@Test`/`@ParameterizedTest`/新 hunk 处停止，上下文调大后 hunk 合并，
> 扫描可能越过 PT 方法末尾进入下一个无注解的方法 —— 这会引入**假阳性**。
> 因此 PDAR 是升是降需要实测，不能先验断定。
>
> **Layer 1 是承重的**，所以这个局限不能先验当成无关。在全语料（106 个采纳者）
> 的逐提交表上把 Layer 1 整个拿掉：PDAR 中位数从 **14.52% 掉到 10.56%**
> （−3.96pp），逐项目差值中位 2.88pp、最大 36.55pp，30/106 个项目为 0。
> 受影响最大的都是 **JUnit5-only** 项目（Hudi +36.55、Commons-Statistics
> +35.71、Commons-Numbers +33.33）—— 因为 Layer 2 只认 JUnit 4，兜不住它们。
> 注意 Layer 1 只命中全部提交的 0.32%（5,561 / 174 万），命中率低但杠杆大。
>
> `--context N` 即为此而设：结果写到 `result_U{N}/`，与论文口径的 `result/` 并存：
> ```bash
> ./batch_pdar.sh --context 25 --projects sens_sample.txt
> python3 calculate_pdar.py --context 25
> ```
> 若只想量化上下文这一个变量，用 `pdar_context_sensitivity.py` 更省：
> 上下文只影响 Layer 1，而 Layer 2/3 的判定已存在于已发表逐提交表的
> `detection_layer` 列，可直接复用作基线、只重算 Layer 1，省掉全部
> `git show` 与 pickaxe。

> **各层的独有贡献**（`pdar_layer_attribution.py`，106 个采纳者的精确值，无需重跑 git）。
> 「拿掉某层」= 该层**首次命中**的提交不再计入分子，分母不变：
>
> | 拿掉 | PDAR 中位 | Δ中位 | 逐项目Δ中位 | 最大Δ | Δ=0 的项目 |
> |---|---|---|---|---|---|
> | — | 14.52% | — | | | |
> | `junit4_file` (L2) | 6.17% | **−8.35** | 6.42 | 49.50 | 25/106 |
> | `junit5_hunk` (L1) | 10.56% | **−3.96** | 2.88 | 36.55 | 30/106 |
> | `pickaxe` (L3) | 13.95% | **−0.57** | 0.00 | 30.00 | **73/106** |
>
> 命中率与杠杆完全不成比例：L1 只命中全部提交的 0.32%、L2 占 1.28%、L3 占 0.06%，
> 但 L2 承了 8 个百分点。L3 对 PDAR 几乎无影响（73/106 个项目完全不变），
> 它实际只对 `core_pdar` 关键 —— 所以上面那条 pickaxe 超时警告主要毁的是
> `core_pdar`，不是 PDAR。

> **最大的方法学隐患是粒度不对称，而它无法与真实现象干净分离。**
>
> | | 判定粒度 |
> |---|---|
> | Layer 1（JUnit 5） | **hunk 级** —— 必须在 `@ParameterizedTest` 附近几行内有 `+`/`-` |
> | Layer 2（JUnit 4） | **文件级** —— 文件含 `@RunWith(Parameterized` 即可，改该文件任何一处都算 |
>
> 而 L2 恰恰比 L1 更承重。后果可以测：有 JUnit4 PT 的项目（n=84）PDAR 中位
> 17.03%，只有 JUnit5 PT 的（n=20）只有 6.40%，Mann-Whitney **p=0.0010**、
> Cliff's δ=**+0.474**；OLS 控制 `files_java`、`total_tests`、提交数、测试开发者数后，
> `has_junit4_pt` 的系数稳定在 **+7.8 ~ +8.3pp**（p≈0.011）。
>
> **但这不能直接算作误差。** JUnit 4 的 `@RunWith(Parameterized.class)` 参数化的是
> **整个类**，所以「碰过这个类的人确实碰过参数化测试代码」在语义上成立；而 JUnit 5 的
> `@ParameterizedTest` 是**方法级**的，本就需要方法级精度。检测粒度的不对称恰好映射了
> 两个框架本身的不对称，两者纠缠，现有数据分不开。
>
> **要给出真正的 precision / recall，只能人工标注。** 没有 ground truth 时，任何
> 「误差率」都是无依据的。可行做法是按 `detection_layer` 分层抽样（`junit5_hunk` /
> `junit4_file` / `pickaxe` / 空 各若干），人工判断每个提交是否真的改动了参数化测试：
> 前三层给出各自的 precision，空值层给出 recall（即上下文局限的直接度量）。

> **两个与上下文无关、但影响口径的实现细节。**
> 1. **merge 提交被跳过。** `git diff-tree -p` 对 merge 提交默认不输出，
>    所以合并提交在逐提交检测里既不进分子也不进分母（实测 Fineract 前 213 个
>    提交中 89 个 diff 为空）。这本身说得过去 —— 合并不产生新的改动 ——
>    但 PDAR 的「提交」实际指**非合并提交**。
> 2. **pickaxe 在大仓库上会超时。** `git log --all -G` 要对每个提交做 diff，
>    实测 Fineract（约 1 万提交）两个 pattern 各 600s 全部 Timeout。超时时
>    脚本只打印 warning 并以**空集**继续，于是 Layer 3 静默失效、`is_core`
>    全为 0。重跑大仓库时必须检查这条 warning，否则会得到偏低的
>    PDAR 与全 0 的 core_pdar。

> **`pdar_repo_map.csv` 是仓库名的唯一来源。** 此前有两套互相冲突的来源：
> `projects.txt` 的解析用了 `url.rstrip('.git')` —— 这是 bug，`rstrip` 剥的是
> **字符集合** `{'.','g','i','t'}` 而非字面后缀，于是 `ambari`→`ambar`、
> `pig`→`p`、`poi`→`po`、`thrift`→`thrif`，42 个项目的名字被剥坏；
> `asf_domain_mapping.csv` 的 `matched_machine` 列则含明显错配
> （Commons-Chain / Commons-HttpClient / Commons-OGNL 三个不同项目全都指向
> `commons-weaver`）。该 bug 只影响「定位仓库」这一步，定位失败会直接退出、
> 不会去分析错的仓库，**已发表的数字未受污染**（115 个项目全有结果、无一为 0，
> 汇总步骤移植后逐行比对完全一致），但已修正。

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
