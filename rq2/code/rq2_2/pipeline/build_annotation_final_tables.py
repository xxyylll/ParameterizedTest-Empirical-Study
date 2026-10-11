#!/usr/bin/env python3
"""把 ValueSource / CsvSource / EnumSource 的 *_raw.csv 以及 ArgumentsSource/FieldSource 的
rq22_methodsource_all.csv 转成交付表 rq22_<source>_all.csv。

之前这一步只散落在 run_full_valuesource.sh（排除名单还硬编码着 hive/storm/camel）和若干
临时命令里，run_full_annotation_sources.sh / run_full_minor_providers.sh 都只跑到 raw 为止，
导致把 camel 加回来重算之后交付表仍然是旧的。这里统一成一个可复现的步骤。

用法: build_annotation_final_tables.py [ValueSource CsvSource EnumSource Minor]
"""

# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv, os, sys
from collections import Counter

HERE = _paths.RQ22_WORK   # full_<source>/ 各目录所在的中间产物根目录

# 每种 source 的交付表字段（raw 里的列名 → 交付表列名相同，note 转成 status）
SPECS = {
    "ValueSource": dict(
        d="full_valuesource", raw="valuesource_raw.csv", out="rq22_valuesource_all.csv",
        fields=["project", "test_class", "test_name", "attribute", "construction", "dependency",
                "hits_production", "dependency_reason", "n_params", "n_sets", "n_constant_refs"]),
    "CsvSource": dict(
        d="full_csvsource", raw="csvsource_raw.csv", out="rq22_csvsource_all.csv",
        fields=["project", "test_class", "test_name", "form", "construction", "param_kinds",
                "dependency", "hits_production", "dependency_reason", "n_params", "n_sets",
                "n_columns", "n_constant_refs"]),
    "EnumSource": dict(
        d="full_enumsource", raw="enumsource_raw.csv", out="rq22_enumsource_all.csv",
        fields=["project", "test_class", "test_name", "enum_type", "enum_location", "dependency",
                "dependency_reason", "enum_structure", "enum_structure_reason", "n_params",
                "n_sets", "n_sets_status", "n_enum_constants", "names_mode"]),
}


def build_simple(name):
    s = SPECS[name]
    rows = list(csv.DictReader(open(os.path.join(HERE, s["d"], s["raw"]))))
    fields = s["fields"] + ["status"]
    out = [{**{k: r.get(k, "") for k in s["fields"]},
            "status": "OK" if r.get("note", "") == "" else r["note"]} for r in rows]
    path = os.path.join(HERE, s["d"], s["out"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    ok = [r for r in out if r["status"] == "OK"]
    print(f'{name}: {len(out)} 行, OK {len(ok)}, {len({r["project"] for r in out})} 个项目 -> {s["out"]}')
    if "construction" in s["fields"]:
        print("   construction:", Counter(r["construction"] for r in ok))
    print("   dependency:", Counter(r["dependency"] for r in ok))
    return out


def build_minor():
    """ArgumentsSource/FieldSource：build_final_table.py 写死输出 rq22_methodsource_all.csv，
    这里给它补上 source 列（来自 minor_all.csv）并改名成交付表。"""
    d = os.path.join(HERE, "full_minor")
    src_of = {}
    for r in csv.DictReader(open(os.path.join(d, "minor_all.csv"))):
        cls = r["file_path"]
        cls = cls[cls.index("/src/test/java/") + 15:-5].replace("/", ".") if "/src/test/java/" in cls else ""
        src_of[(r["project"], cls, r["test_name"])] = r["parameter_source"]
    rows = list(csv.DictReader(open(os.path.join(d, "rq22_methodsource_all.csv"))))
    fields = ["source"] + [k for k in rows[0].keys()]
    out = []
    for r in rows:
        out.append({"source": src_of.get((r["project"], r["test_class"], r["test_name"]), ""), **r})
    path = os.path.join(d, "rq22_argumentssource_fieldsource_all.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    print(f'Minor: {len(out)} 行, {len({r["project"] for r in out})} 个项目 -> rq22_argumentssource_fieldsource_all.csv')
    print("   source:", Counter(r["source"] for r in out))
    return out


if __name__ == "__main__":
    want = sys.argv[1:] or ["ValueSource", "CsvSource", "EnumSource", "Minor"]
    for w in want:
        build_minor() if w == "Minor" else build_simple(w)
