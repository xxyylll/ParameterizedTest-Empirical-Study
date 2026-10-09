#!/bin/bash
#
# PDAR 批处理：逐个项目 clone 全量 → 分析 → 立刻删除。
#
# 为什么是 clone-跑-删：PDAR 需要**全量** git 历史（`git log --all` 与
# `git diff-tree` 在 --depth 1 的浅克隆上只能看到 1 个提交，PDAR 会算成 0），
# 而 117 个项目的全量克隆合计几十 GB，远超可用磁盘。所以一次只落地一个仓库，
# 分析完就删。中断后重跑会自动跳过已有结果的项目。
#
# 用法：
#   ./batch_pdar.sh                  # 论文口径（git 默认 3 行上下文）
#   ./batch_pdar.sh --context 25     # 敏感性分析：25 行上下文，结果写到 result_U25/
#   ./batch_pdar.sh --projects a.txt # 只跑清单里的项目（敏感性分析抽样用）
#
# 跑完接 calculate_pdar.py 做汇总（同样传 --context）。

set +e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT=3
PROJECT_LIST="$HERE/pt_projects_ssk.txt"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --context)  CONTEXT="$2"; shift 2 ;;
        --projects) PROJECT_LIST="$2"; shift 2 ;;
        -h|--help)  sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 工作区与输出目录都走 paths.py，保证与 Python 侧一致
_paths=$(python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$HERE', '..', '..'))
from paths import PDAR_WORK, PDAR_RESULT
print(PDAR_WORK); print(PDAR_RESULT)
")
WORK_DIR=$(echo "$_paths" | sed -n 1p)
RESULT_BASE=$(echo "$_paths" | sed -n 2p)
if [[ -z "$WORK_DIR" || -z "$RESULT_BASE" ]]; then
    echo "错误：无法从 paths.py 解析目录。请确认能 import final/paths.py。"; exit 1
fi
if [[ "$CONTEXT" == "3" ]]; then RESULT_DIR="$RESULT_BASE"; else RESULT_DIR="${RESULT_BASE}_U${CONTEXT}"; fi

mkdir -p "$WORK_DIR" "$RESULT_DIR"

# 不用 mapfile：macOS 自带 bash 3.2 没有这个内建命令
PROJECTS=()
while IFS= read -r line; do
    [[ -n "${line// }" ]] && PROJECTS+=("$line")
done < "$PROJECT_LIST"
TOTAL=${#PROJECTS[@]}

echo "=========================================="
echo "PDAR 批处理"
echo "=========================================="
echo "项目数      : $TOTAL"
echo "diff 上下文 : -U$CONTEXT $( [[ "$CONTEXT" == "3" ]] && echo '(论文口径)' || echo '(敏感性分析)' )"
echo "克隆工作区  : $WORK_DIR"
echo "结果目录    : $RESULT_DIR"
echo ""

processed=0; failed=0; skipped=0

for ((i = 0; i < TOTAL; i++)); do
    project="${PROJECTS[$i]}"

    if [[ -f "$RESULT_DIR/${project}_commits.csv" ]]; then
        echo "[$((i+1))/$TOTAL] $project — 已有结果，跳过"
        ((skipped++)); continue
    fi

    # 仓库 URL 取自 pdar_repo_map.csv —— 与 Python 侧同一份来源
    git_url=$(awk -F, -v p="$project" 'NR>1 && $1==p {print $3; exit}' "$HERE/pdar_repo_map.csv")
    if [[ -z "$git_url" ]]; then
        echo "[$((i+1))/$TOTAL] $project — ✗ pdar_repo_map.csv 里没有这个项目"
        ((failed++)); continue
    fi

    project_dir="$WORK_DIR/$project.git"
    echo "[$((i+1))/$TOTAL] $project"
    echo "  clone  $git_url  (--bare)"
    rm -rf "$project_dir"

    # --bare：PDAR 全程只用 git log / diff-tree / show，不需要工作树。
    # 省掉检出可观地缩短 clone 时间、也少占一半磁盘 —— 大仓库上差别很明显。
    if ! git clone --quiet --bare "$git_url" "$project_dir" 2>/dev/null || [[ ! -d "$project_dir/objects" ]]; then
        echo "  ✗ clone 失败"
        rm -rf "$project_dir"; ((failed++)); continue
    fi

    echo "  分析（三层检测，-U$CONTEXT）..."
    if python3 "$HERE/find_pt_developers.py" "$project" \
            --context "$CONTEXT" --repo "$project_dir" --out "$RESULT_DIR" >/dev/null; then
        echo "  ✓ 完成"
        ((processed++))
    else
        echo "  ✗ 分析失败"
        ((failed++))
    fi

    rm -rf "$project_dir"          # 立刻释放磁盘，这是本脚本存在的理由
done

echo ""
echo "=========================================="
echo "完成：新跑 $processed，跳过 $skipped，失败 $failed"
echo ""
echo "下一步汇总："
echo "  python3 $HERE/calculate_pdar.py --context $CONTEXT"
echo "=========================================="
rmdir "$WORK_DIR" 2>/dev/null || true
