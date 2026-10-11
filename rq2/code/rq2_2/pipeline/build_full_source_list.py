#!/usr/bin/env python3
"""通用的全量 PT 清单生成器：给定若干 parameter source 类型，输出
project,file_path,test_name,parameter_source（每个 test × 每种命中的 source 一行）。

用法: build_full_source_list.py <输出 csv> <SourceType>[,<SourceType>...]
例:   build_full_source_list.py full_minor/minor_all.csv \
          ArgumentsSource,FieldSource,CsvFileSource,NullSource,EmptySource,NullAndEmptySource

项目集合 = all_47_projects.txt 减去 excluded_projects.txt，与 build_full_methodsource_list.py 一致。
之所以要这个脚本：minor_all.csv 原本是手工拼的，camel/storm 补进来之后没法复现。
"""

# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv, json, os, sys


def main(out_path, wanted):
    skip = {l.strip() for l in open(_paths.RQ3_EXCLUDED) if l.strip()}
    rows, per = [], {}
    for p in [l.strip() for l in open(_paths.RQ3_PROJECTS) if l.strip()]:
        if p in skip:
            continue
        f = os.path.join(_paths.PARSER_SSK, f"{p}_output.json")
        if not os.path.exists(f):
            continue
        n = 0
        for m in json.load(open(f)):
            # 一个 test 可能挂多个 @…Source（如 @NullSource + @ValueSource），各自成行。
            for s in m.get("parameterSources") or []:
                st = s.get("sourceType")
                if st in wanted:
                    rows.append({"project": p, "file_path": m["filePath"],
                                 "test_name": m["methodName"], "parameter_source": st})
                    n += 1
        per[p] = n
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["project", "file_path", "test_name", "parameter_source"])
        w.writeheader(); w.writerows(rows)
    print(f"{len([k for k,v in per.items() if v])} projects, {len(rows)} rows -> {out_path}")
    import collections
    print(collections.Counter(r["parameter_source"] for r in rows))

if __name__ == "__main__":
    main(sys.argv[1], set(sys.argv[2].split(",")))
