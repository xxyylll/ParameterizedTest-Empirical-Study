#!/usr/bin/env python3
import os, re, json, glob, csv, argparse
from pathlib import Path

DEFAULT_PARSER_ROOT = "parser_result"
DEFAULT_OUT_CSV = "trend_result/pt_summary.csv"

def load_json_records(path):
    """Return (records_list, meta_dict). If parser wrote wrapped JSON, use it."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return [], {}
    if isinstance(data, dict) and "records" in data:
        meta = data.get("meta") or {}
        records = data.get("records") or []
        return records, meta
    if isinstance(data, list):
        return data, {}
    return [], {}

def compute_stats(records):
    total = 0
    junit4_pt = 0
    junit5_pt = 0
    for rec in records:
        total += 1
        annos = [a.strip() for a in (rec.get("annotations") or [])]
        if "Test" in annos and "RunWith(Parameterized.class)" in annos:
            junit4_pt += 1
        elif "ParameterizedTest" in annos:
            junit5_pt += 1
    pt_total = junit4_pt + junit5_pt
    pt_share = (pt_total / total) if total else 0.0
    return total, pt_total, junit4_pt, junit5_pt, round(pt_share, 6)

def compute_flavor_breakdown(records):
    j4_total = j5_total = j4_param = j5_param = 0
    for r in records:
        flavor = (r.get("junit") or "").strip().lower()   # 只读 parser 的字段
        annos = [a.strip() for a in (r.get("annotations") or [])]
        if flavor == "junit4":
            j4_total += 1
            if "RunWith(Parameterized.class)" in annos:
                j4_param += 1
        elif flavor == "junit5":
            j5_total += 1
            if "ParameterizedTest" in annos:
                j5_param += 1
    j4_share = (j4_param / j4_total) if j4_total else 0.0
    j5_share = (j5_param / j5_total) if j5_total else 0.0
    return j4_total, j5_total, round(j4_share, 6), round(j5_share, 6)

def infer_from_filename(path, project_hint=None):
    """
    Parse parser_result/<project>_<safe_tag>_output.json or parser_result/<project>_output.json
    -> (project, safe_tag). If only <project>_output.json is present, safe_tag will be empty.
    """
    base = os.path.basename(path)
    if not base.endswith("_output.json"):
        return (project_hint or ""), ""
    core = base[:-len("_output.json")]
    # If exactly project (no underscore): pdfbox_output.json -> core == 'pdfbox'
    if project_hint and core == project_hint:
        return project_hint, ""
    # If core starts with project_hint + '_', return rest as tag
    if project_hint and core.startswith(project_hint + "_"):
        return project_hint, core[len(project_hint) + 1:]
    # generic split: take first '_' as separator, but allow no separator
    i = core.find("_")
    if i == -1:
        return core, ""
    return core[:i], core[i + 1:]

def ensure_csv_header(out_csv, header):
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not out_path.exists():
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=header).writeheader()

def append_rows(out_csv, rows, header):
    if not rows:
        return
    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        for r in rows:
            w.writerow(r)

def main():
    ap = argparse.ArgumentParser(
        description="Append PT summary rows to a single CSV from parser_result/*_output.json files."
    )
    ap.add_argument("--parser-root", default=DEFAULT_PARSER_ROOT, help="Where parser JSON files live")
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV, help="CSV path to append rows")
    ap.add_argument("--project", help="Only process this project (expects files like parser_result/<project>_*_output.json)")
    args = ap.parse_args()

    parser_root = Path(args.parser_root)
    if args.project:
        pattern = str(parser_root / f"{args.project}_output.json")  # exact match for project
    else:
        pattern = str(parser_root / "*_output.json")  # any project

    files = sorted(glob.glob(pattern))
    if not files:
        print(f"[INFO] no files matched: {pattern}")
        return

    header = ["project","date","total_tests","pt_total","junit4_pt","junit5_pt","pt_share","junit4_total","junit5_total","junit4_param_share","junit5_param_share"]
    ensure_csv_header(args.out_csv, header)

    out_rows = []
    for path in files:
        records, meta = load_json_records(path)

        # Extract project from meta or filename
        project = meta.get("project")
        date = meta.get("release_date", "")

        # If date missing, use file modification time as ISO date fallback
        if not date:
            try:
                mtime = Path(path).stat().st_mtime
                from datetime import datetime
                date = datetime.utcfromtimestamp(mtime).isoformat()
            except Exception:
                date = ""

        if not project:
            proj_from_name, tag_from_name = infer_from_filename(path, project_hint=args.project)
            project = project or proj_from_name or ""

        total, pt_total, junit4_pt, junit5_pt, pt_share = compute_stats(records)
        j4_total, j5_total, j4_share, j5_share = compute_flavor_breakdown(records)
 

        out_rows.append({
            "project": project,
            "date": date,
            "total_tests": total,
            "pt_total": pt_total,
            "junit4_pt": junit4_pt,
            "junit5_pt": junit5_pt,
            "pt_share": pt_share,
            "junit4_total": j4_total,
            "junit5_total": j5_total,
            "junit4_param_share": j4_share,
            "junit5_param_share": j5_share,
        })

    append_rows(args.out_csv, out_rows, header)
    print(f"✓ appended {len(out_rows)} row(s) to {args.out_csv}")

if __name__ == "__main__":
    main()
