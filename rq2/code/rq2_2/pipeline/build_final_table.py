#!/usr/bin/env python3
"""把 full/ 下三条线的结果并成一张交付表 full/rq22_methodsource_all.csv：
construction / dependency / structure(CC, max helper depth, distinct helpers) / arity(n_params × n_sets)。"""

# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv, os, sys
from collections import Counter
OUT = os.environ.get("RQ22_OUT_DIR", os.path.join(_paths.RQ22_WORK, "full"))
st = {(r["project"], r["test_class"], r["test_name"]): r for r in csv.DictReader(open(f"{OUT}/pt_methodsource_structure.csv"))}
cd = {(r["project"], r["test_class"], r["test_name"]): r for r in csv.DictReader(open(f"{OUT}/construction_dependency_raw.csv"))}
fields = ["project", "test_class", "test_name",
          "construction", "construction_reason",
          "dependency", "hits_production", "dependency_reason",
          "cognitive_complexity", "max_helper_depth_test", "distinct_helpers_test", "max_helper_depth_prod", "distinct_helpers_prod",
          "n_params", "n_sets", "n_sets_status", "n_sets_fail_reason",
          "status", "provider_declaring_class", "traversal_may_be_incomplete"]
rows = []
for k, r in st.items():
    c = cd.get(k, {})
    ok_cc = r["transformation_status"] == "OK"; ok_hd = r["helper_depth_status"] == "OK"
    if r["helper_depth_status"] == "EXTERNAL_PROVIDER": status = "EXTERNAL_PROVIDER"
    elif ok_cc and ok_hd: status = "OK"
    else: status = ";".join(x for x in [("" if ok_cc else "cc:" + r["transformation_status"]), ("" if ok_hd else "hd:" + r["helper_depth_status"])] if x)
    rows.append({
        "project": k[0], "test_class": k[1], "test_name": k[2],
        "construction": r.get("construction", ""), "construction_reason": r.get("construction_reason", ""),
        "dependency": r["dependency"], "hits_production": r["hits_production"], "dependency_reason": r["provider_location_reason"],
        "cognitive_complexity": r["transformation_complexity"],
        "max_helper_depth_test": r["max_depth_test"], "distinct_helpers_test": r["distinct_helpers_test"],
        "max_helper_depth_prod": r["max_depth_prod"], "distinct_helpers_prod": r["distinct_helpers_prod"],
        "n_params": c.get("n_params_effective", ""), "n_sets": c.get("n_sets", ""), "n_sets_status": c.get("n_sets_status", ""), "n_sets_fail_reason": c.get("n_sets_fail_reason", ""),
        "status": status, "provider_declaring_class": r["provider_declaring_class"],
        "traversal_may_be_incomplete": r.get("traversal_may_be_incomplete", ""),
    })
with open(f"{OUT}/rq22_methodsource_all.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
ok = [r for r in rows if r["status"] == "OK"]
print(f"rows {len(rows)}  OK {len(ok)}  status: {Counter(r['status'].split(':')[0] if r['status']!='OK' else 'OK' for r in rows)}")
print("construction:", Counter(r["construction"] for r in ok))
print("dependency:", Counter(r["dependency"] for r in ok))
print("hits_production:", Counter(r["hits_production"] for r in ok))
import statistics
def num(col): return [int(r[col]) for r in ok if (r[col] or "") != ""]
for col in ["cognitive_complexity", "max_helper_depth_test", "distinct_helpers_test", "max_helper_depth_prod", "distinct_helpers_prod", "n_params", "n_sets"]:
    v = num(col); print(f"{col:24s} n={len(v)} mean={statistics.mean(v):.2f} median={statistics.median(v)} p90={sorted(v)[int(len(v)*.9)]} max={max(v)} >0:{sum(1 for x in v if x>0)}")
print("n_sets_status:", Counter(r["n_sets_status"] for r in ok))
