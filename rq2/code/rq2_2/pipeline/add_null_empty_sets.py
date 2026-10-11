#!/usr/bin/env python3
"""@NullSource(+1) / @EmptySource(+1) / @NullAndEmptySource(+2) 并入所搭配主 source 的表：加 extra_null_empty_sets、n_sets_total 两列。
单独使用（没有主 source）的另出 full_minor/rq22_null_empty_standalone.csv。"""

# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv, json, os
from collections import Counter
SKIP = {l.strip() for l in open(_paths.RQ3_EXCLUDED) if l.strip()}; HERE = _paths.RQ22_WORK
EXTRA = {"NullSource": 1, "EmptySource": 1, "NullAndEmptySource": 2}
extra = {}; standalone = []
for p in [l.strip() for l in open(_paths.RQ3_PROJECTS) if l.strip() and l.strip() not in SKIP]:
    f = os.path.join(_paths.PARSER_SSK, f"{p}_output.json")
    if not os.path.exists(f): continue
    for m in json.load(open(f)):
        sts = [ps.get("sourceType") for ps in (m.get("parameterSources") or []) if isinstance(ps, dict)]
        add = sum(EXTRA[s] for s in sts if s in EXTRA); which = "+".join(s for s in sts if s in EXTRA)
        if not add: continue
        mains = [s for s in sts if s not in EXTRA]
        if mains: extra[(p, m["methodName"], m["filePath"].split("/")[-1][:-5])] = (add, which)
        else: standalone.append({"project": p, "test_class": m["filePath"].split("/")[-1][:-5], "test_name": m["methodName"], "sources": which,
                                 "construction": "None(annotation)", "dependency": "L0", "n_params": 1, "n_sets": add})
hit = Counter()
for name, path in [("valuesource", f"{HERE}/full_valuesource/rq22_valuesource_all.csv"), ("enumsource", f"{HERE}/full_enumsource/rq22_enumsource_all.csv"),
                   ("csvsource", f"{HERE}/full_csvsource/rq22_csvsource_all.csv")]:
    rows = list(csv.DictReader(open(path))); 
    for r in rows:
        k = (r["project"], r["test_name"], r["test_class"].split(".")[-1])
        add, which = extra.get(k, (0, ""))
        if not add and not r["test_class"]:   # src/integration/java 这类没解析出类名的行：退到 (project, test_name)
            for (pp, tt, cc), v in extra.items():
                if pp == r["project"] and tt == r["test_name"]: add, which = v; break
        r["extra_null_empty_sets"] = add; r["extra_null_empty_from"] = which
        r["n_sets_total"] = (int(r["n_sets"]) + add) if r.get("n_sets", "") != "" else ""
        if add: hit[name] += 1
    fields = list(rows[0].keys())
    with open(path, "w", newline="") as f: w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
with open(f"{HERE}/full_minor/rq22_null_empty_standalone.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(standalone[0].keys())); w.writeheader(); w.writerows(standalone)
print("merged into:", dict(hit), "; standalone:", len(standalone), [(s["project"], s["test_class"], s["sources"]) for s in standalone])
