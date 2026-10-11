#!/bin/bash
#
# 一键重跑 RQ3：RQ3.1（PT vs 非 PT 的规模 / 复杂度 / 重复率，BH 校正，森林图与热力图）
#             RQ3.2（MethodSource / 跨 source / EnumSource / 摊销）
#
# 用法：
#   cd final/rq3/code
#   ./run_rq3.sh                 # 从指标表开始重跑全部分析与作图
#   ./run_rq3.sh --with-build    # 先从源码快照与 AAA 轨迹重建指标表（小时级），再跑全部分析
#   PYTHON=/path/to/python ./run_rq3.sh
#
# 指标表：RQ3 的全部分析只依赖两张表 ——
#   test_metrics_all_46projects_v2.csv   每个测试一行，LOC / CC / CCTR / DUP%（self / helper / total 三层）
#   test_helper_detail_46projects.csv    每个（测试, helper）一行，RQ3.2 摊销分析用
# 它们由 --with-build 那一段生成，写到 PT_METRICS 目录。仓库在 ../results/rq3_1/ 下附了两者的 .gz；
# 若 PT_METRICS 下没有，本脚本把 .gz 解压到 PT_RQ3_WORK（缺省 <repo>/rq3_work）并改用它。
#
# --with-build 需要：PT_SSD（源码快照与 AAA 轨迹、CCFinderSW 输出）、tree-sitter（../../requirements-recompute.txt）。
# 在当前快照上重建出的指标表，与仓库附带的版本只差 3 行（druid 的 3 个非 PT 测试，helper CCTR 的 N 分量各 +1），
# 不影响任何结果。仓库附带的是产出论文数字时用的那一版。
#
# parse_success_rate.py 还需要 PT_PARSER_SSK（parser 输出），缺了就跳过。

set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
PY="${PYTHON:-python3}"
BUILD=0
[[ "$1" == "--with-build" ]] && BUILD=1

cfg=$("$PY" -c "
import sys, os; sys.path.insert(0, '../..')
import paths
print(paths.METRICS_DIR); print(paths.PARSER_SSK); print(paths.RQ3_1_RESULTS)
print(os.environ.get('PT_RQ3_WORK', os.path.join(paths.REPO, 'rq3_work')))
")
METRICS=$(echo "$cfg" | sed -n 1p); SSK=$(echo "$cfg" | sed -n 2p)
R31=$(echo "$cfg" | sed -n 3p); WORK=$(echo "$cfg" | sed -n 4p)
TABLES="test_metrics_all_46projects_v2.csv test_helper_detail_46projects.csv"

step() { echo; echo "==== $*"; }
run()  { echo "  $*"; "$PY" "$@" > /tmp/run_rq3_step.log 2>&1 || { cat /tmp/run_rq3_step.log; echo "失败：$*"; exit 1; }; }

if [[ $BUILD == 1 ]]; then
    step "0. 重建指标表 → $METRICS（小时级）"
    (cd rq3_1 && run build_test_metrics_unified.py && run build_test_dup_metrics.py && run build_provider_dup_metrics.py \
              && run build_helper_detail.py && run merge_metrics_and_dup_v2.py)
fi

missing=0
for t in $TABLES; do [[ -f "$METRICS/$t" ]] || missing=1; done
if [[ $missing == 1 ]]; then
    step "指标表不在 $METRICS，改用仓库附带的 .gz（解压到 $WORK）"
    mkdir -p "$WORK"
    for t in $TABLES; do [[ -f "$WORK/$t" ]] || gunzip -c "$R31/$t.gz" > "$WORK/$t"; done
    export PT_METRICS="$WORK"
fi

step "1. RQ3.1"
cd rq3_1
if "$PY" -c "import os,sys; sys.exit(0 if os.path.exists('$SSK') else 1)"; then run parse_success_rate.py
else echo "  跳过 parse_success_rate.py：缺 PT_PARSER_SSK —— 沿用已提交的 parse_success_rate.csv"; fi
run rq3_bh_correction.py --cctr eq
run rq3_bh_correction.py --cctr orig
for s in plot_rq3_forest.py plot_rq3_heatmap_portrait.py; do
    run $s --junit5 --cctr orig
    run $s --junit5 --cctr eq
done
cd ..

step "2. RQ3.2"
cd rq3_2/methodsource
run build_rq32_dataset.py                       # 379 条人工核验样本
run build_rq32_dataset.py --full                # 全量 5,508 条
run analyze_rq32.py
run analyze_rq32.py --prefix rq32_full
run plot_rq32.py
run plot_rq32.py --prefix rq32_full
run check_label_agreement.py
cd ../cross_source
run build_cross_source_dataset.py && run analyze_cross_source.py && run plot_cross_source.py
cd ../enumsource
run build_enumsource_dataset.py && run analyze_enumsource.py && run plot_enumsource.py
cd ../amortization                              # 读 cross_source 的产物，必须排在它之后
run build_amortization_dataset.py && run analyze_amortization.py && run plot_amortization.py
cd ..
run make_result_appendix.py                     # 用最新产物重写 5 份 FINDINGS 文末的附录
cd ..

echo
echo "完成。结果见 $(cd ../results && pwd)"
