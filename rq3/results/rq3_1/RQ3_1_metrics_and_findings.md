# RQ3.1：PT 与非 PT 测试的规模、复杂度与重复率

组会讨论用。第 1–3 节是计算口径（每个指标怎么算、怎么相加），第 4 节是结果与发现，第 5 节是已知局限。

语料：**46 个 Apache Java 项目**（47 减 hive，排除理由见 `PAPER_NOTES_methodology.md`）。
单位：**一个测试方法**，共 **199,437 个**（PT 8,299 / 非 PT 191,138）。
数据文件：`rq3/results/rq3_1/test_metrics_all_46projects_v2.csv.gz`（原 `Complexity_Analysis/test_metrics_all_44projects.csv`）（文件名里的 44 是历史遗留，实际 46 个项目）。

---

## 1. 分析单元与三个层次

每个测试方法算出四组指标，每组分三个层次：

| 层次 | 含义 |
|---|---|
| **self** | 测试方法自己的方法体 |
| **helper** | 它（递归）调用到的全部 **test-scope** 辅助方法之和 |
| **total** | self + helper |

**helper 的界定是这套口径里最关键的一步**，三条规则：

1. **来源于 AAA 调用轨迹，不是正则扫源码。** 每个测试的 `parsedStatementsSequence`（JDT 解析出的调用序列）里每一行是一次调用，带声明类的全限定名。
2. **只算 test-scope。** 声明类落在 production 代码、第三方库、JDK 里的调用**全部剔除**，只保留测试代码内部的辅助方法。判定依据是该类的源文件位于测试源根下 —— 包括非标准布局（calcite 的 `testkit/src/main/java`、accumulo 的 `test/src/main/java`、iceberg 的 `src/integration/java`、jmeter 的 `src/testFixtures/java` 都算测试代码；`src/jmh/java` 两边都不算）。
3. **每个不同的 helper 只计一次**，不按调用次数重复累加。同一个 helper 在测试里被调 5 次，只贡献一份。轨迹是递归展开的，所以**间接调用的 helper（helper 的 helper）也在内**，同样去重。

无法唯一定位的 helper（重名重载歧义、找不到声明）记录在 `test_metrics_all_44projects_report.csv` 里，其指标按 0 计 —— 这会让 helper 指标偏**低**，是保守方向。

---

## 2. LOC / CC / CCTR 怎么算

三个指标共用**同一次 tree-sitter 解析**，保证内部一致。

### LOC
节点跨度内被至少一个**非注释叶子 token** 触到的**不同源码行数**。

- 空行、纯注释行不计（没有被计数 token 触到）
- 方法上方的 javadoc 不计（它是兄弟节点，不在声明节点的跨度内）
- **注解行计入**（`@Test`、`@ParameterizedTest` 在声明节点自己的跨度内）

这个定义是为了逼近 Understand 的 `CountLineCode`。

### CC（McCabe）
```
1 + count(if / for / enhanced-for / while / do / catch / 三目运算符 / 每个 case 标签)
```
**不计** `default`、不计 switch 语句本身、**不计 `&&` 和 `||`**。这套口径此前用正则原型对着 Understand 的输出校准过。

### CCTR = N + A + M + T
测试专用的复杂度指标，四个分量：

| 分量 | 计什么 |
|---|---|
| **N**（控制流 / 嵌套） | 每个 if / for / while / do / switch / catch 计 `1 + 当前嵌套层数`（**嵌套越深权重越大**）；含 `&&`/`\|\|` 的二元表达式各计 1；带 break/continue/goto 的标签语句计 1；递归调用自身计 1 |
| **A**（断言） | 方法调用文本里含 `assert` 或 `fail(` 的计 1 |
| **M**（mock） | 方法调用文本里含 `mock(` / `when(` / `verify(` 的计 1 |
| **T**（测试注解） | `@Test` +1；**`@ParameterizedTest` +2**；`@BeforeEach` / `@AfterEach` 各 +1 |

**⚠️ T 分量对 PT 有结构性偏置**：`@ParameterizedTest` 记 2 分而 `@Test` 记 1 分，等于每个 PT 白得 1 分。self 层面 CCTR 的中位 delta 是 0.22，而这 1 分的固定加成在测试体普遍很短的情况下不可忽略。**组会上值得提出来讨论要不要改成同权**，或者在正文里明确声明这一点。（helper 层面不受影响 —— helper 没有测试注解。）

### 相加方式
`self` 和每个 helper 各自算出一份 (loc, cc, cctr)，然后**逐分量直接相加**：

```
total_loc  = self_loc  + Σ helper_loc
total_cc   = self_cc   + Σ helper_cc
total_cctr = self_cctr + Σ helper_cctr
```

注意 CC 这样相加的语义：每个方法的 CC 都含一个基线 1，所以 `total_cc` 里含有 `1 + helper 个数` 份基线。调用 3 个 helper 的测试，即便所有方法体都是直线代码，`total_cc` 也是 4。**这使得 total_cc 部分地在度量「调了多少 helper」而不只是「控制流有多复杂」**，解读时要留意。

---

## 3. 重复率（DUP%）怎么算

工具：**CCFinderSW** classwise 克隆检测，参数 `-t 50 -ccf`（最小克隆 token 数 50），**只扫 `src/test/java`**，每个项目一次，46 个项目同一套参数。

- **单位是行占比，不是 token 占比**：`dupPerc = 重复行数 / 总行数`
- **归因是连续覆盖，不是二元判定**：对某个方法，`dupLines` = 它自己的**物理行**中被至少一个克隆片段覆盖的行数
- **跨文件重复双方各自计入**：测试 A 与测试 B 的代码互为克隆，则 A 和 B 各自都记上这部分重复。这不是重复计数 —— 双方确实各有那么一部分是重复的
- **聚合是先加后除，不是取平均**：
  ```
  dupLines(total)   = dupLines(self)   + Σ dupLines(helper_i)
  totalLines(total) = totalLines(self) + Σ totalLines(helper_i)
  dupPerc(total)    = dupLines(total) / totalLines(total)
  ```
  helper 层小计同理。**不是各 helper 的 dupPerc 求平均** —— 那样会让一个 2 行的 helper 和一个 200 行的 helper 等权。

**⚠️ 一处口径不一致**：DUP% 的分母用的是方法的**物理行跨度**（与 CCFinderSW 按行报告克隆的方式对齐），而 LOC 指标用的是**去掉空行和注释**后的行数。两者不相等，所以 `total_dupPerc × total_loc ≠ total_dupLines`。这是有意为之（各自与自己的工具对齐），但论文里若同时引用两个数要说明。

**hadoop 的克隆检测在另一台 Windows 机器上跑**（本机 8 GB 内存反复 OOM），工具版本与参数完全相同，输入文件集是同一份。

---

## 4. 结果

### 4.1 总体（total 层次中位数）

| 指标 | PT (n=8,299) | 非 PT (n=191,138) |
|---|---:|---:|
| LOC | **58** | 21 |
| CC | **8** | 2 |
| CCTR | **12** | 5 |
| DUP% | 0.37 | **0.57** |

### 4.2 逐项目效应（Mann-Whitney U + Cliff's delta，46 个项目各算一次）

正号 = PT 更高。`*` 表示 p < 0.05。

| 指标 | PT 显著更高 | 非 PT 显著更高 | 不显著 | delta 中位数 | delta 范围 |
|---|---:|---:|---:|---:|---|
| LOC (test) | 27 | 2 | **17** | 0.15 | [−0.31, 0.84] |
| CC (test) | 25 | 3 | **18** | 0.10 | [−0.29, 0.50] |
| CCTR (test) | 33 | 2 | 11 | 0.22 | [−0.53, 0.83] |
| DUP% (test) | 8 | 24 | 14 | −0.09 | [−0.74, 0.84] |
| LOC (helpers) | **42** | 0 | 4 | **0.48** | [−0.02, 0.94] |
| CC (helpers) | **42** | 1 | 3 | **0.44** | [−0.16, 0.94] |
| CCTR (helpers) | 34 | 2 | 10 | 0.25 | [−0.17, 0.97] |
| **DUP% (helpers)** | **37** | 2 | 7 | **+0.30** | [−0.15, 0.78] |
| LOC (total) | **41** | 0 | 5 | **0.50** | [0.06, 0.92] |
| CC (total) | **42** | 1 | 3 | **0.45** | [−0.13, 0.92] |
| CCTR (total) | **40** | 0 | 6 | 0.36 | [−0.04, 0.91] |
| **DUP% (total)** | 4 | **28** | 14 | **−0.24** | [−0.66, 0.21] |

### 4.3 三个发现

**① 差异主要来自 helper，不是测试体本身。**
测试自身层面效应很弱：LOC 只有 27/46 个项目显著、17 个不显著，中位 delta 0.15（negligible–small）；CC 更弱（25/46 显著，中位 0.10）。但 helper 层面 42/46 显著、中位 delta 0.48（接近 large）。
也就是说「PT 更复杂」这个结论的来源，**不是 PT 的测试方法写得更长更绕，而是它拖着更多、更重的辅助代码**（provider 方法、数据构造器、fixture）。这与 RQ2.2 的结果吻合：62.7% 的 MethodSource PT 是 Dynamic construction，37.7% 依赖 L1–L4 的 test-scope helper。

**② 重复率在两个层次方向相反。**
total 层面是非 PT 更重复（28/46 显著，中位 −0.24），但 **helper 层面是 PT 更重复（37/46 显著，中位 +0.30）**。
一个自洽的解释：PT 的测试体本身因为参数化而消除了重复（这正是参数化的目的，所以 total 层面 PT 更低），但**支撑它的 provider 和数据构造代码彼此之间高度相似** —— 一个项目里几十个 provider 都在写 `Stream.of(Arguments.of(...), ...)` 这类样板。参数化把重复从测试体**转移**到了 helper 层，而不是消除。
这个反转是目前最值得写的一点，因为它对「参数化能减少重复」这个通常的假设给出了更细的答案。

**③ 效应在项目间高度一致（helper/total 层）。**
LOC (total) 46 个项目里 41 个显著为正、**0 个显著为负**，delta 范围 [0.06, 0.92] 全为正。CC (total) 同理。这说明不是被少数几个大项目带的。相比之下 test 层面的 delta 范围跨过零（如 CCTR (test) [−0.53, 0.83]），一致性差得多。

---

## 5. 已知局限（Threats to Validity）

1. **CCTR 的 T 分量对 PT 有 +1 的结构性偏置**（`@ParameterizedTest` 记 2 分 vs `@Test` 记 1 分）。只影响 self 和 total，不影响 helper。
2. **CC 相加时基线累积**：`total_cc` 含 `1 + helper 个数` 份基线，部分地在度量 helper 数量。
3. **helper 解析失败按 0 计**，使 helper 指标偏低（保守方向）。失败清单在 `*_report.csv`。
4. **DUP% 与 LOC 的行定义不同**（物理行 vs 去注释行），两者不可直接换算。
5. **每个项目一个效应量、等权汇总**，但项目测试数从 231 到 23,021 相差 100 倍。用逐项目 delta 的分布（而非合并全部测试）是为了避免大项目主导，但代价是小项目与大项目等权。
6. **AAA 轨迹的完整性**：全语料缺失 1.4%；含 unresolved 标签的轨迹其 helper 指标是**下界**。
7. **PT 的判定基于注解静态扫描**，与轨迹质量无关，不受上述影响。

---

## 6. 配套图

| 文件 | 用途 |
|---|---|
| `rq3_forest.png` / `.pdf` | **建议作正文主图**。12 行（4 指标 × 3 层次），x 轴为 Cliff's delta，每个项目一个点，点大小按测试数。方向、程度、一致性、显著性四样都在一张图上，且用位置而非颜色编码量值 |
| `rq3_heatmap_portrait.png` / `.pdf` | **建议作附录**。46 行（项目）× 12 列（指标）竖版，保留逐项目身份，便于回答「是不是某个项目带的」 |

热力图用颜色编码量值，颜色是量化比较里最弱的编码；森林图用位置，且能显示项目间的离散程度。两张图互补：正文回答「效应多大、多一致」，附录回答「具体是哪些项目」。
