#!/bin/bash
#
# RQ2.2 全量流水线：从 parser 输出与 AAA 轨迹，重建 rq2/results/rq2_2/ 下的 9 张交付表。
#
#   rq22_methodsource_all.csv            MethodSource（construction / dependency / structure / arity）
#   pt_methodsource_structure.csv        MethodSource 的 structure 明细（CC、helper depth 等）
#   pt_methodsource_helper_depth.csv     MethodSource 的 helper depth 明细
#   rq22_valuesource_all.csv             ValueSource
#   rq22_csvsource_all.csv               CsvSource
#   rq22_enumsource_all.csv              EnumSource
#   rq22_csvfilesource_all.csv           CsvFileSource
#   rq22_argumentssource_fieldsource_all.csv   ArgumentsSource / FieldSource
#   rq22_null_empty_standalone.csv       单独使用的 @NullSource / @EmptySource / @NullAndEmptySource
#
# 用法：
#   ./run_rq22.sh                    # 结果写到 rq2/results/rq2_2/
#   ./run_rq22.sh --out /some/dir    # 写到别处（用于和已提交结果比对）
#
# 需要（都经 paths.py 解析，可用环境变量覆盖）：
#   PT_PARSER_SSK  轻量 parser 的逐项目 JSON            PT_SSD  源码快照与各项目的 AAA/ 轨迹
#   PT_AAA_JAR     Javalang-analyzing-cli 的 fat jar（提供 JDT；Java 分析器的编译与运行都要）
#   PT_JAVA        java（JDK 21）；javac 取同一 JDK 下的
#   PT_RQ22_WORK   中间产物目录（缺省 <repo>/rq22_work，约 20 MB，不入库）
#
# 顺序（与产出已提交结果时一致）：
#   1. MethodSource：清单 → targets → CC（Java）→ construction / dependency（Java）→ helper depth（AAA）
#      → dependency v2 → 合并 → 交付表
#   2. ValueSource / CsvSource / EnumSource：清单 → targets → 各自的 Java 分析器 → 交付表
#   3. ArgumentsSource / FieldSource：同 1 的整条链，最后转成交付表
#   4. CsvFileSource：csvfilesource_analyzer.py（直接读资源文件，不走 Java）
#   5. add_null_empty_sets.py：把 @NullSource / @EmptySource 带来的额外参数组并入各主表（原地改写），
#      并单独输出只用这三种注解的测试
# 早先的手工流程里，CsvSource 在第 5 步之后又单独重跑过一次，交付表因此缺了第 5 步加的三列；
# 本脚本按上面的顺序统一跑，CsvSource 表会带上这三列（该 source 没有搭配 Null/Empty 的测试，值全为 0）。

set -e
set -o pipefail   # 每步都接了 | tail，没有它前面的失败会被管道吞掉
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
PY="${PYTHON:-python3}"
OUT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --out) OUT="$2"; shift 2 ;;
        -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 从 paths.py 取配置（与各 Python 脚本同一套解析）
cfg=$("$PY" -c "
import sys; sys.path.insert(0, '../../../..')
import paths
for k in ('RQ22_WORK', 'AAA_JAR', 'JAVA_BIN', 'RQ2_2_RESULTS', 'PARSER_SSK', 'APACHE_PROJECTS'): print(getattr(paths, k))
")
WORK=$(echo "$cfg" | sed -n 1p); JAR=$(echo "$cfg" | sed -n 2p); JAVA=$(echo "$cfg" | sed -n 3p)
RESULTS=$(echo "$cfg" | sed -n 4p); SSK=$(echo "$cfg" | sed -n 5p); AP=$(echo "$cfg" | sed -n 6p)
OUT="${OUT:-$RESULTS}"
for x in "$JAR" "$SSK" "$AP"; do
    [[ -e "$x" ]] || { echo "缺少输入：$x（见脚本头部的环境变量说明）"; exit 1; }
done
JAVAC="$(dirname "$(command -v "$JAVA" || echo "$JAVA")")/javac"
[[ -x "$JAVAC" ]] || JAVAC=javac

mkdir -p "$WORK" "$OUT"
CP="$WORK/java_out:$JAR"
JOPT="-Dcognitive.cache.dir=$WORK/file_index_cache"
step() { echo; echo "==== $* ($(date '+%H:%M'))"; }

step "编译 Java 分析器"
rm -rf "$WORK/java_out"; mkdir -p "$WORK/java_out"
"$JAVAC" -encoding UTF-8 -nowarn -cp "$JAR" -d "$WORK/java_out" java/*.java

# 一条完整的 MethodSource 式链：targets → CC → construction/dependency → helper depth → dependency v2 → merge → 交付表
methodsource_chain() {
    "$PY" build_cognitive_targets_v2.py | tail -2
    "$JAVA" $JOPT -cp "$CP" ProviderCognitiveComplexity "$RQ22_OUT_DIR/cognitive_targets_v2.csv" "$RQ22_OUT_DIR/cognitive_complexity_v2_raw.csv" | tail -1
    "$JAVA" $JOPT -cp "$CP" ConstructionDependencyClassifier "$RQ22_OUT_DIR/cognitive_targets_v2.csv" "$RQ22_OUT_DIR/construction_dependency_raw.csv" | tail -1
    "$PY" build_helper_depth.py | grep -v '^\s*$' | tail -3
    "$PY" build_dependency_v2.py | tail -2
    "$PY" merge_results.py | tail -1
    "$PY" build_final_table.py | head -2
}

step "1. MethodSource"
export RQ22_OUT_DIR="$WORK/full" RQ22_SAMPLE_CSV="$WORK/full/methodsource_all.csv" RQ22_PROJECTS=ALL RQ22_PARAM_SOURCE=MethodSource
"$PY" build_full_methodsource_list.py
methodsource_chain

for SRC in ValueSource CsvSource EnumSource; do
    lower=$(echo "$SRC" | tr 'A-Z' 'a-z')
    step "2. $SRC"
    export RQ22_OUT_DIR="$WORK/full_$lower" RQ22_SAMPLE_CSV="$WORK/full_$lower/${lower}_all.csv" RQ22_PROJECTS=ALL RQ22_PARAM_SOURCE=$SRC
    "$PY" build_full_source_list.py "$RQ22_SAMPLE_CSV" "$SRC" | head -1
    "$PY" build_cognitive_targets_v2.py | tail -1
    "$JAVA" $JOPT -cp "$CP" ${SRC}Analyzer "$RQ22_OUT_DIR/cognitive_targets_v2.csv" "$RQ22_OUT_DIR/${lower}_raw.csv" | tail -1
    "$PY" build_annotation_final_tables.py "$SRC"
done

step "3. ArgumentsSource / FieldSource"
export RQ22_OUT_DIR="$WORK/full_minor" RQ22_SAMPLE_CSV="$WORK/full_minor/minor_all.csv" RQ22_PROJECTS=ALL RQ22_PARAM_SOURCE=ArgumentsSource,FieldSource
"$PY" build_full_source_list.py "$RQ22_SAMPLE_CSV" ArgumentsSource,FieldSource,CsvFileSource,NullSource,EmptySource,NullAndEmptySource | head -1
methodsource_chain
"$PY" build_annotation_final_tables.py Minor

step "4. CsvFileSource"
"$PY" csvfilesource_analyzer.py | tail -2

step "5. 并入 @NullSource / @EmptySource"
"$PY" add_null_empty_sets.py

step "拷贝交付表 → $OUT"
for f in full/rq22_methodsource_all.csv full/pt_methodsource_structure.csv full/pt_methodsource_helper_depth.csv \
         full_valuesource/rq22_valuesource_all.csv full_csvsource/rq22_csvsource_all.csv full_enumsource/rq22_enumsource_all.csv \
         full_csvfilesource/rq22_csvfilesource_all.csv full_minor/rq22_argumentssource_fieldsource_all.csv \
         full_minor/rq22_null_empty_standalone.csv; do
    cp "$WORK/$f" "$OUT/"
    echo "  $(basename "$f")"
done
echo
echo "完成。若写到了 rq2/results/rq2_2/，接着重画分布图：cd .. && python plot_construction_distribution.py 等"
