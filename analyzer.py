#!/usr/bin/env python3
import os, re, json, glob, csv
from datetime import datetime

PARSER_ROOT = "parser_result"
SELECTED_DIR = "selected_releases"
OUT_DIR = "trend_result"

SRC_PATS = {
    "methodsource": re.compile(r"@MethodSource\b"),
    "csvsource": re.compile(r"@CsvSource\b"),
    "csvfilesource": re.compile(r"@CsvFileSource\b"),
    "valuesource": re.compile(r"@ValueSource\b"),
    "enumsource": re.compile(r"@EnumSource\b"),
    "argumentssource": re.compile(r"@ArgumentsSource\b"),
}

def load_tag2date(project):
    """从 select_<project>.txt 读出 tag->date 映射"""
    m = {}
    p = os.path.join(SELECTED_DIR, f"select_{project}.txt")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                parts = ln.split()
                if len(parts) >= 2:
                    m[parts[0]] = parts[1]
    return m

def analyze_one_project(project):
    tag2date = load_tag2date(project)

    rows = []
    # parser_result/<project>/<safe_tag>/output.json
    for out_path in sorted(glob.glob(os.path.join(PARSER_ROOT, project, "*", "output.json"))):
        safe_tag = os.path.basename(os.path.dirname(out_path))
        # 还原真实 tag（选文件里的 tag 有斜杠，用 safe 替换判断）
        tag = next((t for t in tag2date if t.replace("/", "_") == safe_tag), safe_tag)
        date = tag2date.get(tag, "")

        try:
            data = json.load(open(out_path, encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []

        total, param = 0, 0
        src_counts = {k: 0 for k in SRC_PATS}

        for rec in data:
            total += 1
            annos = [a.strip() for a in (rec.get("annotations") or [])]
            src = rec.get("sourceCode", "") or ""

            # 统计 *Source 出现次数（方法级）
            for k, pat in SRC_PATS.items():
                if pat.search(src):
                    src_counts[k] += 1

            # find @ParameterizedTest
            if any(a.lower() == "parameterizedtest" for a in annos) \
               or any(pat.search(src) for pat in SRC_PATS.values()):
                param += 1

        share = (param / total) if total else 0.0
        rows.append({
            "project": project,
            "release": tag,
            "date": date,
            "total_tests": total,
            "parameterized_tests": param,
            "param_share": round(share, 6),
            **src_counts,
            "json_path": out_path
        })

    # 按日期排序（没有日期就排前）
    def key(r):
        try:
            return (datetime.strptime(r["date"], "%Y-%m-%d"), r["release"])
        except Exception:
            return (datetime.min, r["release"])
    rows.sort(key=key)

    # 写 CSV
    os.makedirs(OUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUT_DIR, f"{project}_summary.csv")
    cols = ["project","release","date","total_tests","parameterized_tests","param_share",
            "methodsource","csvsource","csvfilesource","valuesource","enumsource","argumentssource","json_path"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

    # 画占比趋势（纵轴是百分比）
    try:
        import matplotlib.pyplot as plt
        xs = [f'{r["release"]}\n{r["date"]}' if r["date"] else r["release"] for r in rows]
        ys = [r["param_share"] * 100 for r in rows]
        if xs:
            plt.figure(figsize=(10, 4))
            plt.plot(xs, ys, marker="o")
            plt.title(f"{project}: Parameterized Tests Share")
            plt.ylabel("%"); plt.xlabel("release (date)")
            plt.xticks(rotation=60, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(OUT_DIR, f"{project}_param_share_trend.png"), dpi=180)
            plt.close()
    except Exception as e:
        print(f"[plot skipped] {project}: {e}")

    return csv_path

def main():
    # 自动发现项目：parser_result/<project>/
    projects = [d for d in os.listdir(PARSER_ROOT)
                if os.path.isdir(os.path.join(PARSER_ROOT, d))]
    if not projects:
        print("no projects under parser_result/"); return
    for p in sorted(projects):
        out = analyze_one_project(p)
        print(f"✓ {p} -> {out}")

if __name__ == "__main__":
    main()
