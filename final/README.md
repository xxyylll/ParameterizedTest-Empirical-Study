# Replication Package — An Empirical Study of Parameterized Tests in Apache Java Projects

本目录是论文的复现包。每个研究问题一个目录，**`code/` 放脚本，`results/` 放脚本产出的表、图与汇总文档**；
所有脚本都可在本目录内直接运行，不依赖原作者机器上的绝对路径。

论文里每个数字的出处见 **[`MANIFEST.md`](MANIFEST.md)**，完整方法学见 [`METHOD_complete.md`](METHOD_complete.md)。

## 目录结构

```
final/
├── README.md               本文件
├── MANIFEST.md             数字 → 来源文件 / 生成脚本的索引，以及踩过的坑
├── METHOD_complete.md      完整方法学
├── paths.py                全部外部路径的唯一解析处（环境变量见下）
├── requirements.txt        Python 依赖（pandas 必须 < 3.0）
├── requirements-recompute.txt   只在重建 RQ3 指标表时需要（tree-sitter）
├── project_name_map.json   仓库目录名 ↔ 项目显示名
├── corpus/                 项目清单：RQ1/RQ2.1 的 175 个、RQ3 的 46 个，以及语料收窄链条
├── tools/                  轻量 parser 的 jar；深度 parser 与 CCFinderSW 的版本与调用方式
├── rq1/   code/  results/  RQ1 采纳情况（175 个项目）            → rq1/README.md
├── rq2/   code/  results/  RQ2 parameter source 的分布与结构       → rq2/README.md
└── rq3/   code/  results/  RQ3 PT 与非 PT 的复杂度、各 source 的收益 → rq3/README.md
```

## 快速开始

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python paths.py                     # 列出各外部数据源是否就位（只核对结果的话一个都不需要）

cd rq1/code && ./run_rq1.sh && cd ../..     # RQ1：全部分析与图，并生成 rq1/results/RQ1_RESULTS.md
cd rq2/code && ./run_rq2.sh && cd ../..     # RQ2：RQ2.1 分布（有 parser 输出时）与 RQ2.2 分布图
cd rq3/code && ./run_rq3.sh && cd ../..     # RQ3：RQ3.1 与 RQ3.2 的全部分析与图
```

三个脚本在**没有任何外部数据**时也能跑完：需要外部数据的步骤会跳过并沿用仓库里已提交的产物，
其余步骤只读仓库内文件。RQ3 的两张指标表以 `.gz` 随包附带（`rq3/results/rq3_1/`），脚本会自动解压使用。

> **`requirements.txt` 的 pandas 上限是必需的。** pandas 3.0 移除了 statsmodels 0.14.x 依赖的内部 API，
> 装上 pandas 3 后 `rq1/code/category_logit.py` 会在 import 阶段就报错。请照 `requirements.txt` 安装，不要 `--upgrade`。

## 外部数据

只有从原始数据重建中间产物时才需要。全部经 `paths.py` 解析，可用环境变量覆盖（模板见 `.env.example`）；
路径缺失时脚本会提示该设哪个变量。

| 变量 | 内容 | 体积 | 用于 |
|---|---|---:|---|
| `PT_PARSER_SSK` | 轻量 parser 的逐项目 JSON（243 个） | ~1.5 GB | 重建 RQ1 底表与 Table 1、RQ2.1、RQ2.2 流水线 |
| `PT_SSD` | 外置盘根目录：源码快照 `apache-projects/`（含各项目的 AAA 轨迹）、CCFinderSW 输出 | ~55 GB | RQ2.2 流水线、重建 RQ3 指标表 |
| `PT_METRICS` | RQ3 指标表目录 | ~400 MB | 缺省时改用随包的 `.gz` |
| `PT_PDAR_RESULT` | PDAR 第一阶段的逐提交表 | 189 MB | 重算 PDAR 汇总 |
| `PT_MANUAL` | RQ2.2 人工标注表（1,497 行） | ~0.6 MB | IRR 抽样 |
| `PT_AAA_JAR` / `PT_JAVA` | 深度 parser 的 jar、JDK 21 | — | RQ2.2 流水线的 Java 分析器 |

大体积数据不随仓库分发（GitHub 单文件上限 100 MB），通过 DOI 归档提供。

## 从原始数据完整重算

```
1. tools/ 的两个 parser 扫源码快照      → parser_result_ssk/（轻量）与各项目的 AAA/（深度）
2. rq1/code/build_merged_ssk.py         → RQ1 底表；PDAR 另见 rq1/code/pdar/PDAR_METHOD.md 第 7 节
3. rq2/code/rq2_2/pipeline/run_rq22.sh  → RQ2.2 的 9 张交付表（约 1–2 小时）
4. rq3/code/run_rq3.sh --with-build     → RQ3 指标表（小时级）及其后全部分析
5. 各 RQ 的 run_rq*.sh                  → 全部分析、表与图
```

第 1 步需要完整的源码快照，第 3、4 步耗时以小时计。**只核对论文数字的话，直接读各 `results/` 下的文件即可。**

## 工具

| | 工具 | 用于 | 本仓库内 |
|---|---|---|---|
| 轻量 parser | `test-parser`（JavaParser，注解级） | RQ1、RQ2.1 | jar + SHA-256（源码已遗失，jar 可反编译核验） |
| 深度 parser | `Javalang-analyzing-cli`（Eclipse JDT，完整 AAA 轨迹） | RQ2.2、RQ3 | 第三方仓库，钉版本 v1.3.2 |
| 克隆检测 | CCFinderSW 1.0 | RQ3 重复率 | 调用参数见 `tools/README.md` |

轻量 parser 的输出另经 200 条分层人工样本核验，见 `rq1/results/parser_validation/`。
