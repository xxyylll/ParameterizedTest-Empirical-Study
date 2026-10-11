# 完整 Method（RQ1 / RQ2.1 / RQ2.2 / RQ3.1）

写论文 Method 与 Threats to Validity 两节用。数据截止 2026-10-04。
RQ3.2 已另行总结，本文不含。

本文整合并取代以下分散文档的方法部分（细节仍以各专题文档为准）：
`STUDY_DESIGN_summary.md`、`rq2/rq2_2_structure/PAPER_NOTES_methodology.md`、
`RQ3_1_metrics_and_findings.md`、`RQ3_1_refinement_2026-09-29.md`、
`CRITERIA_construction_dependency.md`、`TOOLCHAIN_FIXES_2026-09.md`。

---

## 0. 总体设计

### 0.1 三层语料

研究采用**三层逐渐收窄**的语料，而非单一数据集。分层的依据是**分析成本**：

| 层 | 项目数 | 用于 | 解析深度 | 单项目成本 |
|---|---:|---|---|---|
| **L1 广度层** | **175** | RQ1 | 注解级语法扫描 | 秒级 |
| **L2 分布层** | **175**（其中 107 含 PT） | RQ2.1 | 同上 + 读取 source 注解内容 | 秒级 |
| **L3 深度层** | **46** | RQ2.2 / RQ3 | 完整 AAA 调用轨迹（JDT 绑定解析）+ CCFinderSW 克隆检测 | 小时级 |

L1/L2 只需判断注解是否存在、读取注解字面内容，不解析类型绑定，因此可覆盖整个 ASF Java 生态。
L3 需要为每个测试方法重建完整调用链（跨模块类型解析、helper 递归展开），
并对整个测试代码库做克隆检测，camel 一个项目的解析就耗时约 40 小时，因此只能在子集上做。

**三层的 N 不同是设计决策而非数据缺失**，论文里需要在 Method 开头就讲清楚。

### 0.2 数据快照一致性

L3 的全部分析（RQ2.2 / RQ3）基于**同一次 clone 的同一份快照**（外置盘 `apache-projects/`）。
项目的测试代码随时间变化，跨快照比较会引入无法控制的差异，因此所有深度分析共用一份快照。
RQ1 与 RQ2.1 也基于这份快照（`parser_result_ssk/`），共用 175 个项目的语料框架。

---

## 1. RQ1 — 参数化测试的采纳情况

### 1.1 工具

轻量级 parser（`analyzer.py` + `batch_parse_all_projects.sh`），扫描每个项目全部 Java 测试文件，
按**注解**识别：

| 类别 | 识别依据 |
|---|---|
| 普通测试 | `@Test` |
| JUnit5 参数化测试 | `@ParameterizedTest` |
| JUnit4 参数化测试 | `@RunWith(Parameterized.class)` |

只做语法层面识别，不解析类型绑定、不展开调用链。
产物 `parser_result_ssk/{project}_output.json` → 由 `rq1/build_merged_ssk.py` 汇总为 **`rq1/merged_data_219_ssk.csv`**（每项目一行）。
旧底表 `merged_data_218.csv` 的计数来自 2025-10-15 跑的另一批 parser 输出，那批输出后来被部分重跑覆盖、已无法复现，
因此 RQ1 统一切到 ssk 快照。切换后 174 个项目里 61 个计数有变，但没有一个项目的采纳状态翻转，CAR、采纳者数、PAI 中位数均不变。

### 1.2 语料构建

| 步骤 | 剩余 | 掉了 | 原因 |
|---|---:|---:|---|
| ① 候选清单 `apache_java_projects.txt` | **263** | — | ASF 的 Java 项目 |
| ② 成功 clone 到外置盘 | **243** | 20 | 仓库不存在 / 已改名 / clone 失败 |
| ③ 轻量 parser 产出轨迹 | **243** | 0 | 无损 |
| ④ 进入分析清单 `my_projects.txt` | **216** | 28 | 见下 |
| ⑤ 排除已退役项目（Apache Attic） | **176** | **40** | 见 ① |
| ⑥ 排除数据完整性有问题的项目 | **174** | 2 | 见 ② |
| ⑦ 补回第 ④ 步漏掉的 Parquet | **175** | +1 | 见下 |

> **注意计数单位。** `merged_data.csv` 有 **218 行但只有 216 个唯一项目**
> （jclouds 重复 3 行，且三行都是 retired）。所以「退役 42 个」是**行数**，
> 按项目算是 **40 个**。论文里应写「216 个项目中 40 个已退役」而不是「218 − 42」——
> 两种算法最终都得 174，但前者才与事实相符。

**第 ④ 步掉的 28 个**：24 个解析出 **0 个测试方法**（多为用 JUnit 3 继承式写法的老项目，
本文 parser 按 `@Test` 注解识别，自然为零）；另外 4 个有测试却未被选入，见「遗漏的四个项目」。
另外 Commons-HttpClient 在清单里却无独立 clone —— 它与 HttpComponents-Client 是同一仓库，
只 clone 了一次，这本身就是第 ⑥ 步排除它的佐证。

**① 排除 Attic 的依据**：退役项目的测试代码多年未动，其「不采纳 PT」反映的是停止维护而非技术选择。
数据支持这个处理 —— retired 的采纳率 **21.4%（9/42）**，active **61.4%（108/176）**，
相差 40 个百分点（χ²=20.17, p<0.0001）；但**一旦采纳，两者的使用强度无显著差异**
（Mann-Whitney U, p=0.66）。即 retired 只影响「要不要用」，不影响「用多少」，
把它们留在采纳率分析里会系统性压低结果。

**② 两个数据完整性问题**

- **Commons-HttpClient 与 HttpComponents-Client 数据完全相同**（total_tests=1800, pt_total=24,
  files_java=913）—— 同一仓库被计入两次（前者为旧名，后者为继任项目），保留其一
- **Lucene-Core 是子模块**：files_java=5,934 而 total_tests=1,193，项目级统计口径与其它项目不一致

**遗漏的四个项目（threat to validity）**

Parquet、Flume、Fluo、Fluo Recipes 被成功 clone、也解析出了测试，
但在第 ④ 步构建 `my_projects.txt` 时未被选入。四种可能的理由都被证据排除：

| 可能的理由 | 事实 |
|---|---|
| clone 失败 | ❌ 四个都完整在盘上（71–363 MB，带 `.git`） |
| 不是 Java 项目 | ❌ Java 文件占压倒性多数（874 / 565 / 293 / 96 个 `.java`） |
| 解析不到测试 | ❌ 2025-10 的旧 parser 产物里就有，测试数与今日完全一致 |
| 属于已退役项目 | ❌ 不在 `asf_domain.csv` 的 39 个 retired 之列 |

而且它们**同时出现在前一版清单（`projects_副本.txt`，2025-10-14）和后一版清单
（`projects.txt`，2025-10-27）中**，只在中间这份 `my_projects.txt`（2025-10-16）里缺失。
这与「有意排除」不相容，更像是手工整理清单时整段漏粘。

**影响量化**：四者合计 3,180 个测试方法、**205 个参数化测试，且全部是 JUnit 4 写法**
（parquet-mr 176、flume 29，fluo 与 fluo-recipes 各 0）。

- **RQ2.2 与 RQ3 完全不受影响** —— 这两个 RQ 只分析 JUnit 5 的参数化测试，
  而这四个项目一个 JUnit 5 PT 都没有
- **RQ2.1 仅影响 JUnit 4 一侧**，JUnit 5 内部的 source 分布一个数都不变
- **RQ1 的变化可忽略**，没有任何检验的方向或显著性改变（174 → 175，即补回 Parquet）：

| | 174 | 175（补回 Parquet） |
|---|---:|---:|
| CAR | 60.9% | 61.1% |
| Deep Adoption (≥5%) | 19.5% | 20.0% |
| PAI 中位（全部） | 0.281% | 0.282% |
| PAI 中位（采纳者） | 2.211% (n=106) | 2.221% (n=107) |
| PDAR 中位（v4） | 15.50% (n=106) | 15.62% (n=107) |
| 规模 × 采纳 | χ²=14.51, p=0.00071, V=0.289 | χ²=14.50, p=0.00071, V=0.288 |
| Large scale OR | 4.962 | 4.897 |
| Has JUnit5 OR | 5.814 | 5.461 |

**处理：补回 Parquet，其余 3 个不纳入。** Parquet 是活跃项目（ASF category `big-data`，取自 projects.apache.org），
它的首次提交年份与 PDAR 由全量 clone 得到，不存在混合口径的问题；PDAR 的第一阶段表截断到 2026-06-23，
与其余项目的批量 clone 时间对齐（见 `rq1/pdar/PDAR_METHOD.md` 第 5 节）。
其余 3 个按其状态不纳入：Flume 已转入 dormant，Fluo 与 Fluo Recipes 自 2018 年后无更新。

### 1.3 指标定义

**(a) 社区层面采纳率**

| 指标 | 定义 |
|---|---|
| **CAR**（Community Adoption Rate） | 至少含 1 个 PT 的项目占比 |
| **Deep Adoption Rate** | PT 占该项目测试总数 ≥ 5% 的项目占比 |

**(b) PAI**（Parameterized Adoption Intensity）= 项目内 `PT 数 / 测试方法总数`。

**(c) PDAR**（Parameterized-test Developer Adoption Ratio）
= `写过 PT 的开发者数 / 碰过测试代码的开发者数`，基于 git 提交历史逐 commit 判定。

PT 相关 commit 采用 **v4 判定**（`rq1/pdar/`，完整说明见 `rq1/pdar/PDAR_METHOD.md`），只看 `.java`：

1. **JUnit5（方法级）** —— 取 `-U0` diff，`-` 行对应父提交、`+` 行对应本提交的文件快照；
   用 tree-sitter 求出 `@ParameterizedTest` 方法及其**同文件**数据源（`@MethodSource` /
   `@FieldSource` 引用的成员、`@EnumSource` 的 enum、`@ArgumentsSource` 的类）的行区间，
   任一改动行落在区间内即命中（改动前后两侧都看）。纯重命名不算
2. **JUnit4（类级）** —— 同样按改动行判定，区间是 `@RunWith([value =] Parameterized)` 标注的类，
   扣除其中嵌套的独立测试类（带 `@RunWith` / `@Nested` 或含 `@Test` 方法）；`Enclosed` 外层里只算被参数化的嵌套类

`modifiedPT = 1 ∨ 2`；pickaxe（`git log -G`）不再进入分子（只会额外带入 Scala/Kotlin、文档、注释等）。
提交集合与分母沿用 v3 的逐提交表（2026-06 快照）。v3（hunk 邻近判定 + L2 的路径解析 bug 与过窄模式）
中位数为 14.52%，已被取代。

开发者以 email 小写去重。

**PDAR 的分母口径**：只在**采纳了 PT 的项目**上计算。未采纳项目的 `pt_participants = 0`、
PDAR 恒为 0，计入只会把中位数拉向 0 而不反映真实情况。
175 个项目中 107 个采纳了 PT，**这 107 个全部有 PDAR 数据，无缺失**。

### 1.4 统计方法与结果

**描述统计**

| 指标 | 值 |
|---|---|
| CAR | **107/175 = 61.1%** |
| Deep Adoption（≥5%） | 35/175 = 20.0% |
| PAI（全部 175）中位 / 均值 | **0.282%** / 3.240%（Q1–Q3 = 0–3.791%，max 60.03%） |
| PAI（采纳者 n=107）中位 / 均值 | **2.221%** / 5.300% |
| PDAR（n=107）中位 / 均值 | **15.62%** / 18.90%（v4；v3 为 14.52% / 18.05%，n=106） |

**核心发现：采纳普遍（61.1%）但使用极浅** —— 即便在采纳者中，PT 也仅占测试的 2.2%。

**影响因素**（全部在 175 个项目上计算，`rq1/adoption_factors.py`）

| 因素 | 检验 | 结果 |
|---|---|---|
| **项目规模**（files_java，固定切点 **625 / 1806**，左闭右开） | 卡方 + Cramér's V | 采纳率 44.1%(<625) / 60.0%(625–1805) / **77.3%(≥1806)**；χ²=14.50, df=2, **p=0.00071**, V=0.288 |
| 规模 × PAI | Kruskal-Wallis | 中位 PAI 0% / 0.194% / **0.978%**；H=7.08, **p=0.029** |
| **JUnit 版本** | Mann-Whitney U + Cliff's δ | 采纳率 JUnit4-only **38.3%**(n=47) vs JUnit5-only **72.2%**(n=72) vs Mixed 72.5%(n=51)；JUnit5-only vs JUnit4-only 的 **PAI**：U=2289, **p=7.7e-4**, **δ=0.353（medium）**（对采纳 0/1 做同一检验：U=2266, p=2.6e-4, δ=0.339） |
| 测试套件规模 × PAI | Spearman（log 变换） | **ρ=0.422**, p=6.0e-9 |
| 项目年龄（首次提交分四档） | Kruskal-Wallis | 不显著（H=3.32, p=0.345） |

**领域（category）的 logistic regression**（`rq1/category_logit.py`）：

1. 先对比 retired vs active 的采纳率与强度（见 1.2），确认 retired 是混淆因素，所以只用 active 项目
2. 只排除完全没有 category 的 6 个项目，**N = 169**
3. 按 **EPV 原则**（每变量至少 10–15 个事件）筛掉的是**变量**而不是项目：只给项目数 ≥ 20 的类别设 0/1 变量
   —— library(73) / big-data(40) / network-server(26)；其余类别（database 19、network-client 17、web-framework 13、xml 12 等）
   不设变量，项目留在模型里，与没有任何达标类别的项目一起构成参照组（41 个）

结果：Pseudo-R² = 0.0047，LLR p = 0.788；library OR = 0.863（p = 0.683）、big-data OR = 1.283（p = 0.558）、
network-server OR = 0.830（p = 0.685），**没有任何 category 显著**。

> 早先的版本把不属于 top-4 类别的项目整个踢出模型（样本 168 → 139），参照组因此变成「属于另外三类之一」，
> 并报告 big-data OR = 2.568、p = 0.019。该结果在当前数据上无法复现，口径本身也有误，已弃用。

**多元 logistic regression**（规模 + 是否已用 JUnit5 → 是否采纳 PT），N=175，Pseudo-R²=0.158，AIC=205.0：

| 变量 | OR | 95% CI | p |
|---|---:|---|---|
| Large scale (≥1806) | **4.897** | [2.123, 11.296] | 0.0002 *** |
| Has JUnit5 | **5.461** | [2.604, 11.452] | <0.0001 *** |
| Medium scale (625–1805) | 2.246 | [0.979, 5.150] | 0.056 |

**结论**：采纳 PT 最强的两个预测因子是**项目规模大**（OR=4.90）与**已在使用 JUnit5**（OR=5.46）；
年龄与领域（category 与 domain 两种口径）均无显著关联。

> ⚠️ **仓库里有一整套过时的 RQ1 产物，不要使用**：旧脚本 `rq1_build_and_analyze.py.DEPRECATED`
> 串联的 `merged_data_ssk.csv`（214 行，不同 clone、未做筛选）与
> `developer/result_v3_backup_20260602/pdar_summary.csv`（43 行）。
> 使用它们会得到 N=214 / CAR=54.2% / PDAR=20.0% 等**错误数字**。
> 论文口径一律以 **`final/rq1/`**（底表 `merged_data_219_ssk.csv`）+ **`rq1/pdar_summary_ssk.csv`（PDAR v4）** 为准。

---

## 2. RQ2.1 — parameter source 的总体分布

### 2.1 工具与语料

**沿用 RQ1 的同一个轻量 parser** —— source 类型（`@MethodSource` / `@ValueSource` 等）
写在注解上，语法层面即可读出，无需深度解析。

语料：**与 RQ1 同一套 175 个项目**，其中 **107 个含至少一个 PT**。
数据源：**`parser_result_ssk/`** —— 这是全部 243 个项目**同一时间 clone** 的快照，
与 RQ2.2 / RQ3 共用，保证跨 RQ 可比。

> ⚠️ 仓库里另有 `parser_result/`（287 个文件）和据其生成的 `rq2/source_types_summary.csv`。
> 那份快照的 clone 时间不一致，且**只统计了 JUnit5 的 source 类型、遗漏 JUnit4**，
> 用当前数据无法复现（存档记 `Unknown 284 / 5 个项目`，重跑为 `248 / 3 个项目`）。**不要使用。**

### 2.2 JUnit4 与 JUnit5 的分野

175 个项目共 **17,511 个参数化测试**：

| 写法 | PT 数 | 占比 | 跨项目 |
|---|---:|---:|---:|
| **JUnit4 `@RunWith(Parameterized)` + `@Parameters`** | **8,627** | **49.3%** | 42 |
| **JUnit5 十种 source 注解** | **8,884** | **50.7%** | 77 |

**近一半的参数化测试仍是 JUnit4 写法。** 这与 RQ1 的「已用 JUnit5 的项目更可能采纳 PT」
（OR=5.46）互补：采纳了 PT 不等于用的是 JUnit5 的 PT。
后续 RQ2.2 与 RQ3 只分析 JUnit5 部分（JUnit4 的参数供给机制完全不同，
`@Parameters` 是静态方法返回集合，没有 source 注解的概念，无法纳入同一分类体系）。

### 2.3 JUnit5 内部的 source 分布

分母为 8,884 个 JUnit5 PT；40 个测试挂了多个 source 注解，按各自 source 各计一次。

| Source | 数量 | 占 JUnit5 PT | 使用该 source 的项目占比 |
|---|---:|---:|---:|
| **MethodSource** | 5,598 | **63.0%** | 85.7% |
| **ValueSource** | 1,654 | **18.6%** | 76.6% |
| EnumSource | 881 | 9.9% | 42.9% |
| CsvSource | 390 | 4.4% | 45.5% |
| **Unknown**（自定义 source 注解） | 248 | 2.8% | 3.9% |
| CsvFileSource | 53 | 0.6% | 7.8% |
| FieldSource | 38 | 0.4% | 3.9% |
| ArgumentsSource | 32 | 0.4% | 10.4% |
| NullSource | 19 | 0.2% | 7.8% |
| EmptySource | 6 | 0.1% | 2.6% |
| NullAndEmptySource | 5 | 0.1% | 3.9% |

**两种 source 占 81.6%**：MethodSource（用代码生成参数）+ ValueSource（注解内写字面量）。
MethodSource 的主导地位是 RQ2.2 聚焦于它的直接理由。

### 2.4 Unknown 的成因：自定义 source 注解

248 个 `Unknown` **不是解析失败**，而是一类真实存在的用法 —— 开发者用
`@ArgumentsSource(XxxProvider.class)` 定义自己的**元注解**，然后在测试上直接使用该自定义注解。
parser 按十种标准 source 的注解名匹配，自然归不进去。

分布极度集中：

| 项目 | 数量 | 自定义注解 |
|---|---:|---|
| directory-studio | **246** | `@LdapServersSource` |
| causeway | 1 | `@EnumSources`（复数，自定义组合注解） |
| hudi | 1 | 仅 `@ParameterizedTest`，source 可能继承自父类 |

**246/248 来自单个项目。** 这说明 JUnit5 的扩展机制确实被使用，但极不普遍 ——
可作为一项次要发现写入，而非仅作为数据质量说明。

## 3. RQ2.2 — parameter source 的结构刻画

这是全研究人工投入最大的部分，流程是：
**人工打标 → 迭代定义判定口径 → 实现自动分类器 → 多轮抽样校验**。
口径不是预先设定的，而是在 review 中逐步收敛的。

### 3.1 人工打标的抽样设计

分层随机抽样（`generate_pt_stratified_sampling.py`），**Cochran 有限总体样本量公式**：

| 参数 | 取值 |
|---|---|
| 置信水平 | **95%**（z = 1.96） |
| 总体比例 p | 0.5（最保守取值） |
| 容许误差 | **± 5%** |
| 随机种子 | 42 |
| 抽样总体 | 9,619 个 JUnit5 PT，89 个项目 |
| 分层依据 | 项目 × parameter source 类型 |

样本量 **1,604 个 PT**，覆盖 **79 个项目**。按 source 构成：
MethodSource 665 / ValueSource 441 / EnumSource 214 / CsvSource 177 /
ArgumentsSource 32 / CsvFileSource 29。

### 3.2 深度层语料（46 个项目）

L3 从 47 个可完成完整 AAA 轨迹解析的项目起步，最终排除 hive，得 **46 个**。

**排除 hive 的依据**（不要表述为「parser 大面积失败」—— 不准确）：
hive 的**文件级覆盖良好**（10,108 个源码测试中生成 10,084 个轨迹，缺失仅 0.24%），
问题在**轨迹内容质量** —— 抽样 1,200 个 AAA JSON，**23.8% 的 `parsedStatementsSequence` 为空**。
根因是 hive 自身的 `4.2.0-SNAPSHOT` 模块产物未安装到本地 Maven 仓库，
JDT 无法解析跨模块类型绑定，编译单元整体降级。对比（同样抽样口径）：

| 项目 | 空轨迹比例 |
|---|---:|
| **hive** | **23.8%** |
| camel | 11.4% |
| hadoop | 0.4% |
| flink | 0.2% |
| commons-lang / druid | 0.0% |

决定性因素是收益：hive 的 10,228 个测试中仅 **25 个 PT**（MethodSource 14 / ValueSource 10 /
EnumSource 1），占全语料 8,370 个 PT 的 **0.3%**，修复成本（需完整构建 hive）与收益不成比例。

全语料 AAA 完整性：源码测试 210,537 个，缺失 2,849 个（**1.4%**）。

### 3.3 三个维度的判定口径

**分析单元**：一个 `@MethodSource` PT 引用的全部 provider（含抽象测试基类 + 多个子类各自的实现）
**池化为一行**。provider 为 JDK / 第三方方法时单列 `EXTERNAL_PROVIDER`，三维度 N/A。
完整规则见 `CRITERIA_construction_dependency.md`。

#### (a) Construction（Literal / Dynamic）

**判据**：provider 产出的参数集**是否在编译期完全确定**。多 provider 时只要有一个 Dynamic 则整体 Dynamic。

Literal 需同时满足两个条件：

1. **语句形态**：仅允许 (i) 局部变量声明且初始化表达式为字面量表达式；
   (ii) 对已声明的字面量局部容器的单条 `add/addAll/put/putAll/set/offer/push/append`；
   (iii) 简单赋值；(iv) 一条 `return`。出现 if / for / while / switch / try / throw / enhanced-for → Dynamic
2. **字面量表达式**（递归定义）：数字 / 字符串 / 文本块 / 布尔 / 字符 / `null` / `Foo.class`；
   字面量间的中缀运算；数组字面量；**常量引用**（全大写标识符、`Type.MEMBER` 形式的静态成员、
   本类 `static final` 且初始化为字面量的字段）；**值对象构造** `new T(字面量…)` 且无匿名体；
   **静态工厂装箱白名单**（`of/asList/arguments/named/entry/add/put/build/stream` 等，
   且接收者为类型名或无接收者）；对字面量局部容器的单层终结调用

一律判 Dynamic：接收者为对象的链式调用、白名单外的任何调用（含 `Date.from(...)` 这类
看似纯函数的静态工厂，保守处理）、helper 委托、方法引用、块体 lambda、三目、
非常量命名的字段/参数引用、带匿名体的 `new`、mock、IO。

> Construction 与 Cognitive Complexity 相互独立：`return helper()` 的 CC = 0，但 Construction = Dynamic。

#### (b) Dependency（L0–L4）

**判据**：从 provider 出发，沿 parameter-construction 相关的 **test-code** 依赖一路追溯至
production / JDK 边界，在走过的所有 test-code artifact 中取**离测试类最远**的等级。
production 代码不进等级，另以 `hits_production` 布尔列标记。

| 等级 | 名称 | 条件 |
|---|---|---|
| **L0** | Source Local | provider 在测试类自身内，且未调用任何 test-scope helper |
| **L1** | Enclosing-Class Helper | provider 或 helper 与测试类在**同一最外层类**内（含静态嵌套类、`@Nested` 内部类） |
| **L2** | Inheritance | provider 经继承解析到其它类，或 helper 声明在测试类/provider 类的**祖先**中（`extends` 链 / 接口，语法解析 ≤ 8 层） |
| **L3** | Package Helper | provider 或 helper 在同包的其它类中（经 `#` 全限定名或常量限定名**显式引用**） |
| **L4** | Cross-Package | provider 或 helper 在其它包中 |
| EXTERNAL | — | provider 为 JDK / 第三方方法，N/A |

#### (c) Structure

| 子指标 | 定义 |
|---|---|
| **Cognitive Complexity** | SonarSource 认知复杂度，**仅计 provider 方法体**，不递归进 helper |
| **max helper depth** | test-scope helper 调用链的最大深度 |
| **distinct helpers** | 去重后的 test-scope helper 个数 |
| **arity** | `n_params × n_sets`（每组几个参数 × 共几组） |

`n_sets` 为静态推断，结果分**四类**，三者性质完全不同，不可混为一谈：

| 状态 | 含义 |
|---|---|
| `EXACT` | 静态精确算出 |
| `RUNTIME_DEPENDENT` | 组数**原理上必须执行才知道** —— 测试本身的性质 |
| `STATIC_UNSUPPORTED` | 静态可定，但本文分析器未实现该规则 —— **工具局限** |
| `UNRESOLVED_SOURCE` | 无法取得待计数的代码（抽象 provider / 名字解析缺口 / 声明在项目外） |

已实现的计数规则：直接列举、枚举 `values()` 展开、固定次数循环与**嵌套循环乘积**、
`Stream.builder().add()`、保基数 wrapper（`map`/`peek`/`sorted`/`distinct`/`boxed`）、
明确可数的 `flatMap`、`static final` 常量作为循环边界、上游 arity 已知时的 `limit`/`skip`。

### 3.4 自动分类器

`java/ArtifactWalker.java`（JDT **纯语法**遍历 + 文件索引，**不依赖 binding**）驱动
`ConstructionDependencyClassifier`，配合 `build_helper_depth.py` / `build_dependency_v2.py`
消费 AAA 调用轨迹。

**已知近似**（无 binding 的代价）：实例变量上的调用按声明类型解析；同名重载按参数个数匹配；
无法解析的类型按 JDK / 第三方处理；遍历上限 400 个节点、helper 递归上限 6 层。

### 3.5 五轮抽样校验

校验是**迭代式**的：每轮人工 review 一批样本 → 发现口径或实现问题 → 修正 →
**只呈现本轮有变化的条目**供人工复核（而非重复 review 全样本）。
这使校验过程收敛而非穷举。完整记录见 `TOOLCHAIN_FIXES_2026-09.md`。

| 轮 | 样本 | 抽样方式 | 发现与改动 |
|---|---|---|---|
| **1 (pilot)** | **379** 个 MethodSource PT（31 项目） | 随机抽样，每项目设上限 24 条避免大项目主导 | 建立基线；暴露 parser 的第三方误判、子类 provider 池化、父类 provider 解析、匿名类局部方法等缺陷 |
| **2** | **81** 条 | 分层样本中落在已解析项目的 MethodSource PT | **8 个问题定稿口径**：Construction 口径 A、嵌套类→L1、方法引用上下文敏感、嵌套类 AAA 匹配、重载文件名碰撞、JDK provider 单列、同名 provider 查找顺序、`@Disabled` 纳入 |
| **3** | **25** 条变化 | 仅本轮有变化的条目 | Dependency L2 扩展至祖先类/接口；Construction A2 限制装箱白名单 |
| **4** | **59** 条变化 | 同上 | 口径升级为「**传递式 artifact 依赖** / **静态可确定性**」，新增 `ArtifactWalker.java`。dependency 分布大幅重排（L3: 25→45, L4: 27→53） |
| **5** | **42** 条 | 按计数规则分层、对高风险规则超额抽样（seed=42） | 专查 arity 的 `EXACT` 取值，**发现并修复 1 个真实缺陷**（见下） |

**第 5 轮发现的缺陷**：`Stream.of(x)` / `Arrays.asList(x)` 当 `x` 为数组时，
Java varargs 会将其**摊开**为 N 个元素，而原实现在无法确定 `x` 元素数时
**静默回退为「实参个数 = 1」**，产生一个看似合理的错误值。
修复后按声明类型（局部变量 / 字段 / test-scope 方法返回类型）判断实参是否为数组，
是数组则走摊开语义、数不出则如实报失败。影响 **5 行（占 EXACT 的 0.11%）**，
全部由 `EXACT/1` 改判为 `RUNTIME_DEPENDENT`；construction / dependency **零变化**。

**第 5 轮抽样的统计口径**：该抽样**按计数规则分层并对高风险规则刻意超额抽样**
（`limit/skip` 层 5 条全抽、嵌套循环 84 抽 6、「直接列举」3,813 仅抽 8），
**不能直接作为总体准确率**；按各层在总体中的真实占比加权后，总体错误率 **< 0.2%**。

### 3.6 产出规模

| provider | 行数 | 覆盖项目 |
|---|---:|---:|
| MethodSource | **5,508** | 45 |
| ValueSource | 1,537 | 39 |
| EnumSource | 843 | 29 |
| CsvSource | 366 | 26 |
| ArgumentsSource / FieldSource | 66 | 9 |
| CsvFileSource | 48 | 3 |
| Null / Empty 独立使用 | 2 | 2 |
| **合计** | **8,370** | |

质量：MethodSource 的 5,508 行中 **5,448 行（98.9%）三维度全部算出**；
non-OK 60 行主要为 helper 未匹配到 AAA 轨迹，集中在非标准测试布局的项目。

---

## 4. RQ3.1 — PT 与非 PT 测试的规模、复杂度与重复率

### 4.1 分析单元与对照组

**单元**：一个测试方法。**对照**：JUnit5 PT vs **JUnit5** non-PT。

非 PT 组需按 JUnit 版本筛选 —— 研究问题承诺的是 JUnit5 内部对比，
但未筛选时对照组混入了 JUnit4 与 TestNG。判定函数 `classify_junit_api()` 优先级：

1. 源码中出现全限定注解 `@org.junit.jupiter.*` → junit5；`@org.junit.Test` / `@org.junit.Ignore` → junit4
2. `isParameterized` 为真 → junit5（`@ParameterizedTest` 为 jupiter 独有）
3. 否则依据 `importedPackages`：仅含 `org.junit.jupiter.*` → junit5；
   仅含 `org.junit.Test|Assert|Before|After|Rule|runner|runners|experimental` → junit4
4. 两者皆含（迁移中的文件）→ 依据具体 import 的 `Test` 注解判定
5. 含 `org.testng` → testng

| 组 | 总数 | junit5 | junit4 | testng |
|---|---:|---:|---:|---:|
| PT | 8,299 | **8,299（100%）** | 0 | 0 |
| 非 PT | 191,138 | 170,834（89.4%） | **20,093（10.5%）** | 210 |

**无一条落入 mixed 或 unknown**。最终分析集合 **179,133 个测试**（PT 8,299 / 非 PT 170,834），46 个项目。

### 4.2 三个层次

| 层次 | 含义 |
|---|---|
| **self** | 测试方法自身的方法体 |
| **helper** | 它（递归）调用到的全部 **test-scope** 辅助方法之和 |
| **total** | self + helper |

**helper 的界定**（三条规则，是整套口径的关键）：

1. **来源于 AAA 调用轨迹**，非正则扫描源码。轨迹中每行是一次调用，带声明类全限定名
2. **只计 test-scope**。声明类位于 production、第三方库、JDK 的调用全部剔除。
   判定依据是该类源文件位于测试源根下，**包括非标准布局**：
   calcite `testkit/src/main/java`、accumulo `test/src/main/java`、
   iceberg `src/integration/java`、jmeter `src/testFixtures/java` 均计为测试代码；
   `src/jmh/java`（性能基准）两边都不计
3. **每个不同的 helper 只计一次**，不按调用次数重复累加。轨迹为递归展开，
   因此**间接调用的 helper（helper 的 helper）也在内**，同样去重

无法唯一定位的 helper（重名重载歧义、找不到声明）其指标按 0 计 —— 这使 helper 指标偏**低**，
为保守方向；失败清单另存 `*_report.csv`。

### 4.3 四组指标

LOC / CC / CCTR 共用**同一次 tree-sitter 解析**，保证内部一致。

**LOC** —— 节点跨度内被至少一个**非注释叶子 token** 触及的**不同源码行数**。
空行与纯注释行不计；方法上方 javadoc 不计（兄弟节点，不在声明节点跨度内）；
**注解行计入**（在声明节点自身跨度内）。该定义用于逼近 Understand 的 `CountLineCode`。

**CC（McCabe）** —— `1 + count(if / for / enhanced-for / while / do / catch / 三目 / 每个 case 标签)`。
**不计** `default`、不计 switch 语句本身、**不计 `&&` 与 `||`**。此口径曾用正则原型对照 Understand 校准。

**CCTR = N + A + M + T**（测试专用复杂度）

| 分量 | 计数规则 |
|---|---|
| **N**（控制流/嵌套） | 每个 if / for / while / do / switch / catch 计 `1 + 当前嵌套层数`（**嵌套越深权重越大**）；含 `&&`/`\|\|` 的二元表达式各计 1；带 break/continue/goto 的标签语句计 1；递归调用自身计 1 |
| **A**（断言） | 方法调用文本含 `assert` 或 `fail(` 计 1 |
| **M**（mock） | 方法调用文本含 `mock(` / `when(` / `verify(` 计 1 |
| **T**（测试注解） | `@Test` +1；**`@ParameterizedTest` +2**；`@BeforeEach` / `@AfterEach` 各 +1 |

**DUP%** —— CCFinderSW classwise 克隆检测，参数 `-t 50 -ccf`（最小克隆 token 数 50），
每项目一次，**只扫测试代码**，46 个项目同一套参数。

- **单位是行占比**（非 token 占比）：`dupPerc = 重复行数 / 总行数`
- **归因为连续覆盖**（非二元判定）：`dupLines` = 该方法**物理行**中被至少一个克隆片段覆盖的行数
- **跨文件重复双方各自计入**：A 与 B 互为克隆则各自记上，不是重复计数

### 4.4 聚合方式

LOC / CC / CCTR **逐分量直接相加**：

```
total_X = self_X + Σ helper_X
```

DUP% **先加后除**（不是各 helper 比率求平均 —— 那会让 2 行与 200 行的 helper 等权）：

```
dupLines(total)   = dupLines(self)   + Σ dupLines(helper_i)
totalLines(total) = totalLines(self) + Σ totalLines(helper_i)
dupPerc(total)    = dupLines(total) / totalLines(total)
```

### 4.5 统计方法

**每个项目各算一次** Mann-Whitney U 检验 + Cliff's delta 效应量，再对 46 个项目取分布
（而非合并全部测试做单次检验）。这样做是为避免大项目主导 —— 项目测试数从 231 到 23,021，
相差 100 倍。代价是小项目与大项目等权（见 Threats §5.5）。

Cliff's delta 阈值：|δ| < 0.147 negligible，< 0.33 small，< 0.474 medium，≥ 0.474 large。
显著性阈值 p < 0.05。

### 4.6 CCTR 的敏感性分析

CCTR 的 T 分量给 `@ParameterizedTest` 记 2 分而 `@Test` 记 1 分，
**每个 PT 在 T 分量上白得 1 分**，与代码复杂度无关。测试体中位 LOC 仅十余行、
self_cctr 中位数 3–4，这 1 分占比极大 —— 等于把分组变量直接加进了因变量。

实现上并行维护 `t_eq` 计数器（`@ParameterizedTest` 记 1 分，其余规则相同），
得 `cctr_eq = N + A + M + t_eq`。**原口径保留不动**，两套指标一次运行同时产出。

| 层次 | 原 CCTR delta | 显著项目 | 同权 CCTR* delta | 显著项目 |
|---|---:|---|---:|---|
| test | **0.23** | 34 正 / 2 负 | **−0.01** | **11 正 / 11 负** |
| helpers | 0.25 | 35 正 / 2 负 | 0.25 | 35 正 / 2 负 |
| total | 0.36 | 40 正 / 0 负 | **0.20** | 28 正 / 1 负 |

绝对中位数：PT self_cctr 4.0 → 同权 3.0；非 PT 两种口径下均为 3.0。

**test 层面「PT 的 CCTR 更高」完全来自计分规则，无任何真实复杂度差异。**
helper 层不受影响（helper 无测试注解）；total 层从 0.36 降至 0.20 但仍稳健。
**建议正文直接采用同权口径报告 CCTR**，原口径作为对照，说明 CCTR 的原始定义
不适用于 PT / 非 PT 的比较。

### 4.7 附加分析：source-DUP check

**动机**：主分析发现一处反转 —— helper 层是 PT 更重复（37/46 项目，中位 δ=+0.30），
total 层却是非 PT 更重复（中位 δ=−0.24）。假设是「参数化把重复从测试体转移到了参数构造代码」。

**做法**（`build_provider_dup_metrics.py`）：沿用与主 dup 分析**完全相同**的口径
（同一套 helper 解析、同一份克隆数据、同样 line-ratio、同样先加后除），
仅将 PT 的 test-scope helper 按 AAA 轨迹标签拆为两组：

- **provider** —— 标签为 `METHODSOURCE` / `FIELDSOURCE` 的方法
- **其余 helper** —— 该测试调用的其它 test-scope 辅助方法

**结果**（JUnit5 子集）

| 代码类别 | n | dupPerc 中位 | 均值 | 有重复的占比 |
|---|---:|---:|---:|---:|
| **PT 的 provider** | 5,420 | **0.500** | 0.483 | 61.0% |
| PT 的其余 helper | 6,375 | 0.049 | 0.206 | 56.9% |
| 非 PT 的 helper | 170,776 | **0.000** | 0.124 | 28.6% |

成对比较（Cliff's delta，p < 1e-300）：provider vs 其余 helper **+0.277**；
provider vs 非 PT helper **+0.422**。逐项目：**27 个项目 provider 显著更重复 / 7 反向 / 9 不显著**。

**结论：假设成立。** 参数化并未消除重复，而是将其**从测试体转移到了 parameter construction 代码中**。

---

## 5. Threats to Validity

### 5.1 CCTR 的 T 分量对 PT 有结构性偏置
见 §4.6。已通过同权口径的敏感性分析量化，test 层面效应完全消失。

### 5.2 CC 相加时基线累积
每个方法的 CC 均含基线 1，故 `total_cc` 含 `1 + helper 个数` 份基线。
调用 3 个 helper 的测试即便全为直线代码，`total_cc` 也是 4。
**这使 total_cc 部分地在度量「调用了多少 helper」而不仅是控制流复杂度。**

### 5.3 DUP% 与 LOC 的行定义不一致
DUP% 的分母为方法的**物理行跨度**（与 CCFinderSW 按行报告克隆的方式对齐），
LOC 为去除空行与注释后的行数。两者不相等，`total_dupPerc × total_loc ≠ total_dupLines`。
这是有意为之（各自与自身工具对齐），但若论文同时引用两个数需说明。

### 5.4 helper 解析失败按 0 计
使 helper 层指标系统性偏低（保守方向）。
另有 217 条轨迹含 unresolved 标签，其 helper depth / distinct helpers 是**下界而非精确值**，
结构分析时可做敏感性检验。

### 5.5 项目等权
每个项目贡献一个效应量、等权汇总，但项目测试数相差 100 倍（231 ~ 23,021）。
这是为避免大项目主导而做的选择，代价是小项目与大项目等权。
森林图中以点面积编码测试数，使读者可判断每个点的样本量。

### 5.6 RQ2.1 的 Unknown
248 个 JUnit5 PT（占 JUnit5 PT 的 2.8%）使用**自定义 source 注解**（经 `@ArgumentsSource` 元注解封装），
不属于十种标准 source，在分布统计中单列。其中 246 个来自单一项目 directory-studio 的
`@LdapServersSource`，因此该类别的占比高度依赖单个项目，不宜作一般化推断。

### 5.7 CCFinderSW 未在 JUnit5 筛选后重跑
克隆检测在**全部测试文件**上进行。JUnit5 筛选后，指标仅在 JUnit5 测试上统计，
但克隆检测的输入集合未变。因此一个 JUnit5 测试若与某 JUnit4 测试互为克隆，
该重复仍计入前者的 `dupLines`，尽管后者已被排除。

**不重跑的理由**：(i) 重复率是代码自身的属性，不因对方所用测试框架而改变；
(ii) 若排除 JUnit4 文件后重跑，测得的是「JUnit5 测试之间的重复」，属另一研究问题；
(iii) 代价为 46 个项目重跑 CCFinderSW，其中 hadoop 单项目需 16 GB 堆、数小时。

路径本身不构成威胁：CCFinderSW 扫描的是副本目录，克隆检测只看文件内容，
路径仅用于报告，解析时按路径标记还原回项目真实路径（hadoop 4,446 个文件还原零失败）。

### 5.8 hadoop 的克隆检测在另一台机器完成
本机（8 GB 内存）处理 hadoop 的 4,446 个测试文件反复 OOM，改在一台 Windows 机器上以 16 GB 堆完成。
**工具版本与参数完全相同**（CCFinderSW-1.0，`-l java -t 50 -ccf`），输入文件集为同一份。

### 5.9 JUnit5 筛选对单项目效应的影响
语料级结论稳健（12 个指标的 delta 变化全部 ≤ 0.02），但**单个项目可被彻底改写**。
典型例子 druid（88% 测试文件为 JUnit4，筛后非 PT 从 18,154 降至 3,704）：

| druid `total_dupPerc` | PT 中位 | 非 PT 中位 | Cliff's δ |
|---|---:|---:|---:|
| 全部非 PT | 0.115 | **0.447** | **−0.53**（Large non-PT） |
| 仅 JUnit5 | 0.115 | **0.104** | **+0.06**（几乎无差异） |

此前测得的「druid 非 PT 重复率极高」，实为**老代码的重复率**，与参数化无关。

### 5.10 ArtifactWalker 无 binding 的近似
见 §3.4。实例变量按声明类型解析、重载按参数个数匹配、未知类型按第三方处理。
已通过五轮抽样校验（§3.5），加权总体错误率 < 0.2%。

### 5.11 arity 分析的排除口径
arity 分析基于 **EXACT + RUNTIME_DEPENDENT = 5,367 行**，排除
`STATIC_UNSUPPORTED` 86 + `UNRESOLVED_SOURCE` 42 + 上游失败 13 = **141 行（2.6%）**。

**仅在 arity 一节排除，不从整个 RQ2.2 删除这些行。** 原因：这 141 行中 status=OK 的 127 条
**全部是 Dynamic、无一 Literal** —— 数不出组数正是因为构造逻辑是动态的。
若全局删除，等于按「分析难度」筛选样本，而难度与结论变量强相关，
construction 的 Dynamic 占比会从 62.7% 变为 61.8%。虽仅 0.9 个百分点，但属**系统性偏倚**。
仅在 arity 排除则无此问题，因为该节的命题本身就是「能否静态确定」。

由此：「可静态确定组数的 PT 占比」= 4,450 / 5,367 = **82.9%**；
若将 86 条 `STATIC_UNSUPPORTED` 人工补齐后重算为 **83.2%**，
差 0.3 个百分点且方向为**低估**，不利于本文结论，故不构成夸大。
分布类统计（均值/中位数/p90）本就只能在 EXACT 上计算，排除与否完全不影响。
