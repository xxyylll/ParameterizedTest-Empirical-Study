#!/bin/bash
#
# 一键重跑 RQ1：底表 → PDAR 汇总 → 全部分析 → 全部图
#
# 用法：
#   cd rq1/code
#   ./run_rq1.sh                 # 用 PYTHON 环境变量指定解释器，缺省 python3
#   PYTHON=/path/to/python ./run_rq1.sh
#
# 依赖：pip install -r ../requirements.txt（注意 pandas<3）。
#
# 需要外部数据的三步在数据缺失时跳过，沿用仓库里已提交的产物：
#   [1] 重建底表 merged_data_219_ssk.csv   需要 PT_PARSER_SSK（parser 输出）与 PT_SSD（ssk 源码快照）
#   [3] Table 1 的 Test files 一列          需要 PT_PARSER_SSK
#   [4] PDAR 汇总 pdar_summary_ssk.csv      需要 PT_PDAR_RESULT（第一阶段逐提交表）
# 其余步骤只依赖仓库内的文件，任一步失败即停止。
#
# PDAR 的逐项目两阶段检测（需要逐个 clone 仓库，约 45 分钟）不在这里跑，见 README 第 4 节；
# 这里只做汇总。RQ2.1 也读同一份语料，若改动了语料，记得另跑 ../../rq2/code/run_rq2.sh。

set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
PY="${PYTHON:-python3}"

# 用 paths.py 判断外部数据是否就位（与各脚本同一套解析）
have() {
    "$PY" -c "
import os, sys
sys.path.insert(0, '../..')   # 本脚本在 rq1/code/
import paths
sys.exit(0 if all(os.path.exists(getattr(paths, k)) for k in sys.argv[1:]) else 1)
" "$@"
}

step() { echo; echo "==== [$1] $2"; }
skip() { echo "     跳过：$1 —— 沿用仓库里已提交的 $2"; }

step 1 "重建底表（ssk 快照）"
if have PARSER_SSK APACHE_PROJECTS; then "$PY" build_merged_ssk.py
else skip "缺 PT_PARSER_SSK / PT_SSD" "merged_data_219_ssk.csv"; fi

step 2 "语料自检（应为 N=175 / 采纳者 107）"
"$PY" rq1_bins.py

step 3 "Table 1"
if have PARSER_SSK; then "$PY" dataset_stats.py
else skip "缺 PT_PARSER_SSK" "dataset_stats.csv"; fi

step 4 "PDAR v4 汇总"
if have PDAR_RESULT; then (cd pdar && "$PY" calculate_pdar_v4.py)
else skip "缺 PT_PDAR_RESULT" "pdar_summary_ssk.csv"; fi

step 5 "Table 3（PAI / PDAR 按 Size / Age / Domain）"
"$PY" build_table3.py

step 6 "影响因素与多元 logistic 回归"
"$PY" adoption_factors.py

step 7 "category logistic 回归"
"$PY" category_logit.py

step 8 "图：PAI / PDAR 三联图"
"$PY" three_panel_figures.py

step 9 "图：分组采纳率"
"$PY" adoption_by_groups_figure.py

step 10 "描述统计、PAI / PDAR 分布与 PDAR 相关"
"$PY" rq1_descriptives.py

echo
echo "完成。结果见 $(cd ../results && pwd)"
