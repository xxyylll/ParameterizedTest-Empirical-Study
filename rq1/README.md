# RQ1 — 参数化测试的采纳情况

175 个项目（语料构成见 `../corpus/README.md`），其中 107 个采纳了 PT。
**全部结果的汇总见 [`results/RQ1_RESULTS.md`](results/RQ1_RESULTS.md)**，由脚本自动生成，不要手改。

## 运行

```bash
cd code
./run_rq1.sh            # 依次跑全部分析与作图，最后重新生成 results/RQ1_RESULTS.md
```

需要外部数据的三步在缺数据时跳过、沿用已提交的产物：重建底表（`PT_PARSER_SSK` + `PT_SSD`）、
Table 1 的 Test files 一列（`PT_PARSER_SSK`）、PDAR 汇总（`PT_PDAR_RESULT`）。

## 代码与产出

| `code/` | `results/` | 说明 |
|---|---|---|
| `rq1_bins.py` | — | **全部分组口径的唯一定义**：语料筛选、Size / Age 分档、Domain 映射。其余脚本都从它导入 |
| `build_merged_ssk.py`（读 `project_metadata.csv`） | `merged_data_219_ssk.csv` | 项目级底表（计数取自 ssk 快照），由 `rq1_bins.py` 筛成 175 个 |
| `dataset_stats.py` | `dataset_stats.csv` | 论文 Table 1 |
| `build_table3.py` | `table3_pai_pdar.csv` | Table 3：PAI / PDAR 按 Size / Age / Domain 分组，KW 检验（全部组与仅 n > 6 两种口径） |
| `adoption_factors.py` | `adoption_factors.csv` | 影响因素：规模、Age / Domain 与采纳的卡方（含排除小组口径）、JUnit 版本、套件规模，及多元 logistic 回归 |
| `category_logit.py` | `category_logit_results.csv` | category 的 logistic 回归（N = 169） |
| `adoption_by_groups_figure.py` | `pt_adoption_by_groups.{png,pdf}` | 采纳率按 Size / Age / Domain |
| `three_panel_figures.py` | `rq1_pai_three_panel.{png,pdf}`、`rq1_pdar_three_panel.{png,pdf}` | PAI、PDAR 按 Size / Age / Domain 的三联图 |
| `build_rq1_results.py` | `RQ1_RESULTS.md` | 汇总文档：文中每个数字都由脚本从上面的产物计算或读取 |
| `parser_validation/draw_parser_validation.py` | `parser_validation/parser_validation_sample.csv` | parser 人工核验的 200 条分层样本（PT 100 + 非 PT 100） |
| `pdar/` | `pdar_summary_ssk.csv`、`pdar/` | PDAR v4 流水线，见下 |
| `run_rq1.sh` | — | 一键重跑 |

## PDAR

**PDAR = 改过 PT 的开发者 / 改过测试代码的开发者**（%），只在采纳者上计算，中位数 15.62%（n = 107）。
方法、验证、v3 → v4 的对比与复现命令全部见 [`code/pdar/PDAR_METHOD.md`](code/pdar/PDAR_METHOD.md)。

| `code/pdar/` | 说明 |
|---|---|
| `pdar_v4_commit_table.py` | 第一阶段：逐提交表（提交集合、作者、是否碰过测试） |
| `pdar_v4_method_level.py`、`pt_spans.py` | 第二阶段：改动行 ∩ 参数化测试区间，判定每个提交是否改过 PT |
| `calculate_pdar_v4.py` | 汇总成项目级 PDAR → `results/pdar_summary_ssk.csv` |
| `batch_pdar_v4.py` | 批处理：逐个项目 clone → 分析 → 删除 |
| `pdar_repo_map.csv`、`pt_projects_ssk.txt` | 项目 → 仓库 URL；项目清单 |
| `tests/` | 端到端单元测试（24 个） |

`results/pdar/result_v4/` 是第二阶段的逐项目输出，`result_v4_pickaxe/` 是带 pickaxe 的一轮（只提供记录用的
`core_pdar_pickaxe` 列），`pdar_v3_published.csv` 是 v3 的论文数字。第一阶段的逐提交表（189 MB）不随包分发。
