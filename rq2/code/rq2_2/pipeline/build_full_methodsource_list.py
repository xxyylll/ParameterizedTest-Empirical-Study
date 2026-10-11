#!/usr/bin/env python3
"""全量 MethodSource PT 清单（除 hive/storm/camel 外的 44 个项目），格式与 pt_random_sampled_methods_v2.csv 一致：
project,file_path,test_name,parameter_source。来源 parser_result_ssk/<project>_output.json（@Disabled 也纳入）。
输出 full/methodsource_all.csv。"""

# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv, json, os
OUT = os.path.join(_paths.RQ22_WORK, "full")
SKIP = {l.strip() for l in open(_paths.RQ3_EXCLUDED) if l.strip()}
os.makedirs(OUT, exist_ok=True)
rows = []; per = {}
for p in [l.strip() for l in open(_paths.RQ3_PROJECTS) if l.strip()]:
    if p in SKIP: continue
    f = os.path.join(_paths.PARSER_SSK, f"{p}_output.json")
    if not os.path.exists(f): continue
    n = 0
    for m in json.load(open(f)):
        if "MethodSource" not in str(m.get("parameterSources")): continue
        rows.append({"project": p, "file_path": m["filePath"], "test_name": m["methodName"], "parameter_source": "MethodSource"}); n += 1
    per[p] = n
with open(os.path.join(OUT, "methodsource_all.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["project", "file_path", "test_name", "parameter_source"]); w.writeheader(); w.writerows(rows)
print(len(per), "projects", len(rows), "MethodSource PTs"); print(sorted(per.items(), key=lambda x: -x[1])[:10])
