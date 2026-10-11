# RQ2 — parameter source 的分布与结构

- **RQ2.1**：175 个项目的全部 PT 用了哪些 parameter source，JUnit 4 与 JUnit 5 分开统计。
- **RQ2.2**：46 个项目（`../corpus/rq3_corpus_46.txt`）里 JUnit 5 PT 的各种 source，在 construction、
  dependency、structure、arity 四个维度上的刻画。判定规则见 `code/rq2_2/CRITERIA_construction_dependency.md`。

## 运行

```bash
cd code
./run_rq2.sh                    # RQ2.1（有 parser 输出时重算）与 RQ2.2 的三张分布图
./run_rq2.sh --with-pipeline    # 先跑 RQ2.2 全量流水线重建 9 张交付表（约 1–2 小时），再画图
```

## RQ2.1

| `code/rq2_1/` | `results/rq2_1/` | 说明 |
|---|---|---|
| `build_rq2_1_distribution.py` | `rq2_1_source_distribution_ssk.csv` | source 分布，JUnit 4 与 JUnit 5 分开（需 `PT_PARSER_SSK`） |
| `method_source_analysis.py` | — | 判定一个测试是否为 PT 的共用函数（RQ3.1 的解析覆盖率也引用它） |

## RQ2.2

### 交付表：`code/rq2_2/pipeline/run_rq22.sh` → `results/rq2_2/`

| 交付表 | 内容 |
|---|---|
| `rq22_methodsource_all.csv` | MethodSource：construction / dependency / structure（CC、helper depth）/ arity |
| `pt_methodsource_structure.csv`、`pt_methodsource_helper_depth.csv` | MethodSource 的 structure 与 helper depth 明细 |
| `rq22_valuesource_all.csv`、`rq22_csvsource_all.csv`、`rq22_enumsource_all.csv` | 三种注解型 source |
| `rq22_csvfilesource_all.csv` | CsvFileSource（读资源文件计行） |
| `rq22_argumentssource_fieldsource_all.csv` | ArgumentsSource / FieldSource |
| `rq22_null_empty_standalone.csv` | 单独使用的 `@NullSource` / `@EmptySource` / `@NullAndEmptySource` |

另附 `pt_methodsource_structure_validated379.csv`：379 条 MethodSource PT 的 pilot 样本（31 个项目，每项目上限 24 条）
经人工逐条核验后的 structure 表，供 RQ3.2 的 `rq32_*` 分析与标注一致性检查使用。它不由流水线生成，
不要和全量的 `pt_methodsource_structure.csv`（5,508 行）混用。

流水线（`code/rq2_2/pipeline/`）由 11 个 Python 脚本与 `java/` 下的 9 个 Java 分析器组成，Java 依赖深度 parser
`Javalang-analyzing-cli` 的 jar 提供 JDT。顺序与各步说明见 `run_rq22.sh` 头部。输入是 parser 输出
（`PT_PARSER_SSK`）与各项目的源码快照和 AAA 轨迹（`PT_SSD`），中间产物写到 `PT_RQ22_WORK`（不入库）。

> 在新机器上从零重跑整条流水线，MethodSource 的三张表与仓库里的版本逐字节相同。CsvSource 表会比仓库版多出
> `extra_null_empty_sets` 等三列（值全为 0）：早先的手工流程在并入 Null/Empty source 之后又单独重跑过一次 CsvSource，
> 交付表因此缺了这三列；该 source 没有搭配 Null/Empty 的测试，内容不受影响。

### 分布图与 IRR

| `code/rq2_2/` | `results/rq2_2/` | 说明 |
|---|---|---|
| `plot_construction_distribution.py` | `construction_distribution.{png,pdf,csv}` | 各 source 的 construction 分布 |
| `plot_dependency_distribution.py` | `dependency_distribution.{png,pdf,csv}` | 各 source 的 dependency 分布 |
| `plot_nsets_distribution.py` | `nsets_distribution.{png,pdf}`、`nsets_summary.csv` | 参数组数分布 |
| `irr/draw_irr_sample.py` | `irr/sample_items.csv`、`irr/packet_R{1,2,3}.csv` | inter-rater 信度抽样（150 条，种子固定；需 `PT_MANUAL`） |
| `irr/build_packets.py` 等 | `irr/*_review_packet.md` | 发给三位评审人的审阅包（含源码片段；需 `PT_SSD`）。分发时按人名重命名过 |
| `irr/rater_guide.md` | — | 评审说明 |

方法文档：`code/rq2_2/CRITERIA_construction_dependency.md`（判定规则）、`PAPER_NOTES_methodology.md`
（`n_sets_status` 四分口径等）、`TOOLCHAIN_FIXES_2026-09.md`（工具链修订记录）。
