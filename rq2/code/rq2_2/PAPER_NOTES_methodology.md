# 论文方法学说明（RQ2.2 / RQ3）

面向：写论文时需要在 Methodology / Threats to Validity 里如实交代的口径与已知局限。
数据截止 2026-09-28，对应 `rq2/results/rq2_2/rq22_*_all.csv` 与 `rq3/results/rq3_1/test_metrics_all_46projects_v2.csv.gz`。

---

## 1. 语料：46 个 Apache Java 项目（47 减 hive）

RQ2.2 和 RQ3 用**同一套** 46 个项目 —— 两边脚本读同一个排除名单 `corpus/rq3_excluded.txt`（原 `rq2/rq2_2_structure/excluded_projects.txt`），
所以跨 RQ 的对照是成立的。

### 为什么排除 hive

**不要写成「parser 大面积失败」**，这个说法不准确，也容易被追问。准确的表述是：

hive 的**文件级覆盖是好的** —— 10,108 个源码测试里生成了 10,084 个 AAA 轨迹（缺失 0.24%）。
问题出在**轨迹内容质量**：抽样 1,200 个 AAA JSON，其中 **23.8% 的 `parsedStatementsSequence` 是空的**。

根因：hive 自己的 `4.2.0-SNAPSHOT` 模块 jar 没有安装到本地 Maven 仓库，JDT 解析不出跨模块的类型
binding，编译单元整体降级，调用序列就是空的。要修必须先在本地把整个 hive `mvn install` 一遍。

与其它项目对比（同样抽样口径）：

| 项目 | 空轨迹比例 |
|---|---:|
| **hive** | **23.8%** |
| camel | 11.4% |
| hadoop | 0.4% |
| flink | 0.2% |
| commons-lang / druid | 0.0% |

决定性因素是**收益**：hive 的 10,228 个测试方法里只有 **25 个是参数化测试**
（MethodSource 14、ValueSource 10、EnumSource 1），占全语料 8,370 个 PT 的 **0.3%**。
修复成本（全量构建 hive）与收益完全不成比例，因此排除。

**建议的论文表述**：
> We excluded Apache Hive from the corpus. Although 99.8% of its test methods were successfully
> located, 23.8% of the resulting traces were empty because Hive's own SNAPSHOT module artifacts
> were not resolvable from the local repository, degrading JDT type resolution. Hive contributes
> only 25 parameterized tests (0.3% of the corpus), so we excluded it rather than rebuild it.

### storm 与 camel 已包含
两者早期也有问题，但都已修复并纳入：storm 是测试目录识别规则的问题，camel 是 Maven archetype
模板目录拖垮解析速度。camel 重跑后测试类覆盖 99.58%，122 个含 PT 的类、329 个 PT 方法**零缺失**。
camel 整体空轨迹率 11.4% 偏高，但**它的 162 行 MethodSource 结果全部是 OK 状态**，PT 部分未受影响。

---

## 2. MethodSource 结果表各列含义

文件：`full/rq22_methodsource_all.csv`，**5,508 行**，每行 = 一个 `@MethodSource` 参数化测试。
一个测试引用的全部 provider（含抽象基类 + 多个子类各自的 provider）**池化成一行**。

### 2.1 分析状态 `status`

| 值 | 行数 | 含义 |
|---|---:|---|
| `OK` | 5,448 (98.9%) | 三个维度都算出来了 |
| `hd:*` | 47 | helper depth 没匹配上 AAA 轨迹 |
| `cc:*` | 6 | 找不到测试文件或 provider |
| `EXTERNAL_PROVIDER` | 7 | provider 是 JDK/第三方方法（如 `java.util.TimeZone#getAvailableIDs`），三个维度均 N/A |

下面的分布统计都在 `status == OK` 的 5,448 行上。

### 2.2 Construction（Literal / Dynamic）

判定：provider 产出的参数集**在编译期是否完全确定**。完整规则见 `CRITERIA_construction_dependency.md`。
多个 provider 只要有一个 Dynamic，整体 Dynamic。

| | 行数 | 占比 |
|---|---:|---:|
| Dynamic | 3,416 | 62.7% |
| Literal | 2,032 | 37.3% |

注意：**Construction 与 Cognitive Complexity 相互独立**。`return helper()` 的 CC = 0，但 Construction = Dynamic。

### 2.3 Dependency（L0–L4）

判定：从 provider 出发，沿 parameter-construction 相关的 **test-code** 依赖一路追到 production/JDK 边界，
在走过的所有 test-code artifact 里取**离测试类最远**的等级。production 代码不进等级，另用 `hits_production` 标记。

| 等级 | 名称 | 行数 | 占比 |
|---|---|---:|---:|
| L0 | Source Local | 3,395 | 62.3% |
| L1 | Enclosing-Class Helper | 365 | 6.7% |
| L2 | Inheritance | 503 | 9.2% |
| L3 | Package Helper | 510 | 9.4% |
| L4 | Cross-Package | 675 | 12.4% |

`hits_production`：True 2,380（43.7%）/ False 3,068（56.3%）。

### 2.4 Structure

- `cognitive_complexity` —— SonarSource 认知复杂度，**只算 provider 方法体本身，不含 helper**
- `max_helper_depth_test` / `distinct_helpers_test` —— test-scope helper 的最大深度与去重个数
- `max_helper_depth_prod` / `distinct_helpers_prod` —— production 侧同上
- `n_params` × `n_sets` —— arity，即「每组几个参数 × 一共几组」

`n_params`：均值 1.90、中位数 1、最大 15。

### 2.5 `n_sets_status`：四分口径（**这一列最需要在论文里解释**）

`n_sets`（参数组数）是静态推断的，四种结局的**性质完全不同**，不能混为一谈：

| 状态 | 行数 | 占比 | 含义 |
|---|---:|---:|---|
| `EXACT` | 4,450 | 80.8% | 静态精确算出，`n_sets` 有值 |
| `RUNTIME_DEPENDENT` | 917 | 16.6% | **组数原理上必须执行才知道** —— 测试本身的性质 |
| `STATIC_UNSUPPORTED` | 86 | 1.6% | **静态可定，但本文的分析器没实现该规则** —— 工具局限 |
| `UNRESOLVED_SOURCE` | 42 | 0.8% | 拿不到要数的那段代码 |
| （空） | 13 | 0.2% | 上游分析就失败了（含 7 条 EXTERNAL_PROVIDER） |

具体失败原因记在 `n_sets_fail_reason` 列。

**RUNTIME_DEPENDENT（917）主要成因**：`control-flow:*` 279（if / try 分支决定塞几组）、
`field-static-block:*` 156（静态初始化块里往集合 add）、`for-bound-nonconst:*` 82（循环上界是运行期的 `size()`）、
`forEach-lambda-logic` 71、`container-mutated-in:*` 61、`stream-op:filter` 53（过滤掉多少不确定）、`api-call` 43。

**STATIC_UNSUPPORTED（86）主要成因**：`for-shape` 31（for 循环写法超出支持的形状，如多个初始化器/更新器）、
`anonymous-body:*` 18（双花括号初始化 `new ArrayList<>(){{ add(a); add(b); }}`）、`for-updater:*` 15
（`n*=2`、部分 `i++` 形式）、`values-of-non-enum` 11、`new-object:Builder` 7。这些换更强的分析器或人工都能数出来。

**UNRESOLVED_SOURCE（42）主要成因**：`name:*` 25（裸标识符在局部变量、本类及父类字段、静态导入里都找不到声明 ——
本文分析器是纯语法遍历、不带 JDT binding，这是覆盖缺口）、`abstract-provider:*` 13（provider 是抽象方法没有方法体，
真实数据由各子类提供，**组数本就不是单一值**）、外部声明 4（引用的枚举/helper/字段声明在项目外，如 zookeeper 用
netty 的 `SslProvider.values()`）。

#### EXACT 的分布（4,450 行）
均值 **13.24** 组、中位数 **3** 组、p90 **14** 组、最大 **960** 组、最小 1 组。

#### 已实现的计数规则
直接列举、枚举 `values()` 展开、固定次数循环与**嵌套循环乘积**、`Stream.builder().add()`、
保基数的 wrapper（`map` / `peek` / `sorted` / `distinct` / `boxed`）、明确可数的 `flatMap`、
`static final` 常量作为循环边界、上游 arity 已知时的 `limit` / `skip`。

---

## 3. arity 一节的排除口径（**需要在论文里明确写出来**）

arity 的分析基于 **EXACT + RUNTIME_DEPENDENT = 5,367 行**，其中
`STATIC_UNSUPPORTED` 86 + `UNRESOLVED_SOURCE` 42 + 上游失败 13 = **141 行（2.6%）因分析器局限排除**。

**只在 arity 这一节排除，不从整个 RQ2.2 里删行。** 理由是实测出来的：这 141 行里 status=OK 的 127 条
**全部是 Dynamic，没有一条 Literal** —— 数不出组数正是因为构造逻辑是动态的。若全局删除，等于按「分析难度」
筛样本，而难度与结论变量强相关，construction 的 Dynamic 占比会从 62.7% 变成 61.8%。虽然只有 0.9 个百分点，
但这是**系统性偏倚**而非噪声。只在 arity 排除就没有这个问题，因为 arity 这一节的命题本身就是「能否静态确定」。

于是：
- 「可静态确定组数的 PT 占比」= 4,450 / 5,367 = **82.9%**
- 若把那 86 条 STATIC_UNSUPPORTED 人工补齐再算 = **83.2%**，差 0.3 个百分点，方向是**低估**不是高估

分布类统计（均值/中位数/p90）本来就只能在 EXACT 上算，排不排除这 141 行**完全不影响**。

---

## 4. RQ3 口径

规模：**199,437 个测试方法，46 个项目**（PT 8,299 / non-PT 191,138），四组指标**无缺失**。

单位：一个测试方法。指标 **LOC / CC（McCabe）/ CCTR（N+A+M+T）/ Duplication**，
每个指标分 **self（测试方法自身）/ helper（它调用的 test-scope helper 之和）/ total** 三个层次。
重复率用 CCFinderSW classwise 克隆检测，line-ratio 口径（重复行数 ÷ 总行数），参数 `-t 50 -ccf`，只扫测试代码。

### 需要声明的两点

**(a) 非标准测试布局按 test-scope 归类。** 有些项目把测试基础设施放在 `src/main/java` 下
（calcite `testkit/`、accumulo `test/`）或独立 source set（iceberg `src/integration/java`、jmeter `src/testFixtures/java`）。
这些**计入 test scope**，否则它们的 helper 会被误判成 production，helper 指标会系统性偏低。
规则见 `build_test_metrics_unified.py` 的 `TEST_INFRA_SEGMENTS` / `TEST_INFRA_SOURCESETS`。
`src/jmh/java`（性能基准）两边都不算。

整体结果（total 层次的中位数，供正文对照）：

| 指标 | PT (n=8,299) | non-PT (n=191,138) |
|---|---:|---:|
| LOC | 58 | 21 |
| CC (McCabe) | 8 | 2 |
| CCTR | 12 | 5 |
| Duplication | 0.37 | 0.57 |

### 需要声明的两点（续）

**(b) hadoop 的克隆检测在另一台机器上跑。** CCFinderSW 处理 hadoop 的 4,446 个测试文件在本机
（8 GB 内存）反复 OOM，改在一台 Windows 机器上以 16 GB 堆完成。**工具版本与参数完全相同**
（CCFinderSW-1.0，`-l java -t 50 -ccf`），输入文件集也是同一份。结果 4,446 个文件条目、398 万条克隆记录，
路径还原零失败。这一点如实写进去即可，不影响可比性。

---

## 5. 其它需要交代的细节

- **PT 识别**与 AAA 轨迹生成是两套独立产物。PT 识别是基于注解的静态扫描（`parser_result_ssk/`），
  不依赖 binding 解析，因此不受上面那些轨迹质量问题影响。
- **`@Disabled` 的测试计入**。理由：研究对象是测试代码的写法，当前是否执行无关。
- **子类 provider 池化**：抽象测试基类 + 多个子类各自实现 provider 的情况，池化成一行，
  construction 取「任一 Dynamic 则 Dynamic」，dependency 取各 provider 的最大等级。
- **Cognitive Complexity 只算 provider 方法体**，不递归进 helper。helper 的复杂度由
  `max_helper_depth` / `distinct_helpers` 两列单独刻画。
- **全语料 AAA 完整性**：源码测试 210,537 个，缺失 2,849 个（**1.4%**）。camel 单独是 0.4%。
- **`traversal_may_be_incomplete` 列**：标记轨迹里含 unresolved 标签的行（5,451 条 OK 结果里 217 条）。
  这些行的 helper depth / distinct helpers 是**下界而非精确值**，做 structure 分析时可考虑敏感性检验。

---

## 6. 结果校验

### EXACT 取值的抽样校验（已完成第一轮）

`full/exact_arity_sample.md` 的 42 条已人工核对完毕，**发现并修复 1 个真实缺陷**：

`ArtifactWalker` 在处理 `Stream.of(x)` / `Arrays.asList(x)` 这类单实参静态工厂时，若数不出 `x` 的元素数，
会静默回退成「实参个数 = 1」。但当 `x` 是**数组**时 Java 的 varargs 会把它摊开成 N 个元素，
所以正确结果应是数组长度，或在长度未知时如实报失败。修复后按声明类型（局部变量 / 字段 / test-scope
方法返回类型）判断实参是否为数组，是数组则走摊开语义、数不出来就失败，不再回退到 1。

影响面：全语料 5 行（占 EXACT 的 0.11%），全部由 `EXACT/1` 改判为 `RUNTIME_DEPENDENT`
（pdfbox `TestRendering.render` 1 条、commons-imaging `ByteSourceDataTest` 4 条）。
construction / dependency **零变化**。ArgumentsSource/FieldSource 走同一分析器，重算后零变化。

遗留：那 4 条 commons-imaging 的真实答案是 5（`return new byte[][]{...}` 五个元素），静态可定，
但其 helper 方法体内有边界非常量的 `for` 循环（用于填充字节数组、与返回的数组无关），
当前实现会因此整体判失败。要修需改「迭代次数未知但循环体不触碰被计数容器时跳过该循环」的规则，
涉及全部 233 条含循环的 provider，为 4 行改动回归风险过大，故保留在保守的一侧。

**抽样的统计口径**：该抽样是**按计数规则分层、对高风险规则刻意超额抽样**的
（`limit/skip` 层 5 条全抽、嵌套循环 84 抽 6、「直接列举」3,813 只抽 8），
**不能直接当作总体准确率**；要报总体准确率须按各层在总体中的真实占比加权。
按此加权，42 条中唯一的错误来自 `limit/skip` 层（总体仅 5 条，占 0.1%），加权后的总体错误率 < 0.2%。

## 7. 尚未完成

- 合并全部 source 的 n_sets 分布图（按 source 上色）。
