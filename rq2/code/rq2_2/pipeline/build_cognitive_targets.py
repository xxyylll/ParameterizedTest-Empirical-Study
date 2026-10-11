#!/usr/bin/env python3
"""
从已经匹配成功的 helper-depth 结果里，反查每个 provider 在源码里的真实位置
（声明类 -> 文件路径, 起止行号），生成一份清单交给 Java 端的 CognitiveComplexityCli 用。

只处理 pt_methodsource_helper_depth.csv 里已经 ok 的 312 行（用它已经验证过的
AAA 索引 / METHODSOURCE 抽取逻辑，不重新发明一遍匹配规则）。
"""
# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_helper_depth import (AAA_ROOT, PILOT_PROJECTS, build_aaa_index)

# v3（build_cognitive_targets_v2.py）只从本文件复用 build_file_index；下面的 main() 是早期 pilot 版本，保留作对照
OUT_DIR = _paths.RQ22_WORK
METHODSOURCE_LINE_RE = re.compile(r"^METHODSOURCE\s+(.+)\.([A-Za-z_$][A-Za-z0-9_$]*)\(\)#\[(\d+)-(\d+)\]$")


def resolve_source_file(project, declaring_class, file_index):
    """declaring_class 形如 pkg.Outer.Inner 或 pkg.Outer；Java 文件名跟外层类走。"""
    parts = declaring_class.split(".")
    # 找到第一个大写开头的段作为文件名对应的外层类
    top_idx = None
    for i, p in enumerate(parts):
        if p[:1].isupper():
            top_idx = i
            break
    if top_idx is None:
        top_idx = len(parts) - 1
    top_class = parts[top_idx]
    pkg_path = "/".join(parts[:top_idx])

    candidates = file_index.get(top_class, [])
    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        # 优先选路径里包含完整包路径的那个
        for c in candidates:
            if pkg_path and pkg_path.replace(".", "/") in c.replace(os.sep, "/"):
                return c, None
        return candidates[0], f"ambiguous:{len(candidates)}_candidates"
    return None, "file_not_found"


def build_file_index(project):
    """project 源码树里 简单类名(不含包名) -> [绝对路径,...] 的索引。"""
    root = os.path.join(AAA_ROOT, project)
    index = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过输出目录和构建产物，避免重复/生成代码干扰
        dirnames[:] = [d for d in dirnames if d not in ("AAA", "target", "build", ".git")]
        for fn in filenames:
            if fn.endswith(".java"):
                simple = fn[:-len(".java")]
                index.setdefault(simple, []).append(os.path.join(dirpath, fn))
    return index


def main():
    src_csv = os.path.join(OUT_DIR, "pt_methodsource_helper_depth.csv")
    rows = list(csv.DictReader(open(src_csv, encoding="utf-8")))
    print(f"输入行数: {len(rows)}", file=sys.stderr)

    aaa_cache = {}
    file_index_cache = {}
    manifest = []
    problems = []

    for row in rows:
        project = row["project"]
        if project not in aaa_cache:
            aaa_cache[project] = build_aaa_index(project)
        index, test_classes, aaa_dir = aaa_cache[project]
        if project not in file_index_cache:
            file_index_cache[project] = build_file_index(project)
        file_index = file_index_cache[project]

        json_path = None
        # test_class 字段里存的是完整 fqcn，AAA 索引的 key 也是 fqcn；直接查
        key = (row["test_class"], row["test_name"])
        if key in index:
            json_path = os.path.join(aaa_dir, index[key])
        else:
            problems.append({**row, "reason": "reindex_lookup_failed"})
            continue

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        seq = data.get("parsedStatementsSequence", [])

        seq_no = 0
        for line in seq:
            stripped = line.strip()
            if len(line) - len(line.lstrip(" ")) != 0:
                continue
            m = METHODSOURCE_LINE_RE.match(stripped)
            if not m:
                continue
            declaring_class, method_name, start_line, end_line = m.groups()
            seq_no += 1
            src_file, note = resolve_source_file(project, declaring_class, file_index)
            entry = {
                "project": project,
                "test_class": row["test_class"],
                "test_name": row["test_name"],
                "provider_seq": seq_no,
                "declaring_class": declaring_class,
                "method_name": method_name,
                "start_line": start_line,
                "end_line": end_line,
                "source_file": src_file or "",
            }
            manifest.append(entry)
            if note:
                problems.append({**entry, "reason": note})

    out_csv = os.path.join(OUT_DIR, "cognitive_targets.csv")
    fields = ["project", "test_class", "test_name", "provider_seq", "declaring_class",
              "method_name", "start_line", "end_line", "source_file"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(manifest)

    prob_csv = os.path.join(OUT_DIR, "cognitive_targets_problems.csv")
    with open(prob_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["reason"])
        w.writeheader()
        for p in problems:
            w.writerow({k: p.get(k, "") for k in fields + ["reason"]})

    print(f"manifest: {out_csv} ({len(manifest)} providers)")
    print(f"problems: {prob_csv} ({len(problems)} rows)")


if __name__ == "__main__":
    main()
