# PDAR v4 —— 方法、验证与结果

> 本文是论文 PDAR 数字的唯一方法说明。论文报告的 PDAR 自 v4 起全部来自本目录的
> 两阶段流水线；v3 的数字只作对照保留在 `pdar_v3_published.csv` 与 `pdar_summary_ssk.csv` 的 `pdar_v3` 列。

**一句话**：一个提交「改过参数化测试」，当且仅当它的某个改动行落在某个参数化测试的行区间内 ——
JUnit 5 是 `@ParameterizedTest` 方法及其在同一文件里引用的数据源，JUnit 4 是 `@RunWith(Parameterized)`
标注的类（扣除其中嵌套的独立测试类）。只看 `.java`，改动前后两侧都看。107 个采纳者上 PDAR 中位数
**15.62%**（v3 为 14.52%，n=106）。

---

## 1. 指标定义

**PDAR = 改过 PT 的开发者数 / 改过测试代码的开发者数 × 100（%）**

- 是**开发者比例**，不是提交比例。两个集合都按 author email 去重（去空白、转小写），
  没有 email 的提交丢弃（174 万个提交里共 59 个）。
- 分母用「碰过测试代码的人」而非「所有提交者」，回答的是「在写测试的人里，有多少人写过 PT」，
  不被只改生产代码的贡献者稀释。
- 只在 **107 个采纳了 PT 的项目**上计算（未采纳项目的 PDAR 恒为 0，计入只会把中位数拉向 0）。

**分母 `touched_test`**（与 v3 相同，未改动）：提交的 diff 里有任一文件路径含 `src/test/`、
`/test/`、`/tests/`，或文件名形如 `*Test.java` / `*Tests.java` / `*TestCase.java` / `Test*.java`，
或 diff 的任一行含 `@Test`、`import org.junit`、`import org.testng`。

（`pdar_summary_ssk.csv` 里另有 `core_pdar` 列 —— 分子换成新增或删除过 PT 注解的开发者，由 `.java`
的 ± 行文本判定。论文不报告它，只作记录。）

---

## 2. 为什么从 v3 换到 v4

v3 的分子由三层逐层回退判定：L1（JUnit 5，diff 文本上的注解邻近）、L2（JUnit 4，文件级）、
L3（pickaxe，`git log -G`）。重新检查后，三层各有问题。

**L1：在 diff 文本上找注解附近的 `+`/`-`**，能看到多少周围代码完全由 git 的上下文行数（默认 3 行）决定。

| 问题 | 方向 | 例子 |
|---|---|---|
| PT 方法内部、离注解超过 3 行的改动不在同一个 hunk 里 | 漏判 | 改一个长 PT 方法的断言 |
| 注解**前一行**有改动就算命中，不管那行是什么 | 误判 | 在 PT 上方新增一个普通 `@Test`，其末尾空行贴着注解 |
| 不识别重命名，移动文件被当成整文件删除 + 新增 | 误判 | 测试类挪到另一个模块，只改了 `package` 一行 |
| 注解只是文本匹配 | 误判 | 注释里写着 `@ParameterizedTest` |
| 不区分文件类型 | 口径不一致 | Kotlin / Scala 测试里的 `@ParameterizedTest` 也被算进来 |

把上下文调大（例如 `-U25`）不能解决问题：它让分母也跟着变（`touched_test` 在含上下文的
所有行上找 `@Test`），让前向扫描越过 PT 方法末尾引入新的误判，而且取多大都是任意的。

**L2：粒度太粗，且有两个实现 bug。**

- **文件级。** 文件里任何位置出现 `@RunWith(Parameterized`，这个文件的任何改动都算 —— 包括
  只改 import / package / license 头、`@RunWith(Enclosed.class)` 外层里**未被参数化**的嵌套测试类、
  参数化类里嵌套的另一个独立测试类、同一文件里的其他顶层类，甚至 `@RunWith(Parameterized.class)`
  只出现在注释里的文件。而 L1 是方法级的，两框架的判定粒度不对称。
- **路径解析错误。** 从 `diff --git a/<路径> b/<路径>` 里取文件名用的是正则 `b/(.+\.java)$`，它匹配
  行内**第一个** `b/`。路径中只要有以 `b` 结尾的目录（`iotdb/`、`db/`、`lib/`、`web/`……），第一个 `b/`
  就落在 a/ 路径中间，取出一段无效路径，`git show` 报错（Windows 上是 "Filename too long"），
  函数返回空，L2 不命中。IoTDB 29,145 个提交里 L2 命中数为 0 就是这个原因。
- **注解模式太窄。** `@RunWith\s*\(\s*Parameterized` 匹配不到 `@RunWith(value = Parameterized.class)`
  与全限定名写法。Commons-OGNL、Commons-RNG、Cayenne、Commons-Digester 全用前一种写法。
- 另外只看改动**后**的版本：删除 `@RunWith` 的提交不算，与 JUnit 5「删除一个 PT 方法算改动」不对称。

**L3：pickaxe 不限文件类型，且在大仓库上会超时。** 它会命中 Scala/Kotlin 文件、文档、生成的 HTML、
注释，以及重命名识别失效时被当成「新建」的文件；v3 那一轮 Hudi 因超时 `is_core` 全为 0。
在 v3 里 L3 还在替 L2 的两个 bug 兜底 —— 那些项目里只有恰好增删了 `@RunWith` 行的人才被认出来。

**口径一致性**：论文的 PT 计数（PAI、CAR、RQ2/RQ3）来自 JavaParser，只认 `.java`；
PDAR 的分子若混入 Kotlin/Scala 的 PT，就与论文其余部分的「PT」不是同一个东西。

---

## 3. v4 方法

### 3.1 两阶段结构

```
第一阶段  pdar_v4_commit_table.py  逐提交表：提交集合、作者、touched_test
          （= v3 的逐提交检测，原样保留；它的 L1/L2/L3 判定在 v4 中只作对照）
             │   result_v3/{project}_commits.csv   ← 论文快照（2026-06）
             ▼
第二阶段  pdar_v4_method_level.py  完整重算分子：L1（JUnit 5，方法级）、L2（JUnit 4，类级），并归因、自检
             │   result_v4/{project}_method_commits.csv + _method_summary.json
             ▼
汇总      calculate_pdar_v4.py     → rq1/pdar_summary_ssk.csv（论文口径） + result_v4/pdar_v4_summary.csv
```

**分工**：提交集合、分母、作者去重取自第一阶段的同一张表，不改动；分子由第二阶段完整重算。
第一阶段的表同时固定了快照：第二阶段在新 clone 上运行，但只判定表里出现过的提交，快照之后的新
提交一律忽略。

### 3.2 判定定义

一个被判定提交（非 merge、非根提交）的

```
modifiedPT = L1 ∨ L2
```

两层用**同一个判定方式**：取 `-U0` diff，`-` 行的行号属于父提交里的文件，`+` 行的行号属于本提交里的
文件；对两侧快照分别求出「参数化测试区间」，任一改动行落在对应一侧的某个区间内即命中。区间由
`pt_spans.py` 用 tree-sitter 解析得到。

**L1（JUnit 5）的区间**：

- **PT 方法**：带 `@ParameterizedTest`（或全限定名 `@org.junit.jupiter.params.ParameterizedTest`）
  的方法声明，从它的第一个注解/修饰符到方法体右花括号。方法前的 Javadoc / 注释不算。
- **加上同文件里被 source 注解显式引用的东西**：

  | 注解 | 纳入 | 缺省时 |
  |---|---|---|
  | `@MethodSource("m")` | 同文件里名为 m 的方法（含全部重载） | 与测试方法同名的方法 |
  | `@FieldSource("f")` | 同文件里名为 f 的字段 | 与测试方法同名的字段 |
  | `@EnumSource(E.class)` | 同文件里的 enum E | 第一个形参的类型 |
  | `@ArgumentsSource(X.class)` | 同文件里的类 X | — |

  `"Cls#m"` / `"pkg.Cls#m"` 只在 Cls 的简单名于本文件内声明过时解析，否则记为跨文件引用、不纳入。
  production 代码里的 enum、外部 provider 类因此被自然排除，不需要单独写例外。只解析一层。

**L2（JUnit 4）的区间**：

- 被 `@RunWith(...Parameterized...)` 标注的**类**，从它的注解到右花括号。模式为
  `@RunWith\s*\(\s*(value\s*=\s*)?(包名.)*Parameterized`，覆盖 `value =` 与全限定名写法，仍是前缀匹配
  （与 v3 一致，`ParameterizedRobolectricTestRunner` 之类也算）。标注必须是真正的注解节点，注释里的不算。
- **扣除**其中嵌套的**独立测试类**：自己带 `@RunWith` / `@Nested`，或直接含 `@Test` 方法的嵌套类型
  —— 它们是另外的测试类，Parameterized runner 不会参数化地运行它们。
- **保留**不含 `@Test` 的嵌套辅助类型（参数 enum、数据持有类等）—— JUnit 4 参数化的单位是整个类，
  类里的一切（除另一个测试类外）都属于它。
- 嵌套在 `@RunWith(Enclosed.class)` 等外层里的参数化类，只算它自己那一段。

```java
@RunWith(Enclosed.class)
public class BarTest {
    @RunWith(Parameterized.class)
    public static class WithParams { ... }   // ← L2 区间
    public static class Plain {
        @Test public void x() { ... }        // ← 不在区间内
    }
}
```

**L3 不再进入分子。** 定义上，`.java` 里 PT 注解的任何增删都已被覆盖：`@ParameterizedTest` 行在 PT 方法
区间内（L1），`@RunWith` 行在参数化类区间内（L2；删除时落在改动前一侧）。L3 还能额外带进来的只有本文
定义下不该算的东西。实证见 4.4。

### 3.3 设计决策及理由

| 决策 | 理由 |
|---|---|
| **两框架用同一个判定方式（改动行 ∩ 区间）** | 消除 v3 的粒度不对称；JUnit 5 的单位是方法，JUnit 4 的单位是类，区间各自对应其参数化单位 |
| **JUnit 5：「同文件」作为数据源的边界** | 不需要跨文件符号解析就能确定性判定的最大范围。provider 也是参数化测试的一部分：改了它，测试的输入就变了 |
| **JUnit 4：嵌套辅助类型算，嵌套测试类不算** | 参数化的单位是整个类，类里没被用到的辅助方法本来就算，嵌套辅助类型同理；不做「是否被用到」的引用分析。嵌套测试类由各自的 runner 运行，不是参数化测试 |
| **只算 `.java`** | 与论文的 PT 计数（JavaParser）一致 |
| **两侧检查** | 删除一个 PT 方法、删除 `@RunWith(Parameterized)` 都算改动 |
| **纯重命名 / 移动文件不算** | PT 的内容没变。开启 `-M` 重命名识别；带修改的重命名只看真正改动的行 |
| **类外与方法外的注释、import、package、license 头不算** | 不是参数化测试本身，改它不改变测试行为 |
| **数据源只解析一层** | provider 再调用的辅助方法不追；否则范围会无界扩张 |
| **JUnit 5 数据源在整个文件内按名字找** | 比 JUnit 实际的查找范围（测试类及其父类）略宽；对同文件内的嵌套类是保守的超集 |
| **merge 与根提交不判定** | 与分母一致：第一阶段用 `git diff-tree -p`，对二者默认无输出，所以它们的 `touched_test` 恒为 0。根提交多为仓库迁入（如 NetBeans 的 "Initial donation"），作者并非那些测试的写作者 |
| **主口径用「含数据源」，「只算 PT 方法」作敏感性分析** | 两者都报告；差异见 5.3 |

### 3.4 实现细节

**快照截断**：只判定第一阶段表里出现过的提交。表里有、本地 clone 里找不到的提交（上游改写过
历史的分支）保留第一阶段的 L1/L2 原值，计入 `missing_in_repo`。全语料共 4,123 / 1,740,092 个（0.24%）。

**只改了非 `.java` 文件、但 v3 判为 L1 命中的提交**（Kotlin/Scala 测试）：L1 = L2 = 0。全语料 128 个。

**解析出错时回退**：tree-sitter 是容错解析器，遇到不认识的语法会产出带 ERROR 节点的树。
含 `Parameterized` 文本的文件快照共解析 71,236 个，其中 19 个出错：含 JUnit 5 PT 的出错快照涉及 7 个
提交，这些提交的 L1 取 `L1_v4 ∨ L1_v3`（保守）；含 JUnit 4 标注的 12 个出错快照，L2 区间退回整个文件。

**读快照的过滤（纯性能优化）**：一个文件快照要含 PT（或 `@RunWith(...Parameterized`），其内容必然
曾以 `+` 行进入某个路径。因此按拓扑序（父先于子，`--reverse --topo-order`）流式读 diff，分别维护
「曾出现过 ParameterizedTest」与「曾出现过 Parameterized」的路径集合（含重命名传递），只对这些路径
或本次 diff 本身提到它们的文件读快照。`--fullscan` 关掉过滤、对每个改动文件都读，并逐提交比对 L1
与 L2 —— 见 4.2。

**`--full-history` 是必需的**：带路径过滤（`-- '*.java'`）时 `git log` 默认做历史简化，merge 若与
某个父提交在这些路径上相同，就只沿那一侧走，另一侧分支的提交会被整个跳过。验证阶段在
Commons-IO 上实测漏掉 3 个提交，被自检发现后修正；有专门的回归测试（4.1）。

**取 diff 的命令**：
```
git -c core.quotepath=false -c log.showRoot=true log --all --full-history --reverse --topo-order \
    -p -U0 -M --full-index --no-ext-diff --no-textconv --format=%x00%H %P -- '*.java'
```
快照用常驻的 `git cat-file --batch` 按 blob sha 读取，并按 sha 缓存解析结果。

---

## 4. 验证

没有人工标注的 ground truth，所以「准不准」被拆成两个可以检验的问题：
**(a) 判定的定义是否合理**（第 3 节，逐条给出理由）；**(b) 实现是否忠实于定义**。
(b) 用以下证据回答。

### 4.1 端到端单元测试（`tests/test_pdar_v4.py`，24 个，全部通过）

在临时仓库里按场景逐个提交，每个场景的期望结果都是确定的。「第一阶段表」不是手写的，而是用
`pdar_v4_commit_table.py` 里**原样的**函数对同一仓库跑出来的，所以同时检验了第二阶段与第一阶段
口径的衔接，也复现了第一阶段的 bug。

| 场景 | v3 | v4 期望 |
|---|---|---|
| PT 方法内部、离注解很远的改动 | L1 漏 | L1 命中 |
| 路径含空格的文件里同样的改动 | L1 漏 | L1 命中 |
| 改 PT 后面紧邻的 helper 方法 | L1 误判 | 不命中，归因 `overrun_forward` |
| 改同文件的 `@MethodSource` provider | L1 漏 | 仅「含数据源」口径命中 |
| 改同文件、被 `@EnumSource` 缺省引用的 enum | L1 漏 | 仅「含数据源」口径命中 |
| 改 production 里的 enum（`@EnumSource(Prod.class)`） | — | 不命中，记跨文件引用 |
| 注释里出现 `@ParameterizedTest` | L1 误判 | 不命中，归因 `pt_mention_not_method` |
| 改 PT 上方的 Javadoc | L1 误判 | 不命中，归因 `overrun_prev` |
| 新增 / 删除整个 PT 方法 | L1 命中 | L1 命中（删除走父提交一侧） |
| 纯重命名 PT 文件 | L1 误判 | 不命中，归因 `rename` |
| 只改 Kotlin 测试里的 PT；改 Kotlin PT + 生产 `.java` | L1 误判 | 不命中，归因 `non_java_file` |
| 修改 JUnit 4 参数化类内部 | L2 命中 | L2 命中 |
| ……路径含 `db/` | **L2 漏**（路径 bug） | L2 命中 |
| ……类用 `@RunWith(value = Parameterized.class)` | **L2 漏**（模式太窄） | L2 命中 |
| 删除 `@RunWith(Parameterized.class)` 行 | L2 漏（只看改动后） | L2 命中（改动前一侧） |
| `Enclosed` 外层里，改未参数化的嵌套测试类 | L2 误判（文件级） | 不命中 |
| `Enclosed` 外层里，改被参数化的嵌套类 | L2 命中 | L2 命中 |
| 参数化类里，改嵌套的独立测试类（含 `@Test`） | L2 误判（文件级） | 不命中 |
| 参数化类里，改嵌套的辅助类（无 `@Test`） | L2 命中 | L2 命中 |
| 参数化类文件，只改 import | L2 误判（文件级） | 不命中 |
| 纯重命名 JUnit 4 参数化类 | — | 不命中 |
| side 分支改 PT、main cherry-pick、合并后删分支 | — | 命中（`--full-history` 回归测试；去掉该参数时此测试失败） |
| merge / 根提交 | — | 不判定 |
| 表里有、仓库里没有的提交 | — | 计入 `missing_in_repo` |

另有两项整体断言：重放的 v3 L1 与原函数逐提交一致；`--fullscan` 0 差异。

### 4.2 运行时自检（106 个项目）

| 自检 | 应为 | 实测 |
|---|---|---|
| v3 L2 命中的提交必须出现在 `.java` 的 diff 流里 | 0 个缺失 | **0** |
| `--fullscan` 对照（4 个项目，逐提交比对过滤前后的 L1 与 L2） | 0 差异 | **0** |
| 第一阶段表重算的 v3 PDAR 与论文 v3 数字一致 | 106/106 | **106/106** |
| v3 L1 命中而 v4 不命中的提交，全部可归因 | `unexplained` = 0 | **0** |
| 重放 v3 L1 失败 | 0 | **0** |

### 4.3 与 v3 逐提交对比

**L1**：v3 L1 命中 5,561 个提交，v4 L1 命中 7,414 个（只算 PT 方法 6,927 个）。v3 命中而 v4 不命中的
638 个，用与第一阶段完全相同的命令（`git diff-tree -p -U3`）重放 v3 的判定、找到触发它的那一行、
再看那一行落在哪里，**全部归入已知类别**：

| 类别 | 含义 | 提交数 |
|---|---|---:|
| `non_java_file` | 触发行或注解在 Kotlin/Scala 文件里（按「只算 Java」排除） | 296 |
| `overrun_prev` | 前一行规则：注解前一行有改动，但那行不属于 PT 方法（Javadoc、空行、上一个方法） | 175 |
| `rename` | 该文件在 `-M` 下是重命名；v3 不识别重命名，把整文件当新增 | 150 |
| `pt_mention_not_method` | 触发 v3 的 `@ParameterizedTest` 文本不在任何 PT 方法里（注释、字符串） | 17 |
| `overrun_forward` | 前向扫描越过 PT 方法末尾 | 0 |
| `parse_error` / `not_reproduced` / `unexplained` | — | 0 / 0 / 0 |

典型例子（Commons-Numbers）：`a514149` 在已有 PT 上方新增了一个普通 `@Test`，新增内容的末尾空行贴着
`@ParameterizedTest`，v3 的前一行规则把它算作改了 PT；`09b6c6a` 把测试类从 `arrays` 模块移到
`angle` / `core` 模块，每个文件只改了一行 `package` 声明。

**L2**：v3 L2 命中 22,308 个提交，v4 L2 命中 24,380 个。

- **v4 新增的 3,251 个**来自修正的路径 bug、放宽的模式、两侧检查，以及 v3 中 L2 根本没跑的提交
  （v3 逐层回退，L1 命中后不再判 L2）。
- **v3 命中而 v4 不命中的 1,177 个**，来源有两类：
  - **纯重命名 / 目录搬迁**（文件级时就已排除，约 144 个）。抽查 Jena 的 4 个：均为
    "Maven standard layout"、"Move ... into new location" 一类的整体搬迁。
  - **文件级 → 类级排除的**。把改动行逐行定位到文件结构里，抽样分类（Commons-Chain、Commons-RNG、Ivy、
    Directory、Commons-Text、Ant 的全部共 22 个，Jena、Log4j 各 30 个）：

    | 改动行落在 | 例子 |
    |---|---|
    | 类之前（import、package、license 头、类的 Javadoc） | Commons-Chain `7cfdf53` 包重命名；Commons-Text `3da3c7f` 删一个没用的 import、`8c8f012` 补 license 头；Commons-RNG `4113b9a` 修类 Javadoc 错字。Log4j 抽样的 30 个全是这一类 |
    | 同一文件里的其他（非参数化）类 | Commons-RNG `efb4cc0` |
    | 文件里只有注释提到 `@RunWith(Parameterized.class)` | Jena 抽样 30 个中的 20 个，如 `SDBTestSuite2.java`：`// Better: @RunWith(Parameterized.class) and parameters are ...` |

    抽样中没有发现落在参数化类区间内却未命中的情况。

### 4.4 去掉 L3 的实证依据

把第一阶段的 L3（`is_core`）并回分子作对照口径 `pdar_with_l3`，统计「只靠 L3 才进入分子」的开发者：

| 阶段 | 只靠 L3 进入分子的人数 | 主要原因 |
|---|---:|---|
| L2 沿用第一阶段时 | 97（34 个项目） | L3 在替 L2 的两个 bug 兜底 —— IoTDB 的 61 个这类提交全是 `.java` 里的 `±@RunWith(Parameterized.class)` |
| 修正 L2 路径解析 + 两侧检查后 | 45 | 剩余主要是 `@RunWith(value = Parameterized.class)` |
| 放宽 L2 模式后；改为类级后不变（**v4 最终**） | **17（9 个项目）** | 见下表 |

最终剩下的 17 人逐个查看了他们的每一个 L3 提交，**全部是本文定义下不该算的**：

| 情况 | 人数 | 例子 |
|---|---:|---|
| Scala 测试 | 8 | Flink 7 人（`@RunWith(classOf[Parameterized])`）、JAMES 1 人 |
| Kotlin 测试 | 1 | JMeter |
| 文档、生成的 HTML、svn 残留 | 4 | SeaTunnel 的 `.md`（2 人）、Impala 的 doxygen HTML、Commons-Numbers 首个提交带入的 `.svn/pristine` |
| Java 注释里提到 `@ParameterizedTest` | 2 | Doris 的 `// @ParameterizedTest`、NetBeans 的说明注释 |
| `.java~HEAD` 合并残留文件 | 1 | Phoenix |
| 根提交 | 1 | NetBeans 的 "Initial donation" |

`pdar_with_l3` 的中位数与主口径相同（15.50%），均值 18.96% vs 18.85%。

### 4.5 被标记的项目

| 项目 | 标记 | 影响 |
|---|---|---|
| Fineract | 第一阶段表中 566 个提交（2025 年）在当前仓库里已不存在，找到率 94.7% | 这些提交保留第一阶段的 L1/L2 原值（其中 8 个是 v3 L1 命中）。主口径计入 |
| HBase、ZooKeeper | pickaxe 未能跑完 | 只影响记录用的 `core_pdar_pickaxe` 列（记为缺失），PDAR 不受影响 |

---

## 5. 结果（107 个采纳者）

> **2026-10-10 补录 Parquet。** Parquet 在语料构建的 263 → 218 那一步被漏掉，现已补回（RQ1 变为 175 个项目、
> 107 个采纳者，见 `final/corpus/README.md`）。它没有 v3 已发表值，所以只进入 v4 的统计。
> 第一阶段表在一个**截断到 2026-06-23** 的全量 clone 上生成（每个 ref 退回到该日之前最近的提交，
> 与其余项目 2026-05 下旬 ~ 06-23 的批量 clone 对齐），共 3,341 个提交；第二阶段自检全部通过
> （提交全部找到、`published_hit_not_in_stream` 0、`fullscan_mismatch` 0、`core_pickaxe_disagree` 0）。
> Parquet 的 PDAR 为 **23.38%**（201 个测试开发者中 47 人），全部来自 JUnit 4（v4 判出 113 个改动 PT 的提交，v3 为 116 个）。
> 本节 v4 的描述统计（5.1）、分布（5.2）、Table 3（5.4）与相关分析（5.5）已更新到 107 个；
> v3 → v4 的逐项目对比（5.3）以及各表的 v3 列仍是 106 个有 v3 已发表值的项目。

### 5.1 描述统计

| 口径 | 中位数 | 均值 | 标准差 | Q1 | Q3 | 最小 | 最大 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **PDAR v4（主口径，含数据源）** | **15.62** | **18.90** | 13.85 | 7.36 | 27.30 | 0.05 | 70.00 |
| PDAR v4，只算 PT 方法 | 14.77 | 18.63 | 13.70 | 7.36 | 26.71 | 0.05 | 70.00 |
| PDAR v4 + L3（对照） | 15.62 | 19.00 | 13.93 | 7.36 | 27.30 | 0.05 | 70.00 |
| PDAR v3（论文原数字，n=106） | 14.52 | 18.05 | 12.54 | 7.75 | 27.18 | 0.05 | 56.12 |

最小值 0.05 是 Spark（2,009 个测试开发者中 1 人）；最大值 70.00 是 Commons-OGNL（10 人中 7 人）。

### 5.2 分布

| PDAR 区间（%） | [0,5) | [5,10) | [10,15) | [15,20) | [20,25) | [25,30) | [30,40) | [40,50) | [50,100] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v4 项目数（n=107） | 12 | 25 | 15 | 10 | 13 | 12 | 12 | 4 | 4 |
| v3 项目数（n=106） | 11 | 24 | 19 | 9 | 13 | 13 | 10 | 5 | 2 |

逐项目数据（作图用）在 `rq1/pdar_summary_ssk.csv`，列：

| 列 | 含义 |
|---|---|
| `pdar` | v4 主口径 |
| `pt_participants` / `test_developers` | 分子 / 分母的开发者人数 |
| `pdar_pt_only` | v4，只算 PT 方法（敏感性分析） |
| `pdar_with_l3` | v4 + 第一阶段的 L3（对照，见 4.4） |
| `pdar_v3` | v3 原数字 |
| `core_pdar` / `core_developers` / `core_pdar_v3` / `core_pdar_pickaxe` | 记录用，论文不报告 |

### 5.3 v3 → v4 的变化

以下为 106 个有 v3 已发表值的项目（不含 Parquet）。

- **逐项目**：41 个上升、40 个不变、25 个下降。|Δ| = 0 的 40 个，(0,1] 18 个，(1,2] 17 个，(2,5] 23 个，
  (5,10] 6 个，> 10 的 2 个。
- **最大上升**：Commons-OGNL 30.00 → 70.00（`value =` 写法的 L2 漏判）、Commons-RNG 27.27 → 36.36（同上）、
  Commons-Statistics 35.71 → 42.86、ActiveMQ 16.54 → 23.62、IoTDB 6.67 → 13.33（L2 路径 bug）、
  Fineract 11.74 → 16.90。
- **最大下降**：Commons-Numbers 47.62 → 33.33（21 人中 3 人：2 人是 v3 L1 的误报，见 4.3；1 人只在根提交里
  带入了 svn 残留文件，见 4.4）、Commons-Chain 17.65 → 11.76、Aries 11.11 → 6.67、Ivy 12.00 → 8.00、
  Ant 6.56 → 3.28（这几个主要是 L2 改为类级后，只改过 import / license 头的人不再计入）。
- **配对检验**：Wilcoxon 符号秩检验 p = 0.023 —— 整体略微向上。
- **排序基本不变**：v3 与 v4 的 Spearman ρ = 0.979。
- **含数据源 vs 只算 PT 方法**：16 个项目因数据源而上升，无一下降，Wilcoxon p = 4.4×10⁻⁴。

**两个方向的修正部分抵消**：v4 认出了 v3 漏掉的（PT 方法内部的远距离改动、数据源、L2 的两个 bug），
也剔除了 v3 误算的（L1 的邻近误判、Kotlin/Scala、重命名、L2 文件级下的 import / 注释 / 其他类）。
中位数净升 0.98pp，但逐项目看有升有降，单个项目的变化可达 ±10pp 以上。

**提交层面与开发者层面的脱节**：v4 的 L1 比 v3 多认出 33% 的提交（5,561 → 7,414），但这对 PDAR 的影响
远小于此。原因是 PDAR 按 email 去重数开发者，多认出的提交大多出自已被计入的人；小项目的 PDAR 只能按 1/n
跳台阶。**若论文某处报告「PT 相关提交数」，v3 的数会明显偏离。**

### 5.4 影响因素（Table 3，`rq1/table3_pai_pdar.csv`）

Kruskal-Wallis 检验，v4 列为 107 个项目，v3 列为 106 个。

| 因素 | 组 | n | PDAR v4 中位（IQR） | v3 中位 |
|---|---|---:|---|---:|
| Size | Small (<625) | 26 | 16.21 (8.06–25.82) | 16.34 |
| | Medium (625–1805) | 30 | 15.07 (7.32–25.52) | 14.06 |
| | Large (≥1806) | 51 | 16.90 (7.91–28.00) | 14.00 |
| Age | ≤2005 | 35 | 13.89 (7.75–23.71) | 13.89 |
| | 2006–2011 | 38 | 15.50 (6.67–28.62) | 14.41 |
| | 2012–2017 | 28 | 21.56 (9.45–33.33) | 21.28 |
| | ≥2018 | 6 | 14.28 (6.21–37.02) | 15.23 |
| Domain | Data & Analytics | 39 | 16.42 (7.53–28.51) | 12.32 |
| | Network & Comm. | 16 | 19.05 (6.36–25.40) | 15.96 |
| | Dev. & Tools | 48 | 15.20 (7.88–26.46) | 16.34 |
| | Web & Content | 4 | 13.52 (7.55–19.70) | 12.63 |

| 因素 | 口径 | v4 H | v4 p | v3 H | v3 p |
|---|---|---:|---:|---:|---:|
| Size | 全部组 | 0.07 | 0.964 | 0.06 | 0.971 |
| Age | 全部组 | 2.60 | 0.457 | 1.81 | 0.613 |
| Age | 仅 n>6 的组 | 2.74 | 0.254 | 1.89 | 0.388 |
| Domain | 全部组 | 0.61 | 0.895 | 0.78 | 0.855 |
| Domain | 仅 n>6 的组 | 0.09 | 0.958 | 0.28 | 0.867 |

**结论不变**：PDAR 与项目规模、年龄、领域均无显著关联。

### 5.5 补充：与其他项目特征的相关（Spearman，n=107）

| PDAR v4 与 | ρ | p | v3 的 ρ |
|---|---:|---:|---:|
| PAI（PT 占测试方法比例） | **0.670** | 2.8×10⁻¹⁵ | 0.638 |
| Java 文件数 | 0.007 | 0.94 | −0.007 |
| 测试方法总数 | 0.051 | 0.60 | 0.047 |
| 测试开发者数 | −0.069 | 0.48 | −0.100 |

PDAR 只与 PAI 强相关：PT 用得越多的项目，写过 PT 的开发者比例越高；与规模无关。

---

## 6. 局限

1. **没有人工标注的 precision / recall。** 正确性靠「定义合理 + 实现忠实于定义」论证（第 3、4 节），
   残余误差来源逐项列在下面并已量化。
2. **自定义元注解不识别。** 自己定义一个注解、再在上面挂 `@ParameterizedTest` 的写法认不出来。
3. **`@ParameterizedClass`（JUnit 5.13，类级参数化）不在 PT 定义内**，与论文的 PT 计数一致。
   全语料 diff 中提到它的提交 39 个。
4. **跨文件的数据源不纳入**（如 `"com.foo.Util#data"`、production enum、另一个文件里的 helper 类）。
   按快照计，未能在同文件内解析的 JUnit 5 引用共 21,084 次（同一引用在不同快照版本中重复计数）。
5. **JUnit 4 的辅助代码只认嵌套类型。** 参数化类内部的嵌套辅助类型算，但同一文件里另起的**顶层**辅助类
   （非 public 的第二个顶层类）不算，即使它只服务于这个参数化类（如 Commons-RNG `efb4cc0`）。
6. **merge 与根提交不计**（与分母一致），PDAR 里的「提交」实际指非 merge、非根提交。
7. **快照固定在 2026-06。** 第一阶段那一轮之后上游改写过历史的分支上的 4,123 个提交（0.24%）保留原值。
8. **分母沿用 v3 的启发式**（路径 / 文件名 / `@Test` 等文本），未在本轮改动 —— 有意为之，
   以保证 v3 → v4 的差异只来自分子。
9. **重命名识别有预算上限。** 单个提交改动的 `.java` 文件极多时，git 会跳过完整的重命名识别，
   被移动的 PT 文件退化为「整文件删除 + 新增」而被计为改动 —— 偏向多算，不会漏算。

---

## 7. 复现

**依赖**：Python 3.10+、`tree_sitter>=0.23`、`tree_sitter_java>=0.23`（`requirements-recompute.txt`）、git ≥ 2.30。

**外部数据**：第一阶段的逐提交表 `result_v3/`（115 个项目，189 MB，不随仓库分发），用环境变量
`PT_PDAR_RESULT` 指向它。默认位置 `<repo>/result_v3/result_v3`。

```bash
cd final/rq1/pdar

# 单元测试（几秒）
python -m unittest discover -s tests -v

# 第二阶段：106 个项目，bare clone → 分析 → 删除（本轮实测约 45 分钟，3 并发）
python batch_pdar_v4.py --jobs 3 --no-pickaxe --work /path/to/scratch

# 汇总 → rq1/pdar_summary_ssk.csv 与 result_v4/pdar_v4_summary.csv
python calculate_pdar_v4.py

# Table 3
cd .. && python build_table3.py
```

pickaxe 只用于记录用的 `core_pdar_pickaxe` 列，结果在 `result_v4_pickaxe/`（较早一轮带 pickaxe 的运行），
`calculate_pdar_v4.py` 默认从那里取。

**运行环境的两个坑**（都会导致**静默错误**，实测踩过）：
- **不要在 macOS 的外置 exFAT 盘上跑。** macOS 会在 exFAT 上生成大量 `._*` 文件（AppleDouble），
  其中 `._pack-*.idx` 会让本地 `git clone` 产出缺对象的仓库，之后取 diff 失败、返回空串，
  整轮分析给出看似合理但完全错误的数字。必须用的话，用 `rsync -a --exclude='._*'` 复制并
  `git fsck --connectivity-only` 确认。另外，外置 exFAT 盘上 `diff-tree` 的吞吐只有本地盘的约 1/9。
- **pickaxe 在含大二进制 / 大文档的仓库上可能极慢**（ZooKeeper 的网站分支，80 分钟以上未结束）。
  它不影响 PDAR；`--no-pickaxe` 可跳过。

**从零复现（新快照）**：`batch_pdar_v4.py --with-stage1` 会在同一个 clone 上先跑第一阶段。
这会得到新的提交集合，**与论文数字不可比**。

---

## 8. 文件

| 文件 | 作用 |
|---|---|
| `pdar_v4_commit_table.py` | 第一阶段：逐提交表（v3 的逐提交检测，原样保留） |
| `pdar_v4_method_level.py` | 第二阶段：L1（JUnit 5，方法级）、L2（JUnit 4，类级）、v3 L1 重放与归因、pickaxe（可选）、自检 |
| `pt_spans.py` | 判定核心：一个 Java 文件快照里的 PT 方法区间、数据源区间、JUnit 4 参数化类区间 |
| `batch_pdar_v4.py` | 批处理：clone → 分析 → 删除；断点续跑；`--fullscan` / `--no-pickaxe` / `--with-stage1` |
| `calculate_pdar_v4.py` | 汇总各口径、打标记，写论文口径的项目级表 |
| `tests/test_pdar_v4.py` | 端到端测试 |
| `pdar_repo_map.csv` | 仓库名的唯一来源（项目 → git URL） |
| `pdar_v3_published.csv` | v3 的论文数字（115 个项目），用于核对第一阶段表 |
| `result_v4/` | 第二阶段输出：逐项目的稀疏逐提交表、summary JSON、`pdar_v4_summary.csv`（全部口径与自检计数） |
| `result_v4_pickaxe/` | 带 pickaxe 的那一轮，只提供 `core_pdar_pickaxe` 列 |
| `superseded_v2/` | v2（生命周期追踪）的方法学记录，未采用 |

`*_method_commits.csv` 是稀疏的：只写出被判定过、且有任一新标记非零 / 第一阶段 `modifiedPT=1` /
第一阶段 `is_core=1` 的提交。没写出的提交：被判定过的，新判定全为 0；未判定的（merge、根提交、本地缺失），
取第一阶段的 L1/L2 原值。
