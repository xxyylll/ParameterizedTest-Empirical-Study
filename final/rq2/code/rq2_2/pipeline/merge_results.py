#!/usr/bin/env python3
"""合并 helper depth 和 cognitive complexity 两条线的结果，按 (project, test_class, test_name)
汇总（一个测试有多个 @MethodSource provider 时，cognitive_complexity 取各 provider 之和，
跟 helper depth 的池化口径一致）。"""

# 向上找到 final/（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv
from collections import defaultdict

import os
OUT_DIR = os.environ.get("RQ22_OUT_DIR", _paths.RQ22_WORK)

depth_rows = {(r["project"], r["test_class"], r["test_name"]): r
              for r in csv.DictReader(open(f"{OUT_DIR}/pt_methodsource_helper_depth.csv"))}

# 全量 379 条 pilot 样本作为基准（cognitive complexity v2 不再卡在 helper-depth 那 312 条上）
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_helper_depth import load_pilot_sample
all_keys = [(r["project"], r["test_class"] or "", r["test_name"]) for r in load_pilot_sample()]

cc_sum = defaultdict(int)
cc_status = defaultdict(list)
for r in csv.DictReader(open(f"{OUT_DIR}/cognitive_complexity_v2_raw.csv")):
    key = (r["project"], r["test_class"], r["test_name"])
    if r["transformation_complexity"] != "":
        cc_sum[key] += int(r["transformation_complexity"])
    cc_status[key].append(r["note"] or "OK")

# dependency_v2（追到生产代码/API 边界为止那版）也并进来，跟 structure 一张表看
dep_rows = {(r["project"], r["test_class"], r["test_name"]): r
            for r in csv.DictReader(open(f"{OUT_DIR}/dependency_v2.csv"))}

depth_fields = ["max_depth_test", "distinct_helpers_test", "total_calls_test",
                "max_depth_prod", "distinct_helpers_prod", "total_calls_prod", "unresolved_count"]

# 解析质量诊断列：这些是判断"这一行的数字能不能信"的依据，必须带到最终表里，
# 否则下游（人工核对/统计）看不到 traversal 有没有缺口就会当成干净数据用。
DIAG_FIELDS = ["has_unresolved", "unresolved_types", "has_unknown_tag", "unknown_tag_count",
               "unknown_tag_examples", "recursive_count", "method_ref_count",
               "method_ref_unresolved_scope_count", "traversal_may_be_incomplete"]

DEP_FIELDS = ["dependency", "hits_production", "provider_declaring_class",
              "provider_location_reason", "n_test_scope_helpers", "dependency_aaa", "dependency_src"]

# construction（源码侧）也并进来
con_rows = {(r["project"], r["test_class"], r["test_name"]): r
            for r in csv.DictReader(open(f"{OUT_DIR}/construction_dependency_raw.csv"))}

DEP_FIELDS = DEP_FIELDS + ["status"]   # dependency_v2 的 status（OK / EXTERNAL_PROVIDER / AMBIGUOUS… / json_not_found）

fields = (["project", "test_class", "test_name",
           "transformation_complexity", "transformation_status", "construction", "construction_reason"]
          + [("dependency_status" if k == "status" else k) for k in DEP_FIELDS] + depth_fields + ["helper_depth_status"] + DIAG_FIELDS)

out = []
for key in all_keys:
    statuses = cc_status.get(key, ["NO_PROVIDER_TARGET"])
    status = "OK" if all(s == "OK" for s in statuses) else ";".join(sorted(set(statuses)))
    drow = depth_rows.get(key)
    deprow = dep_rows.get(key, {})
    out.append({
        "project": key[0], "test_class": key[1], "test_name": key[2],
        "transformation_complexity": cc_sum.get(key, "") if key in cc_status else "",
        "transformation_status": status,
        "construction": con_rows.get(key, {}).get("construction", ""),
        "construction_reason": con_rows.get(key, {}).get("construction_reason", ""),
        **{("dependency_status" if k == "status" else k): deprow.get(k, "") for k in DEP_FIELDS},
        **({k: drow[k] for k in depth_fields} if drow else {k: "" for k in depth_fields}),
        # ⑥: JDK/第三方 provider 不是"没匹配上"，单列 EXTERNAL_PROVIDER（三个维度 N/A）
        "helper_depth_status": "OK" if drow else (
            "EXTERNAL_PROVIDER" if deprow.get("status") == "EXTERNAL_PROVIDER" else "NOT_MATCHED_TO_AAA"),
        **({k: drow.get(k, "") for k in DIAG_FIELDS} if drow else {k: "" for k in DIAG_FIELDS}),
    })

with open(f"{OUT_DIR}/pt_methodsource_structure.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out)

print(f"merged: {OUT_DIR}/pt_methodsource_structure.csv ({len(out)} rows)")
