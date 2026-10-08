# RQ3.1 口径修订与新增分析（2026-09-29）

组会讨论用。三处修订 + 一项新分析，每一项都给出「原来是什么 / 改了哪里 / 结果变了多少」。
基线口径见 `RQ3_1_metrics_and_findings.md`。

**旧结果全部保留**，新结果一律另起文件名，可直接并排对比：

| | 旧（基线） | 新 |
|---|---|---|
| 合并数据 | `test_metrics_all_44projects.csv` | `test_metrics_all_46projects_v2.csv` |
| 森林图 | `rq3_forest.png` | `rq3_forest_junit5.png` / `rq3_forest_junit5_cctreq.png` |
| 竖版热力图 | `rq3_heatmap_portrait.png` | `rq3_heatmap_portrait_junit5.png` / `..._cctreq.png` |

---

## 1. JUnit5 对照组筛选

### 原来的问题
研究问题承诺的是 **JUnit5 PT vs JUnit5 non-PT**，但实现里 `category = 'pt' if isParameterized else 'nonpt'` —— 非 PT 是「**所有**非参数化测试」，JUnit4 和 TestNG 全混在对照组里。

### 改了哪里
`build_test_metrics_unified.py` 新增 `classify_junit_api(imports, source, is_pt)` 和 `junit_api` 列。判定优先级：

1. 源码里出现全限定注解 `@org.junit.jupiter.*` → junit5；`@org.junit.Test` / `@org.junit.Ignore` → junit4
2. `isParameterized` 为真 → junit5（`@ParameterizedTest` 只存在于 JUnit5）
3. 否则看 `importedPackages`：只含 `org.junit.jupiter.*` → junit5；只含 `org.junit.Test|Assert|Before|After|Rule|runner|runners|experimental` → junit4
4. 两者都含（迁移中的文件）→ 看具体 import 了哪个 `Test` 注解；都 import 了则记 `mixed`
5. 含 `org.testng` → testng；其余 → unknown

### 结果

| 组 | 总数 | junit5 | junit4 | testng |
|---|---:|---:|---:|---:|
| PT | 8,299 | **8,299（100%）** | 0 | 0 |
| 非 PT | 191,138 | 170,834（89.4%） | **20,093（10.5%）** | 210 |

**没有一条落进 `mixed` 或 `unknown`**，分类是干净的。PT 组天然全是 JUnit5，问题只在对照组。
筛选后 199,437 → **179,133** 行（−10.2%）。

### 对结论的影响：语料级几乎没有，但单个项目可以被彻底改写

46 个项目取中位数后，**12 个指标的 delta 变化全部 ≤ 0.02**，显著项目数最多变 1 个。
这本身是个有价值的稳健性结果：主结论不是「把 JUnit4 混进对照组」造成的假象。

但 **druid 是个必须写进论文的反例**（它 88% 的测试文件是 JUnit4，筛后非 PT 从 18,154 降到 3,704）：

| druid `total_dupPerc` | PT 中位 | 非 PT 中位 | Cliff's delta |
|---|---:|---:|---:|
| 全部非 PT | 0.115 | **0.447** | **−0.53**（Large non-PT） |
| 仅 JUnit5 | 0.115 | **0.104** | **+0.06**（几乎无差异） |

druid 的 JUnit4 老测试重复率 0.447，它自己的 JUnit5 测试只有 0.104。
**此前测到的「druid 非 PT 重复率极高」，测的其实是老代码的重复率，与参数化无关。**

其余项目的 delta 变化：jena（保留 74%）最大 +0.12，其它 44 个项目全部 < 0.05。

---

## 2. CCTR 的 T 分量偏置

### 原来的问题
CCTR = N + A + M + T，其中 T 是测试注解分量，原始计分是：

```
@Test            +1
@ParameterizedTest  +2      ← 问题在这
@BeforeEach / @AfterEach  +1
```

**每个 PT 在 T 分量上白得 1 分**，而这 1 分与代码复杂度无关，纯粹来自注解类型。
测试体中位 LOC 只有十几行、self_cctr 中位数才 3–4，这 1 分占比极大。
用它做 PT vs 非 PT 的比较，等于把「是不是 PT」这个分组变量直接加进了因变量。

### 改了哪里
`SnippetScorer` 里并行维护一个 `t_eq` 计数器，**`@ParameterizedTest` 记 1 分而非 2 分**，其余规则完全相同：

```python
if '@Test' in text:
    self.t += 1;  self.t_eq += 1
elif '@ParameterizedTest' in text:
    self.t += 2;  self.t_eq += 1     # 敏感性版本：与 @Test 同权
elif '@BeforeEach' in text or '@AfterEach' in text:
    self.t += 1;  self.t_eq += 1
```

于是 `cctr_eq = N + A + M + t_eq`。**原口径 `cctr` 保留不动**，两个指标一起算、一起落盘
（`self_cctr_eq` / `helper_cctr_eq_sum` / `total_cctr_eq`），一次运行产出两套，不需要跑两遍。

### 结果：test 层面的效应完全消失

| 层次 | 原 CCTR delta | 显著项目 | 同权 CCTR* delta | 显著项目 |
|---|---:|---|---:|---|
| test | **0.23** | 34 正 / 2 负 | **−0.01** | **11 正 / 11 负** |
| helpers | 0.25 | 35 正 / 2 负 | 0.25 | 35 正 / 2 负 |
| total | 0.36 | 40 正 / 0 负 | **0.20** | 28 正 / 1 负 |

绝对中位数印证了原因：

| | 原 CCTR | 同权 CCTR* |
|---|---:|---:|
| PT self | 4.0 | **3.0** |
| 非 PT self | 3.0 | 3.0 |

**「PT 的测试体 CCTR 更高」这个结论 100% 来自计分规则，没有任何真实复杂度差异。**
同权后 11 正 / 11 负，完全对称。

- **helper 层完全不受影响**（helper 方法没有测试注解），delta 稳定在 0.25
- **total 层从 0.36 降到 0.20**，但仍然稳健（28 正 / 1 负），说明 total 层的效应是真的，只是被 T 分量放大了

### 建议
不要把这当成单纯的敏感性分析。**test 层面的 CCTR 结论在原口径下是站不住的**，正文应当直接用同权口径报 CCTR，把原口径作为对照，说明「CCTR 的原始定义不能直接用于 PT / 非 PT 的比较」。这反而是一处方法学贡献。

---

## 3. Source-DUP check：重复确实藏在 parameter construction 里

### 动机
基线分析发现一个反转：**helper 层是 PT 更重复**（37/46 项目，中位 delta +0.30），
但 **total 层是非 PT 更重复**（中位 −0.24）。推测是「参数化把重复从测试体转移到了参数构造代码」。
这一节把 PT 的 helper 聚合拆开，直接验证。

### 做法
`build_provider_dup_metrics.py`。沿用与主 dup 分析**完全相同**的口径（同一套 helper 解析、
同一份 CCFinderSW 克隆数据、同样的 line-ratio、同样先加后除），只是把 PT 的 test-scope helper
按 AAA 轨迹标签分成两组：

- **provider** —— 标签为 `METHODSOURCE` / `FIELDSOURCE` 的方法，即 `@MethodSource` / `@FieldSource` 指向的参数供给方法
- **其余 helper** —— 该测试调用的其它 test-scope 辅助方法

### 结果（JUnit5 子集）

| 代码类别 | n | dupPerc 中位 | 均值 | 有重复的占比 |
|---|---:|---:|---:|---:|
| **PT 的 provider** | 5,420 | **0.500** | 0.483 | **61.0%** |
| PT 的其余 helper | 6,375 | 0.049 | 0.206 | 56.9% |
| 非 PT 的 helper | 170,776 | **0.000** | 0.124 | 28.6% |
| PT 的测试体本身 | 8,289 | 0.862 | 0.665 | 83.4% |

成对比较（Cliff's delta，全部 p < 1e-300）：

| 对比 | delta |
|---|---:|
| provider vs PT 的其余 helper | **+0.277** |
| provider vs 非 PT 的 helper | **+0.422** |
| provider vs PT 测试体 | −0.220 |

逐项目看：**provider 重复率显著高于其余 helper 的有 27 个项目，反向 7 个，不显著 9 个。**

### 结论
**推测成立。** PT 的 helper 层重复率之所以高，主要由 provider 贡献 —— provider 的重复率中位数
是 0.500，而同一批测试的其余 helper 只有 0.049，非 PT 的 helper 更是 0.000。

也就是说，参数化并没有消除重复，而是把它**从测试体转移到了 parameter construction 代码里**：
一个项目里几十个 provider 都在写 `Stream.of(Arguments.of(...), ...)` 这类样板，彼此高度相似。
这给「参数化能减少重复」这个通常假设提供了一个更细的答案。

---

## 4. CCFinderSW 未重跑的说明（threat to validity）

克隆检测是在**全部测试文件**上做的（每个项目一次，`-t 50 -ccf`）。JUnit5 筛选之后，
指标只在 JUnit5 测试上统计，但克隆检测的输入集合没有变。

于是会出现：一个 JUnit5 测试与某个 JUnit4 测试互为克隆，这份重复仍然计入前者的 `dupLines`，
尽管后者已被排除出分析集合。

**我们选择不重跑**，理由：

1. **重复率是代码自身的属性。** 这段代码确实和别的代码重复了，不因为对方用什么测试框架而改变。
2. 若排除 JUnit4 文件后重跑，测到的是「**JUnit5 测试之间**的重复」，那是另一个研究问题。
3. 代价：46 个项目重跑 CCFinderSW，其中 hadoop 单个就需要 16 GB 堆、数小时（本机 8 GB 内存曾反复 OOM，最终是在另一台 Windows 机器上完成的）。

此外，路径本身不构成威胁：CCFinderSW 扫描的是 `temp_test_files/` 下的副本，
克隆检测只看文件内容，路径仅用于报告，解析时按 `temp_test_files` 串还原回项目真实路径
（hadoop 4,446 个文件还原零失败）。

---

## 5. 四张图的口径对照

| 文件 | 对照组 | CCTR 口径 |
|---|---|---|
| `rq3_forest.png`（旧，保留） | 全部非 PT | 原始 |
| `rq3_forest_junit5.png` | 仅 JUnit5 | 原始 |
| `rq3_forest_junit5_cctreq.png` | 仅 JUnit5 | **同权（标为 CCTR\*）** |
| 三个 `rq3_heatmap_portrait*` | 同上 | 同上 |

生成方式（同一套脚本参数化，避免代码分叉）：

```bash
python plot_rq3_forest.py --csv test_metrics_all_46projects_v2.csv --junit5 --cctr eq  --out rq3_forest_junit5_cctreq
python plot_rq3_heatmap_portrait.py --csv test_metrics_all_46projects_v2.csv --junit5 --cctr orig --out rq3_heatmap_portrait_junit5
```
