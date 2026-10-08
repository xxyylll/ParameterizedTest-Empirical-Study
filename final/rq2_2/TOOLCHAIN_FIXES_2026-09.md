# rq2.2 / RQ3 工具链修复记录（2026-09-13）

人工 review 抽样结果时发现 14 个问题（#1–#14），试点阶段又暴露 3 个（#15 #16 + 间接递归）。
本文件记录每个问题的修法、影响范围、以及**这轮刻意没修 / 没跑**的部分，供论文 threats to validity 与后续核对。

## A. 已修复

### A.1 Parser（`/Users/immortal/Javalang-analyzing-cli`，`TestCaseAnalyzer.java`；jar 2026-09-13 22:34）
| # | 症状 | 修法 | 新 tag |
|---|---|---|---|
| #1 | `isThirdParty` 用"当前文件的包前缀"判断项目内外，跨包/父包调用（`AbstractBmpTest`、`Imaging.getImageInfo`、mina-sshd `ClientSession.auth`…）全被记 THIRD，不展开、不进 productionFunctionImplementations | 改为查项目源码树 `getSourceFilePathForClass()==null`（带 memo） | — |
| #2 | 方法引用不带作用域 | `METHOD_REF_TEST/_PROD/_THIRD`，_TEST 展开体 | METHOD_REF_* |
| #8 | 抽象测试类声明 `@ParameterizedTest`，provider 在各子类 → `METHODSOURCE_NOT_FOUND` | 反向继承索引（`extends` 正则）+ BFS 找子类 provider；**多个 provider 各发一条 METHODSOURCE，下游池化成一行**（用户决定） | — |
| #9 | 父类 provider 因 binding 失败找不到（hadoop `ParameterizedSchedulerTestBase`） | 父类链改为语法解析（import / 同包 / 通配 / 唯一简单名） | — |
| #11 | 匿名类内部方法（双花括号初始化里的 `addTestCase`）→ `METHOD_NOT_FOUND_IN_SOURCE` | 识别 `isAnonymous()/isLocal()` 声明类，就地展开 | LOCAL_METHOD |
| #15 | **泛型方法永远匹配不到声明**（`Range.of(Integer,Integer)` vs `of(T,T)`）→ `METHOD_NOT_FOUND_IN_SOURCE`；commons-lang 2297 行 | `findMethodDeclaration` 先用 `getMethodDeclaration()`；`GenericMethodVisitor` 按 erasure 比参数 | — |
| #16 | 参数化接收者 `Range<java.lang.Integer>.contains` 查不到源码文件 → 旧 `SOURCE_FILE_NOT_FOUND`，#1 之后会变 THIRD | `getSourceFilePathForClass` 先去掉 `<…>` | — |
| 递归 | #1 之后遍历更深，互递归（hadoop `printQueues ↔ render`）StackOverflow 丢整个测试 | 展开路径栈；深度上限 60 | INDIRECT_RECURSIVE, MAX_DEPTH_REACHED |
| 外部 provider | `@MethodSource("java.util.Locale#…")` 被记 NOT_FOUND | 区分 JDK/javax 前缀 | METHODSOURCE_EXTERNAL |
| 子根 | orc（`java/`）、thrift（`lib/java/`）根目录无构建文件 → 整项目解析失败 | `BuildToolDetectorFactory` 向下两层找构建根，按测试 .java 数取最大（parser-core） | — |

其它：`--only-test-classes` 入口过滤；`-Danalyzer.perTestCaseTimeoutSeconds`；`-Danalyzer.debugStack=true` 打印分析异常栈。

### A.2 rq2.2 脚本
- `CognitiveComplexityCalculator.java`：#3 自递归调用不计（同名同参数个数、限定符 null/this/本类）；#10 匿名类 / 局部类 (`TypeDeclarationStatement`) 体内结构计入。
- `ProviderCognitiveComplexity.java` / `ConstructionDependencyClassifier.java`：#7 `@MethodSource` 值为常量/拼接/父类常量时解析（`resolveStringConstant`，父类链 ≤6）；#14 同名方法按 MethodSource>ParameterizedTest>Test 排序取；JDK/外部 provider 标 `PROVIDER_EXTERNAL:`。
- `build_helper_depth.py`：tag 词表全量对齐（见文件头）；#6 文件名 `split_aaa_body` 先按最后一个 `.` 再按第一个 `_`（修 `gsp_dft_user0` 这类下划线测试名，+22 条）；#12 `src/test/<pkg>`（无 java 段）路径；`LOCAL_METHOD` 为 NEUTRAL（不计 helper，子行照常）。
- `build_dependency_v2.py`：池化多 provider 时 helper locality 相对**各自** provider 类算（`extract_provider_subtrees_with_owner`），provider 位置对每个类各算取最深；`provider_declaring_class` 多值用 `;` 连接。
- `check_aaa_completeness.py`（#13）：每次 parser 跑完必跑，ssk 枚举 vs AAA 内容字段，排除 @Disabled，@Nested 按外层类匹配。
- `/Users/immortal/Complexity_Analysis/build_test_metrics_unified.py`：#12 orc 类 `src/{main,test}/<pkg>`、`src/java/<pkg>` 根。

## B. 这轮刻意不做（需在论文里标注）
1. **hive / storm / camel 完全不动**（用户决定 2026-09-13）：既不补整模块缺失，也不重跑既有 JSON。三者数据仍是旧 parser 口径（#1 等 bug 未修）。分析时要么剔除，要么单列。影响面见 `rerun_entry_lists_phase2/_plan.csv`（camel 12170 / hive 3236 / storm 421 条本应重跑）。
2. 其它项目**整模块缺失**（#4 #5 #13，`aaa_completeness.csv` 的 `whole_modules_missing`）不补，只补零散缺失（4016 条）。
3. 重跑是**定向**的：只重跑现有 JSON 命中任一条件（third_project / methodsource_not_found / method_not_found / source_file_not_found / empty_trace）的测试，未命中的 31% 保留原 JSON。理由：这些修复对未命中的测试是恒等的（没有可改变的行）；风险是批量跑时的 binding 抖动，靠 `check_aaa_completeness.py` + 抽样 diff 兜底。
4. commons-jexl `CacheTest` 2 个旧 `METHOD_REF` 文件保留（目标全是 JDK，零损失）。
5. Cognitive complexity 只看 provider 本体（用户 2026-09 再次确认），helper 体内复杂度不算；数据流（provider 只调一个 helper 但 helper 很复杂）是已知盲区，由 helper depth 维度补。
6. `LOCAL_METHOD` 子行缩进比概念深一层，极少数 provider 的 max_depth 可能高估 1。

## C. 重跑与回滚
- 清单/计划：`rerun_entry_lists_phase2/`（`_plan.csv` 按项目统计，`_manifest.csv` 逐文件及命中原因）。
- 备份：`/Volumes/SSKSSD/aaa_backup_phase2_20260913/<project>.tar.gz`（原始 JSON，按项目打包）。回滚：`tar -xzf <p>.tar.gz -C /Volumes/SSKSSD/apache-projects/<p>/AAA`。
- 驱动：`run_phase2_all.sh` → `prepare_phase2_rerun.py --apply` → `run_phase2_rerun.sh`（顺序，`-Xss16m`，300s/test，`rerun_logs_phase2/`）。
- 跑完必做：`python3 check_aaa_completeness.py`；抽样 diff 新旧 tag 分布（示例：thrift 25 条 `<prod>` 19→103、MNF 69→0、SFNF 29→0）。

## D. 补缺（refill）需在主重跑之后单独跑一遍
主重跑的入口清单里**没有**补缺类（`_apply.log` 显示 `补缺 0`）：之前单跑 `check_aaa_completeness.py thrift` 把
`aaa_missing/_detail.csv` 覆盖成只剩 thrift。已改成部分运行时合并。流程：
1. 主重跑结束（`_run.log` 出现"全部结束"）。
2. `python3 check_aaa_completeness.py`（全部项目）→ 重新得到缺失明细。
3. `python3 prepare_phase2_rerun.py --refill-only`（只写补缺类入口清单，不备份不删除）→ `./run_phase2_rerun.sh`
   （先清掉 `_done.txt`），工具只生成不存在的 JSON，代价约 4k 测试 + 每项目启动开销。

## E. 对账（reconcile_phase2.py）
`python3 reconcile_phase2.py [project…] --restore`：对每个备份归档逐文件对账。
- 源码已从 checkout 消失的测试（如 commons-numbers `SelectionPerformanceTest` 2 条）无法重生成 → 从备份恢复旧 JSON（`source_gone`）。
- 源码在但没生成（超时/异常）→ `rerun_entry_lists_phase2/_retry/<project>.txt`，用 `run_phase2_rerun.sh` 再跑。
- 新旧 tag 分布写 `rerun_logs_phase2/_reconcile.csv`；行数缩水 >50% 的写 `_reconcile_shrunk.csv`（binding 抖动嫌疑，要人工看）。
- 注意 `_run.log` 里的"生成 N"是工具汇总行的数字，包含被跳过的已有文件；真实写入数看日志里 `Successfully wrote` 行数或 `_reconcile.csv` 的 `regenerated`。
前 7 个小项目对账结果：production 行 2–4×（commons-cli 372→1470），MNF/SFNF 基本归零，无缩水。

## F. 主跑期间发现、待重试
- **NPE `md.resolveBinding()==null`**（skywalking 36 条、commons-text 2 条）：#15 之后 `GenericMethodVisitor` 能在 binding 不全的
  CU 里找到声明，但 `TestCaseAnalyzer.java` 的两处 `md.resolveBinding().getDeclaringClass()` 直接解引用 → 整个测试丢失。
  已改成 `qualifiedNameOfDeclaringType(expandedCu, md)`（源码已改，**jar 未重建**——主跑中不能替换正在用的 jar）。
  主跑结束后：`gradle shadowJar` → `reconcile_phase2.py` 的 `_retry/` 清单 → `run_phase2_rerun.sh`（先清 `_done.txt` 里对应项目）。

## G. 主跑结果（2026-09-15）
- 43 个项目（不含 hive/storm/camel）共重生成 **115,145** 条；SSD 在 druid 中途自行卸载一次，重挂后续跑 druid + hadoop，无损失。
- 全部项目 trace 缩水 0（hadoop 1 条是同名测试方法文件名碰撞，非抖动）。
- 汇总（43 项目，`rerun_logs_phase2/_reconcile.csv`）：production 行 357k→2.73M（hadoop 另 115k→760k），
  `SOURCE_FILE_NOT_FOUND` 46,074→2，`METHODSOURCE_NOT_FOUND` 177→9（hadoop 149→0），`METHOD_NOT_FOUND_IN_SOURCE` 27,325→5,571。
- 残留 MNF 主体是枚举 `values()/valueOf()`（编译器合成，无源码）→ 下游 `build_helper_depth.py` 归为 `SYNTHETIC_ENUM_MEMBER`（排除）；
  其次是 record 访问器 / Lombok getter（causeway 为主）→ 仍记 unresolved，规模约 1k 行。
- **不恢复**的 22 条备份：14 条源码已不在 checkout（commons-numbers `SelectionPerformanceTest` 2、httpcomponents-client 12），
  8 条是包名已变（james 5 → 由补缺流程按新包名生成、ozone 1）或 archetype 模板 `$.` 占位包（avro 1、wicket 1）。当前 checkout 里
  不存在的测试不保留。
- 重跑时间：小项目秒级，hudi 139 min / nifi 282 min / flink 319 min / hadoop 490 min，总计约 32 h。

## H. 补缺 + 重算结果（2026-09-15）
- 补缺：25 个项目 / 541 入口类，1h18m；零散缺失（不含 hive/storm/camel）2,081 → **92**；总缺失 22,070 (10.5%) → **13,926 (6.7%)**，
  剩余几乎全是 hive/storm/camel（10,900）和其它项目的整模块缺失（2,629）。
- **#17 接口 provider**：JUnit 5 允许 provider 是测试类所实现接口上的静态方法（james `BlobStoreDAOContract.blobs()`、
  flink `TableTestProgramRunner.supportedPrograms()`）。parser 的 `resolveLocalOrInheritedProvider` 改为对父类 + 接口做 BFS；
  Java 侧 `ProviderCognitiveComplexity` / `ConstructionDependencyClassifier` 的 `resolveProvider` 同样改 BFS，并加了 #8 的子类向下查找。
  语料里剩余 9 条 `METHODSOURCE_NOT_FOUND` 中 8 条由此修复（重跑对应 5 个类），最后 1 条是 log4j2 的枚举 `values()`（无源码，正常）。
- 已知小限制：Java 侧 CC 对子类 provider 只取第一个命中的（AAA/helper-depth 侧是全部池化）。样本里唯一一例 AbstractLicenseTest 的 7 个
  provider CC 全为 0，不影响结果。
- rq2.2（379 条 pilot 样本，`rerun_logs_phase2/_rq22_before_after.md`）：helper-depth OK 324 → 357；transformation OK 368 → 376；
  dependency 分布 L0 250→255 / L1 17→13 / L2 15→30 / L3 38→34 / L4 16→40，未判定 43→7；hits_production 39 → 88。
  逐条迁移：`-`→L0 16、`-`→L2 14、L0→L4 11、L3→L4 9、L1→L4 4（都是原本被记 THIRD 的跨包 test helper 现在被正确展开）。
  production 侧 helper（max_depth_prod>0）39 → 86 条。
- RQ3（23 项目，`Complexity_Analysis/rq3_before_after_phase2.md`）：self_* 指标不变（不依赖 AAA）；helper/total 指标的 PT-vs-nonPT
  δ 方向全部不变、幅度普遍加大（helper_loc_sum δ +0.40 → +0.56，total_loc +0.48 → +0.53，total_dupPerc −0.20 → −0.23）；
  helper_count 均值 1.02 → 3.07。276 个 (指标×项目) 格子中 42 个换了效应量档位，其中 commons-rng 多个指标从 M 降到 S/N、
  mina-sshd / hudi / zookeeper 从 N/S 升到 M/L。
- 修前结果保留在 `rq2/rq2_2_structure/pre_phase2/` 与 `Complexity_Analysis/pre_phase2/`。
- 新的人工 review 抽样：`manual_review_sample.csv`（89 条）。

## I. Review 第二轮（2026-09-15）：8 个问题与定稿口径
| # | 问题 | 决定 | 改动位置 | 影响面 |
|---|---|---|---|---|
| ① | Construction Literal/Dynamic 定义不清 | **口径 A**："参数集在编译期完全确定"→ Literal。允许字面量、`Type.MEMBER` 常量/枚举、本类 `static final` 字面量字段、字面量局部变量、`new ValueObject(字面量…)`、空容器、装箱/装配白名单调用（`of/asList/arguments/named/entry/add/put/build/stream…`）、多条 `add` 语句、表达式体为字面量的 lambda；有 if/for/switch/try、`map/filter` 等变换、helper 委托、白名单外的调用（含 `Date.from(...)` 这类静态工厂——保守判 Dynamic）、方法引用、字段/参数引用、三目 → Dynamic | `ConstructionDependencyClassifier.isLiteralMethod/isLiteralExpression` | 样本 Literal 108 → 177 |
| ② | 嵌套类 helper/provider 记 L3 | 同一最外层类 → **L1 Enclosing-Class Helper**（含静态嵌套类、@Nested 内部类、外层类）。等级命名：L0 Source Local / L1 Enclosing-Class Helper / L2 Inheritance / L3 Package Helper / L4 Cross-Package | `build_dependency_v2.locality()` | 样本 7 条 L3/L4 → L1 |
| ③ | 方法引用作为数据传出去也算 helper | **(b) 上下文敏感**：parser 在 `METHOD_REF_*` 行尾加 ` ctx=<call:名|target:名|new:类|return|assign|array|lambda|conditional|other>`；下游只有 `call:<非数据装配方法>` 与 `target:` 才算调用，其余（`call:of/arguments/asList/add/put/build/named…`、`new:*`、`return`、`assign`…）连同其展开子树一起剔除。**lambda 体内的调用照常算**（内联代码，与 CC 口径一致）。RQ3 同口径 | parser `methodRefContext()`；`build_helper_depth.drop_data_method_refs`；`build_dependency_v2`；`Complexity_Analysis/build_test_metrics_unified.py` + dup | 补跑含 METHOD_REF_TEST/PROD 的 ~9.4k 条 |
| ④ | 嵌套类里声明的测试匹配不到 AAA | `find_json_file` 加 `{fqcn}.<Inner>_{test}` 前缀匹配，多候选时优先唯一的 MethodSource PT，仍多 → `AMBIGUOUS_NESTED_OR_OVERLOAD`；helper-depth 输出改用样本表的类名做键（AAA 声明类另存 `aaa_test_class`） | `build_helper_depth.py` / `build_dependency_v2.py` | log4j2 2 条恢复；avro 1 条 ambiguous |
| ⑤ | 同类同名重载测试文件名碰撞（第二个被当"已生成"跳过） | parser 文件名加 `-p<参数个数>[-序号]`（仅在同类有同名**测试**方法时），JSON 加 `parameterCount`；完整性检查按 (类, 方法, 参数个数) 比对 | `TestCaseAnalyzer.overloadSuffix`、task 三处命名、`check_aaa_completeness.arity_of` | 460 对 / 1,178 条 / 72 对含 PT；补跑这些类 |
| ⑥ | JDK provider 被当失败 | 单列 `EXTERNAL_PROVIDER`，三维度 N/A（dependency 记 `EXTERNAL`，helper_depth_status `EXTERNAL_PROVIDER`，transformation `PROVIDER_EXTERNAL:`） | `build_helper_depth` / `build_dependency_v2` / `merge_results` | 样本 1 条，语料 6 条 |
| ⑦ | 同文件多嵌套类同名 provider 找错 | 先封闭类型、再外层链、最后整文件 | parser `findMethodByNameInClass`；Java 侧 `findMethodByName` | 语料仅 avro 1 文件 |
| ⑧ | @Disabled 的测试被 parser 跳过 | 纳入（`-Danalyzer.skipDisabled=true` 可恢复旧行为），完整性分母不再剔除 | task `isTestMethod` | 907 条（PT 50 / MS 38）增量生成 |

补跑：`prepare_phase3_rerun.py --apply` + `run_phase3_rerun.sh`，删除重生成 10,432 条 + @Disabled 增量，入口类 2,779；备份 `/Volumes/SSKSSD/aaa_backup_phase3_20260915/`。

## J. Phase 3 结果（2026-09-16）
- 补跑 8h，44 项目全部 rc=0；备份 10,432 条中 10,430 重生成（67 条改名 `-pN`），2 条 httpcomponents-client 源码已删、不恢复。
- 完整性（分母含 @Disabled）：210,537 / 缺失 14,176 (6.7%)；零散缺失（不含 hive/storm/camel）96。
- 同名重载 PT 的样本匹配：多个候选都是 MethodSource PT 时按声明位置取第一个（`OVERLOAD_PICKED_FIRST_DECLARED`），与 Java 侧一致；
  嵌套类多份同名（avro `canonicalization`）同样按声明位置取第一个。
- 显式 provider 引用的判定改为"注解值不是裸名"（含 `#` 或限定名常量），commons-io `testReadAfterClose` L2→L3。
- rq2.2（379 条）：helper-depth OK 370→376（未匹配只剩 2 条 checkout 已删的 + 1 条 EXTERNAL）；
  dependency L0 256 / L1 21 / L2 29 / L3 27 / L4 43 / EXTERNAL 1；construction Literal 108→177（口径 A）；
  helper 指标基本不变（③ 只影响少数 provider：log4j2 `configurations()` 3→0）。
- RQ3：δ 全部方向不变、幅度变化 <0.01；276 格子里 13 个换带；PT 3,687→3,737（@Disabled 纳入 + 重载恢复）。
- 新 review 样本：`manual_review_sample.csv` 83 条。修前结果在 `pre_phase3/`。

## K. Review 第三轮（2026-09-16）：两条规则补充
- **Dependency L2 扩展**：helper 声明在测试类（或 provider 类）的祖先里（`extends` 链 / `implements` 的接口，语法解析 ≤8 层，
  `build_dependency_v2.ancestors_of`）→ `inherited` → L2。判定顺序：同最外层类 L1 → 祖先 L2 → 同包 L3 → 跨包 L4。
  样本 18 条 L3/L4 → L2（commons-imaging 的 `AbstractImagingTest.getTestImages()` 一族、mina-sshd 的 `BaseTestSupport` 一族）。
- **Construction A2**：装箱白名单只对静态工厂形式（接收者是类型名或无接收者）和对字面量局部容器的单条 `add/put/...` 语句、
  单层终结调用 `list.stream()/toArray()/build()` 生效；接收者是对象的链式调用（`new ImmutableMap.Builder<>().putAll(..).put(..).build()`）
  → Dynamic。样本 7 条 Literal → Dynamic（全是 druid `BaseCalciteQueryTest.provideQueryContexts()`）。
- 本轮变化清单：`review_changes_phase3b.csv`（25 条）；变化前结果在 `pre_phase3b/`。不涉及 parser。


## L. Review 第四轮（2026-09-16）：dependency / construction 口径升级为"传递式 artifact 依赖 / 静态可确定性"
- 新增 `java/ArtifactWalker.java`（JDT 语法 + 文件索引，无 binding），由 `ConstructionDependencyClassifier` 调用；
  输出新增 `construction_reason`（第一个触发 Dynamic 的原因）、`dependency_reason`、`hits_production_src`、`artifacts`（走过的 artifact 及等级）。
- `build_dependency_v2.py`：`dependency = max(dependency_aaa, dependency_src)`，`hits_production` 取或；`merge_results.py` 并入 construction 列。
- 已知近似：无 binding，实例变量上的调用按声明类型解析；同名重载按参数个数；找不到的类型按 JDK/第三方处理；遍历上限 400 个节点。
- 样本变化（相对第三轮）：construction Literal 170→150（20 条 Literal→Dynamic：字段在 static 块里填充、helper/构造含逻辑、builder 链）；
  dependency L0 256→225 / L1 21→18 / L2 47→35 / L3 25→45 / L4 27→53（59 条变化，`review_changes_phase3c.csv`）。
  典型：commons-imaging `FullColorRoundtrip` L2→L3（`FormatInfo.READ_WRITE_FORMATS`；`TestImages` 也在 roundtrip 包，所以是 L3 不是 L4）、
  zookeeper `X509KeyType.values()` 一族 L2→L3、rat `new TestingLicense` L1→L4、log4j2 `SslKeyStoreConstants.*` L0→L3。

## M. 全量跑（2026-09-16）：44 个项目全部 MethodSource PT
- 清单：`build_full_methodsource_list.py` → `full/methodsource_all.csv`（ssk 枚举，5,349 条，含 @Disabled；去重后 5,334）。
- 驱动：`run_full_rq22.sh`（环境变量 `RQ22_SAMPLE_CSV / RQ22_OUT_DIR / RQ22_PROJECTS=ALL` 切换，所有输出在 `full/`，pilot 结果不动），全程约 1 分钟。
- 交付表：`full/rq22_methodsource_all.csv`（`build_final_table.py`），列：construction(+reason) / dependency(+hits_production, reason) /
  cognitive_complexity / max_helper_depth_{test,prod} / distinct_helpers_{test,prod} / n_params（去掉 TestInfo 等注入参数）/ n_sets（静态可数时的参数组数，
  `n_sets_status` EXACT|NOT_STATIC）/ status。
- 结果：OK 5,274；未匹配 AAA 47（ssk 里有但 AAA 没有，多为整模块缺失）；EXTERNAL_PROVIDER 7；CC 侧 6 条测试文件未定位。
  construction Literal 1,921 / Dynamic 3,353；dependency L0 3,251 / L1 354 / L2 499 / L3 500 / L4 670；hits_production 1,964；
  CC mean 1.10（>0 的 790 条）；helper depth test >0 893 条；n_sets 可数 3,608 条（median 3，p90 12）。
- 已知：12 条 n_params=0（hadoop 里同名重载的非参数化方法被按名字选中，按名字定位的固有限制）。

## N. 全量 @ValueSource（2026-09-16）
- `java/ValueSourceAnalyzer.java`（复用 `ArtifactWalker.analyzeExpressions`）+ `run_full_valuesource.sh` → `full_valuesource/rq22_valuesource_all.csv`。
- construction 按属性：strings/booleans/ints/longs/doubles/shorts/bytes/floats/chars → Literal-Primitive；classes → Literal-Metadata。
- dependency：注解元素里的常量引用 / `Foo.class` 按 MethodSource 同一套 artifact 规则；纯字面量 L0。structure 不算，只有 arity。
- 1,481 条（ssk）→ 1,449 OK（6 条测试文件定位不到，1 条无 @ValueSource 注解——同名重载）。Literal-Primitive 1,409 / Literal-Metadata 40；
  L0 1,427 / L1 15 / L2 2 / L3 5；hits_production 34（`classes = {ProdType.class}` 或 production 常量）；n_sets median 2、p90 6、max 55；179 条含常量引用。
- 顺带：`ArtifactWalker` 里 production 类型的 `Foo.class` 现在也标 hits_production（MethodSource 全量重跑：hits_production 1,964 → 2,131，其它不变）。

## O. 全量 @CsvSource / @EnumSource（2026-09-17）
- `run_full_annotation_sources.sh [ValueSource|CsvSource|EnumSource]`，Java 侧 `CsvSourceAnalyzer` / `EnumSourceAnalyzer`（复用 ArtifactWalker）。
- **CsvSource**（369 → 360 OK）：construction 固定 Literal-Primitive；dependency 同 ValueSource（常量拼接 → artifact），全部 L0，7 条 hits_production；
  arity n_params × n_sets（value 元素数 / textBlock 行数，语料里全是 value 数组），另给 n_columns（首行按 delimiter 切）。
- **EnumSource**（783 → 743 OK，9 条测试文件定位不到）：
  - dependency：枚举在 test-code → L0–L4；在 production → **Production**（L0–L4 之外单列；含 15 条 protobuf 生成的 `HddsProtos.*`，标 production(generated)）；
    JDK/第三方（AWS SDK、`java.nio.file.LinkOption`…）→ External。
  - enum_structure：Label-based（常量都是裸标签）/ Data-carrying（常量带参数、或枚举有字段/构造函数/方法/常量体），`enum_structure_reason` 给出依据。
  - arity：n_params × n_sets（常量数；`names`+INCLUDE 取 names 数、EXCLUDE 取总数−names、MATCH_* 不可数）。
  - `@EnumSource` 缺省 value 时枚举类型取第一个形参类型；`Outer.Inner.class` 与 `import a.b.Outer.Inner` 的嵌套枚举已解析。
- 复核（2026-09-17）：CsvSource 全 L0 属实——含常量的 8 条引用的都是 production/JDK 常量（`OzoneConfigKeys.*`、`SftpConstants.*`、`AclFileParser.*`、
  `DateFormat.DEFAULT`）→ hits_production，没有引用别的测试类。construction 改按目标参数类型细分：primitive/String → Literal-Primitive（335）；
  `Class<?>` → Literal-Metadata（1）；枚举 / JUnit 隐式转换的 JDK 类型（BigDecimal、File、Charset、LocalDate…）/ 带 String 工厂的项目类型 /
  `@ConvertWith` → 原记 **Literal-Converted**（24），**2026-10-05 并入 Literal-Primitive**（注解里写的仍是字面量，转换由 JUnit 注入时完成，不属于「需要执行逻辑才能得到参数值」；细分信息保留在 `param_kinds` 列的 `converted:` 前缀）；扩展注入的参数（DockerMockSmtp、MiniCluster）标 injected 不参与分类（`param_kinds` 列）。
- EnumSource：祖先类里的嵌套枚举（log4j2 `AbstractAsyncThreadContextTestBase.Mode`）现能解析 → L2；External 保留（11 条），结构按来源填：
  protobuf 生成（含 production(generated) 15 条）→ Data-carrying，AWS SDK → Data-carrying，`LinkOption`/`Thread.State`/Hive `TableType` → Label-based。
  `n_enum_constants` = 枚举总常量数；`n_sets` = 本测试实际用到的组数（无 names 时等于总数；INCLUDE 取 names 数；EXCLUDE 取总数−names；MATCH_* 不可数）。

## P. 小 source（2026-09-19）
- **arity 的 NOT_STATIC**：白名单外调用（production/JDK API 返回集合、helper 递归后仍不可数）、循环填充、条件分支、`filter/flatMap/limit/skip`、
  变量边界的 `range`、无初始化器或 `static {}` 填充的字段。修了 `new ArrayList<>(2)` 容量误当元素、非容器语句导致放弃两个小洞：
  MethodSource EXACT 3,608 → 3,640（69%）。不做下界。
- **@ArgumentsSource / @FieldSource**：parser 新增展开（`METHODSOURCE <Provider>.provideArguments()` / `FIELDSOURCE <Class>.<FIELD>`，
  `dfsAnalyzeScope` 让字段初始化器走同一套调用遍历；provideArguments 沿父类链找）；Java 侧 `ExtraProviders` 把两者接入 CC 与
  construction/dependency（`ArtifactWalker.analyzeField / countSetsOfField`，`CognitiveComplexityCalculator.forExpression`）；下游把 FIELDSOURCE
  当入口行。补跑 59 条（备份 `aaa_backup_phase4_20260919`）。结果 `full_minor/rq22_argumentssource_fieldsource_all.csv`：
  ArgumentsSource 24 OK（L1 20 = provider 是测试类的嵌套类、L4 4；CC>0 4 条；NOT_STATIC 15）；FieldSource 34 OK（L0 24 / L3 5 / L4 5；
  Literal 11 / Dynamic 23；EXACT 28）。未进 OK：accumulo 6 条在 `test/src/main/java`（非标准布局，无 AAA）、iceberg 1 条 `TestHelpers#ALL_VERSIONS` 定位失败。
- **@CsvFileSource**（48 条，`csvfilesource_analyzer.py`）：construction=File、dependency=File；资源按 classpath 规则定位（包目录 → 资源根），
  48 条全部找到；n_sets = 行数（减 numLinesToSkip / 空行 / # 注释 / 表头），median 487.5、max 3072；n_params 2–7；n_columns 与 n_params 一致。
- **@NullSource / @EmptySource / @NullAndEmptySource**（27 条）：不单独建表；并入主 source 表的 `extra_null_empty_sets`（+1/+1/+2）与
  `n_sets_total`（ValueSource 23 条、EnumSource 1 条）；2 条单独使用的在 `full_minor/rq22_null_empty_standalone.csv`（construction None、L0、n_sets 1/2）。

## Q. Arity 计数器升级（2026-09-19）
- provider 定位复核：`expr:NumberLiteral` 那批 123 条逐条与注解值比对，121 条正确、2 条是核对脚本误报——不是 correctness bug；
  原因归因不准是因为局部标量声明被记成第一失败原因，已改为不记录。
- 新规则：`Type.builder().add(..).add(..).build()`（链式与语句式）计数；保基数包装（unmodifiable*/copyOf/StreamSupport.stream/EnumSet.copyOf…）；
  固定 for / enhanced-for 与嵌套循环乘积（循环体只能是对被跟踪容器的 add，遇 if/try 即运行时）；lambda 体可数的 flatMap 取乘积；
  `range/rangeClosed` 与 for 边界支持 `static final` 常量及常量算术（含静态导入）；`limit/skip` 上游可数时精确；`EnumSet.allOf`、
  `Sets.cartesianProduct`；三目两边相等时取值；不碰容器的语句忽略，容器被传给别的方法则视为运行时填充。
- 状态拆分：**EXACT / RUNTIME_DEPENDENT / STATIC_UNSUPPORTED / UNRESOLVED_SOURCE**，`n_sets_fail_reason` 给第一失败点。
- MethodSource（5,274 OK）：EXACT 3,640 → **4,377（83%）**；RUNTIME_DEPENDENT 781（if/try/while 270、static 块填充字段 101、
  容器 set/remove 61、filter 等 55、production/JDK API 49、对象调用 42、容器交给 helper 填充 33、非常量循环/range 边界 45、
  flatMap 内层不可数 21…）；STATIC_UNSUPPORTED 75（非标准 for 形态 47、容器其它操作 13、`values()` 非枚举 11）；
  UNRESOLVED_SOURCE 41（找不到的名字 26、抽象 provider 13）。EXACT 的 n_sets median 3、p90 15、max 960（commons-numbers 嵌套循环乘积）。
- ArgumentsSource/FieldSource 表同步：EXACT 50 / RUNTIME_DEPENDENT 8。
- 2026-09-21 复核 `n_sets=0` 的 156 条：三处漏洞——① 字段只看 `static {}` 是否填充，没看 `@BeforeEach`/构造函数/任意方法里的 `data.add(...)`
  （commons-statistics `BaseDoubleStatisticTest` 一族 100 条，`Stream.builder()` + `data.forEach(d -> b.accept(..))`）；② `x.forEach(lambda)` 语句里
  lambda 对被跟踪容器的 accept 没被看到；③ `new X()` / `X.builder()` 对非集合类型也返回 0（uima `Suite.builder().build().stream()`）、
  双花括号匿名初始化返回 0（mina-sshd）。修法：字段"在声明类任意位置被 add/put/赋值/整个交给别的方法"即视为非静态（同时影响 construction：
  Literal 1,928 → 1,901）；forEach-lambda 只含 add/accept 时 = count(x)×adds，否则 RUNTIME；`new`=0 只对已知集合类型、`builder()`=0 只对
  Stream/Immutable* 系；匿名体 → STATIC_UNSUPPORTED。结果：n_sets=0 156 → 0；EXACT 4,377 → 4,317（RUNTIME 781 → 894）。
- EnumSource 的 `NOT_STATIC`（26 条）改为与 MethodSource 同一套状态：`mode = MATCH_ANY/ALL/NONE` 的 19 条把正则套在枚举常量名上数出来
  （commons-numbers Boost*Test），→ EXACT；7 条看不到枚举源码（protobuf 生成 4、外部 3）→ UNRESOLVED_SOURCE。现在 EXACT 736 / UNRESOLVED_SOURCE 7。
