#!/bin/bash
#
# 一键重跑 RQ2：RQ2.1（parameter source 的总体分布）与 RQ2.2（各 source 的结构刻画）
#
# 用法：
#   cd rq2/code
#   ./run_rq2.sh                    # 从已有的 RQ2.2 交付表重画分布图；RQ2.1 有 parser 输出时重算
#   ./run_rq2.sh --with-pipeline    # 先跑 RQ2.2 全量流水线重建 9 张交付表（约 1–2 小时），再画图
#   PYTHON=/path/to/python ./run_rq2.sh
#
# 外部数据：
#   RQ2.1                       PT_PARSER_SSK（parser 输出），缺了就跳过，沿用已提交的结果
#   RQ2.2 流水线（--with-pipeline）  PT_PARSER_SSK、PT_SSD（源码快照与 AAA 轨迹）、PT_AAA_JAR、JDK 21，
#                               见 rq2_2/pipeline/run_rq22.sh 头部说明
#   RQ2.2 分布图                 只读仓库里的交付表
#
# IRR：draw_irr_sample.py 从人工标注表（rq2/results/rq2_2/manual_coding/）抽 150 条（种子固定），
# compute_irr.py 再从样本与评审人答卷算 κ。审阅包（build_packets.py）要读源码快照，不在这里重跑。

set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
PY="${PYTHON:-python3}"
PIPE=0
[[ "$1" == "--with-pipeline" ]] && PIPE=1

SSK=$("$PY" -c "import sys; sys.path.insert(0, '../..'); import paths; print(paths.PARSER_SSK)")
step() { echo; echo "==== $*"; }
run()  { echo "  $*"; "$PY" "$@" > /tmp/run_rq2_step.log 2>&1 || { cat /tmp/run_rq2_step.log; echo "失败：$*"; exit 1; }; }

step "1. RQ2.1"
if [[ -e "$SSK" ]]; then (cd rq2_1 && run build_rq2_1_distribution.py)
else echo "  跳过：缺 PT_PARSER_SSK —— 沿用已提交的 rq2_1_source_distribution_ssk.csv"; fi

if [[ $PIPE == 1 ]]; then
    step "2a. RQ2.2 全量流水线（重建交付表）"
    (cd rq2_2/pipeline && PYTHON="$PY" ./run_rq22.sh)
fi

step "2. RQ2.2 分布图"
cd rq2_2
run plot_construction_distribution.py
run plot_dependency_distribution.py
run plot_nsets_distribution.py

step "3. RQ2.2 IRR"
(cd irr && run draw_irr_sample.py && run compute_irr.py)

echo
echo "完成。结果见 $(cd ../../results && pwd)"
