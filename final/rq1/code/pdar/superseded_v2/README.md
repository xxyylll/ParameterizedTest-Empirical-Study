# PDAR v2 —— 被取代的方法（**不是论文口径**）

> **论文报告的 PDAR 全部来自上一级目录的三层检测（v3）。** 本目录是方法学记录，
> 不要用它复现论文数字。

## v2 是什么

v2 不做 diff hunk 的邻近判断，而是**按方法身份追踪每个 PT 的生命周期**：

1. **全局扫描** —— `git log --all -G` 找出历史上所有涉及 PT 注解的提交，
   按 diff 里的 `+`/`-` 区分这是一次**新增**还是**删除**事件。
2. **行号 → 方法** —— 解析 hunk 头 `@@ -a,b +c,d @@` 取出注解所在的**行号**
   （`get_line_number_from_diff`），再据该行号在当时的文件快照里定位它所属的
   方法名（`extract_method_name_from_file_content`）。
3. **与 parser 输出 join** —— 读 `parser_result/{project}_output.json`，
   用它的 `startLine` / `endLine` 得到每个测试方法的**真实行区间**；
   parser 结果作为 HEAD 处现存 PT 的 ground truth，`git log -G` 负责补上
   历史上已被删除的 PT。
4. **生命周期回溯** —— 对每个 PT 的 `[新增提交, 删除提交或 HEAD]` 区间用滑动窗口
   找出其间所有贡献者。
5. **重命名识别** —— JUnit 5 的方法名消失时调 RefactoringMiner 判断是重命名还是
   真的删除；JUnit 4 靠 `git log --follow` 跟踪文件改名，并在快照里查
   `@RunWith(Parameterized`。

它取 diff 时用 **`-U0`**（零上下文），因为它靠行号与方法区间定位，
根本不依赖「注解附近几行」这种启发式。

## v2 和 v3 的本质差别

| | v2（本目录） | v3（上一级，论文口径） |
|---|---|---|
| 定位方式 | 行号 → 所属方法 → 方法行区间 | diff hunk 内的**注解邻近性** |
| diff 上下文 | `-U0`，不依赖上下文 | git 默认 **3 行**，直接决定召回率 |
| PT 身份 | `(文件路径, 方法名)`，跨重命名追踪 | 无身份概念，只看单个提交的 diff |
| 已删除的 PT | 显式建模（生命周期有终点） | 仅靠 Layer 3 的 pickaxe 间接体现 |
| 外部依赖 | RefactoringMiner + parser_result | 无，纯 git |
| 开发者去重 | email 小写；**email 缺失时回落到 name** | email 小写；**无 email 则丢弃该提交** |

v3 的已知局限（上一级 README 详述）正是 v2 在设计上避开的：3 行上下文让 v3 漏掉
「在 PT 方法内部但离注解较远」的改动。实测该局限在提交层面漏两到四成，
但在 PDAR 层面只有约 1 个百分点（因 PDAR 按开发者去重）。

## 为什么最终没用 v2

**v2 没有留下结果。** `developer/result/` 目录不存在；归档的 2026-02 那一轮
（43 个项目）用的是 v3 的三层 schema（`detection_layer` 列取值为
`junit5_hunk` / `junit4_file`）。所以 v2 是**设计并实现了、但未被采用**的方法，
没有可与 v3 逐项目对照的产物 —— 两者的实证比较做不了。

可以推断的取舍：v2 需要对**每个**候选提交跑 RefactoringMiner（JVM 进程，
每次数秒到数十秒），在 117 个项目、上百万提交的规模上不可行；
而它依赖的 `parser_result/` 是旧 clone 的产物，
不应用于分析，只能用来回溯旧数字。

## 运行它需要什么（代码保持原样，未做可移植化）

本目录的代码**逐字保留当时的样子**，没有像 `final/` 其余部分那样改成可移植 ——
改了就不再反映当时真正运行的东西。因此它带着三处硬编码路径：

```python
REFACTORING_MINER_PATH = '/Users/immortal/RefactoringMiner-3.0.13/bin/RefactoringMiner'
JAVA_HOME             = '/opt/homebrew/Cellar/openjdk@21/21.0.10/libexec/openjdk.jdk/Contents/Home'
PARSER_RESULT_DIR     = <repo>/parser_result        # 旧 clone 的 parser 产物，624 MB，不随包分发
```

`calculate_pdar_v2.py` 另有指向 `developer/result*` 的硬编码路径。
要跑的话这些都得先改，并且需要 RefactoringMiner 3.0.13 与 JDK 21。
