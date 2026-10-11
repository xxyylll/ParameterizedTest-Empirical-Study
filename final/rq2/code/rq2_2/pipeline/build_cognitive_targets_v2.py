#!/usr/bin/env python3
"""
Cognitive Complexity 的目标清单 v3：测试方法自己的文件位置优先直接读 parser_result_ssk
（243 个项目现成的 filePath/methodName/annotations，不用扫文件系统），只有匹配不上
（有歧义 / 完全没找到）时才退回到按类名扫项目源码树那条路（build_file_index）。

provider 方法本身（如果不在测试类自己的文件里）仍然交给 Java 端
(ProviderCognitiveComplexity.java) 去找——那边现在加了磁盘缓存的类名索引，
批量跑多个项目/多次重跑时不用每次重新扫文件系统。
"""

# 向上找到 final/（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_helper_depth import AAA_ROOT, load_pilot_sample
from build_cognitive_targets import build_file_index

OUT_DIR = os.environ.get("RQ22_OUT_DIR", _paths.RQ22_WORK)
SSK_DIR = _paths.PARSER_SSK
OLD_PREFIX = "/Volumes/SSK Drive/apache-projects/"
NEW_PREFIX = _paths.APACHE_PROJECTS.rstrip("/") + "/"   # parser 输出里记录的旧盘路径改写到当前快照位置


def remap(path):
    if path.startswith(OLD_PREFIX):
        return NEW_PREFIX + path[len(OLD_PREFIX):]
    return path


def load_ssk(project):
    path = os.path.join(SSK_DIR, f"{project}_output.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_via_ssk(ssk_data, test_class, test_name):
    if ssk_data is None:
        return None, "json_missing"
    simple_class = (test_class or "").split(".")[-1]
    candidates = [m for m in ssk_data if m.get("methodName") == test_name
                  and (not simple_class or f"/{simple_class}.java" in m.get("filePath", ""))]
    if len(candidates) > 1:
        # 优先挑带 MethodSource 注解的那个，消掉大部分"同名字撞了"的歧义
        ms_candidates = [c for c in candidates if "MethodSource" in c.get("annotations", [])]
        if len(ms_candidates) == 1:
            candidates = ms_candidates
    if len(candidates) == 1:
        return remap(candidates[0]["filePath"]), None
    if len(candidates) > 1:
        return None, f"ambiguous:{len(candidates)}"
    return None, "not_found_in_ssk"


def resolve_via_walk(project, fqcn, file_index):
    if fqcn is None:
        return None, "no_fqcn"
    parts = fqcn.split(".")
    simple = parts[-1]
    candidates = file_index.get(simple, [])
    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        pkg_path = "/".join(parts[:-1])
        for c in candidates:
            if pkg_path and pkg_path.replace(".", "/") in c.replace(os.sep, "/"):
                return c, None
        return candidates[0], f"ambiguous:{len(candidates)}"
    return None, "file_not_found"


def main():
    sample_rows = load_pilot_sample()
    print(f"pilot MethodSource 样本行数: {len(sample_rows)}", file=sys.stderr)

    ssk_cache = {}
    file_index_cache = {}
    manifest = []
    problems = []
    n_from_ssk = 0
    n_from_walk = 0

    for row in sample_rows:
        project = row["project"]
        if project not in ssk_cache:
            ssk_cache[project] = load_ssk(project)

        test_file, note = resolve_via_ssk(ssk_cache[project], row["test_class"], row["test_name"])
        if test_file is not None:
            n_from_ssk += 1
        else:
            if project not in file_index_cache:
                file_index_cache[project] = build_file_index(project)
            test_file, note2 = resolve_via_walk(project, row["test_class"], file_index_cache[project])
            if test_file is not None:
                n_from_walk += 1
                note = None
            else:
                note = f"ssk:{note};walk:{note2}"

        entry = {
            "project": project,
            "project_root": os.path.join(AAA_ROOT, project),
            "test_class": row["test_class"] or "",
            "test_name": row["test_name"],
            "test_source_file": test_file or "",
        }
        manifest.append(entry)
        if note:
            problems.append({**entry, "reason": note})

    out_csv = os.path.join(OUT_DIR, "cognitive_targets_v2.csv")
    fields = ["project", "project_root", "test_class", "test_name", "test_source_file"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(manifest)

    prob_csv = os.path.join(OUT_DIR, "cognitive_targets_v2_problems.csv")
    with open(prob_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["reason"])
        w.writeheader()
        for p in problems:
            w.writerow({k: p.get(k, "") for k in fields + ["reason"]})

    print(f"manifest: {out_csv} ({len(manifest)} rows)")
    print(f"  来自 parser_result_ssk 直接命中: {n_from_ssk}")
    print(f"  ssk 没命中、靠扫文件系统救回来的: {n_from_walk}")
    print(f"  两边都没解决: {len(problems)}")
    print(f"problems: {prob_csv}")


if __name__ == "__main__":
    main()
