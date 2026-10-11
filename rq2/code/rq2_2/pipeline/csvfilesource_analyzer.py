#!/usr/bin/env python3
"""@CsvFileSource（44 项目）：construction=File、dependency=File；arity = n_params × n_sets（资源文件行数，减 numLinesToSkip、空行、# 注释；
多个文件求和），n_columns 取首个数据行按 delimiter 切。资源定位：resources 是 classpath 路径——相对路径先在测试类包目录下的
src/test/resources/<pkg>/ 找，再 src/test/resources/ 根；以 / 开头的直接接在资源根后；files 相对项目根。
输出 full_csvfilesource/rq22_csvfilesource_all.csv。"""

# 向上找到 仓库根（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv, json, os, re
from collections import Counter
SKIP = {l.strip() for l in open(_paths.RQ3_EXCLUDED) if l.strip()}
OUT = os.path.join(_paths.RQ22_WORK, "full_csvfilesource"); os.makedirs(OUT, exist_ok=True)
NEW = _paths.APACHE_PROJECTS.rstrip("/") + "/"; OLD = "/Volumes/SSK Drive/apache-projects/"

def attr(sc, name):
    m = re.search(name + r"\s*=\s*(\{[^}]*\}|\"(?:[^\"\\\\]|\\\\.)*\"|'[^']*'|[\w.]+)", sc, re.S)
    return m.group(1) if m else None

def str_list(v):
    return re.findall(r'"((?:[^"\\\\]|\\\\.)*)"', v or "")

def locate(resource, test_file, module_root):
    """classpath 资源 → 文件路径。"""
    cands = []
    m = re.search(r"(.*/src/(?:test|it))/(?:java/)?(.*)/[^/]+\.java$", test_file)
    if m:
        base, pkgdir = m.group(1), m.group(2)
        if resource.startswith("/"):
            cands.append(os.path.join(base, "resources", resource.lstrip("/")))
        else:
            cands.append(os.path.join(base, "resources", pkgdir, resource))
            cands.append(os.path.join(base, "resources", resource))
            cands.append(os.path.join(base, "java", pkgdir, resource))
    for c in cands:
        if os.path.isfile(c): return c
    return None

def count_rows(path, skip, delimiter):
    n = 0; first = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i < skip: continue
            t = line.strip()
            if not t or t.startswith("#"): continue
            n += 1
            if first is None: first = t
    cols = None
    if first is not None:
        cols = len(next(csv.reader([first], delimiter=delimiter))) if len(delimiter) == 1 else len(first.split(delimiter))
    return n, cols

def n_params(src, name):
    m = re.search(r"\b" + re.escape(name) + r"\s*\(([^)]*)\)", src)
    if not m: return None
    ps = [p.strip() for p in re.split(r",(?![^<]*>)", m.group(1)) if p.strip()]
    return sum(1 for p in ps if not re.search(r"\b(TestInfo|TestReporter|RepetitionInfo)\b", p))

rows = []
for p in [l.strip() for l in open(_paths.RQ3_PROJECTS) if l.strip() and l.strip() not in SKIP]:
    f = os.path.join(_paths.PARSER_SSK, f"{p}_output.json")
    if not os.path.exists(f): continue
    for m in json.load(open(f)):
        for ps in m.get("parameterSources") or []:
            if not (isinstance(ps, dict) and ps.get("sourceType") == "CsvFileSource"): continue
            sc = ps.get("sourceCode", ""); fp = m["filePath"].replace(OLD, NEW)
            fq = re.search(r"src/(?:test|it)/(?:java/)?(.+)\.java$", fp); test_class = fq.group(1).replace("/", ".") if fq else ""
            resources = str_list(attr(sc, "resources")) or str_list(attr(sc, "value")); files = str_list(attr(sc, "files"))
            d = attr(sc, "delimiterString"); delimiter = str_list(d)[0] if d else (re.search(r"delimiter\s*=\s*'(.)'", sc).group(1) if re.search(r"delimiter\s*=\s*'(.)'", sc) else ",")
            skip = int(re.search(r"numLinesToSkip\s*=\s*(\d+)", sc).group(1)) if re.search(r"numLinesToSkip\s*=\s*(\d+)", sc) else 0
            headers = "useHeadersInDisplayName = true" in sc.replace(" ", "").replace("=", " = ")
            total = 0; cols = None; found = []; missing = []
            for r in resources:
                path = locate(r, fp, None)
                if path: n, c = count_rows(path, skip, delimiter); total += n - (1 if headers and n else 0); cols = cols or c; found.append(os.path.relpath(path, NEW))
                else: missing.append(r)
            for r in files:
                path = os.path.join(NEW, p, r)
                if os.path.isfile(path): n, c = count_rows(path, skip, delimiter); total += n - (1 if headers and n else 0); cols = cols or c; found.append(os.path.relpath(path, NEW))
                else: missing.append(r)
            src = open(fp, encoding="utf-8", errors="ignore").read() if os.path.isfile(fp) else ""
            rows.append({"project": p, "test_class": test_class, "test_name": m["methodName"], "construction": "File", "dependency": "File",
                         "resources": ";".join(resources + files), "resolved_files": ";".join(found), "n_files": len(resources) + len(files),
                         "n_params": n_params(src, m["methodName"]) if src else "", "n_sets": total if not missing else "", "n_columns": cols if cols is not None else "",
                         "n_sets_status": "EXACT" if not missing else "FILE_NOT_FOUND:" + ";".join(missing), "delimiter": delimiter, "num_lines_to_skip": skip,
                         "status": "OK" if src else "TEST_FILE_UNKNOWN"})
with open(os.path.join(OUT, "rq22_csvfilesource_all.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ok = [r for r in rows if r["status"] == "OK"]
print(len(rows), "rows; status", Counter(r["status"] for r in rows), "; n_sets_status", Counter(r["n_sets_status"].split(":")[0] for r in ok))
ns = [int(r["n_sets"]) for r in ok if r["n_sets"] != ""]
import statistics
if ns: print("n_sets median", statistics.median(ns), "p90", sorted(ns)[int(len(ns) * .9)], "max", max(ns), "; n_params", Counter(r["n_params"] for r in ok), "; n_columns", Counter(r["n_columns"] for r in ok).most_common(5))
